"""Optional plugin: global veil / shadow black-point lift (`out = lift + (1 - lift) * x`)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

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


class BlackLiftPlugin(Plugin):
    name = "black_lift"
    param_spec = [
        ParamSpec("lift_rgb", [0.0, 0.0, 0.0], 0.0, 0.25, "rgb_0_1", "rgb_0_1", "Global screen/veil black floor lift per channel"),
    ]

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {"lift_rgb": [0.0, 0.0, 0.0]}

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        lifts_255: List[float] = []
        dark_counts = 0

        for r_im, t_im, pctx in items:
            am = pctx.masks.active_mask
            rl = luma_rec709(r_im)
            dark_m = am & (rl <= 0.07)
            if int(dark_m.sum()) >= 80:
                dark_counts += int(dark_m.sum())
                med_lift = float(np.median(t_im[dark_m] - r_im[dark_m]) * 255.0)
                lifts_255.append(med_lift)

        mean_lift = float(np.mean(lifts_255)) if lifts_255 else 0.0
        if dark_counts >= 80 and mean_lift >= 3.0 and all(l > 1.5 for l in lifts_255):
            status = "present"
        else:
            status = "absent"

        return Evidence(
            plugin_name=self.name,
            status=status,
            score=max(0.0, mean_lift),
            notes=(
                f"Shadow black-point veil check on {dark_counts} dark pixels: "
                f"median lift={mean_lift:.2f}/255 -> {status}."
            ),
            metrics={"median_dark_lift_255": mean_lift, "dark_pixel_count": dark_counts},
            mask_of_interest=items[0][2].masks.active_mask,
        )

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        lift = np.asarray(params.get("lift_rgb", [0.0, 0.0, 0.0]), dtype=np.float32)
        if float(np.max(lift)) <= 1e-5:
            return np.clip(img, 0.0, 1.0).astype(np.float32)
        x = np.clip(img, 0.0, 1.0).astype(np.float32)
        out = lift[None, None, :] + (1.0 - lift[None, None, :]) * x
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
            errs.append(float(np.sqrt(np.mean(((p_im[am] - t_im[am]) * 255.0) ** 2))))
        return float(np.mean(errs)) if errs else 0.0

    def _solve_lift(self, refs: List[np.ndarray], tgts: List[np.ndarray], masks: List[np.ndarray]) -> np.ndarray:
        num = np.zeros(3, dtype=np.float64)
        den = np.zeros(3, dtype=np.float64) + 1e-4
        for r_im, t_im, m in zip(refs, tgts, masks):
            if int(m.sum()) < 20:
                continue
            omx = (1.0 - r_im[m]).astype(np.float64)
            diff = (t_im[m] - r_im[m]).astype(np.float64)
            num += np.sum(omx * diff, axis=0)
            den += np.sum(omx * omx, axis=0) + 1e-4
        return np.clip(num / den, 0.0, 0.25).astype(np.float32)

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        refs = [r for r, _, _ in items]
        tgts = [t for _, t, _ in items]
        ctxs = [c for _, _, c in items]
        n_folds = int(items[0][2].masks.block_folds.max()) + 1

        fold_before = [self.loss(refs, tgts, ctxs, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(refs, tgts, ctxs, fold=None, train=True)

        fold_after: List[float] = []
        for f in range(n_folds):
            tr_m = [c.masks.active_mask & (c.masks.block_folds != f) for c in ctxs]
            lf = self._solve_lift(refs, tgts, tr_m)
            preds_val = [self.render(r, {"lift_rgb": lf.tolist()}) for r in refs]
            fold_after.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

        ho_after = float(np.mean(fold_after))
        lift_full = self._solve_lift(refs, tgts, [c.masks.active_mask for c in ctxs])
        best_params = {"lift_rgb": [round(float(x), 5) for x in lift_full]}
        preds_final = [self.render(r, best_params) for r in refs]
        tr_after = self.loss(preds_final, tgts, ctxs, fold=None, train=True)
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)

        accepted = (float(np.max(lift_full)) > 0.008) and (ho_after < ho_before - 0.08) and (rel_gain > 0.02)
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
                notes=f"Black lift absent/rejected ({ho_before:.2f} -> {ho_after:.2f}).",
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
            notes=f"Global black lift veil={best_params['lift_rgb']}, RMSE {ho_before:.2f} -> {ho_after:.2f}.",
            diagnostics={"accepted_params": best_params},
        )

    def to_glsl(self, params: Dict[str, Any]) -> str:
        l_rgb = params.get("lift_rgb", [0.0, 0.0, 0.0])
        if float(np.max(l_rgb)) <= 1e-5:
            return "// --- Plugin: black_lift (inactive, 0 taps) ---\nvec3 msApplyBlackLift(vec3 col) { return col; }"
        return f"""// --- Plugin: black_lift (global veil, 0 extra taps) ---
vec3 msApplyBlackLift(vec3 col) {{
    vec3 lift = vec3({l_rgb[0]:.6f}, {l_rgb[1]:.6f}, {l_rgb[2]:.6f});
    return clamp(lift + (vec3(1.0) - lift) * col, 0.0, 1.0);
}}"""

    def describe(self, params: Dict[str, Any]) -> str:
        l_rgb = params.get("lift_rgb", [0.0, 0.0, 0.0])
        if float(np.max(l_rgb)) <= 1e-5:
            return "Black Lift: absent."
        return f"Global shadow veil / black-point lift RGB={[round(float(x)*255, 2) for x in l_rgb]} (/255)."
