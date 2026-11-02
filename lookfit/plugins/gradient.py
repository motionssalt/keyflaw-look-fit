"""Linear/vertical smoothstep multiply or tint gradient plugin (yTop = 1.0 - vTex.y aware)."""

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


def _smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    span = max(float(edge1) - float(edge0), 0.04)
    u = np.clip((x - float(edge0)) / span, 0.0, 1.0)
    return (u * u * (3.0 - 2.0 * u)).astype(np.float32)


def _gradient_ramp(shape_hw: Tuple[int, int], angle_deg: float, start: float, end: float) -> np.ndarray:
    h, w = shape_hw
    x_norm = ((np.arange(w, dtype=np.float32) + 0.5) / float(w))[None, :]
    y_top = ((np.arange(h, dtype=np.float32) + 0.5) / float(h))[:, None]
    rad = np.deg2rad(float(angle_deg))
    t = 0.5 + (x_norm - 0.5) * float(np.cos(rad)) + (y_top - 0.5) * float(np.sin(rad))
    return _smoothstep(start, end, t)


def _blur_lf(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    ds = max(1, min(w, h) // 180)
    if ds > 1:
        sw, sh = max(16, w // ds), max(16, h // ds)
        sm = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
        sm_b = cv2.GaussianBlur(sm, (0, 0), max(1.5, 0.03 * sh))
        return cv2.resize(sm_b, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    return cv2.GaussianBlur(img, (0, 0), max(2.0, 0.03 * h)).astype(np.float32)


class GradientPlugin(Plugin):
    name = "gradient"
    param_spec = [
        ParamSpec("angle_deg", 90.0, -180.0, 180.0, "deg", "dimensionless", "Gradient direction in (xNorm, yTop): 90 = top-to-bottom"),
        ParamSpec("start", 0.15, -0.20, 0.85, "pos_0_1", "dimensionless", "Smoothstep start position along gradient axis"),
        ParamSpec("end", 0.85, 0.15, 1.20, "pos_0_1", "dimensionless", "Smoothstep end position along gradient axis"),
        ParamSpec("mode", "multiply", None, None, "enum", "categorical", "Composite mode: 'multiply' or 'tint'"),
        ParamSpec("strength_rgb", [0.0, 0.0, 0.0], -0.65, 0.65, "rgb_delta", "rgb_0_1", "Per-channel strength at ramp=1"),
    ]

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {
            "angle_deg": 90.0,
            "start": 0.15,
            "end": 0.85,
            "mode": "multiply",
            "strength_rgb": [0.0, 0.0, 0.0],
        }

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        best_r2_all: List[float] = []
        amp_255_all: List[float] = []

        # Measure coherent linear plane trend in smooth residual across pairs
        for r_im, t_im, pctx in items:
            am = pctx.masks.active_mask
            if int(am.sum()) < 200:
                continue
            res_lf = _blur_lf(t_im - r_im)
            h, w = t_im.shape[:2]
            x_n = np.broadcast_to(((np.arange(w, dtype=np.float32) + 0.5) / w)[None, :], (h, w))[am] - 0.5
            y_n = np.broadcast_to(((np.arange(h, dtype=np.float32) + 0.5) / h)[:, None], (h, w))[am] - 0.5
            X = np.column_stack([np.ones_like(x_n), x_n, y_n])
            Y = res_lf[am]
            # Fit linear plane per channel; check zero-mean slope component (excluding constant offset)
            coef, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
            plane_only = X[:, 1:] @ coef[1:, :]
            slope_rms_255 = float(np.sqrt(np.mean(plane_only ** 2)) * 255.0)
            tot_var = float(np.mean((Y - Y.mean(axis=0, keepdims=True)) ** 2)) + 1e-8
            r2 = float(np.mean(plane_only ** 2) / tot_var)
            best_r2_all.append(r2)
            amp_255_all.append(slope_rms_255 * 2.0)

        mean_amp = float(np.mean(amp_255_all)) if amp_255_all else 0.0
        mean_r2 = float(np.mean(best_r2_all)) if best_r2_all else 0.0

        if mean_amp >= 2.2 and mean_r2 >= 0.14:
            status = "present"
        elif mean_amp >= 1.3 and mean_r2 >= 0.08:
            status = "weak"
        else:
            status = "absent"

        return Evidence(
            plugin_name=self.name,
            status=status,
            score=float(mean_amp * max(mean_r2, 0.05)),
            notes=(
                f"Low-frequency directional gradient check: peak-to-peak amp={mean_amp:.2f}/255, "
                f"linear plane R^2={mean_r2:.3f} -> {status}."
            ),
            metrics={"linear_amp_255": mean_amp, "linear_r2": mean_r2},
            mask_of_interest=items[0][2].masks.active_mask,
        )

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        strength = np.asarray(params.get("strength_rgb", [0.0, 0.0, 0.0]), dtype=np.float32)
        if float(np.max(np.abs(strength))) <= 1e-5:
            return np.clip(img, 0.0, 1.0).astype(np.float32)

        ramp = _gradient_ramp(
            img.shape[:2],
            float(params.get("angle_deg", 90.0)),
            float(params.get("start", 0.15)),
            float(params.get("end", 0.85)),
        )[..., None]

        mode = str(params.get("mode", "multiply"))
        x = np.clip(img, 0.0, 1.0).astype(np.float32)
        if mode == "tint":
            out = x + ramp * strength[None, None, :]
        else:
            out = x * (1.0 + ramp * strength[None, None, :])
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
            am = pctx.masks.active_mask
            if fold is not None:
                am = am & ((pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold))
            if int(am.sum()) < 50:
                am = pctx.masks.active_mask
            p_lf = _blur_lf(p_im)
            t_lf = _blur_lf(t_im)
            rmse_255 = float(np.sqrt(np.mean(((p_lf[am] - t_lf[am]) * 255.0) ** 2)))
            errs.append(rmse_255)
        return float(np.mean(errs)) if errs else 0.0

    def _solve_strength_closed_form(
        self,
        refs_lf: List[np.ndarray],
        tgts_lf: List[np.ndarray],
        masks: List[np.ndarray],
        angle_deg: float,
        start: float,
        end: float,
        mode: str,
    ) -> np.ndarray:
        num = np.zeros(3, dtype=np.float64)
        den = np.zeros(3, dtype=np.float64) + 1e-3
        lim = 0.35 if mode == "tint" else 0.65
        for r_lf, t_lf, m in zip(refs_lf, tgts_lf, masks):
            if int(m.sum()) < 20:
                continue
            s = _gradient_ramp(r_lf.shape[:2], angle_deg, start, end)[m]  # (N,)
            diff = (t_lf[m] - r_lf[m]).astype(np.float64)  # (N, 3)
            if mode == "tint":
                basis = s[:, None]
            else:
                basis = s[:, None] * r_lf[m].astype(np.float64)
            num += np.sum(basis * diff, axis=0)
            den += np.sum(basis * basis, axis=0) + 0.02 * basis.shape[0] * 1e-3
        return np.clip(num / den, -lim, lim).astype(np.float32)

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]
        n_folds = int(items[0][2].masks.block_folds.max()) + 1

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        # Downsample LF images for fast screening & Powell refinement
        small_refs, small_tgts, small_masks = [], [], []
        for r_im, t_im, pctx in items:
            h, w = t_im.shape[:2]
            sw = min(240, w)
            sh = max(32, int(round(h * (sw / float(w)))))
            sr = cv2.resize(_blur_lf(r_im), (sw, sh), interpolation=cv2.INTER_AREA)
            st = cv2.resize(_blur_lf(t_im), (sw, sh), interpolation=cv2.INTER_AREA)
            sm = cv2.resize(pctx.masks.active_mask.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_NEAREST) > 0
            small_refs.append(sr)
            small_tgts.append(st)
            small_masks.append(sm)

        best_mode = "multiply"
        best_vec = np.array([90.0, 0.15, 0.85], dtype=np.float64)
        best_small_err = float("inf")

        for mode in ("multiply", "tint"):
            for ang in (90.0, -90.0, 0.0, 180.0, 45.0, -45.0, 135.0, -135.0):
                for st_p, en_p in ((0.0, 1.0), (0.15, 0.85), (0.0, 0.55), (0.45, 1.0)):
                    str_rgb = self._solve_strength_closed_form(small_refs, small_tgts, small_masks, ang, st_p, en_p, mode)
                    prm = {"angle_deg": ang, "start": st_p, "end": en_p, "mode": mode, "strength_rgb": str_rgb.tolist()}
                    err = float(
                        np.mean([
                            np.sqrt(np.mean(((self.render(sr, prm)[sm] - st[sm]) * 255.0) ** 2))
                            for sr, st, sm in zip(small_refs, small_tgts, small_masks)
                            if int(sm.sum()) > 10
                        ])
                    )
                    if err < best_small_err:
                        best_small_err = err
                        best_mode = mode
                        best_vec = np.array([ang, st_p, en_p], dtype=np.float64)

        # Refine (angle_deg, start, end) for both modes around their top candidates
        refined_candidates = []
        for mode in ("multiply", "tint"):
            def _obj_m(v: np.ndarray) -> float:
                ang = float(v[0])
                st_p = float(np.clip(v[1], -0.20, 0.85))
                en_p = float(max(st_p + 0.08, np.clip(v[2], 0.10, 1.20)))
                s_rgb = self._solve_strength_closed_form(small_refs, small_tgts, small_masks, ang, st_p, en_p, mode)
                prm = {"angle_deg": ang, "start": st_p, "end": en_p, "mode": mode, "strength_rgb": s_rgb.tolist()}
                return float(
                    np.mean([
                        np.sqrt(np.mean(((self.render(sr, prm)[sm] - st[sm]) * 255.0) ** 2))
                        for sr, st, sm in zip(small_refs, small_tgts, small_masks)
                        if int(sm.sum()) > 10
                    ])
                )

            init_v = best_vec if mode == best_mode else np.array([90.0, 0.15, 0.85], dtype=np.float64)
            opt = minimize(
                _obj_m,
                x0=init_v,
                method="Powell",
                bounds=[(-180.0, 180.0), (-0.20, 0.85), (0.10, 1.20)],
                options={"maxiter": 10, "maxfev": 65, "ftol": 1e-3},
            )
            ang_f = float(opt.x[0])
            st_f = float(np.clip(opt.x[1], -0.20, 0.85))
            en_f = float(max(st_f + 0.08, np.clip(opt.x[2], 0.10, 1.20)))

            # Full-res 5-fold block CV
            refs_lf_full = [_blur_lf(r) for r in refs]
            tgts_lf_full = [_blur_lf(t) for t in tgts]
            fold_losses = []
            for f in range(n_folds):
                tr_masks = [c.masks.active_mask & (c.masks.block_folds != f) for c in ctxs]
                s_fold = self._solve_strength_closed_form(refs_lf_full, tgts_lf_full, tr_masks, ang_f, st_f, en_f, mode)
                pf = {"angle_deg": ang_f, "start": st_f, "end": en_f, "mode": mode, "strength_rgb": s_fold.tolist()}
                preds_val = [self.render(r, pf) for r in refs]
                fold_losses.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

            full_masks = [c.masks.active_mask for c in ctxs]
            s_full = self._solve_strength_closed_form(refs_lf_full, tgts_lf_full, full_masks, ang_f, st_f, en_f, mode)
            p_full = {
                "angle_deg": round(ang_f, 3),
                "start": round(st_f, 4),
                "end": round(en_f, 4),
                "mode": mode,
                "strength_rgb": [round(float(x), 5) for x in s_full],
            }
            refined_candidates.append((float(np.mean(fold_losses)), fold_losses, p_full))

        refined_candidates.sort(key=lambda x: x[0])
        ho_after, best_fold_after, best_params = refined_candidates[0]
        preds_final = [self.render(r, best_params) for r in refs]
        tr_after = self.loss(preds_final, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)
        max_str = float(np.max(np.abs(best_params["strength_rgb"])))

        accepted = (max_str > 0.015) and (ho_after < ho_before - 0.10) and (rel_gain > 0.025)
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
                notes=f"Gradient rejected on held-out blocks ({ho_before:.2f} -> {ho_after:.2f}, max_strength={max_str:.3f}).",
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
            fold_losses_after=best_fold_after,
            notes=(
                f"Linear {best_params['mode']} gradient: angle={best_params['angle_deg']:.1f} deg, "
                f"smoothstep=[{best_params['start']:.2f}, {best_params['end']:.2f}], "
                f"strength_rgb={[round(x, 3) for x in best_params['strength_rgb']]}. "
                f"Held-out LF RMSE {ho_before:.2f} -> {ho_after:.2f}."
            ),
            diagnostics={"candidates": [c[2] for c in refined_candidates]},
        )

    def to_glsl(self, params: Dict[str, Any]) -> str:
        s_rgb = params.get("strength_rgb", [0.0, 0.0, 0.0])
        if float(np.max(np.abs(s_rgb))) <= 1e-5:
            return (
                "// --- Plugin: gradient (inactive, 0 taps) ---\n"
                "vec3 msApplyGradient(vec3 col, vec2 uv) { return col; }"
            )
        rad = float(np.deg2rad(float(params.get("angle_deg", 90.0))))
        cx, sy = float(np.cos(rad)), float(np.sin(rad))
        st = float(params.get("start", 0.15))
        en = float(params.get("end", 0.85))
        span = max(en - st, 0.04)
        mode = str(params.get("mode", "multiply"))

        comb = (
            f"col + s * vec3({s_rgb[0]:.6f}, {s_rgb[1]:.6f}, {s_rgb[2]:.6f})"
            if mode == "tint"
            else f"col * (vec3(1.0) + s * vec3({s_rgb[0]:.6f}, {s_rgb[1]:.6f}, {s_rgb[2]:.6f}))"
        )
        return f"""// --- Plugin: gradient ({mode}, uses yTop = 1.0 - uv.y, 0 extra taps) ---
vec3 msApplyGradient(vec3 col, vec2 uv) {{
    float yTop = 1.0 - uv.y;
    float t = 0.5 + (uv.x - 0.5) * {cx:.6f} + (yTop - 0.5) * {sy:.6f};
    float u = clamp((t - ({st:.6f})) / {span:.6f}, 0.0, 1.0);
    float s = u * u * (3.0 - 2.0 * u);
    return clamp({comb}, 0.0, 1.0);
}}"""

    def describe(self, params: Dict[str, Any]) -> str:
        s_rgb = params.get("strength_rgb", [0.0, 0.0, 0.0])
        if float(np.max(np.abs(s_rgb))) <= 1e-5:
            return "Gradient: absent."
        return (
            f"Smoothstep {params.get('mode', 'multiply')} gradient at {float(params['angle_deg']):.1f} deg "
            f"(yTop coords), range [{float(params['start']):.2f}, {float(params['end']):.2f}], "
            f"RGB strength={[round(float(x), 3) for x in s_rgb]}."
        )
