"""P3 Layer-by-Layer Tuning, Adjacent-Order Swap Check, P4 Coordinate-Descent Joint Refinement, and Limits Analysis."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from lookfit.core.io import write_rgb_jpg
from lookfit.core.metrics import (
    channel_mae,
    ciede2000_rgb,
    compute_ssim,
    edge_profile_metrics,
    noise_statistics,
)
from lookfit.planner import AlignedPairBundle, PlanResult
from lookfit.plugins.base import FitReport, Plugin


@dataclass
class LayerRecord:
    plugin_name: str
    params: Dict[str, Any]
    report: FitReport
    describe_text: str
    glsl_taps: int
    metrics_after: Dict[str, Any]


@dataclass
class RejectedLayerRecord:
    plugin_name: str
    reason: str
    report: Optional[FitReport] = None


@dataclass
class TuneResult:
    owner_slug: str
    accepted_layers: List[LayerRecord]
    rejected_layers: List[RejectedLayerRecord]
    swap_checks: List[Dict[str, Any]]
    refinement_rounds: List[Dict[str, Any]]
    metrics_initial: Dict[str, Any]
    metrics_final: Dict[str, Any]
    final_predictions: List[np.ndarray]
    honest_limits: Dict[str, Any]


def evaluate_pair_suite_metrics(
    preds: List[np.ndarray],
    bundles: List[AlignedPairBundle],
) -> Dict[str, Any]:
    """Compute full P6 evaluation metrics per pair and aggregated across pairs."""
    per_pair: Dict[str, Any] = {}
    med_de_list, p90_de_list, mean_de_list = [], [], []
    mae_r_list, mae_g_list, mae_b_list, mae_m_list = [], [], [], []
    edge_raw_list, edge_halo_list, ssim_list = [], [], []

    for pred, b in zip(preds, bundles):
        am = b.masks.active_mask
        de = ciede2000_rgb(pred, b.tgt_rgb, mask=am)
        mae = channel_mae(pred, b.tgt_rgb, mask=am)
        ep = edge_profile_metrics(pred, b.tgt_rgb, b.ref_aligned, am, half_width=8)
        ssim_val = compute_ssim(pred, b.tgt_rgb, mask=am)

        per_pair[b.pair_id] = {
            "ciede2000_median": round(de["median"], 4),
            "ciede2000_p90": round(de["p90"], 4),
            "ciede2000_mean": round(de["mean"], 4),
            "mae_r_255": round(mae["r_255"], 4),
            "mae_g_255": round(mae["g_255"], 4),
            "mae_b_255": round(mae["b_255"], 4),
            "mae_mean_255": round(mae["mean_255"], 4),
            "edge_raw_rmse_255": round(float(ep["raw_rmse_255"]), 4),
            "edge_halo_rmse_255": round(float(ep["halo_rmse_255"]), 4),
            "ssim": round(ssim_val, 5),
        }
        med_de_list.append(de["median"])
        p90_de_list.append(de["p90"])
        mean_de_list.append(de["mean"])
        mae_r_list.append(mae["r_255"])
        mae_g_list.append(mae["g_255"])
        mae_b_list.append(mae["b_255"])
        mae_m_list.append(mae["mean_255"])
        edge_raw_list.append(float(ep["raw_rmse_255"]))
        edge_halo_list.append(float(ep["halo_rmse_255"]))
        ssim_list.append(ssim_val)

    mean_de = float(np.mean(mean_de_list))
    mean_mae = float(np.mean(mae_m_list))
    mean_halo = float(np.mean(edge_halo_list))
    # Composite perceptual objective (lower is better)
    joint_score = 0.55 * mean_de + 0.30 * mean_mae + 0.15 * mean_halo

    return {
        "aggregate": {
            "ciede2000_median": round(float(np.mean(med_de_list)), 4),
            "ciede2000_p90": round(float(np.mean(p90_de_list)), 4),
            "ciede2000_mean": round(mean_de, 4),
            "mae_r_255": round(float(np.mean(mae_r_list)), 4),
            "mae_g_255": round(float(np.mean(mae_g_list)), 4),
            "mae_b_255": round(float(np.mean(mae_b_list)), 4),
            "mae_mean_255": round(mean_mae, 4),
            "edge_raw_rmse_255": round(float(np.mean(edge_raw_list)), 4),
            "edge_halo_rmse_255": round(mean_halo, 4),
            "ssim": round(float(np.mean(ssim_list)), 5),
            "joint_loss": round(joint_score, 5),
        },
        "per_pair": per_pair,
    }


def render_stack(
    imgs: List[np.ndarray],
    layers: List[Tuple[str, Dict[str, Any]]],
    plugins: Dict[str, Plugin],
) -> List[np.ndarray]:
    cur = [im.copy() for im in imgs]
    for pname, prm in layers:
        pl = plugins[pname]
        cur = [pl.render(im, prm) for im in cur]
    return cur


def _save_layer_step_visual(
    step_tag: str,
    preds: List[np.ndarray],
    bundles: List[AlignedPairBundle],
    artifacts_dir: Optional[Path],
) -> None:
    if artifacts_dir is None:
        return
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for pred, b in zip(preds, bundles):
        am = b.masks.active_mask.astype(np.float32)[..., None]
        res_vis = np.clip(0.5 + 3.0 * (b.tgt_rgb - pred) * am, 0.0, 1.0)
        strip = np.concatenate([b.ref_aligned, pred, b.tgt_rgb, res_vis], axis=1)
        if strip.shape[1] > 1920:
            nh = max(64, int(round(strip.shape[0] * (1920.0 / strip.shape[1]))))
            strip = cv2.resize(strip, (1920, nh), interpolation=cv2.INTER_AREA)
        write_rgb_jpg(artifacts_dir / f"{b.pair_id}_{step_tag}.jpg", strip, quality=88)


def _analyze_honest_limits(
    final_preds: List[np.ndarray],
    bundles: List[AlignedPairBundle],
    accepted_layers: List[LayerRecord],
) -> Dict[str, Any]:
    """Quantify physical sources of remaining residual error with concrete measurements."""
    flat_maes, edge_maes, active_maes = [], [], []
    block_lf_stds = []
    blockiness_vals = []
    flat_noise_tgt, flat_noise_pred = [], []
    edge_corrs = []

    for pred, b in zip(final_preds, bundles):
        fm = b.masks.flat_mask
        em = b.masks.edge_mask
        am = b.masks.active_mask
        flat_maes.append(channel_mae(pred, b.tgt_rgb, mask=fm)["mean_255"])
        edge_maes.append(channel_mae(pred, b.tgt_rgb, mask=em)["mean_255"])
        active_maes.append(channel_mae(pred, b.tgt_rgb, mask=am)["mean_255"])
        edge_corrs.append(b.alignment.edge_corr_after)

        ns = noise_statistics(b.tgt_rgb, pred, fm)
        blockiness_vals.append(float(ns["blockiness_ratio"]))
        flat_noise_tgt.append(float(ns["tgt_std_255"]))
        flat_noise_pred.append(float(ns["ref_std_255"]))

        # Measure spatially local block-to-block residual drift (unexplainable by shift-invariant CC)
        res_lf = cv2.GaussianBlur(b.tgt_rgb - pred, (0, 0), 12.0)
        h, w = pred.shape[:2]
        blk_means = []
        for y in range(0, h, 96):
            for x in range(0, w, 96):
                sm = am[y : y + 96, x : x + 96]
                if int(sm.sum()) >= 400:
                    blk_means.append(res_lf[y : y + 96, x : x + 96][sm].mean(axis=0) * 255.0)
        if len(blk_means) >= 4:
            block_lf_stds.append(float(np.std(np.asarray(blk_means), axis=0).mean()))

    shader_gap_255 = 0.0
    for lr in accepted_layers:
        if lr.plugin_name == "colour" and "shader_model" in lr.params:
            shader_gap_255 = float(lr.params["shader_model"]["accuracy_vs_cube"]["mean_diff_255"])

    mean_flat_mae = float(np.mean(flat_maes))
    mean_edge_mae = float(np.mean(edge_maes))
    mean_active_mae = float(np.mean(active_maes))
    mean_blk_drift = float(np.mean(block_lf_stds)) if block_lf_stds else 0.0
    mean_corr = float(np.mean(edge_corrs))

    limiting_factors = []
    if mean_edge_mae > 1.35 * max(mean_flat_mae, 0.5):
        limiting_factors.append(
            f"Edge/resampling & source-replica micro-geometry difference: edge MAE is {mean_edge_mae:.2f}/255 "
            f"vs flat-interior MAE {mean_flat_mae:.2f}/255 (mean post-alignment gradient correlation = {mean_corr:.3f}). "
            f"Different source resolution/cropping or redrawn line-art widths cannot be collapsed by a global filter."
        )
    if mean_blk_drift > 1.2:
        limiting_factors.append(
            f"Spatially local / scene-dependent differences across 96x96 blocks (std = {mean_blk_drift:.2f}/255): "
            f"local relighting, motion blur, or per-shot adjustments vary across frame regions."
        )
    limiting_factors.append(
        f"High-frequency recompression & quantization texture in flat areas: target flat noise std = "
        f"{float(np.mean(flat_noise_tgt)):.2f}/255 vs prediction {float(np.mean(flat_noise_pred)):.2f}/255 "
        f"(8x8 blockiness ratio = {float(np.mean(blockiness_vals)):.2f})."
    )
    limiting_factors.append(
        f"GLSL ES 1.00 single-pass shader compression vs full 3D .cube LUT: mean difference = {shader_gap_255:.3f}/255."
    )

    dominant = (
        "edge/line-art resampling & source-replica geometry differences"
        if mean_edge_mae > 1.35 * max(mean_flat_mae, 0.5)
        else "spatially local / per-shot tonal variations and video recompression"
    )

    return {
        "flat_mae_255": round(mean_flat_mae, 4),
        "edge_mae_255": round(mean_edge_mae, 4),
        "active_mae_255": round(mean_active_mae, 4),
        "spatial_96px_block_drift_std_255": round(mean_blk_drift, 4),
        "mean_edge_correlation": round(mean_corr, 4),
        "target_flat_noise_std_255": round(float(np.mean(flat_noise_tgt)), 4),
        "blockiness_ratio": round(float(np.mean(blockiness_vals)), 4),
        "shader_vs_cube_mean_diff_255": round(shader_gap_255, 4),
        "dominant_limiter": dominant,
        "evidence_notes": limiting_factors,
    }


def tune_owner_stack(
    bundles: List[AlignedPairBundle],
    plan: PlanResult,
    plugins: Dict[str, Plugin],
    artifacts_dir: Optional[Path] = None,
) -> TuneResult:
    """Execute P3 Layer-by-Layer Tuning, Adjacent-Swap Check, and P4 Joint Coordinate Descent."""
    refs_base = [b.ref_aligned for b in bundles]
    tgts = [b.tgt_rgb for b in bundles]
    ctxs = [b.ctx for b in bundles]

    metrics_init = evaluate_pair_suite_metrics(refs_base, bundles)
    _save_layer_step_visual("00_aligned_ref", refs_base, bundles, artifacts_dir)

    accepted: List[LayerRecord] = []
    rejected: List[RejectedLayerRecord] = [
        RejectedLayerRecord(plugin_name=k, reason=v, report=None)
        for k, v in plan.dropped_plugins.items()
    ]

    cur_preds = [r.copy() for r in refs_base]
    cur_metrics = metrics_init

    # --- P3: Tune layer by layer ---
    for step_idx, pname in enumerate(plan.planned_order, start=1):
        plugin = plugins[pname]
        params, report = plugin.fit(cur_preds, tgts, ctxs)

        if not report.accepted_hint:
            rejected.append(
                RejectedLayerRecord(
                    plugin_name=pname,
                    reason=f"Rejected at P3 fit: {report.notes}",
                    report=report,
                )
            )
            continue

        cand_preds = [plugin.render(im, params) for im in cur_preds]
        cand_metrics = evaluate_pair_suite_metrics(cand_preds, bundles)

        if pname != "grain":
            prev_joint = float(cur_metrics["aggregate"]["joint_loss"])
            cand_joint = float(cand_metrics["aggregate"]["joint_loss"])
            # Accept if joint loss improves OR plugin's dedicated held-out metric improved strongly without hurting joint loss
            improves_joint = cand_joint < prev_joint - 0.002
            domain_win_neutral_joint = (report.held_out_rel_gain >= 0.04) and (cand_joint <= prev_joint + 0.008)
            if not (improves_joint or domain_win_neutral_joint):
                rejected.append(
                    RejectedLayerRecord(
                        plugin_name=pname,
                        reason=(
                            f"Rejected at P3 joint check: plugin held-out {report.held_out_loss_before:.3f}->"
                            f"{report.held_out_loss_after:.3f}, but overall perceptual loss did not improve "
                            f"({prev_joint:.4f} -> {cand_joint:.4f})."
                        ),
                        report=report,
                    )
                )
                continue

        lr = LayerRecord(
            plugin_name=pname,
            params=params,
            report=report,
            describe_text=plugin.describe(params),
            glsl_taps=plugin.glsl_taps(params),
            metrics_after=cand_metrics,
        )
        accepted.append(lr)
        cur_preds = cand_preds
        cur_metrics = cand_metrics
        _save_layer_step_visual(f"p3_{step_idx:02d}_{pname}", cur_preds, bundles, artifacts_dir)

    # --- P2/P3 Adjacent-Order Swap Check on accepted non-colour layers ---
    swap_checks: List[Dict[str, Any]] = []
    idx = 0
    while idx + 1 < len(accepted):
        a_rec = accepted[idx]
        b_rec = accepted[idx + 1]
        # Keep colour first and stochastic grain last; test swaps among deterministic spatial/tonal layers
        if a_rec.plugin_name in ("colour", "grain") or b_rec.plugin_name in ("colour", "grain"):
            idx += 1
            continue

        prefix_layers = [(x.plugin_name, x.params) for x in accepted[:idx]]
        suffix_layers = [(x.plugin_name, x.params) for x in accepted[idx + 2 :]]
        in_imgs = render_stack(refs_base, prefix_layers, plugins)

        # Fit B first, then A
        pb, rep_b = plugins[b_rec.plugin_name].fit(in_imgs, tgts, ctxs)
        mid_imgs = [plugins[b_rec.plugin_name].render(im, pb) for im in in_imgs]
        pa, rep_a = plugins[a_rec.plugin_name].fit(mid_imgs, tgts, ctxs)

        if rep_b.accepted_hint and rep_a.accepted_hint:
            swapped_stack = prefix_layers + [(b_rec.plugin_name, pb), (a_rec.plugin_name, pa)] + suffix_layers
            swapped_preds = render_stack(refs_base, swapped_stack, plugins)
            swapped_metrics = evaluate_pair_suite_metrics(swapped_preds, bundles)
            cur_j = float(cur_metrics["aggregate"]["joint_loss"])
            swp_j = float(swapped_metrics["aggregate"]["joint_loss"])
            kept_swap = swp_j < cur_j - 0.005
            swap_checks.append({
                "pair": [a_rec.plugin_name, b_rec.plugin_name],
                "original_joint_loss": cur_j,
                "swapped_joint_loss": swp_j,
                "swapped_kept": kept_swap,
            })
            if kept_swap:
                accepted[idx] = LayerRecord(
                    plugin_name=b_rec.plugin_name,
                    params=pb,
                    report=rep_b,
                    describe_text=plugins[b_rec.plugin_name].describe(pb),
                    glsl_taps=plugins[b_rec.plugin_name].glsl_taps(pb),
                    metrics_after=evaluate_pair_suite_metrics(mid_imgs, bundles),
                )
                after_pair_imgs = [plugins[a_rec.plugin_name].render(im, pa) for im in mid_imgs]
                accepted[idx + 1] = LayerRecord(
                    plugin_name=a_rec.plugin_name,
                    params=pa,
                    report=rep_a,
                    describe_text=plugins[a_rec.plugin_name].describe(pa),
                    glsl_taps=plugins[a_rec.plugin_name].glsl_taps(pa),
                    metrics_after=evaluate_pair_suite_metrics(after_pair_imgs, bundles),
                )
                cur_preds = swapped_preds
                cur_metrics = swapped_metrics
        idx += 1

    # --- P4: Coordinate-Descent Joint Refinement ---
    refinement_rounds: List[Dict[str, Any]] = []
    det_indices = [i for i, r in enumerate(accepted) if r.plugin_name != "grain"]

    if len(det_indices) >= 2:
        for rnd in range(1, 3):
            round_start_joint = float(cur_metrics["aggregate"]["joint_loss"])
            improved_any = False
            layer_updates = []

            for k_idx in det_indices:
                rec = accepted[k_idx]
                pl = plugins[rec.plugin_name]

                prefix = [(accepted[j].plugin_name, accepted[j].params) for j in range(k_idx)]
                suffix_det = [
                    (accepted[j].plugin_name, accepted[j].params)
                    for j in range(k_idx + 1, len(accepted))
                    if accepted[j].plugin_name != "grain"
                ]

                x_in = render_stack(refs_base, prefix, plugins)
                if suffix_det:
                    y_cur = [pl.render(im, rec.params) for im in x_in]
                    z_cur = render_stack(y_cur, suffix_det, plugins)
                    # Pull back target through downstream additive perturbation delta = z_cur - y_cur
                    tgt_eff = [
                        np.clip(t_im - (z_im - y_im), 0.0, 1.0).astype(np.float32)
                        for t_im, z_im, y_im in zip(tgts, z_cur, y_cur)
                    ]
                else:
                    tgt_eff = tgts

                if rec.plugin_name == "colour":
                    f_cfg = {k: rec.params[k] for k in ("grid_size", "space", "pre_blur_sigma", "cluster_weighted", "lam_smooth")}
                    cand_p, cand_rep = pl.fit(x_in, tgt_eff, ctxs, fixed_cfg=f_cfg)  # type: ignore[call-arg]
                else:
                    cand_p, cand_rep = pl.fit(x_in, tgt_eff, ctxs)
                if not cand_rep.accepted_hint:
                    continue

                # Evaluate full stack with candidate update
                trial_layers = [
                    (accepted[j].plugin_name, cand_p if j == k_idx else accepted[j].params)
                    for j in range(len(accepted))
                ]
                trial_preds = render_stack(refs_base, trial_layers, plugins)
                trial_metrics = evaluate_pair_suite_metrics(trial_preds, bundles)

                before_j = float(cur_metrics["aggregate"]["joint_loss"])
                after_j = float(trial_metrics["aggregate"]["joint_loss"])
                # Also ensure colour's own held-out CV did not degrade
                ho_ok = cand_rep.held_out_loss_after <= rec.report.held_out_loss_after + 0.03
                if after_j < before_j - 0.003 and ho_ok:
                    accepted[k_idx] = LayerRecord(
                        plugin_name=rec.plugin_name,
                        params=deepcopy(cand_p),
                        report=cand_rep,
                        describe_text=pl.describe(cand_p),
                        glsl_taps=pl.glsl_taps(cand_p),
                        metrics_after=trial_metrics,
                    )
                    cur_preds = trial_preds
                    cur_metrics = trial_metrics
                    improved_any = True
                    layer_updates.append({
                        "plugin": rec.plugin_name,
                        "joint_before": before_j,
                        "joint_after": after_j,
                    })

            round_end_joint = float(cur_metrics["aggregate"]["joint_loss"])
            refinement_rounds.append({
                "round": rnd,
                "joint_loss_start": round_start_joint,
                "joint_loss_end": round_end_joint,
                "delta": round(round_start_joint - round_end_joint, 5),
                "updates": layer_updates,
            })
            if (not improved_any) or (round_start_joint - round_end_joint < 0.003):
                break

        # Refresh cumulative metrics_after for each accepted layer after P4 refinement
        walk_imgs = [r.copy() for r in refs_base]
        for j, rec in enumerate(accepted):
            walk_imgs = [plugins[rec.plugin_name].render(im, rec.params) for im in walk_imgs]
            accepted[j].metrics_after = evaluate_pair_suite_metrics(walk_imgs, bundles)
        cur_preds = walk_imgs
        cur_metrics = accepted[-1].metrics_after if accepted else metrics_init

    _save_layer_step_visual("99_final_stack", cur_preds, bundles, artifacts_dir)
    limits = _analyze_honest_limits(cur_preds, bundles, accepted)

    return TuneResult(
        owner_slug=bundles[0].owner_slug,
        accepted_layers=accepted,
        rejected_layers=rejected,
        swap_checks=swap_checks,
        refinement_rounds=refinement_rounds,
        metrics_initial=metrics_init,
        metrics_final=cur_metrics,
        final_predictions=cur_preds,
        honest_limits=limits,
    )
