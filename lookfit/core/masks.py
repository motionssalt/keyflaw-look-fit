"""Automatic bar, border, burnt-in subtitle/caption, flat-interior, edge, and block-CV masks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

from .colour_spaces import luma_rec709


@dataclass
class PairMasks:
    valid_warp_mask: np.ndarray  # bool (H, W)
    bar_mask: np.ndarray         # bool (H, W) True where letterbox/pillarbox bars exist
    border_mask: np.ndarray      # bool (H, W) True near frame edges / warp boundary
    caption_mask: np.ndarray     # bool (H, W) True where burnt-in subtitles/overlays exist
    active_mask: np.ndarray      # bool (H, W) usable scene interior
    flat_mask: np.ndarray        # bool (H, W) smooth interior pixels for colour & noise analysis
    edge_mask: np.ndarray        # bool (H, W) clean structural line-art neighbourhood
    block_folds: np.ndarray      # int32 (H, W) fold index 0..(n_folds-1) for 96px block CV
    bar_bounds: Tuple[int, int, int, int]  # (top_px, bottom_px, left_px, right_px)


def _scan_bar_thickness(luma_a: np.ndarray, luma_b: np.ndarray, axis: int, from_end: bool) -> int:
    """Scan inward from an edge along rows (axis=1) or cols (axis=0) for uniform dark bars."""
    n = luma_a.shape[0 if axis == 1 else 1]
    max_scan = int(0.24 * n)
    indices = range(n - 1, n - 1 - max_scan, -1) if from_end else range(0, max_scan)
    count = 0
    for idx in indices:
        sl_a = luma_a[idx, :] if axis == 1 else luma_a[:, idx]
        sl_b = luma_b[idx, :] if axis == 1 else luma_b[:, idx]
        rng_a = float(np.percentile(sl_a, 98) - np.percentile(sl_a, 2))
        rng_b = float(np.percentile(sl_b, 98) - np.percentile(sl_b, 2))
        p95_a = float(np.percentile(sl_a, 95))
        p95_b = float(np.percentile(sl_b, 95))
        # Bar if either ref or tgt has a flat dark band along this line
        is_bar_a = (rng_a < (4.0 / 255.0)) and (p95_a < (18.0 / 255.0))
        is_bar_b = (rng_b < (6.0 / 255.0)) and (p95_b < (24.0 / 255.0))
        if is_bar_a or is_bar_b:
            count += 1
        else:
            break
    if count > 0:
        # Add 4 px inward safety margin for anti-aliased / sharpened bar transitions
        count = min(max_scan, count + 4)
    return count


def detect_bars(ref_rgb: np.ndarray, tgt_rgb: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    h, w = tgt_rgb.shape[:2]
    la = luma_rec709(ref_rgb)
    lb = luma_rec709(tgt_rgb)
    top = _scan_bar_thickness(la, lb, axis=1, from_end=False)
    bot = _scan_bar_thickness(la, lb, axis=1, from_end=True)
    left = _scan_bar_thickness(la, lb, axis=0, from_end=False)
    right = _scan_bar_thickness(la, lb, axis=0, from_end=True)

    bar_mask = np.zeros((h, w), dtype=bool)
    if top > 0:
        bar_mask[:top, :] = True
    if bot > 0:
        bar_mask[h - bot :, :] = True
    if left > 0:
        bar_mask[:, :left] = True
    if right > 0:
        bar_mask[:, w - right :] = True
    return bar_mask, (top, bot, left, right)


def detect_captions(
    ref_rgb: np.ndarray,
    tgt_rgb: np.ndarray,
    valid_warp_mask: np.ndarray,
    bar_mask: np.ndarray,
) -> np.ndarray:
    """Detect burnt-in subtitles, watermarks, or overlaid text strokes absent in reference."""
    h, w = tgt_rgb.shape[:2]
    base_valid = valid_warp_mask & (~bar_mask)
    if int(base_valid.sum()) < 500:
        return np.zeros((h, w), dtype=bool)

    ref_l = luma_rec709(ref_rgb)
    tgt_l = luma_rec709(tgt_rgb)

    # Rough global quadratic RGB -> tgt_luma predictor so normal colour grades don't trigger caption outlier
    ys, xs = np.nonzero(base_valid)
    step = max(1, ys.size // 8000)
    sub_r = ref_rgb[ys[::step], xs[::step]]
    sub_t = tgt_l[ys[::step], xs[::step]]
    X_sub = np.column_stack([np.ones(sub_r.shape[0], np.float32), sub_r, sub_r * sub_r])
    coef, _, _, _ = np.linalg.lstsq(X_sub, sub_t, rcond=None)
    X_all = np.concatenate(
        [np.ones((h, w, 1), np.float32), ref_rgb, ref_rgb * ref_rgb], axis=-1
    )
    pred_l = np.clip(X_all @ coef, 0.0, 1.0)
    luma_res = np.abs(tgt_l - pred_l)

    # Gradient magnitudes (dilate ref_grad so upscaled/soft anime edges in ref are NEVER mistaken for captions)
    rgx = cv2.Sobel(cv2.GaussianBlur(ref_l, (0, 0), 0.8), cv2.CV_32F, 1, 0, ksize=3)
    rgy = cv2.Sobel(cv2.GaussianBlur(ref_l, (0, 0), 0.8), cv2.CV_32F, 0, 1, ksize=3)
    tgx = cv2.Sobel(cv2.GaussianBlur(tgt_l, (0, 0), 0.8), cv2.CV_32F, 1, 0, ksize=3)
    tgy = cv2.Sobel(cv2.GaussianBlur(tgt_l, (0, 0), 0.8), cv2.CV_32F, 0, 1, ksize=3)
    r_grad = np.hypot(rgx, rgy)
    t_grad = np.hypot(tgx, tgy)

    k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    r_grad_near = cv2.dilate(r_grad, k9)
    res_near = cv2.dilate(luma_res, k9)

    # Overlaid glyph stroke: crisp edge in tgt, flat neighbourhood in ref, AND strong unexplained luma residual
    stroke_seed = (
        base_valid
        & (t_grad > 0.28)
        & (r_grad_near < 0.10)
        & (res_near > 0.22)
    )

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(stroke_seed.astype(np.uint8), connectivity=8)
    filtered = np.zeros((h, w), dtype=np.uint8)
    max_glyph_h = int(0.16 * h)
    max_glyph_w = int(0.32 * w)
    for lbl in range(1, num_labels):
        area = int(stats[lbl, cv2.CC_STAT_AREA])
        bw = int(stats[lbl, cv2.CC_STAT_WIDTH])
        bh = int(stats[lbl, cv2.CC_STAT_HEIGHT])
        if area >= 6 and bh <= max_glyph_h and bw <= max_glyph_w:
            filtered[labels == lbl] = 255

    if filtered.max() == 0:
        return np.zeros((h, w), dtype=bool)

    dil_r = max(12, int(round(0.018 * h)))
    k_dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dil_r + 1, 2 * dil_r + 1))
    caption_mask = cv2.dilate(filtered, k_dil) > 0

    if float(caption_mask.mean()) > 0.16:
        return np.zeros((h, w), dtype=bool)
    return caption_mask


def make_block_folds(
    shape: Tuple[int, int],
    block_size: int = 96,
    n_folds: int = 5,
    seed: int = 42,
) -> np.ndarray:
    """Assign spatial 96x96 px blocks to k cross-validation folds without spatial leakage."""
    h, w = shape
    bh = int(np.ceil(h / float(block_size)))
    bw = int(np.ceil(w / float(block_size)))
    n_blocks = bh * bw
    rng = np.random.default_rng(seed)
    # Balanced fold assignment shuffled across spatial blocks
    block_ids = np.arange(n_blocks, dtype=np.int32) % n_folds
    rng.shuffle(block_ids)
    grid = block_ids.reshape(bh, bw)
    ys = np.minimum(np.arange(h) // block_size, bh - 1)
    xs = np.minimum(np.arange(w) // block_size, bw - 1)
    return grid[np.ix_(ys, xs)].astype(np.int32)


def build_pair_masks(
    ref_aligned: np.ndarray,
    tgt_rgb: np.ndarray,
    valid_warp_mask: np.ndarray,
    block_size: int = 96,
    n_folds: int = 5,
) -> PairMasks:
    h, w = tgt_rgb.shape[:2]
    bar_mask, bar_bounds = detect_bars(ref_aligned, tgt_rgb)

    # Border mask around outer perimeter and warp footprint boundary
    bpx = max(8, int(round(0.01 * h)))
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:bpx, :] = True
    border_mask[h - bpx :, :] = True
    border_mask[:, :bpx] = True
    border_mask[:, w - bpx :] = True
    k_warp = cv2.getStructuringElement(cv2.MORPH_RECT, (2 * bpx + 1, 2 * bpx + 1))
    inner_warp = cv2.erode(valid_warp_mask.astype(np.uint8), k_warp) > 0
    border_mask |= valid_warp_mask & (~inner_warp)

    caption_mask = detect_captions(ref_aligned, tgt_rgb, valid_warp_mask, bar_mask)
    active_mask = valid_warp_mask & (~bar_mask) & (~border_mask) & (~caption_mask)

    # Compute local gradient and local 7x7 std on both ref and tgt for flat vs edge separation
    ref_l = luma_rec709(ref_aligned)
    tgt_l = luma_rec709(tgt_rgb)

    def _local_std(img_l: np.ndarray) -> np.ndarray:
        m1 = cv2.boxFilter(img_l, cv2.CV_32F, (7, 7))
        m2 = cv2.boxFilter(img_l * img_l, cv2.CV_32F, (7, 7))
        return np.sqrt(np.maximum(m2 - m1 * m1, 0.0))

    std_ref = _local_std(ref_l)
    std_tgt = _local_std(tgt_l)

    rgx = cv2.Sobel(cv2.GaussianBlur(ref_l, (0, 0), 1.0), cv2.CV_32F, 1, 0, ksize=3)
    rgy = cv2.Sobel(cv2.GaussianBlur(ref_l, (0, 0), 1.0), cv2.CV_32F, 0, 1, ksize=3)
    tgx = cv2.Sobel(cv2.GaussianBlur(tgt_l, (0, 0), 1.0), cv2.CV_32F, 1, 0, ksize=3)
    tgy = cv2.Sobel(cv2.GaussianBlur(tgt_l, (0, 0), 1.0), cv2.CV_32F, 0, 1, ksize=3)
    grad_ref = np.hypot(rgx, rgy)
    grad_tgt = np.hypot(tgx, tgy)

    if int(active_mask.sum()) > 500:
        std_thr_r = min(0.032, float(np.percentile(std_ref[active_mask], 65)))
        std_thr_t = min(0.042, float(np.percentile(std_tgt[active_mask], 65)))
        std_thr_r = max(std_thr_r, 0.008)
        std_thr_t = max(std_thr_t, 0.012)
        raw_flat = active_mask & (std_ref <= std_thr_r) & (std_tgt <= std_thr_t)
        k_flat = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        flat_mask = (cv2.erode(raw_flat.astype(np.uint8), k_flat) > 0) & active_mask
        if int(flat_mask.sum()) < int(0.05 * active_mask.sum()):
            flat_mask = raw_flat

        edge_thr_r = max(0.06, float(np.percentile(grad_ref[active_mask], 82)))
        edge_thr_t = max(0.06, float(np.percentile(grad_tgt[active_mask], 80)))
        edge_core = active_mask & (grad_ref >= edge_thr_r) & (grad_tgt >= 0.5 * edge_thr_t)
        k_edge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        edge_mask = (cv2.dilate(edge_core.astype(np.uint8), k_edge) > 0) & active_mask
    else:
        flat_mask = active_mask.copy()
        edge_mask = active_mask.copy()

    folds = make_block_folds((h, w), block_size=block_size, n_folds=n_folds, seed=42)
    return PairMasks(
        valid_warp_mask=valid_warp_mask,
        bar_mask=bar_mask,
        border_mask=border_mask,
        caption_mask=caption_mask,
        active_mask=active_mask,
        flat_mask=flat_mask,
        edge_mask=edge_mask,
        block_folds=folds,
        bar_bounds=bar_bounds,
    )
