"""Integration tests for planner.py, tuner.py, glsl_exporter.py, and kfpack.py on synthetic multi-layer looks."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from lookfit.core.masks import build_pair_masks
from lookfit.export.glsl_exporter import (
    compose_owner_keyflaw_shader,
    validate_glsl_es100,
    verify_shader_vs_python_parity,
)
from lookfit.export.kfpack import build_motionsalt_kfpack
from lookfit.planner import AlignedPairBundle, detect_and_plan
from lookfit.plugins import create_all_plugins
from lookfit.plugins.base import PairContext
from lookfit.core.alignment import AlignmentResult
from lookfit.tuner import tune_owner_stack


def _make_synthetic_bundle(h: int = 320, w: int = 480) -> tuple[AlignedPairBundle, dict]:
    rng = np.random.default_rng(2026)
    img = np.full((h, w, 3), 0.36, dtype=np.float32)
    # Diverse coloured flat regions + bright highlight + crisp dark line-art
    cv2.rectangle(img, (20, 20), (220, 290), (0.28, 0.52, 0.74), -1)
    cv2.rectangle(img, (20, 20), (220, 290), (0.07, 0.07, 0.09), 3)
    cv2.circle(img, (340, 175), 85, (0.80, 0.62, 0.50), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (340, 175), 85, (0.08, 0.07, 0.09), 3, lineType=cv2.LINE_AA)
    # Bright sun highlight in upper right for bloom test
    cv2.circle(img, (405, 70), 28, (0.97, 0.95, 0.88), -1, lineType=cv2.LINE_AA)
    ref = cv2.GaussianBlur(img, (0, 0), 1.0).astype(np.float32)

    plugins = create_all_plugins()
    # Apply known 3-layer stack: colour grade -> sharpen -> vignette (no haze_flare, no grain!)
    x = np.clip(ref * np.array([1.08, 0.98, 1.12], dtype=np.float32) + np.array([0.02, -0.01, 0.03], dtype=np.float32), 0.0, 1.0)
    x = plugins["sharpen"].render(x, {"k": 0.65, "kernel": "binomial3x3", "channel_mode": "rgb"})
    tgt = plugins["vignette"].render(
        x,
        {"center_x": 0.50, "center_y_top": 0.50, "radius": 0.42, "softness": 0.55, "strength": 0.30},
    )

    vmask = np.ones((h, w), dtype=bool)
    masks = build_pair_masks(ref, tgt, vmask)
    al = AlignmentResult(
        ref_aligned=ref,
        valid_warp_mask=vmask,
        warp_matrix_2x3=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        tx_px=0.0,
        ty_px=0.0,
        scale_x=1.0,
        scale_y=1.0,
        rotation_deg=0.0,
        edge_corr_before=0.99,
        edge_corr_after=0.99,
        method="identity",
    )
    bundle = AlignedPairBundle(
        owner_slug="synth",
        pair_id="pairA",
        ref_orig_shape=ref.shape,
        tgt_shape=tgt.shape,
        ref_aligned=ref,
        tgt_rgb=tgt,
        alignment=al,
        masks=masks,
        ctx=PairContext(pair_id="pairA", masks=masks, orig_ref_rgb=ref),
    )
    return bundle, plugins


def test_end_to_end_plan_tune_shader_parity_and_kfpack(tmp_path: Path):
    bundle, plugins = _make_synthetic_bundle()
    plan = detect_and_plan([bundle], plugins, diag_dir=tmp_path / "diag")
    assert "colour" in plan.planned_order
    assert "grain" not in plan.planned_order  # Clean scene -> grain must be dropped!

    tune_res = tune_owner_stack([bundle], plan, plugins, artifacts_dir=tmp_path / "art")
    acc_names = [lr.plugin_name for lr in tune_res.accepted_layers]
    assert "colour" in acc_names
    assert "vignette" in acc_names
    assert ("sharpen" in acc_names) or ("unsharp_mask" in acc_names)
    assert "haze_flare" not in acc_names
    assert "grain" not in acc_names

    m0 = tune_res.metrics_initial["aggregate"]
    m1 = tune_res.metrics_final["aggregate"]
    assert m1["ciede2000_median"] < 0.30 * m0["ciede2000_median"]
    assert m1["mae_mean_255"] < 0.30 * m0["mae_mean_255"]

    shader_src, shader_meta = compose_owner_keyflaw_shader("synth", tune_res.accepted_layers, plugins, max_taps=60)
    assert shader_meta["total_texture_taps"] <= 60
    assert shader_meta["has_haze_flare_switch"] is False

    ok_glsl, log_glsl = validate_glsl_es100(shader_src)
    assert ok_glsl, f"glslangValidator failed:\n{log_glsl}"

    parity = verify_shader_vs_python_parity([bundle.ref_aligned], tune_res.accepted_layers, shader_meta, plugins)
    assert parity["colour_within_1_255"] is True
    assert parity["full_stack_within_2_255"] is True

    # Build and validate Keyflaw .kfpack
    pack_info = build_motionsalt_kfpack(tmp_path, {"synth": (shader_src, shader_meta)}, version="2.0.0")
    assert Path(pack_info["kfpack_path"]).exists()
    assert len(pack_info["errors"]) == 0
    assert "suite.json" in pack_info["zip_entries"]
    assert "effects/MS_synth_cc/effect.json" in pack_info["zip_entries"]
    assert "effects/MS_synth_cc/shader.glsl" in pack_info["zip_entries"]
