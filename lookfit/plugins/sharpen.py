"""Plugin 3: After Effects Sharpen (3x3 fixed small neighbourhood; kernel fitted, not known)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.optimize import minimize_scalar

from lookfit.core.colour_spaces import luma_rec709
from lookfit.core.metrics import compute_ssim, edge_profile_metrics
from lookfit.plugins.base import (
    ContextOrList,
    Evidence,
    FitReport,
    ImageOrList,
    ParamSpec,
    Plugin,
    normalize_pair_inputs,
)

KERNELS_3X3: Dict[str, np.ndarray] = {
    "cross4": np.array(
        [[0.0, 0.25, 0.0], [0.25, 0.0, 0.25], [0.0, 0.25, 0.0]],
        dtype=np.float32,
    ),
    "box8": np.array(
        [[0.125, 0.125, 0.125], [0.125, 0.0, 0.125], [0.125, 0.125, 0.125]],
        dtype=np.float32,
    ),
    "binomial3x3": (
        np.array([[1.0, 2.0, 1.0], [2.0, 4.0, 2.0], [1.0, 2.0, 1.0]], dtype=np.float32) / 16.0
    ),
}


def apply_small_blur(img: np.ndarray, kernel_name: str) -> np.ndarray:
    k = KERNELS_3X3[kernel_name]
    return cv2.filter2D(img.astype(np.float32), cv2.CV_32F, k, borderType=cv2.BORDER_REFLECT101)


class SharpenPlugin(Plugin):
    """After Effects Sharpen plugin (explicitly labelled 'fitted, not known' in every output)."""

    name = "sharpen"
    param_spec = [
        ParamSpec("k", 0.0, 0.0, 3.0, "gain", "dimensionless", "High-pass gain k in x + k*(x - Blur_small(x)) (fitted, not known)"),
        ParamSpec("kernel", "binomial3x3", None, None, "enum", "1_texel_3x3", "3x3 neighbourhood blur kernel: cross4, box8, binomial3x3 (fitted, not known)"),
        ParamSpec("channel_mode", "rgb", None, None, "enum", "categorical", "Apply high-pass per-channel ('rgb') or luminance ('luma') (fitted, not known)"),
        ParamSpec("amount_ae_est", 0.0, 0.0, 150.0, "ae_units", "dimensionless", "Estimated AE Sharpen slider proxy (~50*k; fitted, not known)"),
    ]

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        gain_ratios = []
        halo_diffs = []
        for r_im, t_im, pctx in items:
            rl = luma_rec709(r_im)
            tl = luma_rec709(t_im)
            hp_r = np.abs(rl - apply_small_blur(rl, "binomial3x3"))
            hp_t = np.abs(tl - apply_small_blur(tl, "binomial3x3"))
            em = pctx.masks.edge_mask
            if int(em.sum()) < 50:
                continue
            r_med = float(np.percentile(hp_r[em], 75))
            t_med = float(np.percentile(hp_t[em], 75))
            gain_ratios.append(t_med / max(r_med, 1e-4))
            ep = edge_profile_metrics(r_im, t_im, pctx.orig_ref_rgb if pctx.orig_ref_rgb is not None else r_im, pctx.masks.active_mask)
            halo_diffs.append(float(ep["halo_rmse_255"]))

        ratio = float(np.mean(gain_ratios)) if gain_ratios else 1.0
        h_rmse = float(np.mean(halo_diffs)) if halo_diffs else 0.0
        status = "present" if (ratio > 1.04 and h_rmse > 1.0) else ("weak" if ratio > 1.01 else "absent")
        score = max(0.0, (ratio - 1.0) * 10.0)
        return Evidence(
            plugin_name=self.name,
            status=status,
            score=score,
            notes=(
                f"3x3 fine-edge high-pass ratio tgt/ref={ratio:.3f}, edge-halo RMSE={h_rmse:.2f}/255 "
                f"(kernel model fitted, not known)."
            ),
            metrics={"hp3x3_ratio": ratio, "edge_halo_rmse_255": h_rmse},
            mask_of_interest=items[0][2].masks.edge_mask,
        )

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {
            "k": 0.0,
            "kernel": "binomial3x3",
            "channel_mode": "rgb",
            "amount_ae_est": 0.0,
            "model_note": "fitted, not known",
        }

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
        k = float(params.get("k", 0.0))
        if k <= 1e-6:
            return x.copy()
        kernel_name = str(params.get("kernel", "binomial3x3"))
        cmode = str(params.get("channel_mode", "rgb"))
        if cmode == "luma":
            xl = luma_rec709(x)
            diff = (xl - apply_small_blur(xl, kernel_name))[..., None]
            return np.clip(x + k * diff, 0.0, 1.0).astype(np.float32)
        blur = apply_small_blur(x, kernel_name)
        return np.clip(x + k * (x - blur), 0.0, 1.0).astype(np.float32)

    def loss(
        self,
        pred: ImageOrList,
        tgt: ImageOrList,
        ctx: ContextOrList = None,
        fold: Optional[int] = None,
        train: bool = False,
    ) -> float:
        items = normalize_pair_inputs(pred, tgt, ctx)
        losses = []
        for p_im, t_im, pctx in items:
            em = pctx.masks.edge_mask
            am = pctx.masks.active_mask
            if fold is not None:
                fm = (pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold)
                em = em & fm
                am = am & fm
            if int(em.sum()) < 30:
                continue
            # Zero-local-mean high-frequency detail error on edge_mask + flat speckle penalty
            pl = luma_rec709(p_im)
            tl = luma_rec709(t_im)
            p_hp = pl - cv2.GaussianBlur(pl, (0, 0), 2.5)
            t_hp = tl - cv2.GaussianBlur(tl, (0, 0), 2.5)
            edge_hp_rmse = float(np.sqrt(np.mean(((p_hp[em] - t_hp[em]) * 255.0) ** 2)))
            rgb_edge_rmse = float(np.sqrt(np.mean(((p_im[em] - t_im[em]) * 255.0) ** 2)))

            # Penalize unwanted noise amplification on flat areas
            flm = pctx.masks.flat_mask
            if fold is not None:
                flm = flm & fm
            flat_pen = 0.0
            if int(flm.sum()) > 50:
                flat_hp_rmse = float(np.sqrt(np.mean(((p_hp[flm] - t_hp[flm]) * 255.0) ** 2)))
                flat_pen = 0.35 * flat_hp_rmse

            losses.append(0.65 * edge_hp_rmse + 0.35 * rgb_edge_rmse + flat_pen)
        return float(np.mean(losses)) if losses else 0.0

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        n_folds = int(items[0][2].masks.block_folds.max()) + 1
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        best_cv = float("inf")
        best_params = self.initial_guess(ref_in, tgt, ctx)
        best_fold_after = list(fold_before)
        candidates_log = []

        for kname in ("cross4", "box8", "binomial3x3"):
            for cmode in ("rgb", "luma"):
                # Precompute detail arrays once per pair
                details = []
                for r_im in refs:
                    if cmode == "luma":
                        rl = luma_rec709(r_im)
                        details.append((rl - apply_small_blur(rl, kname))[..., None])
                    else:
                        details.append(r_im - apply_small_blur(r_im, kname))

                fold_k = []
                fold_losses = []
                for f in range(n_folds):
                    def _obj_tr(k_val: float) -> float:
                        preds = [np.clip(r_im + float(k_val) * d, 0.0, 1.0) for r_im, d in zip(refs, details)]
                        return self.loss(preds, tgts, ctxs, fold=f, train=True)

                    res = minimize_scalar(_obj_tr, bounds=(0.0, 3.0), method="bounded", options={"xatol": 1e-3})
                    kf = float(np.clip(res.x, 0.0, 3.0))
                    fold_k.append(kf)
                    preds_val = [np.clip(r_im + kf * d, 0.0, 1.0) for r_im, d in zip(refs, details)]
                    fold_losses.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

                mean_cv = float(np.mean(fold_losses))
                candidates_log.append({
                    "kernel": kname,
                    "channel_mode": cmode,
                    "mean_k": float(np.mean(fold_k)),
                    "held_out_cv_loss": mean_cv,
                })
                if mean_cv < best_cv:
                    best_cv = mean_cv
                    best_fold_after = fold_losses
                    # Fit k on all folds for this configuration
                    def _obj_full(k_val: float) -> float:
                        preds = [np.clip(r_im + float(k_val) * d, 0.0, 1.0) for r_im, d in zip(refs, details)]
                        return self.loss(preds, tgts, ctxs, fold=None, train=True)

                    res_full = minimize_scalar(_obj_full, bounds=(0.0, 3.0), method="bounded", options={"xatol": 5e-4})
                    k_full = float(np.clip(res_full.x, 0.0, 3.0))
                    # Note: for binomial3x3, x - B(x) has center weight 12/16 = 0.75 vs 1.0 for cross4/box8
                    ae_scale = 66.7 if kname == "binomial3x3" else 50.0
                    best_params = {
                        "k": k_full,
                        "kernel": kname,
                        "channel_mode": cmode,
                        "amount_ae_est": float(round(k_full * ae_scale, 2)),
                        "model_note": "fitted, not known",
                    }

        preds_after = [self.render(r_im, best_params) for r_im in refs]
        tr_after = self.loss(preds_after, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - best_cv) / max(ho_before, 1e-6)
        ssim_before = float(np.mean([compute_ssim(r, t, c.masks.edge_mask) for r, t, c in items]))
        ssim_after = float(np.mean([compute_ssim(p, t, c.masks.edge_mask) for p, (_, t, c) in zip(preds_after, items)]))

        accepted = (best_params["k"] > 0.02) and (best_cv < ho_before - 0.04) and (rel_gain > 0.008)
        report = FitReport(
            plugin_name=self.name,
            accepted_hint=accepted,
            train_loss_before=tr_before,
            train_loss_after=tr_after,
            held_out_loss_before=ho_before,
            held_out_loss_after=best_cv,
            held_out_rel_gain=rel_gain,
            fold_losses_before=fold_before,
            fold_losses_after=best_fold_after,
            notes=(
                f"3x3 Sharpen (fitted, not known): kernel={best_params['kernel']}, "
                f"channel_mode={best_params['channel_mode']}, k={best_params['k']:.4f} "
                f"(~AE amount {best_params['amount_ae_est']:.1f}). Edge SSIM {ssim_before:.4f} -> {ssim_after:.4f}."
            ),
            diagnostics={
                "candidates": candidates_log,
                "edge_ssim_before": ssim_before,
                "edge_ssim_after": ssim_after,
                "model_note": "fitted, not known",
            },
        )
        return best_params, report

    def glsl_taps(self, params: Dict[str, Any]) -> int:
        if float(params.get("k", 0.0)) <= 1e-6:
            return 0
        return 4 if params.get("kernel", "binomial3x3") == "cross4" else 8

    def to_glsl(self, params: Dict[str, Any]) -> str:
        k = float(params.get("k", 0.0))
        kname = str(params.get("kernel", "binomial3x3"))
        cmode = str(params.get("channel_mode", "rgb"))
        taps = self.glsl_taps(params)

        lines = [
            f"// --- Plugin: sharpen (fitted, not known; kernel={kname}, k={k:.5f}, {taps} neighbour taps) ---",
            "// Expects helper: vec3 msFetchGraded(vec2 uv);",
            "vec3 msApplySharpen(vec3 centerCol, vec2 uv, vec2 texelSize) {",
        ]
        if k <= 1e-6:
            lines.append("    return centerCol;")
            lines.append("}")
            return "\n".join(lines)

        lines.append("    vec3 n0 = msFetchGraded(uv + vec2(0.0, -texelSize.y));")
        lines.append("    vec3 n1 = msFetchGraded(uv + vec2(0.0,  texelSize.y));")
        lines.append("    vec3 n2 = msFetchGraded(uv + vec2(-texelSize.x, 0.0));")
        lines.append("    vec3 n3 = msFetchGraded(uv + vec2( texelSize.x, 0.0));")
        if kname == "cross4":
            lines.append("    vec3 blurSmall = 0.25 * (n0 + n1 + n2 + n3);")
        elif kname == "box8":
            lines.append("    vec3 d0 = msFetchGraded(uv + vec2(-texelSize.x, -texelSize.y));")
            lines.append("    vec3 d1 = msFetchGraded(uv + vec2( texelSize.x, -texelSize.y));")
            lines.append("    vec3 d2 = msFetchGraded(uv + vec2(-texelSize.x,  texelSize.y));")
            lines.append("    vec3 d3 = msFetchGraded(uv + vec2( texelSize.x,  texelSize.y));")
            lines.append("    vec3 blurSmall = 0.125 * (n0 + n1 + n2 + n3 + d0 + d1 + d2 + d3);")
        else:
            lines.append("    vec3 d0 = msFetchGraded(uv + vec2(-texelSize.x, -texelSize.y));")
            lines.append("    vec3 d1 = msFetchGraded(uv + vec2( texelSize.x, -texelSize.y));")
            lines.append("    vec3 d2 = msFetchGraded(uv + vec2(-texelSize.x,  texelSize.y));")
            lines.append("    vec3 d3 = msFetchGraded(uv + vec2( texelSize.x,  texelSize.y));")
            lines.append("    vec3 blurSmall = (4.0 * centerCol + 2.0 * (n0 + n1 + n2 + n3) + (d0 + d1 + d2 + d3)) / 16.0;")

        if cmode == "luma":
            lines.append("    vec3 lumaW = vec3(0.2126, 0.7152, 0.0722);")
            lines.append(f"    float dL = dot(centerCol - blurSmall, lumaW);")
            lines.append(f"    return clamp(centerCol + {k:.6f} * vec3(dL), 0.0, 1.0);")
        else:
            lines.append(f"    return clamp(centerCol + {k:.6f} * (centerCol - blurSmall), 0.0, 1.0);")
        lines.append("}")
        return "\n".join(lines)

    def describe(self, params: Dict[str, Any]) -> str:
        return (
            f"After Effects 3x3 Sharpen (fitted, not known): kernel='{params.get('kernel')}', "
            f"channel_mode='{params.get('channel_mode')}', gain k={float(params.get('k', 0.0)):.4f} "
            f"(estimated AE slider ~{float(params.get('amount_ae_est', 0.0)):.1f})."
        )
