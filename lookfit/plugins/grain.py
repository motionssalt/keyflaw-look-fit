"""Film grain plugin: flat-area noise & blockiness detector, statistics-matching fitter, and GLSL exporter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

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


def _hp_gain_sigma(sigma: float = 1.4) -> float:
    imp = np.zeros((15, 15), dtype=np.float32)
    imp[7, 7] = 1.0
    hp = imp - cv2.GaussianBlur(imp, (0, 0), sigma)
    return float(np.sqrt(np.sum(hp * hp)))


_HP_GAIN_14 = _hp_gain_sigma(1.4)


def _blur_unit_norm(sigma_px: float) -> float:
    if sigma_px <= 0.38:
        return 1.0
    r = max(7, int(np.ceil(sigma_px * 4.0)))
    sz = 2 * r + 1
    imp = np.zeros((sz, sz), dtype=np.float32)
    imp[r, r] = 1.0
    b = cv2.GaussianBlur(imp, (0, 0), sigmaX=sigma_px, sigmaY=sigma_px)
    return max(float(np.sqrt(np.sum(b * b))), 1e-6)


def _mad_std_255(vals: np.ndarray) -> float:
    if vals.size < 24:
        return 0.0
    med = float(np.median(vals))
    return float(1.4826 * np.median(np.abs(vals - med)) * 255.0)


def _compute_grain_signature(img_rgb: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
    """Extract distributional flat-area high-frequency statistics on `mask`."""
    img_l = luma_rec709(img_rgb)
    hp_l = (img_l - cv2.GaussianBlur(img_l, (0, 0), 1.4)) / _HP_GAIN_14
    hp_rgb = (img_rgb - cv2.GaussianBlur(img_rgb, (0, 0), 1.4)) / _HP_GAIN_14

    if int(mask.sum()) < 120:
        return {
            "luma_std_255": 0.0,
            "chroma_std_255": 0.0,
            "bin_stds_255": [0.0] * 5,
            "bin_counts": [0] * 5,
            "corr_lag1": 0.0,
            "corr_lag2": 0.0,
            "blockiness_ratio": 1.0,
        }

    luma_std = _mad_std_255(hp_l[mask])
    # Chroma residual: R - G and B - G high-pass differences
    rg_diff = (hp_rgb[..., 0] - hp_rgb[..., 1]) / np.sqrt(2.0)
    bg_diff = (hp_rgb[..., 2] - hp_rgb[..., 1]) / np.sqrt(2.0)
    chroma_std = 0.5 * (_mad_std_255(rg_diff[mask]) + _mad_std_255(bg_diff[mask]))

    bins = np.linspace(0.0, 1.0, 6)
    bin_stds: List[float] = []
    bin_counts: List[int] = []
    for i in range(5):
        hi = bins[i + 1] + (1e-4 if i == 4 else 0.0)
        bm = mask & (img_l >= bins[i]) & (img_l < hi)
        cnt = int(bm.sum())
        bin_counts.append(cnt)
        bin_stds.append(_mad_std_255(hp_l[bm]) if cnt >= 50 else luma_std)

    # Lag-1 and Lag-2 spatial autocorrelation along rows & cols inside mask
    def _lag_corr(lag: int) -> float:
        corrs = []
        mh = mask[:, :-lag] & mask[:, lag:]
        if int(mh.sum()) > 150:
            a, b = hp_l[:, :-lag][mh], hp_l[:, lag:][mh]
            if float(a.std()) > 1e-6 and float(b.std()) > 1e-6:
                corrs.append(float(np.corrcoef(a, b)[0, 1]))
        mv = mask[:-lag, :] & mask[lag:, :]
        if int(mv.sum()) > 150:
            a, b = hp_l[:-lag, :][mv], hp_l[lag:, :][mv]
            if float(a.std()) > 1e-6 and float(b.std()) > 1e-6:
                corrs.append(float(np.corrcoef(a, b)[0, 1]))
        return float(np.mean(corrs)) if corrs else 0.0

    corr1 = _lag_corr(1)
    corr2 = _lag_corr(2)

    # 8x8 DCT blockiness in X and Y
    h, w = img_l.shape
    ratios = []
    dx = np.abs(img_l[:, 1:] - img_l[:, :-1])
    mdx = mask[:, 1:] & mask[:, :-1]
    is_bx = np.broadcast_to((np.arange(1, w)[None, :] % 8) == 0, dx.shape)
    bx_v, nbx_v = dx[mdx & is_bx], dx[mdx & (~is_bx)]
    if bx_v.size > 40 and nbx_v.size > 40 and float(nbx_v.mean()) > 1e-6:
        ratios.append(float(bx_v.mean() / nbx_v.mean()))

    dy = np.abs(img_l[1:, :] - img_l[:-1, :])
    mdy = mask[1:, :] & mask[:-1, :]
    is_by = np.broadcast_to((np.arange(1, h)[:, None] % 8) == 0, dy.shape)
    by_v, nby_v = dy[mdy & is_by], dy[mdy & (~is_by)]
    if by_v.size > 40 and nby_v.size > 40 and float(nby_v.mean()) > 1e-6:
        ratios.append(float(by_v.mean() / nby_v.mean()))

    blockiness = float(max(ratios)) if ratios else 1.0
    return {
        "luma_std_255": luma_std,
        "chroma_std_255": chroma_std,
        "bin_stds_255": bin_stds,
        "bin_counts": bin_counts,
        "corr_lag1": corr1,
        "corr_lag2": corr2,
        "blockiness_ratio": blockiness,
    }


def _luma_envelope(luma: np.ndarray, sh_w: float, mid_w: float, hi_w: float) -> np.ndarray:
    y = np.clip(luma, 0.0, 1.0)
    om = 1.0 - y
    return (sh_w * (om * om) + mid_w * (2.0 * y * om) + hi_w * (y * y)).astype(np.float32)


class GrainPlugin(Plugin):
    name = "grain"
    param_spec = [
        ParamSpec("amount_255", 0.0, 0.0, 25.0, "std_255", "0_255_gate", "Grain standard deviation at unit luma envelope (/255)"),
        ParamSpec("size_frac", 0.0010, 0.0005, 0.0055, "height_frac", "fraction_of_height", "Spatial Gaussian grain correlation sigma as fraction of height"),
        ParamSpec("shadow_weight", 0.70, 0.0, 2.0, "gain", "dimensionless", "Shadow luma grain envelope weight"),
        ParamSpec("midtone_weight", 1.00, 0.1, 2.0, "gain", "dimensionless", "Midtone luma grain envelope weight"),
        ParamSpec("highlight_weight", 0.50, 0.0, 2.0, "gain", "dimensionless", "Highlight luma grain envelope weight"),
        ParamSpec("chroma_mix", 0.0, 0.0, 1.0, "ratio", "dimensionless", "0 = monochrome film grain, 1 = independent per-channel RGB grain"),
    ]

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {
            "amount_255": 0.0,
            "size_frac": 0.0010,
            "shadow_weight": 0.80,
            "midtone_weight": 1.00,
            "highlight_weight": 0.60,
            "chroma_mix": 0.0,
            "seed": 1337,
        }

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        excess_stds: List[float] = []
        blockiness_list: List[float] = []
        positive_block_fracs: List[float] = []

        for r_im, t_im, pctx in items:
            fm = pctx.masks.flat_mask
            if int(fm.sum()) < 200:
                continue
            sig_r = _compute_grain_signature(r_im, fm)
            sig_t = _compute_grain_signature(t_im, fm)
            ex_std = float(np.sqrt(max(0.0, sig_t["luma_std_255"] ** 2 - sig_r["luma_std_255"] ** 2)))
            excess_stds.append(ex_std)
            blockiness_list.append(sig_t["blockiness_ratio"])

            # Check spatial ubiquity across 96x96 blocks: real grain covers most flat blocks
            rl = luma_rec709(r_im)
            tl = luma_rec709(t_im)
            hp_r = (rl - cv2.GaussianBlur(rl, (0, 0), 1.4)) / _HP_GAIN_14
            hp_t = (tl - cv2.GaussianBlur(tl, (0, 0), 1.4)) / _HP_GAIN_14
            h, w = tl.shape
            pos_blocks, tot_blocks = 0, 0
            for by in range(0, h, 96):
                for bx in range(0, w, 96):
                    sub_m = fm[by : by + 96, bx : bx + 96]
                    if int(sub_m.sum()) >= 80:
                        tot_blocks += 1
                        sr_b = _mad_std_255(hp_r[by : by + 96, bx : bx + 96][sub_m])
                        st_b = _mad_std_255(hp_t[by : by + 96, bx : bx + 96][sub_m])
                        if st_b > sr_b + 0.65:
                            pos_blocks += 1
            positive_block_fracs.append(float(pos_blocks) / max(tot_blocks, 1))

        mean_ex = float(np.mean(excess_stds)) if excess_stds else 0.0
        max_blk = float(np.max(blockiness_list)) if blockiness_list else 1.0
        mean_ubiq = float(np.mean(positive_block_fracs)) if positive_block_fracs else 0.0

        if max_blk > 1.22:
            return Evidence(
                plugin_name=self.name,
                status="not_provable",
                score=0.0,
                notes=(
                    f"not provable: flat-area noise shows 8x8 recompression blockiness "
                    f"(blockiness_ratio={max_blk:.2f} > 1.22, excess_std={mean_ex:.2f}/255); skipping grain."
                ),
                metrics={"excess_std_255": mean_ex, "blockiness_ratio": max_blk, "flat_block_ubiquity": mean_ubiq},
                mask_of_interest=items[0][2].masks.flat_mask,
            )

        if mean_ex < 1.25 or mean_ubiq < 0.60:
            return Evidence(
                plugin_name=self.name,
                status="not_provable",
                score=float(mean_ex),
                notes=(
                    f"not provable: excess flat-area noise is weak or non-uniform "
                    f"(excess_std={mean_ex:.2f}/255, flat_block_ubiquity={mean_ubiq:.2f}); not adding grain."
                ),
                metrics={"excess_std_255": mean_ex, "blockiness_ratio": max_blk, "flat_block_ubiquity": mean_ubiq},
                mask_of_interest=items[0][2].masks.flat_mask,
            )

        return Evidence(
            plugin_name=self.name,
            status="present",
            score=float(mean_ex),
            notes=(
                f"Detected spatially uniform non-blocky excess flat grain "
                f"(excess_std={mean_ex:.2f}/255, ubiquity={mean_ubiq:.2f}, blockiness={max_blk:.2f})."
            ),
            metrics={"excess_std_255": mean_ex, "blockiness_ratio": max_blk, "flat_block_ubiquity": mean_ubiq},
            mask_of_interest=items[0][2].masks.flat_mask,
        )

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        amt = float(params.get("amount_255", 0.0))
        if amt <= 1e-4:
            return np.clip(img, 0.0, 1.0).astype(np.float32)

        h, w = img.shape[:2]
        seed = int(params.get("seed", 1337))
        rng = np.random.default_rng(seed)

        sigma_px = float(params.get("size_frac", 0.0010)) * float(h)
        norm_div = _blur_unit_norm(sigma_px)

        def _make_sized(channels: int) -> np.ndarray:
            raw = rng.standard_normal((h, w, channels), dtype=np.float32)
            if sigma_px > 0.38:
                blurred = cv2.GaussianBlur(raw, (0, 0), sigmaX=sigma_px, sigmaY=sigma_px)
                if blurred.ndim == 2:
                    blurred = blurred[..., None]
                return (blurred / norm_div).astype(np.float32)
            return raw

        n_mono = _make_sized(1)
        cmix = float(np.clip(params.get("chroma_mix", 0.0), 0.0, 1.0))
        if cmix <= 1e-4:
            n_field = np.repeat(n_mono, 3, axis=-1)
        else:
            n_rgb = _make_sized(3)
            denom = float(np.sqrt((1.0 - cmix) ** 2 + cmix ** 2))
            n_field = ((1.0 - cmix) * n_mono + cmix * n_rgb) / max(denom, 1e-6)

        env = _luma_envelope(
            luma_rec709(img),
            float(params.get("shadow_weight", 0.80)),
            float(params.get("midtone_weight", 1.00)),
            float(params.get("highlight_weight", 0.60)),
        )
        out = img.astype(np.float32) + (amt / 255.0) * env[..., None] * n_field
        return np.clip(out, 0.0, 1.0).astype(np.float32)

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
            fm = pctx.masks.flat_mask
            if fold is not None:
                if train:
                    fm = fm & (pctx.masks.block_folds != fold)
                else:
                    fm = fm & (pctx.masks.block_folds == fold)
            if int(fm.sum()) < 100:
                fm = pctx.masks.flat_mask
            sp = _compute_grain_signature(p_im, fm)
            st = _compute_grain_signature(t_im, fm)

            std_err = abs(sp["luma_std_255"] - st["luma_std_255"])
            # Weighted luma-bin std RMSE across populated tonal bands
            bin_sq, bin_w = 0.0, 0.0
            for bp, bt, cnt in zip(sp["bin_stds_255"], st["bin_stds_255"], st["bin_counts"]):
                wt = 1.0 if cnt >= 50 else 0.15
                bin_sq += wt * ((bp - bt) ** 2)
                bin_w += wt
            bin_rmse = float(np.sqrt(bin_sq / max(bin_w, 1e-6)))

            corr_err = 12.0 * (abs(sp["corr_lag1"] - st["corr_lag1"]) + 0.7 * abs(sp["corr_lag2"] - st["corr_lag2"]))
            chroma_err = 0.6 * abs(sp["chroma_std_255"] - st["chroma_std_255"])
            errs.append(0.45 * std_err + 0.35 * bin_rmse + corr_err + chroma_err)
        return float(np.mean(errs)) if errs else 0.0

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]

        ev = self.detect(refs, tgts, ctxs)
        n_folds = int(items[0][2].masks.block_folds.max()) + 1
        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        if ev.status != "present":
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
                notes=ev.notes,
                diagnostics={"status": "not_provable", "evidence": ev.metrics},
            )

        # Estimate initial luma weights, chroma_mix, and size_frac from excess statistics
        ex_bins_accum = [[] for _ in range(5)]
        chroma_ratios = []
        lag1_vals = []
        for r_im, t_im, pctx in items:
            sr = _compute_grain_signature(r_im, pctx.masks.flat_mask)
            st = _compute_grain_signature(t_im, pctx.masks.flat_mask)
            for b_idx in range(5):
                if st["bin_counts"][b_idx] >= 50:
                    ex_b = float(np.sqrt(max(0.0, st["bin_stds_255"][b_idx] ** 2 - sr["bin_stds_255"][b_idx] ** 2)))
                    ex_bins_accum[b_idx].append(ex_b)
            ex_l = max(0.2, float(np.sqrt(max(0.0, st["luma_std_255"] ** 2 - sr["luma_std_255"] ** 2))))
            ex_c = float(np.sqrt(max(0.0, st["chroma_std_255"] ** 2 - sr["chroma_std_255"] ** 2)))
            chroma_ratios.append(float(np.clip(ex_c / max(ex_l, 0.2), 0.0, 1.0)))
            lag1_vals.append(max(0.0, st["corr_lag1"]))

        mean_ex_std = float(ev.metrics.get("excess_std_255", 2.0))
        bin_means = [float(np.mean(b)) if b else mean_ex_std for b in ex_bins_accum]
        mid_est = max(0.3, float(np.mean(bin_means[1:4])))
        sh_init = float(np.clip(bin_means[0] / mid_est, 0.2, 1.8))
        hi_init = float(np.clip(bin_means[4] / mid_est, 0.2, 1.8))
        cmix_init = float(np.clip(np.mean(chroma_ratios), 0.0, 1.0)) if chroma_ratios else 0.0

        # Screen size_frac candidates first (since spatial lag correlation depends on size_frac)
        size_cands = [0.0006, 0.0011, 0.0017, 0.0025, 0.0036]
        best_size = 0.0011
        best_screen_loss = float("inf")
        for sc in size_cands:
            cand_p = {
                "amount_255": mid_est,
                "size_frac": sc,
                "shadow_weight": sh_init,
                "midtone_weight": 1.0,
                "highlight_weight": hi_init,
                "chroma_mix": cmix_init,
                "seed": 2027,
            }
            preds_sc = [self.render(r_im, cand_p) for r_im in refs]
            l_sc = self.loss(preds_sc, tgts, ctxs, fold=None, train=True)
            if l_sc < best_screen_loss:
                best_screen_loss = l_sc
                best_size = sc

        def _vec_to_params(v: np.ndarray, seed: int = 2027) -> Dict[str, Any]:
            return {
                "amount_255": float(np.clip(v[0], 0.0, 25.0)),
                "size_frac": float(np.clip(v[1], 0.0005, 0.0055)),
                "shadow_weight": float(np.clip(v[2], 0.05, 2.0)),
                "midtone_weight": 1.0,
                "highlight_weight": float(np.clip(v[3], 0.05, 2.0)),
                "chroma_mix": float(np.clip(v[4], 0.0, 1.0)),
                "seed": seed,
            }

        x0 = np.array([mid_est, best_size, sh_init, hi_init, cmix_init], dtype=np.float64)
        bounds = [(0.0, 25.0), (0.0005, 0.0055), (0.05, 2.0), (0.05, 2.0), (0.0, 1.0)]

        def _obj_full(v: np.ndarray) -> float:
            prm = _vec_to_params(v, seed=2027)
            preds = [self.render(r_im, prm) for r_im in refs]
            return self.loss(preds, tgts, ctxs, fold=None, train=True)

        opt = minimize(_obj_full, x0=x0, method="Powell", bounds=bounds, options={"maxiter": 10, "maxfev": 70, "ftol": 1e-3})
        fitted_params = _vec_to_params(opt.x, seed=1337)

        # Evaluate 5-fold block CV (fitting scalar amount per fold on train blocks)
        fold_after: List[float] = []
        for f in range(n_folds):
            def _obj_f(amt_val: float) -> float:
                pf = dict(fitted_params)
                pf["amount_255"] = float(np.clip(amt_val, 0.0, 25.0))
                pf["seed"] = 3000 + f
                preds_f = [self.render(r_im, pf) for r_im in refs]
                return self.loss(preds_f, tgts, ctxs, fold=f, train=True)

            from scipy.optimize import minimize_scalar
            rf = minimize_scalar(_obj_f, bounds=(0.0, 25.0), method="bounded", options={"xatol": 0.05})
            pf_val = dict(fitted_params)
            pf_val["amount_255"] = float(np.clip(rf.x, 0.0, 25.0))
            pf_val["seed"] = 4000 + f
            preds_val = [self.render(r_im, pf_val) for r_im in refs]
            fold_after.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

        ho_after = float(np.mean(fold_after))
        preds_final = [self.render(r_im, fitted_params) for r_im in refs]
        tr_after = self.loss(preds_final, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)

        accepted = (fitted_params["amount_255"] >= 1.0) and (ho_after < ho_before - 0.15) and (rel_gain > 0.08)
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
                notes=f"not provable: grain statistics fit did not improve held-out blocks sufficiently ({ho_before:.2f} -> {ho_after:.2f}).",
                diagnostics={"status": "not_provable", "candidate_params": fitted_params},
            )

        return fitted_params, FitReport(
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
                f"Film grain matched by flat-area statistics: amount={fitted_params['amount_255']:.2f}/255, "
                f"size={fitted_params['size_frac']*100:.3f}% height, "
                f"luma_env=[{fitted_params['shadow_weight']:.2f}, 1.00, {fitted_params['highlight_weight']:.2f}], "
                f"chroma_mix={fitted_params['chroma_mix']:.2f}."
            ),
            diagnostics={"status": "present", "evidence": ev.metrics},
        )

    def to_glsl(self, params: Dict[str, Any]) -> str:
        amt = float(params.get("amount_255", 0.0))
        if amt <= 1e-4:
            return (
                "// --- Plugin: grain (not provable / inactive, 0 taps) ---\n"
                "vec3 msApplyGrain(vec3 col, vec2 uv, vec2 texelSize, float timeSec) { return col; }"
            )

        s_frac = float(params.get("size_frac", 0.0010))
        sh_w = float(params.get("shadow_weight", 0.80))
        mid_w = float(params.get("midtone_weight", 1.00))
        hi_w = float(params.get("highlight_weight", 0.60))
        cmix = float(np.clip(params.get("chroma_mix", 0.0), 0.0, 1.0))
        amp01 = amt / 255.0
        # Map Gaussian sigma fraction to bilinear cell pitch; 1.85x compensates bilinear variance attenuation
        cell_frac = max(0.0007, s_frac * 2.1)

        return f"""// --- Plugin: grain (luma-modulated sized triangular-Gaussian hash noise, 0 extra taps) ---
float msGrainHash(vec2 p) {{
    vec2 q = mod(p, 289.0);
    return fract(sin(dot(q, vec2(12.9898, 78.233))) * 43758.5453);
}}
float msGrainTriValue(vec2 gridPos, float seedOff) {{
    vec2 i = floor(gridPos);
    vec2 f = fract(gridPos);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = msGrainHash(i + vec2(0.0, 0.0) + seedOff) + msGrainHash(i + vec2(17.0, 31.0) + seedOff) - 1.0;
    float b = msGrainHash(i + vec2(1.0, 0.0) + seedOff) + msGrainHash(i + vec2(18.0, 31.0) + seedOff) - 1.0;
    float c = msGrainHash(i + vec2(0.0, 1.0) + seedOff) + msGrainHash(i + vec2(17.0, 32.0) + seedOff) - 1.0;
    float d = msGrainHash(i + vec2(1.0, 1.0) + seedOff) + msGrainHash(i + vec2(18.0, 32.0) + seedOff) - 1.0;
    float v = mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
    return v * 3.15;
}}
vec3 msApplyGrain(vec3 col, vec2 uv, vec2 texelSize, float timeSec) {{
    float frameH = 1.0 / max(texelSize.y, 0.0001);
    float cellPx = max(1.0, {cell_frac:.6f} * frameH);
    vec2 gridPos = uv / max(texelSize * cellPx, vec2(0.00001));
    float frameTick = mod(floor(max(timeSec, 0.0) * 24.0), 60.0);
    float nMono = msGrainTriValue(gridPos, frameTick * 1.73);
    vec3 nVec = vec3(nMono);
    if ({cmix:.6f} > 0.001) {{
        vec3 nRgb = vec3(
            msGrainTriValue(gridPos + vec2(11.3, 5.7), frameTick * 1.73),
            msGrainTriValue(gridPos + vec2(23.1, 19.4), frameTick * 1.73),
            msGrainTriValue(gridPos + vec2(37.9, 41.2), frameTick * 1.73)
        );
        float denom = max(sqrt((1.0 - {cmix:.6f}) * (1.0 - {cmix:.6f}) + {cmix:.6f} * {cmix:.6f}), 0.0001);
        nVec = ((1.0 - {cmix:.6f}) * vec3(nMono) + {cmix:.6f} * nRgb) / denom;
    }}
    float y = clamp(dot(col, vec3(0.2126, 0.7152, 0.0722)), 0.0, 1.0);
    float om = 1.0 - y;
    float env = {sh_w:.6f} * (om * om) + {mid_w:.6f} * (2.0 * y * om) + {hi_w:.6f} * (y * y);
    return clamp(col + {amp01:.6f} * env * nVec, 0.0, 1.0);
}}"""

    def describe(self, params: Dict[str, Any]) -> str:
        amt = float(params.get("amount_255", 0.0))
        if amt <= 1e-4:
            return "Grain: not provable (flat-area excess noise absent or dominated by recompression)."
        return (
            f"Film Grain (statistics-matched): std={amt:.2f}/255, size={float(params['size_frac'])*100:.3f}% height, "
            f"luma envelope=[shadow {float(params['shadow_weight']):.2f}, mid {float(params['midtone_weight']):.2f}, "
            f"high {float(params['highlight_weight']):.2f}], chroma_mix={float(params['chroma_mix']):.2f}."
        )
