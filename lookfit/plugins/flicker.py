"""Optional plugin: temporal global exposure flicker across multi-pair captures."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from lookfit.plugins.base import (
    ContextOrList,
    Evidence,
    FitReport,
    ImageOrList,
    ParamSpec,
    Plugin,
    normalize_pair_inputs,
)


class FlickerPlugin(Plugin):
    name = "flicker"
    param_spec = [
        ParamSpec("amplitude", 0.0, 0.0, 0.25, "gain", "dimensionless", "Peak exposure modulation amplitude"),
        ParamSpec("frequency_hz", 8.0, 1.0, 30.0, "Hz", "dimensionless", "Temporal flicker frequency for GLSL uTime"),
    ]

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        return {"amplitude": 0.0, "frequency_hz": 8.0, "pair_gains": []}

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        if len(items) < 3:
            return Evidence(
                plugin_name=self.name,
                status="absent",
                score=0.0,
                notes=f"Flicker requires >=3 independent frame pairs to distinguish temporal oscillation from static look (have {len(items)}).",
                metrics={"n_pairs": len(items)},
            )

        gains: List[float] = []
        r2_per_pair: List[float] = []
        for r_im, t_im, pctx in items:
            fm = pctx.masks.flat_mask
            if int(fm.sum()) < 100:
                fm = pctx.masks.active_mask
            rv = r_im[fm].astype(np.float64)
            tv = t_im[fm].astype(np.float64)
            # Fit uniform scalar exposure multiplier tv ≈ g * rv
            g = float(np.sum(rv * tv) / max(np.sum(rv * rv), 1e-6))
            gains.append(g)
            before_mse = float(np.mean((tv - rv) ** 2))
            after_mse = float(np.mean((tv - g * rv) ** 2))
            r2 = (before_mse - after_mse) / max(before_mse, 1e-8) if before_mse > 1e-5 else 0.0
            r2_per_pair.append(r2)

        g_arr = np.asarray(gains, dtype=np.float64)
        amp_est = float(np.sqrt(2.0) * np.std(g_arr))
        mean_r2 = float(np.mean(r2_per_pair))

        # Only trigger if pairs differ primarily by a clean global exposure multiplier (R^2 >= 0.65)
        if amp_est >= 0.04 and mean_r2 >= 0.65:
            status = "present"
        else:
            status = "absent"

        return Evidence(
            plugin_name=self.name,
            status=status,
            score=amp_est if status == "present" else 0.0,
            notes=(
                f"Multi-pair global exposure flicker check: est_amp={amp_est:.3f}, "
                f"scalar-gain R^2={mean_r2:.3f}, pair_gains={[round(g, 3) for g in gains]} -> {status}."
            ),
            metrics={"est_amplitude": amp_est, "scalar_gain_r2": mean_r2, "pair_gains": gains},
        )

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        # On a static still frame without frame timestamp, neutral phase gain = 1.0 unless explicit phase_gain given
        g = float(params.get("static_gain", 1.0))
        if abs(g - 1.0) <= 1e-5:
            return np.clip(img, 0.0, 1.0).astype(np.float32)
        return np.clip(img.astype(np.float32) * g, 0.0, 1.0).astype(np.float32)

    def loss(
        self,
        pred: ImageOrList,
        tgt: ImageOrList,
        ctx: ContextOrList = None,
        fold: Optional[int] = None,
        train: bool = False,
    ) -> float:
        items = normalize_pair_inputs(pred, tgt, ctx)
        errs = []
        for p_im, t_im, pctx in items:
            fm = pctx.masks.flat_mask
            if fold is not None:
                fm = fm & ((pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold))
            if int(fm.sum()) < 50:
                fm = pctx.masks.active_mask
            errs.append(float(np.sqrt(np.mean(((p_im[fm] - t_im[fm]) * 255.0) ** 2))))
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

        if ev.status != "present":
            zero_p = self.initial_guess(ref_in, tgt, ctx)
            return zero_p, FitReport(
                plugin_name=self.name,
                accepted_hint=False,
                train_loss_before=ho_before,
                train_loss_after=ho_before,
                held_out_loss_before=ho_before,
                held_out_loss_after=ho_before,
                held_out_rel_gain=0.0,
                fold_losses_before=fold_before,
                fold_losses_after=fold_before,
                notes=ev.notes,
                diagnostics={"status": "absent", "evidence": ev.metrics},
            )

        # Evaluate held-out block CV with per-pair uniform exposure gain
        fold_after = []
        for f in range(n_folds):
            preds_val = []
            for r_im, t_im, pctx in items:
                tr_m = pctx.masks.flat_mask & (pctx.masks.block_folds != f)
                if int(tr_m.sum()) < 50:
                    tr_m = pctx.masks.active_mask & (pctx.masks.block_folds != f)
                rv = r_im[tr_m].astype(np.float64)
                tv = t_im[tr_m].astype(np.float64)
                gf = float(np.clip(np.sum(rv * tv) / max(np.sum(rv * rv), 1e-6), 0.75, 1.25))
                preds_val.append(np.clip(r_im * gf, 0.0, 1.0).astype(np.float32))
            fold_after.append(self.loss(preds_val, tgts, ctxs, fold=f, train=False))

        ho_after = float(np.mean(fold_after))
        amp = round(float(np.clip(ev.metrics["est_amplitude"], 0.0, 0.25)), 4)
        params = {
            "amplitude": amp,
            "frequency_hz": 8.0,
            "pair_gains": [round(float(g), 4) for g in ev.metrics["pair_gains"]],
        }
        rel_gain = (ho_before - ho_after) / max(ho_before, 1e-6)
        return params, FitReport(
            plugin_name=self.name,
            accepted_hint=(ho_after < ho_before - 0.30 and rel_gain > 0.20),
            train_loss_before=ho_before,
            train_loss_after=ho_after,
            held_out_loss_before=ho_before,
            held_out_loss_after=ho_after,
            held_out_rel_gain=rel_gain,
            fold_losses_before=fold_before,
            fold_losses_after=fold_after,
            notes=f"Multi-pair uniform exposure flicker amplitude={amp:.3f}.",
            diagnostics={"evidence": ev.metrics},
        )

    def to_glsl(self, params: Dict[str, Any]) -> str:
        amp = float(params.get("amplitude", 0.0))
        if amp <= 1e-5:
            return "// --- Plugin: flicker (inactive, 0 taps) ---\nvec3 msApplyFlicker(vec3 col, float timeSec) { return col; }"
        freq = float(params.get("frequency_hz", 8.0))
        return f"""// --- Plugin: flicker (temporal exposure modulation, 0 extra taps) ---
vec3 msApplyFlicker(vec3 col, float timeSec) {{
    float ph = mod(max(timeSec, 0.0) * {freq:.4f}, 6.2831853);
    float gain = 1.0 + {amp:.6f} * sin(ph * 6.2831853);
    return clamp(col * gain, 0.0, 1.0);
}}"""

    def describe(self, params: Dict[str, Any]) -> str:
        amp = float(params.get("amplitude", 0.0))
        if amp <= 1e-5:
            return "Flicker: absent."
        return f"Temporal exposure flicker: amplitude={amp:.3f}, frequency={float(params.get('frequency_hz', 8.0)):.1f} Hz."
