"""Unit tests for lookfit.core (I/O guard, colour spaces, CIEDE2000, alignment, masks, metrics)."""
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
import pytest
from skimage.color import deltaE_ciede2000, rgb2lab

from lookfit.core import (
    align_pair,
    build_pair_masks,
    channel_mae,
    ciede2000,
    ciede2000_rgb,
    compute_ssim,
    edge_profile_metrics,
    lab_to_srgb,
    linear_to_srgb,
    make_block_folds,
    noise_statistics,
    srgb_to_lab,
    srgb_to_linear,
    verify_inputs_untouched,
    write_rgb_png,
)


def test_inputs_untouched_and_write_guard():
    repo_root = Path(__file__).resolve().parent.parent
    assert verify_inputs_untouched(repo_root) is True
    with pytest.raises(PermissionError):
        write_rgb_png(repo_root / "owners" / "floby" / "inputs" / "forbidden.png", np.zeros((8, 8, 3), np.float32))


def test_colour_space_roundtrip_and_lab_accuracy():
    rng = np.random.default_rng(123)
    rgb = rng.uniform(0.0, 1.0, size=(64, 64, 3)).astype(np.float32)
    lin = srgb_to_linear(rgb)
    rgb_rt = linear_to_srgb(lin)
    assert np.max(np.abs(rgb - rgb_rt)) < 1e-5

    lab = srgb_to_lab(rgb)
    lab_ref = rgb2lab(rgb.astype(np.float64)).astype(np.float32)
    assert np.max(np.abs(lab - lab_ref)) < 0.03

    rgb_lab_rt = lab_to_srgb(lab)
    assert np.max(np.abs(rgb - rgb_lab_rt)) < 2e-4


def test_ciede2000_matches_reference_implementation():
    # Sharma et al. (2005) canonical test pairs + random RGB pairs vs scikit-image
    lab1 = np.array(
        [
            [50.0000, 2.6772, -79.7751],
            [50.0000, 3.1571, -77.2803],
            [50.0000, 2.5000, 0.0000],
            [60.2574, -34.0099, 36.2677],
        ],
        dtype=np.float32,
    )
    lab2 = np.array(
        [
            [50.0000, 0.0000, -82.7485],
            [50.0000, 0.0000, -82.7485],
            [73.0000, 25.0000, -18.0000],
            [60.4626, -34.1751, 39.4387],
        ],
        dtype=np.float32,
    )
    expected = np.array([2.0425, 2.8615, 27.1492, 1.2644], dtype=np.float32)
    got = ciede2000(lab1, lab2)
    assert np.allclose(got, expected, atol=1e-3)

    rng = np.random.default_rng(7)
    r1 = rng.uniform(0.0, 1.0, (200, 3)).astype(np.float32)
    r2 = rng.uniform(0.0, 1.0, (200, 3)).astype(np.float32)
    de_ours = ciede2000(srgb_to_lab(r1), srgb_to_lab(r2))
    de_sk = deltaE_ciede2000(rgb2lab(r1), rgb2lab(r2)).astype(np.float32)
    assert np.max(np.abs(de_ours - de_sk)) < 0.02


def test_subpixel_alignment_recovers_synthetic_shift_and_scale():
    # Build synthetic anime-style test canvas with sharp shapes & textures
    h, w = 360, 640
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ref = np.zeros((h, w, 3), dtype=np.float32)
    ref[..., 0] = 0.25 + 0.2 * np.sin(xx / 45.0)
    ref[..., 1] = 0.35 + 0.2 * np.cos(yy / 40.0)
    ref[..., 2] = 0.50
    cv2.circle(ref, (220, 170), 75, (0.9, 0.7, 0.4), -1, lineType=cv2.LINE_AA)
    cv2.circle(ref, (220, 170), 75, (0.08, 0.08, 0.1), 3, lineType=cv2.LINE_AA)
    cv2.rectangle(ref, (360, 90), (520, 270), (0.2, 0.8, 0.6), -1)
    cv2.rectangle(ref, (360, 90), (520, 270), (0.05, 0.05, 0.05), 3)
    for k in range(12):
        cv2.line(ref, (60 + k * 42, 40), (90 + k * 38, 320), (0.12, 0.15, 0.2), 2, lineType=cv2.LINE_AA)

    # Apply known sub-pixel shift (+3.35 px, -2.15 px) AND a colour grade
    true_dx, true_dy = 3.35, -2.15
    M_true = np.array([[1.0, 0.0, true_dx], [0.0, 1.0, true_dy]], dtype=np.float32)
    warped = cv2.warpAffine(ref, M_true, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT101)
    tgt = np.clip(np.power(np.clip(warped, 0.0, 1.0), 0.85) * np.array([1.08, 0.96, 1.12], np.float32), 0.0, 1.0)

    res = align_pair(ref, tgt)
    assert abs(res.tx_px - true_dx) < 0.20
    assert abs(res.ty_px - true_dy) < 0.20
    assert res.edge_corr_after > 0.96


def test_masks_detect_bars_captions_and_96px_blocks():
    h, w = 360, 640
    ref = np.full((h, w, 3), 0.45, dtype=np.float32)
    cv2.circle(ref, (320, 180), 80, (0.8, 0.6, 0.5), -1, lineType=cv2.LINE_AA)
    cv2.circle(ref, (320, 180), 80, (0.08, 0.08, 0.08), 3, lineType=cv2.LINE_AA)
    # Add 32px top/bottom letterbox bars
    ref[:32, :] = 0.0
    ref[h - 32 :, :] = 0.0

    tgt = ref.copy() * np.array([0.95, 1.02, 1.08], dtype=np.float32)
    tgt = np.clip(tgt, 0.0, 1.0)
    # Burn a high-contrast white+black-outlined subtitle on target only
    tgt_u8 = np.clip(np.rint(tgt * 255.0), 0, 255).astype(np.uint8)
    cv2.putText(tgt_u8, "SUBTITLE TEST", (190, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(tgt_u8, "SUBTITLE TEST", (190, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    tgt = tgt_u8.astype(np.float32) / 255.0

    vmask = np.ones((h, w), dtype=bool)
    pm = build_pair_masks(ref, tgt, vmask, block_size=96, n_folds=5)

    assert pm.bar_bounds[0] >= 32 and pm.bar_bounds[1] >= 32
    assert pm.bar_mask[10, 320] and pm.bar_mask[h - 10, 320]
    # Subtitle area around (y=288, x=260) should be caught by caption_mask and excluded from active_mask
    assert pm.caption_mask[280:300, 200:410].mean() > 0.45
    assert not pm.active_mask[288, 250]
    # Circle boundary should be in edge_mask and excluded from flat_mask
    assert pm.edge_mask[180, 240]
    assert not pm.flat_mask[180, 240]
    # Block folds must have 5 folds and constant fold inside each 96x96 cell
    assert set(np.unique(pm.block_folds)) == {0, 1, 2, 3, 4}
    assert np.unique(pm.block_folds[0:96, 0:96]).size == 1


def test_metrics_edge_profile_and_noise():
    h, w = 256, 256
    ref = np.full((h, w, 3), 0.35, dtype=np.float32)
    ref[:, 128:, :] = 0.75
    ref = cv2.GaussianBlur(ref, (0, 0), 1.0)
    # Sharpened target
    blur = cv2.GaussianBlur(ref, (0, 0), 2.5)
    tgt = np.clip(ref + 0.8 * (ref - blur), 0.0, 1.0)

    active = np.ones((h, w), dtype=bool)
    active[:16, :] = False
    active[-16:, :] = False
    active[:, :16] = False
    active[:, -16:] = False

    ep_before = edge_profile_metrics(ref, tgt, ref, active)
    ep_after = edge_profile_metrics(tgt, tgt, ref, active)
    assert ep_before["n_profiles"] > 20
    assert ep_before["halo_rmse_255"] > 2.0
    assert ep_after["halo_rmse_255"] < 1e-4

    mae = channel_mae(ref, tgt, active)
    assert mae["mean_255"] > 0.1
    assert compute_ssim(tgt, tgt, active) > 0.9999

    rng = np.random.default_rng(99)
    mono_noise = rng.normal(0.0, 6.0 / 255.0, (h, w, 1)).astype(np.float32)
    grainy = np.clip(ref + mono_noise, 0.0, 1.0)
    flat = active.copy()
    flat[:, 116:140] = False
    ns = noise_statistics(grainy, ref, flat)
    assert 4.5 <= ns["excess_std_255"] <= 7.5
