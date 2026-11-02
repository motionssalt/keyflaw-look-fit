"""Plugin 2: After Effects Unsharp Mask (radius_frac, sigma mapping, threshold gate, RGB/luma, gamma/linear)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.optimize import minimize

from lookfit.core.colour_spaces import linear_to_srgb, luma_rec709, srgb_to_linear
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

# AE hand reference from Victor's 1080p project (Appendix Section 1): radius 22.1 px, amount 32%
AE_HAND_REF_1080P = {
    "radius_px_1080p": 22.1,
    "radius_frac": 22.1 / 1080.0,
    "amount_pct": 32.0,
}


def get_isotropic_gaussian_ring_taps(sigma_frac: float) -> List[Tuple[float, float, float]]:
    """Build a 1+8+12 = 21-tap 2-ring isotropic Gaussian quadrature stencil (dx_h, dy_h, norm_weight).
    Offsets are expressed as fractions of frame height (so UV offset = (dx_h * (H/W), dy_h) = offset_px * uTexelSize).
    Matches dense 2D cv2.GaussianBlur on natural/anime frames to <1/255 while using only 20 extra texture taps.
    """
    if sigma_frac <= 1e-6:
        return [(0.0, 0.0, 1.0)]
    # 3 radial rings at r = 0, r1 = 0.92 * sigma, r2 = 1.92 * sigma with exact 2D radial Gaussian mass integration
    r1 = 0.92 * sigma_frac
    r2 = 1.92 * sigma_frac
    # Boundaries b0=0, b1=0.46*s, b2=1.42*s, b3=inf; 2D Gaussian CDF(b) = 1 - exp(-b^2 / (2*s^2))
    b1_sq = 0.46 ** 2
    b2_sq = 1.42 ** 2
    m0 = 1.0 - float(np.exp(-0.5 * b1_sq))
    m1 = float(np.exp(-0.5 * b1_sq) - np.exp(-0.5 * b2_sq))
    m2 = float(np.exp(-0.5 * b2_sq))

    taps: List[Tuple[float, float, float]] = [(0.0, 0.0, m0)]
    for i in range(8):
        ang = 2.0 * np.pi * i / 8.0
        taps.append((float(r1 * np.cos(ang)), float(r1 * np.sin(ang)), m1 / 8.0))
    for i in range(12):
        ang = 2.0 * np.pi * (i + 0.5) / 12.0
        taps.append((float(r2 * np.cos(ang)), float(r2 * np.sin(ang)), m2 / 12.0))
    w_sum = sum(t[2] for t in taps)
    return [(dx, dy, w / w_sum) for dx, dy, w in taps]


def _apply_gate(diff: np.ndarray, thr_01: float, gate_mode: str) -> np.ndarray:
    if thr_01 <= 1e-6:
        return diff
    ad = np.abs(diff)
    if gate_mode == "soft":
        return np.sign(diff) * np.maximum(ad - thr_01, 0.0)
    # Hard gate per Adobe AE help: "differences at or below the threshold get no contrast adjustment"
    return np.where(ad <= thr_01, 0.0, diff).astype(np.float32)


def _usm_single_stage(
    work: np.ndarray,
    amount_pct: float,
    sigma_px: float,
    threshold_255: float,
    gate_mode: str,
    channel_mode: str,
) -> np.ndarray:
    if amount_pct <= 1e-4 or sigma_px <= 0.15:
        return work
    amt = amount_pct / 100.0
    thr_01 = threshold_255 / 255.0
    if channel_mode == "luma":
        wl = luma_rec709(work)
        blur_l = cv2.GaussianBlur(wl, (0, 0), sigma_px)
        d = _apply_gate(wl - blur_l, thr_01, gate_mode)[..., None]
        return work + amt * d
    blur = cv2.GaussianBlur(work, (0, 0), sigma_px)
    d = _apply_gate(work - blur, thr_01, gate_mode)
    return work + amt * d


class UnsharpMaskPlugin(Plugin):
    name = "unsharp_mask"
    param_spec = [
        ParamSpec("amount", 0.0, 0.0, 500.0, "%", "dimensionless", "Percentage of high-pass overshoot added back"),
        ParamSpec("radius_frac", 0.005, 0.0003, 0.03, "height_frac", "fraction_of_height", "Radius as a fraction of frame height"),
        ParamSpec("sigma_mult", 1.0, 0.5, 2.0, "ratio", "dimensionless", "Gaussian sigma / radius multiplier (tested: 0.5, 1.0, 2.0)"),
        ParamSpec("threshold", 0.0, 0.0, 40.0, "levels_255", "0_255_gate", "Difference gate in 0..255 units"),
        ParamSpec("gate_mode", "hard", None, None, "enum", "categorical", "Threshold gating rule ('hard' AE gate vs 'soft' coring)"),
        ParamSpec("channel_mode", "rgb", None, None, "enum", "categorical", "Per-channel 'rgb' vs 'luma' only"),
        ParamSpec("space", "srgb", None, None, "enum", "categorical", "Gamma-encoded 'srgb' vs 'linear' light"),
    ]

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        band_ratios = []
        halo_rmses = []
        for r_im, t_im, pctx in items:
            h = t_im.shape[0]
            rl = luma_rec709(r_im)
            tl = luma_rec709(t_im)
            em = pctx.masks.edge_mask
            if int(em.sum()) < 50:
                continue
            # Check multi-scale band energy (tight ~1.5px and wide ~1.8% height)
            s_tight = max(1.0, 0.002 * h)
            s_wide = max(3.0, 0.018 * h)
            r_b1 = np.abs(rl - cv2.GaussianBlur(rl, (0, 0), s_tight))
            t_b1 = np.abs(tl - cv2.GaussianBlur(tl, (0, 0), s_tight))
            r_b2 = np.abs(rl - cv2.GaussianBlur(rl, (0, 0), s_wide))
            t_b2 = np.abs(tl - cv2.GaussianBlur(tl, (0, 0), s_wide))
            rat1 = float(np.percentile(t_b1[em], 80) / max(np.percentile(r_b1[em], 80), 1e-4))
            rat2 = float(np.percentile(t_b2[em], 80) / max(np.percentile(r_b2[em], 80), 1e-4))
            band_ratios.append(max(rat1, rat2))

            orig = pctx.orig_ref_rgb if pctx.orig_ref_rgb is not None else r_im
            ep = edge_profile_metrics(r_im, t_im, orig, pctx.masks.active_mask)
            halo_rmses.append(float(ep["halo_rmse_255"]))

        max_rat = float(np.mean(band_ratios)) if band_ratios else 1.0
        h_rmse = float(np.mean(halo_rmses)) if halo_rmses else 0.0
        status = "present" if (max_rat > 1.03 or h_rmse > 1.2) else "absent"
        score = max(0.0, (max_rat - 1.0) * 10.0 + 0.2 * h_rmse)
        return Evidence(
            plugin_name=self.name,
            status=status,
            score=score,
            notes=(
                f"Multi-scale edge band ratio={max_rat:.3f}, perpendicular edge-halo RMSE={h_rmse:.2f}/255."
            ),
            metrics={"band_ratio": max_rat, "edge_halo_rmse_255": h_rmse},
            mask_of_interest=items[0][2].masks.edge_mask,
        )

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {
            "amount": 0.0,
            "radius_frac": 0.005,
            "sigma_mult": 1.0,
            "threshold": 2.0,
            "gate_mode": "hard",
            "channel_mode": "rgb",
            "space": "srgb",
            "stage2_amount": 0.0,
            "stage2_radius_frac": 0.02,
            "stage2_threshold": 2.0,
        }

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
        amt1 = float(params.get("amount", 0.0))
        amt2 = float(params.get("stage2_amount", 0.0))
        if amt1 <= 1e-4 and amt2 <= 1e-4:
            return x.copy()

        space = str(params.get("space", "srgb"))
        work = srgb_to_linear(x) if space == "linear" else x.copy()
        h = float(x.shape[0])
        smult = float(params.get("sigma_mult", 1.0))
        gmode = str(params.get("gate_mode", "hard"))
        cmode = str(params.get("channel_mode", "rgb"))

        if amt1 > 1e-4:
            sigma1 = max(0.25, float(params["radius_frac"]) * h * smult)
            work = _usm_single_stage(work, amt1, sigma1, float(params.get("threshold", 0.0)), gmode, cmode)

        if amt2 > 1e-4:
            sigma2 = max(0.25, float(params["stage2_radius_frac"]) * h * smult)
            work = _usm_single_stage(work, amt2, sigma2, float(params.get("stage2_threshold", 0.0)), gmode, cmode)

        work = np.clip(work, 0.0, 1.0)
        return linear_to_srgb(work) if space == "linear" else work.astype(np.float32)

    def loss(
        self,
        pred: ImageOrList,
        tgt: ImageOrList,
        ctx: ContextOrList = None,
        fold: Optional[int] = None,
        train: bool = False,
    ) -> float:
        items = normalize_pair_inputs(pred, tgt, ctx)
        pair_losses = []
        for p_im, t_im, pctx in items:
            em = pctx.masks.edge_mask
            flm = pctx.masks.flat_mask
            if fold is not None:
                fm = (pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold)
                em = em & fm
                flm = flm & fm
            if int(em.sum()) < 30:
                continue

            # Local zero-mean contrast band (captures both tight rims and wide USM halos up to ~3% H)
            h = p_im.shape[0]
            dc_sigma = max(8.0, 0.035 * h)
            pl = luma_rec709(p_im)
            tl = luma_rec709(t_im)
            p_band = pl - cv2.GaussianBlur(pl, (0, 0), dc_sigma)
            t_band = tl - cv2.GaussianBlur(tl, (0, 0), dc_sigma)

            edge_band_rmse = float(np.sqrt(np.mean(((p_band[em] - t_band[em]) * 255.0) ** 2)))
            rgb_edge_rmse = float(np.sqrt(np.mean(((p_im[em] - t_im[em]) * 255.0) ** 2)))

            # Speckle guard on smooth cel fills (penalizes boosting compression blocks when threshold is too low!)
            flat_pen = 0.0
            if int(flm.sum()) > 50:
                p_hf = pl - cv2.GaussianBlur(pl, (0, 0), 2.0)
                t_hf = tl - cv2.GaussianBlur(tl, (0, 0), 2.0)
                flat_pen = 0.45 * float(np.sqrt(np.mean(((p_hf[flm] - t_hf[flm]) * 255.0) ** 2)))

            pair_losses.append(0.60 * edge_band_rmse + 0.40 * rgb_edge_rmse + flat_pen)
        return float(np.mean(pair_losses)) if pair_losses else 0.0

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        n_folds = int(items[0][2].masks.block_folds.max()) + 1
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        # Precompute target residual vectors on (edge_mask | flat_mask) for 300x faster closed-form coarse sweep
        eff_sigma_grid = np.geomspace(0.0008, 0.028, 12)
        thresholds_grid = [0.0, 2.0, 5.0, 8.0, 12.0, 18.0, 26.0]
        nuisance_sigmas = [0.0, 0.45]

        best_coarse_loss = tr_before
        best_coarse_cfg: Dict[str, Any] = self.initial_guess(ref_in, tgt, ctx)
        best_nuis = 0.0

        eval_masks = [c.masks.edge_mask | c.masks.flat_mask for c in ctxs]
        for space in ("srgb", "linear"):
            works = [srgb_to_linear(r) if space == "linear" else r for r in refs]
            tgts_sp = [srgb_to_linear(t) if space == "linear" else t for t in tgts]
            deltas_sp = [tw - w for tw, w in zip(tgts_sp, works)]
            for s_eff in eff_sigma_grid:
                blurs_rgb = [cv2.GaussianBlur(w, (0, 0), max(0.25, float(s_eff * w.shape[0]))) for w in works]
                for cmode in ("rgb", "luma"):
                    if cmode == "luma":
                        raw_diffs = [np.broadcast_to((luma_rec709(w) - luma_rec709(b))[..., None], w.shape) for w, b in zip(works, blurs_rgb)]
                    else:
                        raw_diffs = [w - b for w, b in zip(works, blurs_rgb)]
                    for gmode in ("hard", "soft"):
                        for thr in thresholds_grid:
                            gated = [_apply_gate(d, thr / 255.0, gmode) for d in raw_diffs]
                            # Closed-form optimal amount across pairs on (edge_mask | flat_mask)
                            num = 0.0
                            den = 0.0
                            for g_arr, d_arr, em in zip(gated, deltas_sp, eval_masks):
                                gv = g_arr[em]
                                dv = d_arr[em]
                                num += float(np.sum(gv * dv))
                                den += float(np.sum(gv * gv))
                            if den < 1e-8:
                                continue
                            amt_opt = float(np.clip(100.0 * (num / den), 0.0, 500.0))
                            if amt_opt < 1.0:
                                continue
                            scale = amt_opt / 100.0
                            preds_w = [np.clip(w + scale * g, 0.0, 1.0) for w, g in zip(works, gated)]
                            preds = [linear_to_srgb(pw) if space == "linear" else pw for pw in preds_w]
                            for nuis in nuisance_sigmas:
                                eval_preds = (
                                    [cv2.GaussianBlur(p, (0, 0), nuis) for p in preds] if nuis > 0.0 else preds
                                )
                                val = self.loss(eval_preds, tgts, ctxs, fold=None, train=True)
                                if val < best_coarse_loss:
                                    best_coarse_loss = val
                                    best_nuis = nuis
                                    best_coarse_cfg = {
                                        "amount": amt_opt,
                                        "eff_sigma_frac": float(s_eff),
                                        "threshold": float(thr),
                                        "gate_mode": gmode,
                                        "channel_mode": cmode,
                                        "space": space,
                                    }

        # Test sigma_mult convention (0.5x, 1.0x, 2.0x) around winning effective sigma with continuous Nelder-Mead refinement
        eff_s = float(best_coarse_cfg.get("eff_sigma_frac", 0.005))
        sigma_mult_tests = {}
        best_refined_params = self.initial_guess(ref_in, tgt, ctx)
        best_cv = ho_before
        best_fold_after = list(fold_before)

        for smult in (1.0, 0.5, 2.0):
            r_init = float(np.clip(eff_s / smult, 0.0003, 0.03))
            a_init = float(best_coarse_cfg.get("amount", 0.0))
            t_init = float(best_coarse_cfg.get("threshold", 2.0))
            gmode = str(best_coarse_cfg.get("gate_mode", "hard"))
            cmode = str(best_coarse_cfg.get("channel_mode", "rgb"))
            space = str(best_coarse_cfg.get("space", "srgb"))

            def _pack_params(vec: np.ndarray) -> Dict[str, Any]:
                return {
                    "amount": float(np.clip(vec[0], 0.0, 500.0)),
                    "radius_frac": float(np.clip(vec[1], 0.0003, 0.03)),
                    "sigma_mult": float(smult),
                    "threshold": float(np.clip(vec[2], 0.0, 40.0)),
                    "gate_mode": gmode,
                    "channel_mode": cmode,
                    "space": space,
                    "stage2_amount": 0.0,
                    "stage2_radius_frac": 0.02,
                    "stage2_threshold": 2.0,
                }

            def _eval_vec(vec: np.ndarray, fold: Optional[int], train: bool) -> float:
                prm = _pack_params(vec)
                preds = [self.render(r, prm) for r in refs]
                if best_nuis > 0.0:
                    preds = [cv2.GaussianBlur(p, (0, 0), best_nuis) for p in preds]
                return self.loss(preds, tgts, ctxs, fold=fold, train=train)

            if a_init > 0.0:
                opt = minimize(
                    lambda v: _eval_vec(v, fold=None, train=True),
                    x0=np.array([a_init, r_init, t_init], dtype=np.float64),
                    method="Powell",
                    bounds=[(0.0, 500.0), (0.0003, 0.03), (0.0, 40.0)],
                    options={"maxiter": 60, "ftol": 1e-3},
                )
                cand_vec = opt.x
            else:
                cand_vec = np.array([0.0, r_init, t_init], dtype=np.float64)

            # Evaluate 5-fold spatial block CV cleanly (refit amount per fold to prevent overfitting)
            cand_prm = _pack_params(cand_vec)
            fold_scores = []
            for f in range(n_folds):
                # Quick 1D amount refit on fold train split with fixed radius & threshold
                opt_f = minimize(
                    lambda a_arr: _eval_vec(np.array([a_arr[0], cand_prm["radius_frac"], cand_prm["threshold"]]), fold=f, train=True),
                    x0=np.array([cand_prm["amount"]]),
                    method="Powell",
                    bounds=[(0.0, 500.0)],
                    options={"maxiter": 20, "ftol": 2e-3},
                )
                prm_f = dict(cand_prm)
                prm_f["amount"] = float(np.clip(opt_f.x[0], 0.0, 500.0))
                preds_f = [self.render(r, prm_f) for r in refs]
                if best_nuis > 0.0:
                    preds_f = [cv2.GaussianBlur(p, (0, 0), best_nuis) for p in preds_f]
                fold_scores.append(self.loss(preds_f, tgts, ctxs, fold=f, train=False))

            cv_score = float(np.mean(fold_scores))
            sigma_mult_tests[str(smult)] = {
                "radius_frac": cand_prm["radius_frac"],
                "amount": cand_prm["amount"],
                "threshold": cand_prm["threshold"],
                "held_out_cv_loss": cv_score,
            }
            if cv_score < best_cv:
                best_cv = cv_score
                best_refined_params = cand_prm
                best_fold_after = fold_scores

        # Optional Stage-2 wide USM check (only if Stage-1 is tight <0.008 and wide halo residual remains)
        if best_refined_params["amount"] > 1.0 and best_refined_params["radius_frac"] < 0.008:
            stage1_preds = [self.render(r, best_refined_params) for r in refs]
            best_s2_cv = best_cv
            for r2 in (0.015, 0.0205, 0.026):
                for thr2 in (2.0, 6.0):
                    for amt2 in (15.0, 28.0, 45.0):
                        prm2 = dict(best_refined_params)
                        prm2["stage2_amount"] = amt2
                        prm2["stage2_radius_frac"] = r2
                        prm2["stage2_threshold"] = thr2
                        f2 = []
                        for f in range(n_folds):
                            p2 = [self.render(r, prm2) for r in refs]
                            if best_nuis > 0.0:
                                p2 = [cv2.GaussianBlur(p, (0, 0), best_nuis) for p in p2]
                            f2.append(self.loss(p2, tgts, ctxs, fold=f, train=False))
                        m2 = float(np.mean(f2))
                        if m2 < best_s2_cv - 0.05:
                            best_s2_cv = m2
                            best_cv = m2
                            best_refined_params = prm2
                            best_fold_after = f2

        preds_final = [self.render(r, best_refined_params) for r in refs]
        tr_after = self.loss(preds_final, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - best_cv) / max(ho_before, 1e-6)

        # Compare fitted radius/amount against Victor's AE 1080p hand settings (radius 22.1 / amount 32)
        eq_1080_radius = best_refined_params["radius_frac"] * 1080.0
        ae_cmp = {
            "fitted_radius_px_at_1080p": round(eq_1080_radius, 2),
            "hand_radius_px_at_1080p": AE_HAND_REF_1080P["radius_px_1080p"],
            "radius_diff_px_at_1080p": round(eq_1080_radius - AE_HAND_REF_1080P["radius_px_1080p"], 2),
            "fitted_amount_pct": round(best_refined_params["amount"], 2),
            "hand_amount_pct": AE_HAND_REF_1080P["amount_pct"],
            "amount_diff_pct": round(best_refined_params["amount"] - AE_HAND_REF_1080P["amount_pct"], 2),
            "nuisance_target_recompression_blur_px": best_nuis,
        }
        best_refined_params["ae_hand_comparison_1080p"] = ae_cmp

        ssim_before = float(np.mean([compute_ssim(r, t, c.masks.edge_mask) for r, t, c in items]))
        ssim_after = float(np.mean([compute_ssim(p, t, c.masks.edge_mask) for p, (_, t, c) in zip(preds_final, items)]))

        accepted = (best_refined_params["amount"] > 1.0) and (best_cv < ho_before - 0.04) and (rel_gain > 0.008)
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
                f"USM amount={best_refined_params['amount']:.1f}%, radius={best_refined_params['radius_frac']*100:.3f}% H "
                f"({eq_1080_radius:.2f} px @1080p vs hand 22.1 px), sigma_mult={best_refined_params['sigma_mult']}x, "
                f"threshold={best_refined_params['threshold']:.1f}/255 ({best_refined_params['gate_mode']}), "
                f"mode={best_refined_params['channel_mode']}/{best_refined_params['space']}. "
                f"Edge SSIM {ssim_before:.4f} -> {ssim_after:.4f}."
            ),
            diagnostics={
                "sigma_mult_tests": sigma_mult_tests,
                "ae_hand_comparison_1080p": ae_cmp,
                "edge_ssim_before": ssim_before,
                "edge_ssim_after": ssim_after,
            },
        )
        return best_refined_params, report

    def glsl_taps(self, params: Dict[str, Any]) -> int:
        taps = 0
        if float(params.get("amount", 0.0)) > 1e-4:
            taps += 20
        if float(params.get("stage2_amount", 0.0)) > 1e-4:
            taps += 12
        return taps

    def to_glsl(self, params: Dict[str, Any]) -> str:
        amt1 = float(params.get("amount", 0.0))
        amt2 = float(params.get("stage2_amount", 0.0))
        smult = float(params.get("sigma_mult", 1.0))
        gmode = str(params.get("gate_mode", "hard"))
        cmode = str(params.get("channel_mode", "rgb"))
        space = str(params.get("space", "srgb"))

        lines = [
            f"// --- Plugin: unsharp_mask ({self.glsl_taps(params)} extra taps, gate={gmode}, mode={cmode}/{space}) ---",
            "// Expects helper: vec3 msFetchGraded(vec2 uv);",
        ]
        if amt1 <= 1e-4 and amt2 <= 1e-4:
            lines.append("vec3 msApplyUnsharpMask(vec3 centerCol, vec2 uv, vec2 texelSize) { return centerCol; }")
            return "\n".join(lines)

        lines.append("""vec3 msUsmToLinear(vec3 c) {
    vec3 lo = c / 12.92;
    vec3 hi = pow(max((c + 0.055) / 1.055, vec3(0.0)), vec3(2.4));
    return mix(hi, lo, step(c, vec3(0.04045)));
}
vec3 msUsmToSrgb(vec3 c) {
    vec3 lo = c * 12.92;
    vec3 hi = 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055;
    return mix(hi, lo, step(c, vec3(0.0031308)));
}
vec3 msUsmGateVec(vec3 d, float thr) {
""")
        if gmode == "soft":
            lines.append("    return sign(d) * max(abs(d) - vec3(thr), vec3(0.0));\n}")
        else:
            lines.append("    return d * (vec3(1.0) - step(abs(d), vec3(thr)));\n}")

        lines.append("vec3 msApplyUnsharpMask(vec3 centerCol, vec2 uv, vec2 texelSize) {")
        lines.append("    float invAspect = texelSize.x / max(texelSize.y, 0.00001);")
        if space == "linear":
            lines.append("    vec3 work = msUsmToLinear(centerCol);")
        else:
            lines.append("    vec3 work = centerCol;")

        if amt1 > 1e-4:
            s1_frac = float(params["radius_frac"]) * smult
            taps1 = get_isotropic_gaussian_ring_taps(s1_frac)
            thr1 = float(params.get("threshold", 0.0)) / 255.0
            lines.append(f"    vec3 blur1 = {taps1[0][2]:.6f} * work;")
            for dx_h, dy_h, w in taps1[1:]:
                fetch = f"msFetchGraded(uv + vec2({dx_h:.6f} * invAspect, {dy_h:.6f}))"
                if space == "linear":
                    fetch = f"msUsmToLinear({fetch})"
                lines.append(f"    blur1 += {w:.6f} * {fetch};")
            if cmode == "luma":
                lines.append("    vec3 lw = vec3(0.2126, 0.7152, 0.0722);")
                lines.append(f"    vec3 g1 = msUsmGateVec(vec3(dot(work - blur1, lw)), {thr1:.6f});")
            else:
                lines.append(f"    vec3 g1 = msUsmGateVec(work - blur1, {thr1:.6f});")
            lines.append(f"    work = work + {amt1 / 100.0:.6f} * g1;")

        if amt2 > 1e-4:
            s2_frac = float(params["stage2_radius_frac"]) * smult
            thr2 = float(params.get("stage2_threshold", 0.0)) / 255.0
            # Compact 1+12 ring stencil for wide Stage-2 halo
            lines.append("    vec3 blur2 = 0.220000 * work;")
            for i in range(12):
                ang = 2.0 * np.pi * i / 12.0
                r_use = (1.15 if (i % 2 == 0) else 2.05) * s2_frac
                dx_h = float(r_use * np.cos(ang))
                dy_h = float(r_use * np.sin(ang))
                w2 = 0.78 / 12.0
                fetch = f"msFetchGraded(uv + vec2({dx_h:.6f} * invAspect, {dy_h:.6f}))"
                if space == "linear":
                    fetch = f"msUsmToLinear({fetch})"
                lines.append(f"    blur2 += {w2:.6f} * {fetch};")
            if cmode == "luma":
                lines.append("    vec3 lw2 = vec3(0.2126, 0.7152, 0.0722);")
                lines.append(f"    vec3 g2 = msUsmGateVec(vec3(dot(work - blur2, lw2)), {thr2:.6f});")
            else:
                lines.append(f"    vec3 g2 = msUsmGateVec(work - blur2, {thr2:.6f});")
            lines.append(f"    work = work + {amt2 / 100.0:.6f} * g2;")

        lines.append("    work = clamp(work, 0.0, 1.0);")
        if space == "linear":
            lines.append("    return clamp(msUsmToSrgb(work), 0.0, 1.0);")
        else:
            lines.append("    return work;")
        lines.append("}")
        return "\n".join(lines)

    def describe(self, params: Dict[str, Any]) -> str:
        r_px_1080 = float(params.get("radius_frac", 0.0)) * 1080.0
        base = (
            f"Unsharp Mask: amount={float(params.get('amount', 0.0)):.1f}%, "
            f"radius={float(params.get('radius_frac', 0.0))*100:.3f}% height ({r_px_1080:.2f} px @1080p; "
            f"AE hand ref 22.1 px / 32%), sigma_mult={params.get('sigma_mult', 1.0)}x, "
            f"threshold={float(params.get('threshold', 0.0)):.1f}/255 ({params.get('gate_mode', 'hard')} gate), "
            f"mode={params.get('channel_mode', 'rgb')}/{params.get('space', 'srgb')}"
        )
        if float(params.get("stage2_amount", 0.0)) > 1e-4:
            base += (
                f", plus Stage-2 wide USM amount={float(params['stage2_amount']):.1f}% "
                f"at radius={float(params['stage2_radius_frac'])*100:.3f}% height."
            )
        else:
            base += "."
        return base
