"""P5 & P6 Export and Honest Markdown Report builder (`look.json`, `look.cube`, snippets, visuals, `REPORT.md`)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lookfit.core.io import write_rgb_jpg
from lookfit.core.metrics import edge_profile_metrics
from lookfit.export.cube import write_cube_file
from lookfit.export.glsl_exporter import (
    compose_owner_keyflaw_shader,
    validate_glsl_es100,
    verify_shader_vs_python_parity,
)
from lookfit.planner import AlignedPairBundle, PlanResult
from lookfit.plugins.base import Plugin
from lookfit.tuner import TuneResult


def export_owner_results(
    owner_slug: str,
    bundles: List[AlignedPairBundle],
    plan: PlanResult,
    tune_res: TuneResult,
    plugins: Dict[str, Plugin],
    results_dir: Path,
) -> Dict[str, Any]:
    """Export all P5/P6 deliverables into `results_dir` (`owners/<owner>/results/`)."""
    results_dir.mkdir(parents=True, exist_ok=True)
    snippets_dir = results_dir / "snippets"
    visuals_dir = results_dir / "visuals"
    snippets_dir.mkdir(parents=True, exist_ok=True)
    visuals_dir.mkdir(parents=True, exist_ok=True)

    # Clean stale snippet files if re-running after stack changes
    for old_g in snippets_dir.glob("*.glsl"):
        old_g.unlink()

    # 1. Export look.cube (if colour plugin accepted)
    cube_written = False
    for lr in tune_res.accepted_layers:
        if lr.plugin_name == "colour" and "lut" in lr.params:
            lut_arr = np.asarray(lr.params["lut"], dtype=np.float32)
            write_cube_file(results_dir / "look.cube", lut_arr, title=f"MS_{owner_slug}_CC")
            cube_written = True

    # 2. Export per-plugin GLSL snippets + full single-pass Keyflaw shader.glsl
    for idx, lr in enumerate(tune_res.accepted_layers, start=1):
        snip = plugins[lr.plugin_name].to_glsl(lr.params)
        (snippets_dir / f"{idx:02d}_{lr.plugin_name}.glsl").write_text(snip + "\n", encoding="utf-8")

    shader_src, shader_meta = compose_owner_keyflaw_shader(
        owner_slug, tune_res.accepted_layers, plugins, max_taps=60
    )
    (results_dir / "shader.glsl").write_text(shader_src, encoding="utf-8")
    glsl_ok, glsl_log = validate_glsl_es100(shader_src)

    # 3. Verify NumPy port of shader maths vs Python plugin stack & .cube LUT
    parity = verify_shader_vs_python_parity(
        [b.ref_aligned for b in bundles],
        tune_res.accepted_layers,
        shader_meta,
        plugins,
    )

    # 4. Save compact comparison strips: Reference | Prediction | Target | Signed Residual (x3)
    for pred, b in zip(tune_res.final_predictions, bundles):
        am = b.masks.active_mask.astype(np.float32)[..., None]
        res_signed = np.clip(0.5 + 3.0 * (b.tgt_rgb - pred) * am, 0.0, 1.0)
        strip = np.concatenate([b.ref_aligned, pred, b.tgt_rgb, res_signed], axis=1)
        if strip.shape[1] > 1600:
            nh = max(64, int(round(strip.shape[0] * (1600.0 / strip.shape[1]))))
            strip = cv2.resize(strip, (1600, nh), interpolation=cv2.INTER_AREA)
        write_rgb_jpg(visuals_dir / f"{b.pair_id}_ref_pred_tgt_res.jpg", strip, quality=86)

    # Edge profile before/after plot
    fig, axes = plt.subplots(1, len(bundles), figsize=(4.5 * len(bundles), 3.4), squeeze=False)
    xs = np.arange(-8, 9)
    for idx, (pred, b) in enumerate(zip(tune_res.final_predictions, bundles)):
        ax = axes[0, idx]
        ep = edge_profile_metrics(pred, b.tgt_rgb, b.ref_aligned, b.masks.active_mask, half_width=8)
        ax.plot(xs, ep["mean_ref_profile"], "--", label="Aligned Ref", color="#777777", linewidth=1.3)
        ax.plot(xs, ep["mean_pred_profile"], "-", label="Final Stack", color="#2ca02c", linewidth=1.8)
        ax.plot(xs, ep["mean_tgt_profile"], "-", label="Target", color="#d62728", linewidth=1.7)
        ax.axhline(0.0, color="#aaaaaa", linewidth=0.6)
        ax.set_title(f"{b.pair_id}: halo RMSE {ep['halo_rmse_255']:.2f}/255", fontsize=9)
        ax.set_xlabel("Normal offset (px)")
        if idx == 0:
            ax.set_ylabel("Zero-mean luma (/255)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(visuals_dir / "edge_profiles_final.png", dpi=110)
    plt.close(fig)

    # 5. Build compact look.json (storing full LUT in look.cube rather than duplicating 15k floats in JSON)
    serializable_layers = []
    for order_idx, lr in enumerate(tune_res.accepted_layers, start=1):
        p_clean = deepcopy(lr.params)
        if lr.plugin_name == "colour" and "lut" in p_clean:
            p_clean["lut_file"] = "look.cube"
            del p_clean["lut"]
        spec_list = [
            {
                "name": ps.name,
                "unit": ps.unit,
                "scale_law": ps.scale_law,
                "min": ps.min_val,
                "max": ps.max_val,
            }
            for ps in plugins[lr.plugin_name].param_spec
        ]
        serializable_layers.append({
            "order": order_idx,
            "plugin": lr.plugin_name,
            "describe": lr.describe_text,
            "glsl_extra_taps": lr.glsl_taps,
            "parameters": p_clean,
            "param_spec": spec_list,
            "held_out_fit": {
                "loss_before": round(lr.report.held_out_loss_before, 5),
                "loss_after": round(lr.report.held_out_loss_after, 5),
                "rel_gain": round(lr.report.held_out_rel_gain, 5),
                "notes": lr.report.notes,
            },
            "cumulative_metrics_after": lr.metrics_after["aggregate"],
        })

    look_doc = {
        "owner": owner_slug,
        "effect_id": f"MS_{owner_slug}_cc",
        "cube_file": "look.cube" if cube_written else None,
        "accepted_order": [lr.plugin_name for lr in tune_res.accepted_layers],
        "layers": serializable_layers,
        "rejected_or_absent_plugins": [
            {"plugin": rr.plugin_name, "reason": rr.reason}
            for rr in tune_res.rejected_layers
        ],
        "adjacent_swap_checks": tune_res.swap_checks,
        "joint_refinement_rounds": tune_res.refinement_rounds,
        "shader_validation": {
            "glslang_es100_passed": glsl_ok,
            "glslang_output": glsl_log,
            "total_texture_taps": shader_meta["total_texture_taps"],
            "has_haze_flare_switch": shader_meta["has_haze_flare_switch"],
            "numpy_vs_python_parity": parity,
            "tested_inside_keyflaw_app": False,
        },
        "metrics_before": tune_res.metrics_initial,
        "metrics_after": tune_res.metrics_final,
        "honest_limits": tune_res.honest_limits,
    }
    (results_dir / "look.json").write_text(json.dumps(look_doc, indent=2) + "\n", encoding="utf-8")

    # 6. Build REPORT.md
    report_md = _build_markdown_report(owner_slug, plan, tune_res, shader_meta, glsl_ok, parity)
    (results_dir / "REPORT.md").write_text(report_md, encoding="utf-8")

    return {
        "shader_src": shader_src,
        "shader_meta": shader_meta,
        "glsl_ok": glsl_ok,
        "parity": parity,
        "look_doc": look_doc,
    }


def _build_markdown_report(
    owner_slug: str,
    plan: PlanResult,
    tune_res: TuneResult,
    shader_meta: Dict[str, Any],
    glsl_ok: bool,
    parity: Dict[str, Any],
) -> str:
    m0 = tune_res.metrics_initial["aggregate"]
    m1 = tune_res.metrics_final["aggregate"]
    acc_names = [lr.plugin_name for lr in tune_res.accepted_layers]

    lines = [
        f"# Look-Fit Report: `{owner_slug}` (`MS_{owner_slug}_cc`)",
        "",
        "## 1. Summary",
        f"- **Accepted Layer Stack ({len(acc_names)}):** `{ ' -> '.join(acc_names) if acc_names else 'none' }`",
        f"- **Median CIEDE2000:** `{m0['ciede2000_median']:.2f}` -> **`{m1['ciede2000_median']:.2f}`** "
        f"(p90: `{m0['ciede2000_p90']:.2f}` -> **`{m1['ciede2000_p90']:.2f}`**)",
        f"- **Active RGB MAE (/255):** `{m0['mae_mean_255']:.2f}` -> **`{m1['mae_mean_255']:.2f}`** "
        f"(R `{m1['mae_r_255']:.2f}`, G `{m1['mae_g_255']:.2f}`, B `{m1['mae_b_255']:.2f}`)",
        f"- **Edge-Profile Halo RMSE (/255):** `{m0['edge_halo_rmse_255']:.2f}` -> **`{m1['edge_halo_rmse_255']:.2f}`** "
        f"(raw edge RMSE: `{m0['edge_raw_rmse_255']:.2f}` -> `{m1['edge_raw_rmse_255']:.2f}`)",
        f"- **Active SSIM:** `{m0['ssim']:.4f}` -> **`{m1['ssim']:.4f}`**",
        f"- **Keyflaw 1.4.8 Shader:** `{shader_meta['total_texture_taps']}` texture taps, "
        f"`glslangValidator` (`#version 100`) = `{'PASS' if glsl_ok else 'FAIL'}`, "
        f"`Haze Flare` switch = `{'present' if shader_meta['has_haze_flare_switch'] else 'absent (omitted)'}`.",
        "",
        "## 2. P0 Alignment & Mask Summary (All Pairs Treated Equally)",
        "| Pair | Ref Res | Target Res | Method | Shift (dx, dy px) | Scale (sx, sy) | Edge Corr (before -> after) | Active / Flat / Edge / Caption % |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for ps in plan.pair_summaries:
        al = ps["alignment"]
        mk = ps["masks"]
        lines.append(
            f"| `{ps['pair_id']}` | `{ps['ref_orig_shape'][1]}x{ps['ref_orig_shape'][0]}` | "
            f"`{ps['tgt_shape'][1]}x{ps['tgt_shape'][0]}` | `{al['method']}` | "
            f"`({al['tx_px']:+.2f}, {al['ty_px']:+.2f})` | `({al['scale_x']:.4f}, {al['scale_y']:.4f})` | "
            f"`{al['edge_corr_before']:.3f} -> {al['edge_corr_after']:.3f}` | "
            f"`{mk['active_frac']*100:.1f}% / {mk['flat_frac']*100:.1f}% / {mk['edge_frac']*100:.1f}% / {mk['caption_frac']*100:.1f}%` |"
        )

    lines.extend([
        "",
        "## 3. P1 Detector Evidence",
    ])
    for pw in plan.plain_words_evidence:
        lines.append(f"- {pw}")

    lines.extend([
        "",
        "## 4. P3 & P4 Layer-by-Layer Progression",
        "| Stage | Median DE00 | p90 DE00 | RGB MAE (/255) | Edge Halo RMSE (/255) | SSIM | Layer Notes |",
        "|---|---|---|---|---|---|---|",
        f"| `0. Aligned Ref` | {m0['ciede2000_median']:.2f} | {m0['ciede2000_p90']:.2f} | {m0['mae_mean_255']:.2f} | {m0['edge_halo_rmse_255']:.2f} | {m0['ssim']:.4f} | Unmodified aligned reference |",
    ])
    for idx, lr in enumerate(tune_res.accepted_layers, start=1):
        ma = lr.metrics_after["aggregate"]
        lines.append(
            f"| `{idx}. +{lr.plugin_name}` | {ma['ciede2000_median']:.2f} | {ma['ciede2000_p90']:.2f} | "
            f"{ma['mae_mean_255']:.2f} | {ma['edge_halo_rmse_255']:.2f} | {ma['ssim']:.4f} | {lr.describe_text} |"
        )

    lines.extend([
        "",
        "### Absent or Rejected Plugins",
    ])
    for rr in tune_res.rejected_layers:
        lines.append(f"- **`{rr.plugin_name}`**: {rr.reason}")

    if tune_res.swap_checks:
        lines.extend(["", "### Adjacent-Order Swap Checks"])
        for sw in tune_res.swap_checks:
            lines.append(
                f"- `{sw['pair'][0]} <-> {sw['pair'][1]}`: original joint loss `{sw['original_joint_loss']:.4f}` "
                f"vs swapped `{sw['swapped_joint_loss']:.4f}` -> kept `{'swapped' if sw['swapped_kept'] else 'original'}`."
            )

    if tune_res.refinement_rounds:
        lines.extend(["", "### P4 Coordinate-Descent Joint Refinement"])
        for rnd in tune_res.refinement_rounds:
            lines.append(
                f"- Round {rnd['round']}: joint loss `{rnd['joint_loss_start']:.4f}` -> `{rnd['joint_loss_end']:.4f}` "
                f"(delta `{rnd['delta']:+.5f}`, updates={len(rnd['updates'])})."
            )

    lines.extend([
        "",
        "## 5. Per-Pair Before vs After Metrics",
        "| Pair | Med DE00 (Before -> After) | p90 DE00 (Before -> After) | R / G / B MAE After (/255) | Mean MAE (Before -> After) | Edge Halo RMSE (Before -> After) | SSIM (Before -> After) |",
        "|---|---|---|---|---|---|---|",
    ])
    for pid, p_init in tune_res.metrics_initial["per_pair"].items():
        p_fin = tune_res.metrics_final["per_pair"][pid]
        lines.append(
            f"| `{pid}` | `{p_init['ciede2000_median']:.2f} -> {p_fin['ciede2000_median']:.2f}` | "
            f"`{p_init['ciede2000_p90']:.2f} -> {p_fin['ciede2000_p90']:.2f}` | "
            f"`{p_fin['mae_r_255']:.2f} / {p_fin['mae_g_255']:.2f} / {p_fin['mae_b_255']:.2f}` | "
            f"`{p_init['mae_mean_255']:.2f} -> {p_fin['mae_mean_255']:.2f}` | "
            f"`{p_init['edge_halo_rmse_255']:.2f} -> {p_fin['edge_halo_rmse_255']:.2f}` | "
            f"`{p_init['ssim']:.4f} -> {p_fin['ssim']:.4f}` |"
        )

    lines.extend([
        "",
        "## 6. Shader Compression & Parity Verification",
        f"- **Colour Shader vs Python Colour Plugin:** `{parity['colour_shader_vs_python_mean_255']:.4f} / 255` (limit `<= 1.0 / 255`)",
        f"- **Colour Shader vs Full 3D `.cube` LUT:** `{parity['colour_shader_vs_cube_mean_255']:.4f} / 255` (limit `<= 1.0 / 255`)",
        f"- **Full Single-Pass Shader vs Sequential Python Stack:** `{parity['full_stack_shader_vs_python_mean_255']:.4f} / 255` (limit `<= 2.0 / 255`)",
        f"- **Texture Fetch Count:** `{shader_meta['total_texture_taps']}` taps (`<= 60` mobile budget).",
        "",
        "## 7. Visuals",
        "- Per-pair strips (`Reference | Prediction | Target | Signed Residual x3`): `visuals/*_ref_pred_tgt_res.jpg`",
        "- Perpendicular edge-halo cross-sections: `visuals/edge_profiles_final.png` and `visuals/p1_edge_halo_profiles.png`",
        "- Low-frequency & flat-noise diagnostic maps: `visuals/*_p1_lowfreq_map.jpg`, `visuals/*_p1_noise_map.jpg`",
        "",
        "## 8. Honest Limits",
        f"- **Dominant remaining error source:** {tune_res.honest_limits['dominant_limiter']}.",
    ])
    for note in tune_res.honest_limits["evidence_notes"]:
        lines.append(f"- {note}")
    lines.append(
        "- **After Effects Sharpen note:** Any `sharpen` kernel (`cross4`, `box8`, `binomial3x3`) and slider mapping is **fitted, not known**, because Adobe does not publish the exact kernel."
    )
    lines.append(
        "- **Keyflaw runtime verification:** Validated with `SKILL.md` pack checker, `glslangValidator` (`#version 100`), and NumPy shader parity; **not tested inside the live Keyflaw Android app**."
    )
    return "\n".join(lines) + "\n"
