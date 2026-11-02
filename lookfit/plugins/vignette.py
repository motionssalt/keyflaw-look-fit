"""Radial smoothstep falloff multiply vignette plugin (aspect-corrected, yTop = 1.0 - vTex.y aware)."""

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
from lookfit.plugins.gradient import _blur_lf


def _vignette_falloff(
    shape_hw: Tuple[int, int],
    center_x: float,
    center_y_top: float,
    radius: float,
    softness: float,
) -> np.ndarray:
    h, w = shape_hw
    aspect = float(w) / max(float(h), 1.0)
    x_norm = ((np.arange(w, dtype=np.float32) + 0.5) / float(w))[None, :]
    y_top = ((np.arange(h, dtype=np.float32) + 0.5) / float(h))[:, None]
    dx = (x_norm - float(center_x)) * aspect
    dy = y_top - float(center_y_top)
    dist = np.hypot(dx, dy)
    soft = max(float(softness), 0.05)
    u = np.clip((dist - float(radius)) / soft, 0.0, 1.0)
    return (u * u * (3.0 - 2.0 * u)).astype(np.float32)


class VignettePlugin(Plugin):
    name = "vignette"
    param_spec = [
        ParamSpec("center_x", 0.50, 0.25, 0.75, "uv_0_1", "dimensionless", "Horizontal vignette centre (0..1)"),
        ParamSpec("center_y_top", 0.50, 0.25, 0.75, "uv_0_1", "dimensionless", "Vertical vignette centre from TOP edge (yTop = 1.0 - vTex.y)"),
        ParamSpec("radius", 0.55, 0.15, 1.35, "aspect_h", "fraction_of_height", "Inner un-darkened radius in height-normalized circular units"),
        ParamSpec("softness", 0.50, 0.08, 1.25, "aspect_h", "fraction_of_height", "Radial smoothstep feather width"),
        ParamSpec("strength", 0.0, 0.0, 0.85, "gain", "dimensionless", "Corner darkening multiply strength (0 = none)"),
    ]

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {
            "center_x": 0.50,
            "center_y_top": 0.50,
            "radius": 0.55,
            "softness": 0.50,
            "strength": 0.0,
        }

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        corner_drops_255: List[float] = []
        quadrant_consistency: List[float] = []

        for r_im, t_im, pctx in items:
            am = pctx.masks.active_mask
            if int(am.sum()) < 200:
                continue
            res_lf = _blur_lf(t_im - r_im).mean(axis=-1)
            h, w = t_im.shape[:2]
            aspect = float(w) / max(float(h), 1.0)
            x_n = ((np.arange(w, dtype=np.float32) + 0.5) / w)[None, :]
            y_n = ((np.arange(h, dtype=np.float32) + 0.5) / h)[:, None]
            dist = np.hypot((x_n - 0.5) * aspect, y_n - 0.5)

            inner = am & (dist < 0.38)
            outer = am & (dist > 0.68)
            if int(inner.sum()) > 80 and int(outer.sum()) > 80:
                drop = float((res_lf[inner].mean() - res_lf[outer].mean()) * 255.0)
                corner_drops_255.append(drop)
                # Check how many of the 4 outer quadrants also darken relative to centre
                in_m = float(res_lf[inner].mean())
                q_dark = 0
                q_tot = 0
                for qx in (x_n < 0.5, x_n >= 0.5):
                    for qy in (y_n < 0.5, y_n >= 0.5):
                        qm = outer & np.broadcast_to(qx, (h, w)) & np.broadcast_to(qy, (h, w))
                        if int(qm.sum()) >= 30:
                            q_tot += 1
                            if float(res_lf[qm].mean()) < in_m - (1.0 / 255.0):
                                q_dark += 1
                quadrant_consistency.append(float(q_dark) / max(q_tot, 1))

        mean_drop = float(np.mean(corner_drops_255)) if corner_drops_255 else 0.0
        mean_q = float(np.mean(quadrant_consistency)) if quadrant_consistency else 0.0

        if mean_drop >= 2.5 and mean_q >= 0.70:
            status = "present"
        elif mean_drop >= 1.4 and mean_q >= 0.50:
            status = "weak"
        else:
            status = "absent"

        return Evidence(
            plugin_name=self.name,
            status=status,
            score=max(0.0, mean_drop * mean_q),
            notes=(
                f"Radial corner darkening check: centre-to-outer drop={mean_drop:.2f}/255, "
                f"quadrant consistency={mean_q:.2f} -> {status}."
            ),
            metrics={"corner_drop_255": mean_drop, "quadrant_consistency": mean_q},
            mask_of_interest=items[0][2].masks.active_mask,
        )

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        strength = float(params.get("strength", 0.0))
        if strength <= 1e-5:
            return np.clip(img, 0.0, 1.0).astype(np.float32)
        falloff = _vignette_falloff(
            img.shape[:2],
            float(params.get("center_x", 0.50)),
            float(params.get("center_y_top", 0.50)),
            float(params.get("radius", 0.55)),
            float(params.get("softness", 0.50)),
        )[..., None]
        out = np.clip(img, 0.0, 1.0).astype(np.float32) * (1.0 - strength * falloff)
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
            errs.append(float(np.sqrt(np.mean(((p_lf[am] - t_lf[am]) * 255.0) ** 2))))
        return float(np.mean(errs)) if errs else 0.0

    def _solve_strength(
        self,
        refs_lf: List[np.ndarray],
        tgts_lf: List[np.ndarray],
        masks: List[np.ndarray],
        cx: float,
        cy: float,
        radius: float,
        softness: float,
    ) -> float:
        num = 0.0
        den = 1e-4
        for r_lf, t_lf, m in zip(refs_lf, tgts_lf, masks):
            if int(m.sum()) < 20:
                continue
            fo = _vignette_falloff(r_lf.shape[:2], cx, cy, radius, softness)[m][:, None]
            basis = fo * r_lf[m].astype(np.float64)
            diff = (r_lf[m] - t_lf[m]).astype(np.float64)
            num += float(np.sum(basis * diff))
            den += float(np.sum(basis * basis)) + 1e-4
        return float(np.clip(num / den, 0.0, 0.85))

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]
        n_folds = int(items[0][2].masks.block_folds.max()) + 1

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        small_refs, small_tgts, small_masks = [], [], []
        for r_im, t_im, pctx in items:
            h, w = t_im.shape[:2]
            sw = min(240, w)
            sh = max(32, int(round(h * (sw / float(w)))))
            small_refs.append(cv2.resize(_blur_lf(r_im), (sw, sh), interpolation=cv2.INTER_AREA))
            small_tgts.append(cv2.resize(_blur_lf(t_im), (sw, sh), interpolation=cv2.INTER_AREA))
            small_masks.append(
                cv2.resize(pctx.masks.active_mask.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_NEAREST) > 0
            )

        best_init = np.array([0.50, 0.50, 0.55, 0.50], dtype=np.float64)
        best_err = float("inf")
        for rad in (0.28, 0.48, 0.68, 0.88):
            for soft in (0.25, 0.55, 0.90):
                st_v = self._solve_strength(small_refs, small_tgts, small_masks, 0.50, 0.50, rad, soft)
                prm = {"center_x": 0.50, "center_y_top": 0.50, "radius": rad, "softness": soft, "strength": st_v}
                err = float(
                    np.mean([
                        np.sqrt(np.mean(((self.render(sr, prm)[sm] - st[sm]) * 255.0) ** 2))
                        for sr, st, sm in zip(small_refs, small_tgts, small_masks)
                        if int(sm.sum()) > 10
                    ])
                )
                if err < best_err:
                    best_err = err
                    best_init = np.array([0.50, 0.50, rad, soft], dtype=np.float64)

        def _obj_small(v: np.ndarray) -> float:
            cx = float(np.clip(v[0], 0.25, 0.75))
            cy = float(np.clip(v[1], 0.25, 0.75))
            rad = float(np.clip(v[2], 0.15, 1.35))
            soft = float(np.clip(v[3], 0.08, 1.25))
            st_v = self._solve_strength(small_refs, small_tgts, small_masks, cx, cy, rad, soft)
            prm = {"center_x": cx, "center_y_top": cy, "radius": rad, "softness": soft, "strength": st_v}
            return float(
                np.mean([
                    np.sqrt(np.mean(((self.render(sr, prm)[sm] - st[sm]) * 255.0) ** 2))
                    for sr, st, sm in zip(small_refs, small_tgts, small_masks)
                    if int(sm.sum()) > 10
                ])
            )

        opt = minimize(
            _obj_small,
            x0=best_init,
            method="Powell",
            bounds=[(0.25, 0.75), (0.25, 0.75), (0.15, 1.35), (0.08, 1.25)],
            options={"maxiter": 10, "maxfev": 70, "ftol": 1e-3},
        )
        cx_f = float(np.clip(opt.x[0], 0.25, 0.75))
        cy_f = float(np.clip(opt.x[1], 0.25, 0.75))
        rad_f = float(np.clip(opt.x[2], 0.15, 1.35))
        soft_f = float(np.clip(opt.x[3], 0.08, 1.25))

        refs_lf = [_blur_lf(r) for r in refs]
        tgts_lf = [_blur_lf(t) for t in tgts]
        fold_after: List[float] = []
        for f in range(n_folds):
            tr_m = [c.masks.active_mask & (c.masks.block_folds != f) for c in ctxs]
            st_f = self._solve_strength(refs_lf, tgts_lf, tr_m, cx_f, cy_f, rad_f, soft_f)
            pf = {"center_x": cx_f, "center_y_top": cy_f, "radius": rad_f, "softness": soft_f, "strength": st_f}
            preds_val = [self.render(r, pf) for r in refs]
            fold_after.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

        ho_after = float(np.mean(fold_after))
        st_full = self._solve_strength(refs_lf, tgts_lf, [c.masks.active_mask for c in ctxs], cx_f, cy_f, rad_f, soft_f)
        best_params = {
            "center_x": round(cx_f, 4),
            "center_y_top": round(cy_f, 4),
            "radius": round(rad_f, 4),
            "softness": round(soft_f, 4),
            "strength": round(st_full, 5),
        }
        preds_final = [self.render(r, best_params) for r in refs]
        tr_after = self.loss(preds_final, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)

        accepted = (st_full > 0.02) and (ho_after < ho_before - 0.08) and (rel_gain > 0.02)
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
                notes=f"Vignette rejected on held-out blocks ({ho_before:.2f} -> {ho_after:.2f}, strength={st_full:.3f}).",
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
                f"Radial vignette: centre=({best_params['center_x']:.2f}, {best_params['center_y_top']:.2f} yTop), "
                f"radius={best_params['radius']:.2f}, softness={best_params['softness']:.2f}, "
                f"strength={best_params['strength']:.3f}. Held-out LF RMSE {ho_before:.2f} -> {ho_after:.2f}."
            ),
            diagnostics={"accepted_params": best_params},
        )

    def to_glsl(self, params: Dict[str, Any]) -> str:
        st = float(params.get("strength", 0.0))
        if st <= 1e-5:
            return (
                "// --- Plugin: vignette (inactive, 0 taps) ---\n"
                "vec3 msApplyVignette(vec3 col, vec2 uv, vec2 texelSize) { return col; }"
            )
        cx = float(params.get("center_x", 0.50))
        cy = float(params.get("center_y_top", 0.50))
        rad = float(params.get("radius", 0.55))
        soft = max(float(params.get("softness", 0.50)), 0.05)
        return f"""// --- Plugin: vignette (aspect-corrected radial multiply, yTop = 1.0 - uv.y, 0 extra taps) ---
vec3 msApplyVignette(vec3 col, vec2 uv, vec2 texelSize) {{
    float yTop = 1.0 - uv.y;
    float aspect = texelSize.y / max(texelSize.x, 0.0001);
    vec2 pa = vec2((uv.x - {cx:.6f}) * aspect, yTop - {cy:.6f});
    float dist = length(pa);
    float u = clamp((dist - {rad:.6f}) / {soft:.6f}, 0.0, 1.0);
    float falloff = u * u * (3.0 - 2.0 * u);
    return clamp(col * (1.0 - {st:.6f} * falloff), 0.0, 1.0);
}}"""

    def describe(self, params: Dict[str, Any]) -> str:
        st = float(params.get("strength", 0.0))
        if st <= 1e-5:
            return "Vignette: absent."
        return (
            f"Radial falloff multiply vignette: centre=({float(params['center_x']):.2f}, "
            f"{float(params['center_y_top']):.2f} yTop), radius={float(params['radius']):.2f}, "
            f"softness={float(params['softness']):.2f}, strength={st:.3f}."
        )
