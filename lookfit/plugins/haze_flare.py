"""Plugin 4: Haze Flare (real scene-highlight multi-scale bloom, never a painted overlay)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from scipy.optimize import minimize

from lookfit.core.colour_spaces import luma_rec709
from lookfit.plugins.base import (
    ContextOrList,
    Evidence,
    FitReport,
    ImageOrList,
    ParamSpec,
    Plugin,
    normalize_pair_inputs,
)

DEFAULT_SCALES_FRAC = [0.008, 0.022, 0.055]


def extract_soft_knee_highlights(img_rgb: np.ndarray, threshold: float, softness: float) -> np.ndarray:
    """Extract colourful scene highlights above `threshold` with C1 quadratic soft knee `softness`.
    Strictly zero on a black frame (img_rgb == 0).
    """
    x = np.clip(img_rgb, 0.0, 1.0).astype(np.float32)
    luma = luma_rec709(x)
    mx = np.max(x, axis=-1)
    m = 0.5 * luma + 0.5 * mx
    knee = max(float(softness), 1e-4)
    lo = float(threshold) - knee
    hi = float(threshold) + knee

    excess = np.where(
        m <= lo,
        0.0,
        np.where(
            m >= hi,
            m - float(threshold),
            ((m - lo) ** 2) / (4.0 * knee),
        ),
    ).astype(np.float32)
    excess = np.maximum(excess, 0.0)
    gain = excess / np.maximum(m, 1e-4)
    return (x * gain[..., None]).astype(np.float32)


def _fast_gaussian_blur_frac(img: np.ndarray, sigma_x_px: float, sigma_y_px: float) -> np.ndarray:
    """Fast multi-scale Gaussian blur using Pyramid/Area downsampling when sigma > 4 px."""
    h, w = img.shape[:2]
    min_s = min(sigma_x_px, sigma_y_px)
    if min_s <= 0.3:
        return img.copy()
    ds = 1
    if min_s > 16.0:
        ds = 8
    elif min_s > 8.0:
        ds = 4
    elif min_s > 3.5:
        ds = 2

    if ds > 1:
        sw = max(8, w // ds)
        sh = max(8, h // ds)
        small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
        sx = max(0.4, sigma_x_px * (sw / float(w)))
        sy = max(0.4, sigma_y_px * (sh / float(h)))
        blurred_s = cv2.GaussianBlur(small, (0, 0), sigmaX=sx, sigmaY=sy)
        return cv2.resize(blurred_s, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    return cv2.GaussianBlur(img, (0, 0), sigmaX=max(0.3, sigma_x_px), sigmaY=max(0.3, sigma_y_px)).astype(np.float32)


def composite_bloom(base: np.ndarray, bloom: np.ndarray, blend_mode: str) -> np.ndarray:
    b = np.clip(bloom, 0.0, 1.0)
    x = np.clip(base, 0.0, 1.0)
    if blend_mode == "add":
        return np.clip(x + b, 0.0, 1.0).astype(np.float32)
    if blend_mode == "soft_light":
        # W3C soft light upper branch mixed with subtle screen lift so dark surroundings still receive glow
        sl = x + b * (np.sqrt(np.maximum(x, 0.0)) - x)
        sc = 1.0 - (1.0 - x) * (1.0 - b)
        return np.clip(0.5 * sl + 0.5 * sc, 0.0, 1.0).astype(np.float32)
    # Default: Screen
    return np.clip(1.0 - (1.0 - x) * (1.0 - b), 0.0, 1.0).astype(np.float32)


def get_bloom_glsl_taps(scales_frac: Sequence[float], weights: Sequence[float]) -> List[Tuple[float, float, float]]:
    """Build a compact <=28-fetch staggered multi-scale radial Gaussian stencil (dx_h, dy_h, weight) for single-pass GLSL."""
    w_arr = np.maximum(np.asarray(weights, dtype=np.float64), 0.0)
    w_sum = float(w_arr.sum())
    if w_sum <= 1e-8:
        return []
    w_norm = w_arr / w_sum
    active_n = max(1, sum(1 for sw in w_norm if sw > 1e-4))
    # Budget <= 28 extra fetches across 3, 4, or 5 scales: (4+5)=9 for <=3 scales, (3+4)=7 for 4 scales, (2+3)=5 for 5 scales
    if active_n <= 3:
        n_in, n_out = 4, 5
    elif active_n == 4:
        n_in, n_out = 3, 4
    else:
        n_in, n_out = 2, 3

    taps: List[Tuple[float, float, float]] = []
    center_w = 0.0
    for s_idx, (s_frac, sw) in enumerate(zip(scales_frac, w_norm)):
        if sw <= 1e-4:
            continue
        c_share = 0.14 * sw
        in_share = 0.48 * sw
        out_share = 0.38 * sw
        center_w += c_share
        phase = s_idx * 0.61803398875 * 2.0 * np.pi
        for k in range(n_in):
            ang = phase + 2.0 * np.pi * k / float(n_in)
            r = 0.85 * float(s_frac)
            taps.append((float(r * np.cos(ang)), float(r * np.sin(ang)), float(in_share / n_in)))
        for k in range(n_out):
            ang = phase + 0.39 + 2.0 * np.pi * k / float(n_out)
            r = 1.85 * float(s_frac)
            taps.append((float(r * np.cos(ang)), float(r * np.sin(ang)), float(out_share / n_out)))

    all_taps = [(0.0, 0.0, center_w)] + taps
    tot = sum(t[2] for t in all_taps)
    return [(dx, dy, wt / max(tot, 1e-8)) for dx, dy, wt in all_taps]


class HazeFlarePlugin(Plugin):
    name = "haze_flare"
    param_spec = [
        ParamSpec("threshold", 0.65, 0.30, 0.95, "level_0_1", "dimensionless", "Highlight luma/channel threshold"),
        ParamSpec("softness", 0.10, 0.00, 0.30, "level_0_1", "dimensionless", "Soft-knee transition width"),
        ParamSpec("scales_frac", [0.008, 0.022, 0.055], 0.003, 0.15, "height_frac", "fraction_of_height", "Multi-scale Gaussian blur sigmas as fractions of height"),
        ParamSpec("scale_weights", [0.45, 0.35, 0.20], 0.0, 1.0, "weight", "dimensionless", "Relative per-scale weights"),
        ParamSpec("channel_widths", [1.0, 1.2, 1.4], 0.7, 2.0, "ratio", "dimensionless", "R:G:B optical dispersion width multipliers"),
        ParamSpec("tint", [1.0, 1.0, 1.0], 0.0, 1.0, "rgb", "rgb_0_1", "Multiplicative bloom tint"),
        ParamSpec("intensity", 0.0, 0.0, 2.0, "gain", "dimensionless", "Overall bloom intensity"),
        ParamSpec("blend", "screen", None, None, "enum", "categorical", "Composite mode: screen, add, soft_light"),
    ]

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        lf_excess_near_hi = []
        lf_halo_mae = []
        lf_overall_err = []

        for r_im, t_im, pctx in items:
            h = t_im.shape[0]
            am = pctx.masks.active_mask
            if int(am.sum()) < 100:
                continue
            # Smooth low-frequency residual (tgt - ref)
            s_lf = max(6.0, 0.025 * h)
            res_lf = _fast_gaussian_blur_frac(t_im - r_im, s_lf, s_lf)
            rl = luma_rec709(r_im)
            # Dilated highlight halo neighbourhood around bright pixels (>= 0.58 or top 12% if >= 0.50)
            hi_thr = max(0.50, float(np.percentile(rl[am], 88)))
            if float(rl[am].max()) >= 0.62:
                hi_thr = max(0.58, min(hi_thr, 0.78))
            hi_core = (rl >= hi_thr) & am
            rad = max(7, int(round(0.035 * h)))
            k_el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1))
            hi_halo = (cv2.dilate(hi_core.astype(np.uint8), k_el) > 0) & am & (~hi_core)
            dark_bg = am & (~hi_halo) & (~hi_core)

            lf_overall_err.append(float(np.mean(np.abs(res_lf[am])) * 255.0))
            if int(hi_halo.sum()) > 40 and int(dark_bg.sum()) > 40:
                halo_mae = float(np.mean(np.abs(res_lf[hi_halo])) * 255.0)
                lift_halo = float(np.mean(luma_rec709(np.maximum(res_lf, 0.0))[hi_halo]) * 255.0)
                lift_bg = float(np.mean(luma_rec709(np.maximum(res_lf, 0.0))[dark_bg]) * 255.0)
                lf_halo_mae.append(halo_mae)
                lf_excess_near_hi.append(lift_halo - lift_bg)
            else:
                lf_halo_mae.append(0.0)
                lf_excess_near_hi.append(0.0)

        mean_lf = float(np.mean(lf_overall_err)) if lf_overall_err else 0.0
        mean_halo_mae = float(np.mean(lf_halo_mae)) if lf_halo_mae else 0.0
        mean_halo_lift = float(np.mean(lf_excess_near_hi)) if lf_excess_near_hi else 0.0

        # Existence test per Section 4 & Appendix Section 3.7:
        # Check smooth residual in highlight-halo rings (not diluted by dark background) and positive halo excess.
        if mean_halo_mae < 1.1 or mean_halo_lift < 0.45:
            status = "absent"
            score = max(0.0, mean_halo_lift)
        elif mean_halo_lift < 1.1:
            status = "weak"
            score = mean_halo_lift
        else:
            status = "present"
            score = mean_halo_lift

        return Evidence(
            plugin_name=self.name,
            status=status,
            score=score,
            notes=(
                f"Low-frequency smooth residual MAE={mean_lf:.2f}/255 (halo-ring MAE={mean_halo_mae:.2f}/255); "
                f"excess positive glow in highlight-halo rings vs background={mean_halo_lift:+.2f}/255 -> {status}."
            ),
            metrics={
                "lf_mae_255": mean_lf,
                "halo_ring_lf_mae_255": mean_halo_mae,
                "highlight_halo_excess_255": mean_halo_lift,
            },
            mask_of_interest=items[0][2].masks.active_mask,
        )

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {
            "threshold": 0.65,
            "softness": 0.10,
            "scales_frac": list(DEFAULT_SCALES_FRAC),
            "scale_weights": [0.45, 0.35, 0.20],
            "channel_widths": [1.0, 1.2, 1.4],
            "tint": [1.0, 1.0, 1.0],
            "intensity": 0.0,
            "blend": "screen",
            "aniso_xy": [1.0, 1.0],
        }

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
        intensity = float(params.get("intensity", 0.0))
        if intensity <= 1e-5:
            return x.copy()

        bright = extract_soft_knee_highlights(
            x,
            threshold=float(params.get("threshold", 0.65)),
            softness=float(params.get("softness", 0.10)),
        )
        if float(bright.max()) <= 1e-7:
            return x.copy()

        h = float(x.shape[0])
        scales = [float(s) for s in params.get("scales_frac", DEFAULT_SCALES_FRAC)]
        weights = np.maximum(np.asarray(params.get("scale_weights", [0.45, 0.35, 0.20]), dtype=np.float32), 0.0)
        w_sum = float(weights.sum())
        if w_sum <= 1e-7:
            return x.copy()
        weights = weights / w_sum

        ch_widths = [float(cw) for cw in params.get("channel_widths", [1.0, 1.2, 1.4])]
        aniso = params.get("aniso_xy", [1.0, 1.0])
        ax_mult, ay_mult = float(aniso[0]), float(aniso[1])

        bloom = np.zeros_like(x, dtype=np.float32)
        # If uniform channel widths, blur all 3 channels in one call; otherwise per-channel dispersion
        if abs(ch_widths[0] - ch_widths[1]) < 1e-3 and abs(ch_widths[1] - ch_widths[2]) < 1e-3:
            cw = ch_widths[0]
            for s_frac, wt in zip(scales, weights):
                if wt <= 1e-5:
                    continue
                sx = s_frac * cw * ax_mult * h
                sy = s_frac * cw * ay_mult * h
                bloom += float(wt) * _fast_gaussian_blur_frac(bright, sx, sy)
        else:
            for c in range(3):
                cw = ch_widths[c]
                bc = np.zeros(x.shape[:2], dtype=np.float32)
                for s_frac, wt in zip(scales, weights):
                    if wt <= 1e-5:
                        continue
                    sx = s_frac * cw * ax_mult * h
                    sy = s_frac * cw * ay_mult * h
                    bc += float(wt) * _fast_gaussian_blur_frac(bright[..., c], sx, sy)
                bloom[..., c] = bc

        tint = np.asarray(params.get("tint", [1.0, 1.0, 1.0]), dtype=np.float32)
        bloom_tinted = bloom * tint[None, None, :] * intensity
        return composite_bloom(x, bloom_tinted, str(params.get("blend", "screen")))

    def run_real_bloom_tests(
        self,
        params: Dict[str, Any],
        refs: Sequence[np.ndarray],
        tgts: Sequence[np.ndarray],
        ctxs: Sequence[Any],
    ) -> Dict[str, Any]:
        """Run the 3 mandatory real-bloom tests:
        1. Zero on a pure black frame (max output <= 1e-6).
        2. Stronger around bright shapes than dark areas on synthetic bright-circle test frame.
        3. Counterfactual mismatched-scene test: driving bloom from flipped scene highlights must NOT help as much.
        """
        # Test 1: Pure black frame
        black = np.zeros((128, 128, 3), dtype=np.float32)
        out_black = self.render(black, params)
        black_max = float(np.max(np.abs(out_black)))
        pass_black = black_max <= 1e-6

        # Test 2: Bright shape concentration
        synth = np.zeros((160, 160, 3), dtype=np.float32)
        cv2.circle(synth, (45, 45), 16, (0.98, 0.96, 0.92), -1)
        out_synth = self.render(synth, params)
        delta_s = luma_rec709(out_synth - synth)
        yy, xx = np.mgrid[0:160, 0:160]
        dist = np.hypot(xx - 45, yy - 45)
        near_ring = (dist > 17) & (dist <= 38)
        far_corner = dist > 95
        near_glow = float(delta_s[near_ring].mean())
        far_glow = float(delta_s[far_corner].mean())
        pass_bright_shape = (float(params.get("intensity", 0.0)) > 1e-4) and (near_glow > max(far_glow * 3.0, 1e-4))

        # Test 3: Counterfactual mismatched-scene test on actual pairs
        loss_before = self.loss(refs, tgts, ctxs, fold=None, train=True)
        preds_own = [self.render(r, params) for r in refs]
        loss_own = self.loss(preds_own, tgts, ctxs, fold=None, train=True)

        preds_mismatch = []
        for idx, r in enumerate(refs):
            # Take highlight field from 180-deg rotated + mirrored scene (wrong highlight locations!)
            wrong_src = r[::-1, ::-1].copy()
            wrong_bloom_only = self.render(wrong_src, params) - wrong_src
            preds_mismatch.append(np.clip(r + np.maximum(wrong_bloom_only, 0.0), 0.0, 1.0).astype(np.float32))
        loss_mismatch = self.loss(preds_mismatch, tgts, ctxs, fold=None, train=True)

        own_gain = loss_before - loss_own
        mismatch_gain = loss_before - loss_mismatch
        # Real bloom must genuinely outperform mismatched highlight positions
        pass_mismatch = (own_gain > 0.05) and (loss_mismatch > loss_own + 0.35 * max(own_gain, 0.05))

        return {
            "all_passed": bool(pass_black and pass_bright_shape and pass_mismatch),
            "zero_on_black_passed": bool(pass_black),
            "black_frame_max": black_max,
            "bright_shape_passed": bool(pass_bright_shape),
            "near_bright_glow": near_glow,
            "far_dark_glow": far_glow,
            "mismatched_scene_passed": bool(pass_mismatch),
            "loss_before": loss_before,
            "loss_own_highlights": loss_own,
            "loss_mismatched_highlights": loss_mismatch,
        }

    def loss(
        self,
        pred: ImageOrList,
        tgt: ImageOrList,
        ctx: ContextOrList = None,
        fold: Optional[int] = None,
        train: bool = False,
    ) -> float:
        items = normalize_pair_inputs(pred, tgt, ctx)
        scores = []
        for p_im, t_im, pctx in items:
            am = pctx.masks.active_mask
            if fold is not None:
                fm = (pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold)
                am = am & fm
            if int(am.sum()) < 50:
                continue
            h = p_im.shape[0]
            s_lf = max(5.0, 0.018 * h)
            p_lf = _fast_gaussian_blur_frac(p_im, s_lf, s_lf)
            t_lf = _fast_gaussian_blur_frac(t_im, s_lf, s_lf)
            rmse_lf = float(np.sqrt(np.mean(((p_lf[am] - t_lf[am]) * 255.0) ** 2)))
            scores.append(rmse_lf)
        return float(np.mean(scores)) if scores else 0.0

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        ev = self.detect(ref_in, tgt, ctx)
        n_folds = int(items[0][2].masks.block_folds.max()) + 1
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        if ev.status == "absent":
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
                notes=f"haze_flare: absent ({ev.notes})",
                diagnostics={"status": "absent", "evidence": ev.metrics},
            )

        # Downsample pairs to ~240p for super-fast global search over threshold, scales, blend, tint, dispersion
        small_refs, small_tgts, small_masks = [], [], []
        for r_im, t_im, pctx in items:
            h, w = t_im.shape[:2]
            ds = min(1.0, 240.0 / float(h))
            sh, sw = max(32, int(round(h * ds))), max(32, int(round(w * ds)))
            sr = cv2.resize(r_im, (sw, sh), interpolation=cv2.INTER_AREA)
            st = cv2.resize(t_im, (sw, sh), interpolation=cv2.INTER_AREA)
            sm = cv2.resize(pctx.masks.active_mask.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_NEAREST) > 0
            s_lf = max(2.0, 0.018 * sh)
            st_lf = _fast_gaussian_blur_frac(st, s_lf, s_lf)
            small_refs.append(sr)
            small_tgts.append(st_lf)
            small_masks.append(sm)

        scale_presets = [
            ([0.006, 0.018, 0.045], [0.50, 0.32, 0.18]),
            ([0.012, 0.032, 0.080], [0.40, 0.35, 0.25]),
            ([0.005, 0.015, 0.040, 0.095], [0.35, 0.30, 0.20, 0.15]),
        ]
        disp_presets = [
            [1.0, 1.0, 1.0],
            [1.0, 1.2, 1.4],
        ]

        best_s_loss = float("inf")
        for sr, st_lf, sm in zip(small_refs, small_tgts, small_masks):
            pass
        best_s_loss = float(np.mean([
            np.sqrt(np.mean(((_fast_gaussian_blur_frac(sr, max(2.0, 0.018 * sr.shape[0]), max(2.0, 0.018 * sr.shape[0]))[sm] - st_lf[sm]) * 255.0) ** 2))
            for sr, st_lf, sm in zip(small_refs, small_tgts, small_masks)
        ]))
        best_cfg = self.initial_guess(ref_in, tgt, ctx)

        for thr in (0.45, 0.60, 0.72, 0.84):
            for soft in (0.06, 0.15):
                for scales_f, s_wts in scale_presets:
                    for ch_w in disp_presets:
                        # Precompute un-tinted unit-intensity bloom fields on small_refs
                        blooms_unit = []
                        valid_any = False
                        for sr in small_refs:
                            br = extract_soft_knee_highlights(sr, thr, soft)
                            if float(br.max()) > 1e-5:
                                valid_any = True
                            sh_f = float(sr.shape[0])
                            bl = np.zeros_like(sr)
                            for c in range(3):
                                bc = np.zeros(sr.shape[:2], np.float32)
                                for sf, wt in zip(scales_f, s_wts):
                                    sig = sf * ch_w[c] * sh_f
                                    bc += wt * _fast_gaussian_blur_frac(br[..., c], sig, sig)
                                bl[..., c] = bc
                            blooms_unit.append(bl)
                        if not valid_any:
                            continue

                        # Estimate optimal per-channel tint * intensity directly from positive residual!
                        num_c = np.zeros(3, dtype=np.float64)
                        den_c = np.zeros(3, dtype=np.float64)
                        for sr, st_lf, sm, bl in zip(small_refs, small_tgts, small_masks, blooms_unit):
                            # For Screen: out - sr = bloom * (1 - sr)
                            eff_basis = bl[sm] * (1.0 - sr[sm])
                            res_pos = st_lf[sm] - sr[sm]
                            num_c += np.sum(eff_basis * res_pos, axis=0)
                            den_c += np.sum(eff_basis * eff_basis, axis=0) + 1e-6
                        gains_rgb = np.clip(num_c / den_c, 0.0, 2.0)
                        max_g = float(np.max(gains_rgb))
                        if max_g <= 0.02:
                            continue
                        tint_est = (gains_rgb / max_g).tolist()
                        int_est = min(2.0, max_g)

                        for blend in ("screen", "add", "soft_light"):
                            l_vals = []
                            for sr, st_lf, sm, bl in zip(small_refs, small_tgts, small_masks, blooms_unit):
                                comp = composite_bloom(sr, bl * np.asarray(tint_est, np.float32) * int_est, blend)
                                comp_lf = _fast_gaussian_blur_frac(comp, max(2.0, 0.018 * sr.shape[0]), max(2.0, 0.018 * sr.shape[0]))
                                l_vals.append(float(np.sqrt(np.mean(((comp_lf[sm] - st_lf[sm]) * 255.0) ** 2))))
                            m_loss = float(np.mean(l_vals))
                            if m_loss < best_s_loss:
                                best_s_loss = m_loss
                                best_cfg = {
                                    "threshold": float(thr),
                                    "softness": float(soft),
                                    "scales_frac": list(scales_f),
                                    "scale_weights": list(s_wts),
                                    "channel_widths": list(ch_w),
                                    "tint": [float(round(x, 4)) for x in tint_est],
                                    "intensity": float(int_est),
                                    "blend": blend,
                                    "aniso_xy": [1.0, 1.0],
                                }

        # Continuous Powell refinement of (threshold, softness, intensity, tint_r, tint_g, tint_b) on small_refs
        if best_cfg["intensity"] > 0.02:
            def _vec_to_cfg(v: np.ndarray) -> Dict[str, Any]:
                c = dict(best_cfg)
                c["threshold"] = float(np.clip(v[0], 0.30, 0.95))
                c["softness"] = float(np.clip(v[1], 0.01, 0.30))
                c["intensity"] = float(np.clip(v[2], 0.0, 2.0))
                t_raw = np.clip(v[3:6], 0.1, 1.0)
                t_max = float(np.max(t_raw))
                c["tint"] = (t_raw / max(t_max, 1e-4)).tolist()
                return c

            def _small_obj(v: np.ndarray) -> float:
                c = _vec_to_cfg(v)
                errs = []
                for sr, st_lf, sm in zip(small_refs, small_tgts, small_masks):
                    pr = self.render(sr, c)
                    pr_lf = _fast_gaussian_blur_frac(pr, max(2.0, 0.018 * sr.shape[0]), max(2.0, 0.018 * sr.shape[0]))
                    errs.append(float(np.sqrt(np.mean(((pr_lf[sm] - st_lf[sm]) * 255.0) ** 2))))
                return float(np.mean(errs))

            x0 = np.array(
                [best_cfg["threshold"], best_cfg["softness"], best_cfg["intensity"], *best_cfg["tint"]],
                dtype=np.float64,
            )
            opt = minimize(
                _small_obj,
                x0=x0,
                method="Powell",
                bounds=[(0.30, 0.95), (0.01, 0.30), (0.0, 2.0), (0.1, 1.0), (0.1, 1.0), (0.1, 1.0)],
                options={"maxiter": 10, "maxfev": 75, "ftol": 1e-3},
            )
            best_cfg = _vec_to_cfg(opt.x)

        # Evaluate 5-fold spatial 96px block CV at full resolution + mandatory real-bloom tests
        fold_after = []
        for f in range(n_folds):
            # Fit scalar intensity per fold on train blocks to prevent overfitting
            preds_unit_f = []
            for r_im in refs:
                p_u = dict(best_cfg)
                preds_unit_f.append(self.render(r_im, p_u) - r_im)

            num_f, den_f = 0.0, 0.0
            for r_im, t_im, pctx, d_bloom in zip(refs, tgts, ctxs, preds_unit_f):
                tr_m = pctx.masks.active_mask & (pctx.masks.block_folds != f)
                dv = d_bloom[tr_m]
                rv = (t_im - r_im)[tr_m]
                num_f += float(np.sum(dv * rv))
                den_f += float(np.sum(dv * dv)) + 1e-6
            scale_f = float(np.clip(num_f / max(den_f, 1e-6), 0.0, 1.5))
            prm_f = dict(best_cfg)
            prm_f["intensity"] = float(np.clip(best_cfg["intensity"] * scale_f, 0.0, 2.0))
            preds_val = [self.render(r_im, prm_f) for r_im in refs]
            fold_after.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

        ho_after = float(np.mean(fold_after))
        preds_full = [self.render(r_im, best_cfg) for r_im in refs]
        tr_after = self.loss(preds_full, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)

        bloom_tests = self.run_real_bloom_tests(best_cfg, refs, tgts, ctxs)
        accepted = (
            bool(bloom_tests["all_passed"])
            and (ho_after < ho_before - 0.12)
            and (rel_gain > 0.025)
        )

        if not accepted:
            reason = (
                f"haze_flare: absent/rejected (held-out LF RMSE {ho_before:.2f} -> {ho_after:.2f}, "
                f"real_bloom_tests={bloom_tests['all_passed']})."
            )
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
                notes=reason,
                diagnostics={"status": "absent", "candidate_params": best_cfg, "real_bloom_tests": bloom_tests},
            )

        return best_cfg, FitReport(
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
                f"Real highlight bloom verified: threshold={best_cfg['threshold']:.2f} (soft={best_cfg['softness']:.2f}), "
                f"intensity={best_cfg['intensity']:.2f}, blend={best_cfg['blend']}, "
                f"tint={[round(x, 2) for x in best_cfg['tint']]}, widths={best_cfg['channel_widths']}. "
                f"Held-out LF RMSE {ho_before:.2f} -> {ho_after:.2f} (passed all 3 real-bloom tests)."
            ),
            diagnostics={"status": "present", "real_bloom_tests": bloom_tests},
        )

    def glsl_taps(self, params: Dict[str, Any]) -> int:
        if float(params.get("intensity", 0.0)) <= 1e-5:
            return 0
        taps = get_bloom_glsl_taps(
            params.get("scales_frac", DEFAULT_SCALES_FRAC),
            params.get("scale_weights", [0.45, 0.35, 0.20]),
        )
        return max(0, len(taps) - 1)

    def to_glsl(self, params: Dict[str, Any]) -> str:
        intensity = float(params.get("intensity", 0.0))
        thr = float(params.get("threshold", 0.65))
        soft = max(float(params.get("softness", 0.10)), 1e-4)
        tint = params.get("tint", [1.0, 1.0, 1.0])
        ch_w = params.get("channel_widths", [1.0, 1.2, 1.4])
        blend = str(params.get("blend", "screen"))
        scales = params.get("scales_frac", DEFAULT_SCALES_FRAC)[:5]
        weights = params.get("scale_weights", [0.45, 0.35, 0.20])[: len(scales)]
        taps = get_bloom_glsl_taps(scales, weights)

        lines = [
            f"// --- Plugin: haze_flare (real highlight bloom, {max(0, len(taps)-1)} extra taps, blend={blend}) ---",
            "// Expects helper: vec3 msFetchGraded(vec2 uv);",
        ]
        if intensity <= 1e-5 or not taps:
            lines.append("vec3 msApplyHazeFlare(vec3 baseCol, vec2 uv, vec2 texelSize) { return baseCol; }")
            return "\n".join(lines)

        lo = thr - soft
        hi = thr + soft
        mean_cw = float(np.mean(ch_w))

        lines.append(f"""vec3 msHighlightPass(vec3 x) {{
    float luma = dot(x, vec3(0.2126, 0.7152, 0.0722));
    float mx = max(max(x.r, x.g), x.b);
    float m = 0.5 * luma + 0.5 * mx;
    float ex = 0.0;
    if (m >= {hi:.6f}) {{
        ex = m - {thr:.6f};
    }} else if (m > {lo:.6f}) {{
        float dm = m - {lo:.6f};
        ex = (dm * dm) / {4.0 * soft:.6f};
    }}
    return x * (max(ex, 0.0) / max(m, 0.0001));
}}""")

        lines.append("vec3 msApplyHazeFlare(vec3 baseCol, vec2 uv, vec2 texelSize) {")
        lines.append("    float invAspect = texelSize.x / max(texelSize.y, 0.00001);")
        lines.append(f"    vec3 bloom = {taps[0][2]:.6f} * msHighlightPass(baseCol);")
        for dx_h, dy_h, wt in taps[1:]:
            dx_use = dx_h * mean_cw
            dy_use = dy_h * mean_cw
            lines.append(
                f"    bloom += {wt:.6f} * msHighlightPass(msFetchGraded(uv + vec2({dx_use:.6f} * invAspect, {dy_use:.6f})));"
            )
        lines.append(f"    bloom = clamp(bloom * vec3({tint[0]:.6f}, {tint[1]:.6f}, {tint[2]:.6f}) * {intensity:.6f}, 0.0, 1.0);")
        if blend == "add":
            lines.append("    return clamp(baseCol + bloom, 0.0, 1.0);")
        elif blend == "soft_light":
            lines.append("    vec3 sl = baseCol + bloom * (sqrt(max(baseCol, vec3(0.0))) - baseCol);")
            lines.append("    vec3 sc = vec3(1.0) - (vec3(1.0) - baseCol) * (vec3(1.0) - bloom);")
            lines.append("    return clamp(0.5 * sl + 0.5 * sc, 0.0, 1.0);")
        else:
            lines.append("    return clamp(vec3(1.0) - (vec3(1.0) - baseCol) * (vec3(1.0) - bloom), 0.0, 1.0);")
        lines.append("}")
        return "\n".join(lines)

    def describe(self, params: Dict[str, Any]) -> str:
        if float(params.get("intensity", 0.0)) <= 1e-5:
            return "Haze Flare: absent (smooth residual within error after colour and sharpening)."
        return (
            f"Haze Flare (real highlight bloom): threshold={float(params['threshold']):.2f} "
            f"(softness={float(params['softness']):.2f}), scales={[round(s*100, 2) for s in params['scales_frac']]}% height, "
            f"R:G:B widths={params['channel_widths']}, tint={[round(x, 2) for x in params['tint']]}, "
            f"intensity={float(params['intensity']):.2f}, blend='{params['blend']}'."
        )
