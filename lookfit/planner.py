"""P0 Analysis, P1 Detection (with diagnostic maps), and P2 Stack Planning."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lookfit.core.alignment import AlignmentResult, align_pair
from lookfit.core.colour_spaces import luma_rec709
from lookfit.core.io import (
    FramePair,
    load_owner_pairs,
    verify_inputs_untouched,
    write_rgb_jpg,
)
from lookfit.core.masks import PairMasks, build_pair_masks
from lookfit.core.metrics import edge_profile_metrics, noise_statistics
from lookfit.export.cube import eval_lut_trilinear
from lookfit.plugins import CORE_PLUGIN_ORDER, OPTIONAL_PLUGIN_ORDER
from lookfit.plugins.base import Evidence, PairContext, Plugin
from lookfit.plugins.colour import _compute_cluster_weights, fit_3d_lut_direct


@dataclass
class AlignedPairBundle:
    owner_slug: str
    pair_id: str
    ref_orig_shape: tuple[int, int, int]
    tgt_shape: tuple[int, int, int]
    ref_aligned: np.ndarray
    tgt_rgb: np.ndarray
    alignment: AlignmentResult
    masks: PairMasks
    ctx: PairContext


@dataclass
class PlanResult:
    owner_slug: str
    evidence_by_plugin: Dict[str, Evidence]
    plain_words_evidence: List[str]
    planned_order: List[str]
    dropped_plugins: Dict[str, str]
    pair_summaries: List[Dict[str, Any]] = field(default_factory=list)


def analyze_owner_pairs(repo_root: str | Path, owner_slug: str) -> List[AlignedPairBundle]:
    """P0 Analysis: verify untouched inputs, load all pairs for owner, align sub-pixel, build masks."""
    verify_inputs_untouched(repo_root)
    raw_pairs: List[FramePair] = load_owner_pairs(repo_root, owner_slug)
    bundles: List[AlignedPairBundle] = []

    for fp in raw_pairs:
        al = align_pair(fp.ref_rgb, fp.tgt_rgb)
        masks = build_pair_masks(al.ref_aligned, fp.tgt_rgb, al.valid_warp_mask, block_size=96, n_folds=5)
        pctx = PairContext(
            pair_id=fp.pair_id,
            masks=masks,
            orig_ref_rgb=al.ref_aligned,
            extra={
                "alignment_method": al.method,
                "edge_corr_after": al.edge_corr_after,
            },
        )
        bundles.append(
            AlignedPairBundle(
                owner_slug=owner_slug,
                pair_id=fp.pair_id,
                ref_orig_shape=fp.ref_rgb.shape,
                tgt_shape=fp.tgt_rgb.shape,
                ref_aligned=al.ref_aligned,
                tgt_rgb=fp.tgt_rgb,
                alignment=al,
                masks=masks,
                ctx=pctx,
            )
        )
    return bundles


def _fit_fast_probe_colour(bundles: List[AlignedPairBundle]) -> List[np.ndarray]:
    """Fit a fast 17^3 smooth flat-area 3D LUT so spatial/noise detectors inspect post-colour residuals."""
    s_list, d_list = [], []
    for b in bundles:
        rb = cv2.GaussianBlur(b.ref_aligned, (0, 0), 2.0)
        tb = cv2.GaussianBlur(b.tgt_rgb, (0, 0), 2.0)
        fm = b.masks.flat_mask
        if int(fm.sum()) < 200:
            fm = b.masks.active_mask
        pts_s = rb[fm]
        pts_d = tb[fm]
        if pts_s.shape[0] > 25000:
            idx = np.linspace(0, pts_s.shape[0] - 1, 25000, dtype=np.int64)
            pts_s, pts_d = pts_s[idx], pts_d[idx]
        s_list.append(pts_s)
        d_list.append(pts_d)
    src_all = np.concatenate(s_list, axis=0)
    dst_all = np.concatenate(d_list, axis=0)
    probe_lut = fit_3d_lut_direct(src_all, dst_all, _compute_cluster_weights(src_all), grid_size=17, lam_smooth=0.35)
    return [eval_lut_trilinear(b.ref_aligned, probe_lut) for b in bundles]


def _save_p1_diagnostic_maps(
    bundles: List[AlignedPairBundle],
    probe_graded: List[np.ndarray],
    diag_dir: Path,
) -> None:
    """Save human-inspectable P1 diagnostic visuals: channel residuals, edge-halo plot, LF map, noise map."""
    diag_dir.mkdir(parents=True, exist_ok=True)

    # 1. Per-pair channel residual & low-frequency residual & noise map (compact JPEGs)
    for b, g_im in zip(bundles, probe_graded):
        am = b.masks.active_mask.astype(np.float32)[..., None]
        res = (b.tgt_rgb - g_im) * am  # signed [-1, 1]
        # Signed residual visualization: 0.5 = zero, +/-0.25 full scale (x2 gain around mid-grey)
        r_vis = np.repeat(np.clip(0.5 + 2.5 * res[..., 0:1], 0.0, 1.0), 3, axis=-1)
        g_vis = np.repeat(np.clip(0.5 + 2.5 * res[..., 1:2], 0.0, 1.0), 3, axis=-1)
        b_vis = np.repeat(np.clip(0.5 + 2.5 * res[..., 2:3], 0.0, 1.0), 3, axis=-1)
        strip = np.concatenate([r_vis, g_vis, b_vis], axis=1)
        h, w = strip.shape[:2]
        if w > 1440:
            nh = max(64, int(round(h * (1440.0 / w))))
            strip = cv2.resize(strip, (1440, nh), interpolation=cv2.INTER_AREA)
        write_rgb_jpg(diag_dir / f"{b.pair_id}_p1_channel_residuals.jpg", strip, quality=85)

        # Low-frequency smooth residual map (x4 gain around 0.5 grey)
        s_lf = max(8.0, 0.03 * b.tgt_rgb.shape[0])
        lf_res = cv2.GaussianBlur(res, (0, 0), s_lf)
        lf_vis = np.clip(0.5 + 4.0 * lf_res, 0.0, 1.0)
        # Overlay mask outline on second panel: [probe_graded | target | lf_residual_x4]
        lf_strip = np.concatenate([g_im, b.tgt_rgb, lf_vis], axis=1)
        if lf_strip.shape[1] > 1440:
            nh = max(64, int(round(lf_strip.shape[0] * (1440.0 / lf_strip.shape[1]))))
            lf_strip = cv2.resize(lf_strip, (1440, nh), interpolation=cv2.INTER_AREA)
        write_rgb_jpg(diag_dir / f"{b.pair_id}_p1_lowfreq_map.jpg", lf_strip, quality=85)

        # Flat-area high-frequency noise comparison [ref_hp | tgt_hp] amplified x8 around 0.5
        gl = luma_rec709(g_im)
        tl = luma_rec709(b.tgt_rgb)
        hp_g = (gl - cv2.GaussianBlur(gl, (0, 0), 1.4)) * b.masks.flat_mask
        hp_t = (tl - cv2.GaussianBlur(tl, (0, 0), 1.4)) * b.masks.flat_mask
        noise_strip = np.repeat(
            np.concatenate([np.clip(0.5 + 8.0 * hp_g, 0.0, 1.0), np.clip(0.5 + 8.0 * hp_t, 0.0, 1.0)], axis=1)[..., None],
            3,
            axis=-1,
        )
        if noise_strip.shape[1] > 1280:
            nh = max(64, int(round(noise_strip.shape[0] * (1280.0 / noise_strip.shape[1]))))
            noise_strip = cv2.resize(noise_strip, (1280, nh), interpolation=cv2.INTER_AREA)
        write_rgb_jpg(diag_dir / f"{b.pair_id}_p1_noise_map.jpg", noise_strip, quality=85)

    # 2. Combined perpendicular edge-halo profile plot across pairs
    fig, axes = plt.subplots(1, len(bundles), figsize=(4.5 * len(bundles), 3.4), squeeze=False)
    xs = np.arange(-8, 9)
    for idx, (b, g_im) in enumerate(zip(bundles, probe_graded)):
        ax = axes[0, idx]
        ep = edge_profile_metrics(g_im, b.tgt_rgb, b.ref_aligned, b.masks.active_mask, half_width=8)
        ax.plot(xs, ep["mean_ref_profile"], "--", label="Ref (aligned)", color="#666666", linewidth=1.3)
        ax.plot(xs, ep["mean_pred_profile"], "-", label="Ref + probe LUT", color="#1f77b4", linewidth=1.6)
        ax.plot(xs, ep["mean_tgt_profile"], "-", label="Target", color="#d62728", linewidth=1.8)
        ax.axhline(0.0, color="#aaaaaa", linewidth=0.6)
        ax.set_title(f"{b.owner_slug}/{b.pair_id} (halo RMSE={ep['halo_rmse_255']:.2f}/255)", fontsize=9)
        ax.set_xlabel("Normal offset (px)")
        if idx == 0:
            ax.set_ylabel("Zero-mean luma (/255)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(diag_dir / "p1_edge_halo_profiles.png", dpi=110)
    plt.close(fig)


def detect_and_plan(
    bundles: List[AlignedPairBundle],
    plugins: Dict[str, Plugin],
    diag_dir: Optional[Path] = None,
) -> PlanResult:
    """Run P1 detection across all plugins and build P2 initial stack plan."""
    assert len(bundles) > 0
    owner_slug = bundles[0].owner_slug
    refs_raw = [b.ref_aligned for b in bundles]
    tgts = [b.tgt_rgb for b in bundles]
    ctxs = [b.ctx for b in bundles]

    probe_graded = _fit_fast_probe_colour(bundles)
    if diag_dir is not None:
        _save_p1_diagnostic_maps(bundles, probe_graded, diag_dir)

    evidence_by_plugin: Dict[str, Evidence] = {}
    plain_words: List[str] = []

    # 1. Colour plugin runs on raw aligned reference vs target
    ev_col = plugins["colour"].detect(refs_raw, tgts, ctxs)
    evidence_by_plugin["colour"] = ev_col
    plain_words.append(f"[colour] {ev_col.status.upper()}: {ev_col.notes}")

    # 2. Downstream spatial, highlight-bloom, low-freq, and noise plugins inspect post-colour residual
    for pname in CORE_PLUGIN_ORDER[1:] + OPTIONAL_PLUGIN_ORDER:
        if pname not in plugins:
            continue
        ev = plugins[pname].detect(probe_graded, tgts, ctxs)
        evidence_by_plugin[pname] = ev
        plain_words.append(f"[{pname}] {ev.status.upper()}: {ev.notes}")

    # 3. Build planned stack
    planned_order: List[str] = []
    dropped: Dict[str, str] = {}

    for pname in CORE_PLUGIN_ORDER:
        ev = evidence_by_plugin[pname]
        if ev.status in ("absent", "not_provable"):
            dropped[pname] = f"Dropped at P2 Plan ({ev.status}): {ev.notes}"
        else:
            planned_order.append(pname)

    # Optional plugins: include ONLY if detector fires with status == 'present'
    for pname in OPTIONAL_PLUGIN_ORDER:
        ev = evidence_by_plugin[pname]
        if ev.status == "present":
            # Insert black_lift right after colour, chromatic_aberration before sharpen, flicker at end
            if pname == "black_lift":
                ins_idx = 1 if (planned_order and planned_order[0] == "colour") else 0
                planned_order.insert(ins_idx, pname)
            elif pname == "chromatic_aberration":
                ins_idx = 1 if (planned_order and planned_order[0] == "colour") else 0
                planned_order.insert(ins_idx, pname)
            else:
                planned_order.append(pname)
        else:
            dropped[pname] = f"Optional plugin not triggered ({ev.status}): {ev.notes}"

    pair_summaries = []
    for b in bundles:
        ns = noise_statistics(b.tgt_rgb, b.ref_aligned, b.masks.flat_mask)
        pair_summaries.append({
            "pair_id": b.pair_id,
            "ref_orig_shape": list(b.ref_orig_shape),
            "tgt_shape": list(b.tgt_shape),
            "alignment": {
                "method": b.alignment.method,
                "tx_px": round(b.alignment.tx_px, 3),
                "ty_px": round(b.alignment.ty_px, 3),
                "scale_x": round(b.alignment.scale_x, 5),
                "scale_y": round(b.alignment.scale_y, 5),
                "rotation_deg": round(b.alignment.rotation_deg, 4),
                "edge_corr_before": round(b.alignment.edge_corr_before, 4),
                "edge_corr_after": round(b.alignment.edge_corr_after, 4),
            },
            "masks": {
                "active_frac": round(float(b.masks.active_mask.mean()), 4),
                "flat_frac": round(float(b.masks.flat_mask.mean()), 4),
                "edge_frac": round(float(b.masks.edge_mask.mean()), 4),
                "caption_frac": round(float(b.masks.caption_mask.mean()), 4),
                "bar_bounds_tblr": list(b.masks.bar_bounds),
            },
            "raw_noise_stats": {
                "ref_std_255": round(float(ns["ref_std_255"]), 3),
                "tgt_std_255": round(float(ns["tgt_std_255"]), 3),
                "excess_std_255": round(float(ns["excess_std_255"]), 3),
                "blockiness_ratio": round(float(ns["blockiness_ratio"]), 3),
            },
        })

    if diag_dir is not None:
        ev_payload = {
            "owner": owner_slug,
            "pair_summaries": pair_summaries,
            "plain_words": plain_words,
            "planned_order": planned_order,
            "dropped_plugins": dropped,
            "evidence": {
                k: {
                    "status": v.status,
                    "score": round(float(v.score), 4),
                    "notes": v.notes,
                    "metrics": v.metrics,
                }
                for k, v in evidence_by_plugin.items()
            },
        }
        (diag_dir / "evidence.json").write_text(json.dumps(ev_payload, indent=2) + "\n", encoding="utf-8")

    return PlanResult(
        owner_slug=owner_slug,
        evidence_by_plugin=evidence_by_plugin,
        plain_words_evidence=plain_words,
        planned_order=planned_order,
        dropped_plugins=dropped,
        pair_summaries=pair_summaries,
    )
