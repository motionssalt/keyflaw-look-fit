"""Optional plugin: radial lateral R/B chromatic aberration (`uv_c = center + p * (1 + k_c * r2)`)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.optimize import minimize

from lookfit.plugins.base import (
    ContextOrList,
    Evidence,
    FitReport,
    ImageOrList,
    ParamSpec,
    Plugin,
    normalize_pair_inputs,
)


def _warp_channel_radial(ch: np.ndarray, k_rad: float, cx: float = 0.5, cy_top: float = 0.5) -> np.ndarray:
    if abs(k_rad) <= 1e-6:
        return ch
    h, w = ch.shape
    aspect = float(w) / max(float(h), 1.0)
    x_norm = ((np.arange(w, dtype=np.float32) + 0.5) / float(w))[None, :]
    y_top = ((np.arange(h, dtype=np.float32) + 0.5) / float(h))[:, None]
    px = x_norm - float(cx)
    py = y_top - float(cy_top)
    r2 = (px * aspect) ** 2 + py ** 2
    xs_u = np.clip(float(cx) + px * (1.0 + float(k_rad) * r2), 0.0, 1.0) * float(w) - 0.5
    ys_u = np.clip(float(cy_top) + py * (1.0 + float(k_rad) * r2), 0.0, 1.0) * float(h) - 0.5
    xs_map = np.clip(xs_u, 0.0, float(w - 1)).astype(np.float32)
    ys_map = np.clip(ys_u, 0.0, float(h - 1)).astype(np.float32)
    return cv2.remap(ch, xs_map, ys_map, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class ChromaticAberrationPlugin(Plugin):
    name = "chromatic_aberration"
    param_spec = [
        ParamSpec("k_red", 0.0, -0.04, 0.04, "r2_scale", "dimensionless", "Red channel radial r^2 UV scale offset"),
        ParamSpec("k_blue", 0.0, -0.04, 0.04, "r2_scale", "dimensionless", "Blue channel radial r^2 UV scale offset"),
        ParamSpec("center_x", 0.50, 0.35, 0.65, "uv_0_1", "dimensionless", "Optical centre X"),
        ParamSpec("center_y_top", 0.50, 0.35, 0.65, "uv_0_1", "dimensionless", "Optical centre Y from top (yTop)"),
    ]

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {"k_red": 0.0, "k_blue": 0.0, "center_x": 0.50, "center_y_top": 0.50}

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        est_kr: List[float] = []
        est_kb: List[float] = []
        corner_px_shifts: List[float] = []

        for r_im, t_im, pctx in items:
            em = pctx.masks.edge_mask
            h, w = t_im.shape[:2]
            aspect = float(w) / max(float(h), 1.0)
            x_n = ((np.arange(w, dtype=np.float32) + 0.5) / w)[None, :]
            y_n = ((np.arange(h, dtype=np.float32) + 0.5) / h)[:, None]
            px = x_n - 0.5
            py = y_n - 0.5
            r2 = (px * aspect) ** 2 + py ** 2
            outer_em = em & (r2 > 0.18)
            if int(outer_em.sum()) < 120:
                continue

            # Linearized shift model: C_tgt - C_ref ≈ k_c * r2 * (px * w * dC/dx + py * h * dC/dy)
            for ch_idx, bucket in [(0, est_kr), (2, est_kb)]:
                rc = r_im[..., ch_idx]
                gx = cv2.Sobel(rc, cv2.CV_32F, 1, 0, ksize=3) / 8.0
                gy = cv2.Sobel(rc, cv2.CV_32F, 0, 1, ksize=3) / 8.0
                radial_deriv = r2 * (px * float(w) * gx + py * float(h) * gy)
                # Subtract green residual so unmodelled luma sharpening doesn't masquerade as CA
                res_cg = (t_im[..., ch_idx] - r_im[..., ch_idx]) - (t_im[..., 1] - r_im[..., 1])
                b_v = radial_deriv[outer_em].astype(np.float64)
                y_v = res_cg[outer_em].astype(np.float64)
                k_est = float(np.sum(b_v * y_v) / (np.sum(b_v * b_v) + 1e-3))
                bucket.append(k_est)

            if est_kr and est_kb:
                max_k = max(abs(est_kr[-1]), abs(est_kb[-1]), abs(est_kr[-1] - est_kb[-1]) * 0.5)
                # At 16:9 corner, r2 ≈ (0.5*1.78)^2 + 0.5^2 ≈ 1.04, shift in px ≈ 0.5 * w * max_k * 1.04
                corner_px_shifts.append(float(0.52 * w * max_k))

        mean_shift_px = float(np.mean(corner_px_shifts)) if corner_px_shifts else 0.0
        same_sign_r = len(est_kr) > 0 and (all(x > 0 for x in est_kr) or all(x < 0 for x in est_kr))
        same_sign_b = len(est_kb) > 0 and (all(x > 0 for x in est_kb) or all(x < 0 for x in est_kb))

        if mean_shift_px >= 0.45 and (same_sign_r or same_sign_b):
            status = "present"
        else:
            status = "absent"

        return Evidence(
            plugin_name=self.name,
            status=status,
            score=mean_shift_px,
            notes=(
                f"Outer-frame radial R/B chromatic fringe check: corner shift={mean_shift_px:.2f} px -> {status}."
            ),
            metrics={
                "est_corner_shift_px": mean_shift_px,
                "mean_k_red": float(np.mean(est_kr)) if est_kr else 0.0,
                "mean_k_blue": float(np.mean(est_kb)) if est_kb else 0.0,
            },
            mask_of_interest=items[0][2].masks.edge_mask,
        )

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        kr = float(params.get("k_red", 0.0))
        kb = float(params.get("k_blue", 0.0))
        if max(abs(kr), abs(kb)) <= 1e-6:
            return np.clip(img, 0.0, 1.0).astype(np.float32)
        cx = float(params.get("center_x", 0.50))
        cy = float(params.get("center_y_top", 0.50))
        x = np.clip(img, 0.0, 1.0).astype(np.float32)
        r_w = _warp_channel_radial(x[..., 0], kr, cx, cy)
        b_w = _warp_channel_radial(x[..., 2], kb, cx, cy)
        return np.stack([r_w, x[..., 1], b_w], axis=-1).astype(np.float32)

    def loss(
        self,
        pred: ImageOrList,
        tgt: ImageOrList,
        ctx: ContextOrList = None,
        fold: Optional[int] = None,
        train: bool = False,
    ) -> float:
        items = normalize_pair_inputs(pred, tgt, ctx)
        errs: List[float] = []
        for p_im, t_im, pctx in items:
            em = pctx.masks.edge_mask
            if fold is not None:
                em = em & ((pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold))
            if int(em.sum()) < 50:
                em = pctx.masks.edge_mask
            # Measure R-G and B-G chroma fringe RMSE on edges (/255)
            prg = (p_im[..., 0] - p_im[..., 1])[em]
            trg = (t_im[..., 0] - t_im[..., 1])[em]
            pbg = (p_im[..., 2] - p_im[..., 1])[em]
            tbg = (t_im[..., 2] - t_im[..., 1])[em]
            rmse = float(np.sqrt(0.5 * np.mean(((prg - trg) * 255.0) ** 2) + 0.5 * np.mean(((pbg - tbg) * 255.0) ** 2)))
            errs.append(rmse)
        return float(np.mean(errs)) if errs else 0.0

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]
        n_folds = int(items[0][2].masks.block_folds.max()) + 1

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        ev = self.detect(refs, tgts, ctxs)
        init_kr = float(np.clip(ev.metrics.get("mean_k_red", 0.0), -0.03, 0.03))
        init_kb = float(np.clip(ev.metrics.get("mean_k_blue", 0.0), -0.03, 0.03))

        fold_after: List[float] = []
        fold_kr, fold_kb = [], []
        for f in range(n_folds):
            def _obj_f(v: np.ndarray) -> float:
                pf = {"k_red": float(v[0]), "k_blue": float(v[1]), "center_x": 0.50, "center_y_top": 0.50}
                preds = [self.render(r, pf) for r in refs]
                return self.loss(preds, tgts, ctxs, fold=f, train=True)

            opt_f = minimize(
                _obj_f,
                x0=np.array([init_kr, init_kb], dtype=np.float64),
                method="Powell",
                bounds=[(-0.04, 0.04), (-0.04, 0.04)],
                options={"maxiter": 8, "maxfev": 40, "ftol": 1e-3},
            )
            kr_f, kb_f = float(opt_f.x[0]), float(opt_f.x[1])
            fold_kr.append(kr_f)
            fold_kb.append(kb_f)
            pf_val = {"k_red": kr_f, "k_blue": kb_f, "center_x": 0.50, "center_y_top": 0.50}
            fold_after.append(self.loss([self.render(r, pf_val) for r in refs], tgts, ctxs, fold=f, train=False))

        ho_after = float(np.mean(fold_after))

        def _obj_full(v: np.ndarray) -> float:
            pf = {"k_red": float(v[0]), "k_blue": float(v[1]), "center_x": 0.50, "center_y_top": 0.50}
            return self.loss([self.render(r, pf) for r in refs], tgts, ctxs, fold=None, train=True)

        opt_full = minimize(
            _obj_full,
            x0=np.array([np.mean(fold_kr), np.mean(fold_kb)], dtype=np.float64),
            method="Powell",
            bounds=[(-0.04, 0.04), (-0.04, 0.04)],
            options={"maxiter": 8, "maxfev": 45, "ftol": 5e-4},
        )
        best_params = {
            "k_red": round(float(opt_full.x[0]), 6),
            "k_blue": round(float(opt_full.x[1]), 6),
            "center_x": 0.50,
            "center_y_top": 0.50,
        }
        preds_final = [self.render(r, best_params) for r in refs]
        tr_after = self.loss(preds_final, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)
        w_max = max(t.shape[1] for t in tgts)
        corner_px = 0.52 * w_max * max(abs(best_params["k_red"]), abs(best_params["k_blue"]))

        accepted = (corner_px >= 0.40) and (ho_after < ho_before - 0.06) and (rel_gain > 0.025)
        if not accepted:
            zero_p = self.initial_guess(ref_in, tgt, ctx)
            return zero_p, FitReport(
                plugin_name=self.name,
                accepted_hint=False,
                train_loss_before=tr_before,
                train_loss_after=tr_before,
                held_out_loss_before=ho_before,
                held_out_loss_after=ho_before,
                held_out_rel_gain=0.0,
                fold_losses_before=fold_before,
                fold_losses_after=fold_before,
                notes=f"Chromatic aberration absent/rejected ({ho_before:.2f} -> {ho_after:.2f}, corner_px={corner_px:.2f}).",
                diagnostics={"candidate": best_params},
            )

        return best_params, FitReport(
            plugin_name=self.name,
            accepted_hint=True,
            train_loss_before=tr_before,
            train_loss_after=tr_after,
            held_out_loss_before=ho_before,
            held_out_loss_after=ho_after,
            held_out_rel_gain=rel_gain,
            fold_losses_before=fold_before,
            fold_losses_after=fold_after,
            notes=(
                f"Radial lateral chromatic aberration: k_red={best_params['k_red']:.5f}, "
                f"k_blue={best_params['k_blue']:.5f} (~{corner_px:.2f} px corner shift). "
                f"Edge chroma RMSE {ho_before:.2f} -> {ho_after:.2f}."
            ),
            diagnostics={"accepted_params": best_params},
        )

    def glsl_taps(self, params: Dict[str, Any]) -> int:
        if max(abs(float(params.get("k_red", 0.0))), abs(float(params.get("k_blue", 0.0)))) <= 1e-6:
            return 0
        return 2

    def to_glsl(self, params: Dict[str, Any]) -> str:
        kr = float(params.get("k_red", 0.0))
        kb = float(params.get("k_blue", 0.0))
        if max(abs(kr), abs(kb)) <= 1e-6:
            return (
                "// --- Plugin: chromatic_aberration (inactive, 0 taps) ---\n"
                "vec3 msApplyChromaticAberration(vec3 baseCol, vec2 uv, vec2 texelSize) { return baseCol; }"
            )
        cx = float(params.get("center_x", 0.50))
        cy_uv = 1.0 - float(params.get("center_y_top", 0.50))
        return f"""// --- Plugin: chromatic_aberration (radial R/B dispersion, 2 extra taps) ---
// Expects helper: vec3 msFetchGraded(vec2 uv);
vec3 msApplyChromaticAberration(vec3 baseCol, vec2 uv, vec2 texelSize) {{
    vec2 center = vec2({cx:.6f}, {cy_uv:.6f});
    vec2 p = uv - center;
    float aspect = texelSize.y / max(texelSize.x, 0.0001);
    vec2 pa = vec2(p.x * aspect, p.y);
    float r2 = dot(pa, pa);
    vec2 uvR = clamp(center + p * (1.0 + ({kr:.6f}) * r2), 0.0, 1.0);
    vec2 uvB = clamp(center + p * (1.0 + ({kb:.6f}) * r2), 0.0, 1.0);
    float rCh = msFetchGraded(uvR).r;
    float bCh = msFetchGraded(uvB).b;
    return vec3(rCh, baseCol.g, bCh);
}}"""

    def describe(self, params: Dict[str, Any]) -> str:
        kr = float(params.get("k_red", 0.0))
        kb = float(params.get("k_blue", 0.0))
        if max(abs(kr), abs(kb)) <= 1e-6:
            return "Chromatic Aberration: absent."
        return f"Radial lateral Chromatic Aberration: k_red={kr:.5f}, k_blue={kb:.5f}."
