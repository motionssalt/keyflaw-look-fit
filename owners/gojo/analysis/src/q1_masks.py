#!/usr/bin/env python3
"""Q1: Build and verify masks + overlay previews for Pair A and Pair B for Xenoz CC."""

import os
import json
import cv2
import numpy as np

OWNER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO = os.path.abspath(os.path.join(OWNER_DIR, "..", ".."))
MASK_DIR = os.path.join(OWNER_DIR, "masks")
INPUT_DIR = os.path.join(OWNER_DIR, "inputs")
os.makedirs(MASK_DIR, exist_ok=True)

def load_rgb(path: str) -> np.ndarray:
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(path)
    if im.ndim == 3 and im.shape[2] == 4:
        assert np.all(im[:, :, 3] == 255), f"Alpha not opaque in {path}"
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGB)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    return im

def grad_mag_sigma1(rgb: np.ndarray) -> np.ndarray:
    """Max per-channel Sobel gradient magnitude (per-pixel units) after Gaussian sigma=1.0."""
    f = rgb.astype(np.float32)
    blur = cv2.GaussianBlur(f, (0, 0), sigmaX=1.0, sigmaY=1.0)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    mag = np.hypot(gx, gy)
    return mag.max(axis=2)

def make_overlay(base_rgb: np.ndarray, masks: dict) -> np.ndarray:
    """Create colour-coded overlay preview for visual inspection."""
    vis = (base_rgb.astype(np.float32) * 0.55).copy()
    # Color coding:
    # Flat interior = Green tint
    if "flat_interior" in masks:
        vis[masks["flat_interior"]] += np.array([0, 75, 0], dtype=np.float32)
    # Line edges = Orange
    if "line_edges" in masks:
        vis[masks["line_edges"]] = np.array([255, 140, 0], dtype=np.float32)
    # Invalid border = Cyan
    if "invalid_border" in masks:
        vis[masks["invalid_border"]] = np.array([0, 220, 255], dtype=np.float32)
    # Caption = Red
    if "caption" in masks and masks["caption"].any():
        vis[masks["caption"]] = np.array([255, 40, 40], dtype=np.float32)
    # Bars = Dark Blue / Magenta
    if "bars" in masks and masks["bars"].any():
        vis[masks["bars"]] = np.array([180, 0, 180], dtype=np.float32)
    return np.clip(vis, 0, 255).astype(np.uint8)

def save_mask(name: str, mask: np.ndarray):
    cv2.imwrite(os.path.join(MASK_DIR, name), (mask.astype(np.uint8) * 255))

def build_pair_a():
    ed = load_rgb(os.path.join(INPUT_DIR, "pairA_edited.png"))           # 720 x 1280
    or_im = load_rgb(os.path.join(INPUT_DIR, "pairA_original_matched.png")) # 768 x 1376
    h, w, _ = ed.shape
    ho, wo, _ = or_im.shape

    # SIFT + RANSAC initial affine alignment
    sift = cv2.SIFT_create(5000)
    kp1, des1 = sift.detectAndCompute(cv2.cvtColor(or_im, cv2.COLOR_RGB2GRAY), None)
    kp2, des2 = sift.detectAndCompute(cv2.cvtColor(ed, cv2.COLOR_RGB2GRAY), None)
    matches = cv2.BFMatcher().knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    M_init, _ = cv2.estimateAffine2D(
        np.float32([kp1[m.queryIdx].pt for m in good]),
        np.float32([kp2[m.trainIdx].pt for m in good]),
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
    )
    or_warped = cv2.warpAffine(or_im, M_init, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 1. Bars: None on pairA_edited (inspected row luminance > 100 throughout)
    bars = np.zeros((h, w), dtype=bool)

    # 2. Caption: None on pairA
    caption = np.zeros((h, w), dtype=bool)

    # 3. Invalid border: 6 px border on original mapped to edit + 6 px frame border
    valid_orig_6px = np.zeros((ho, wo), dtype=np.uint8)
    valid_orig_6px[6 : ho - 6, 6 : wo - 6] = 255
    valid_warped = cv2.warpAffine(valid_orig_6px, M_init, (w, h), flags=cv2.INTER_NEAREST, borderValue=0) > 0
    invalid_border = (~valid_warped)
    invalid_border[:6, :] = True
    invalid_border[-6:, :] = True
    invalid_border[:, :6] = True
    invalid_border[:, -6:] = True

    # 4. Line-art edges: high gradient after Gaussian sigma=1.0 in either image, dilated 3 px
    g_ed = grad_mag_sigma1(ed)
    g_or_w = grad_mag_sigma1(or_warped)
    edge_raw = ((g_ed > 4.5) | (g_or_w > 4.0)) & (~invalid_border)
    line_edges = cv2.dilate(
        edge_raw.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    ) > 0

    # 5. Flat interior: low gradient in BOTH images, eroded >= 3 px
    low_grad_both = (g_ed < 2.8) & (g_or_w < 2.5)
    flat_cand = low_grad_both & (~bars) & (~caption) & (~invalid_border) & (~line_edges)
    flat_interior = cv2.erode(
        flat_cand.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    ) > 0

    save_mask("pairA_bars.png", bars)
    save_mask("pairA_caption.png", caption)
    save_mask("pairA_invalid_border.png", invalid_border)
    save_mask("pairA_line_edges.png", line_edges)
    save_mask("pairA_flat_interior.png", flat_interior)

    ov = make_overlay(ed, {
        "bars": bars,
        "caption": caption,
        "invalid_border": invalid_border,
        "line_edges": line_edges,
        "flat_interior": flat_interior,
    })
    cv2.imwrite(os.path.join(MASK_DIR, "pairA_overlay_preview.png"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))

    return {
        "size_edit": [w, h],
        "size_orig": [wo, ho],
        "affine_matrix": M_init.tolist(),
        "counts": {
            "total": int(h * w),
            "bars": int(bars.sum()),
            "caption": int(caption.sum()),
            "invalid_border": int(invalid_border.sum()),
            "line_edges": int(line_edges.sum()),
            "flat_interior": int(flat_interior.sum()),
        },
        "pct": {
            k: round(100.0 * float(v.sum()) / (h * w), 2)
            for k, v in [
                ("bars", bars),
                ("caption", caption),
                ("invalid_border", invalid_border),
                ("line_edges", line_edges),
                ("flat_interior", flat_interior),
            ]
        },
    }

def build_pair_b():
    ed = load_rgb(os.path.join(INPUT_DIR, "pairB_edited.png"))           # 720 x 1280
    or_im = load_rgb(os.path.join(INPUT_DIR, "pairB_original_matched.png")) # 768 x 1359
    h, w, _ = ed.shape
    ho, wo, _ = or_im.shape

    # SIFT + RANSAC initial affine alignment
    sift = cv2.SIFT_create(5000)
    kp1, des1 = sift.detectAndCompute(cv2.cvtColor(or_im, cv2.COLOR_RGB2GRAY), None)
    kp2, des2 = sift.detectAndCompute(cv2.cvtColor(ed, cv2.COLOR_RGB2GRAY), None)
    matches = cv2.BFMatcher().knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    M_init, _ = cv2.estimateAffine2D(
        np.float32([kp1[m.queryIdx].pt for m in good]),
        np.float32([kp2[m.trainIdx].pt for m in good]),
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
    )
    or_warped = cv2.warpAffine(or_im, M_init, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 1. Bars: None
    bars = np.zeros((h, w), dtype=bool)

    # 2. Caption/subtitle: Detect 'IS THIS...' text in lower region (y in [540, 660], x in [450, 850])
    # The subtitle text has bright letters and dark drop shadow on top of clean skin
    diff = np.abs(ed.astype(np.float32) - or_warped.astype(np.float32)).max(axis=2)
    g_ed = grad_mag_sigma1(ed)
    g_or_w = grad_mag_sigma1(or_warped)

    caption_raw = np.zeros((h, w), dtype=bool)
    # Mask subtitle strokes in the lower center region
    sub_roi = np.zeros((h, w), dtype=bool)
    sub_roi[540:655, 450:850] = True
    caption_raw[sub_roi & ((diff > 25.0) | ((g_ed > 4.0) & (g_or_w < 2.0)))] = True
    # Dilate caption by 8 px per brief
    caption = cv2.dilate(
        caption_raw.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)), # radius 8 px
    ) > 0

    # 3. Invalid border: 6 px on original mapped to edit + 6 px frame border
    valid_orig_6px = np.zeros((ho, wo), dtype=np.uint8)
    valid_orig_6px[6 : ho - 6, 6 : wo - 6] = 255
    valid_warped = cv2.warpAffine(valid_orig_6px, M_init, (w, h), flags=cv2.INTER_NEAREST, borderValue=0) > 0
    invalid_border = (~valid_warped)
    invalid_border[:6, :] = True
    invalid_border[-6:, :] = True
    invalid_border[:, :6] = True
    invalid_border[:, -6:] = True

    # 4. Line-art edges: high gradient after Gaussian sigma=1.0 in either image (excluding caption), dilated 3 px
    edge_raw = ((g_ed > 4.5) | (g_or_w > 4.0)) & (~invalid_border) & (~caption)
    line_edges = cv2.dilate(
        edge_raw.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)), # radius 3 px
    ) > 0

    # 5. Flat interior: low gradient in BOTH images, eroded >= 3 px
    caption_margin = cv2.dilate(caption.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
    low_grad_both = (g_ed < 2.8) & (g_or_w < 2.5)
    flat_cand = low_grad_both & (~bars) & (~caption_margin) & (~invalid_border) & (~line_edges)
    flat_interior = cv2.erode(
        flat_cand.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    ) > 0

    save_mask("pairB_bars.png", bars)
    save_mask("pairB_caption.png", caption)
    save_mask("pairB_invalid_border.png", invalid_border)
    save_mask("pairB_line_edges.png", line_edges)
    save_mask("pairB_flat_interior.png", flat_interior)

    ov = make_overlay(ed, {
        "bars": bars,
        "caption": caption,
        "invalid_border": invalid_border,
        "line_edges": line_edges,
        "flat_interior": flat_interior,
    })
    cv2.imwrite(os.path.join(MASK_DIR, "pairB_overlay_preview.png"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))

    return {
        "size_edit": [w, h],
        "size_orig": [wo, ho],
        "affine_matrix": M_init.tolist(),
        "counts": {
            "total": int(h * w),
            "bars": int(bars.sum()),
            "caption": int(caption.sum()),
            "invalid_border": int(invalid_border.sum()),
            "line_edges": int(line_edges.sum()),
            "flat_interior": int(flat_interior.sum()),
        },
        "pct": {
            k: round(100.0 * float(v.sum()) / (h * w), 2)
            for k, v in [
                ("bars", bars),
                ("caption", caption),
                ("invalid_border", invalid_border),
                ("line_edges", line_edges),
                ("flat_interior", flat_interior),
            ]
        },
    }

if __name__ == "__main__":
    res_a = build_pair_a()
    res_b = build_pair_b()
    summary = {"pairA": res_a, "pairB": res_b}
    with open(os.path.join(MASK_DIR, "mask_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
