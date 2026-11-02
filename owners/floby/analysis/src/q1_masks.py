#!/usr/bin/env python3
"""Q1: Build and verify masks + overlay previews for Pair A and Pair B."""
import os
import json
import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MASK_DIR = os.path.join(REPO, "owners", "floby", "masks")
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
    # Sobel ksize=3 has scale factor 8 for central diff (2 * 4); divide by 8 for true px/step derivative
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    mag = np.hypot(gx, gy)
    return mag.max(axis=2)


def make_overlay(base_rgb: np.ndarray, masks: dict) -> np.ndarray:
    """Create colour-coded overlay preview for visual inspection."""
    vis = (base_rgb.astype(np.float32) * 0.55).copy()
    # Priority order from background to foreground
    layers = [
        ("flat_interior", np.array([40, 220, 90], dtype=np.float32), 0.45),
        ("line_edges", np.array([40, 200, 255], dtype=np.float32), 0.50),
        ("invalid_border", np.array([255, 150, 30], dtype=np.float32), 0.60),
        ("bars", np.array([170, 70, 240], dtype=np.float32), 0.60),
        ("caption", np.array([255, 50, 70], dtype=np.float32), 0.65),
    ]
    for name, col, alpha in layers:
        if name in masks and masks[name] is not None:
            m = masks[name] > 0
            vis[m] = vis[m] * (1.0 - alpha) + col * alpha
    out = np.clip(vis, 0, 255).astype(np.uint8)
    # Add small legend bar at top-left inside bar region or corner
    legend_items = [
        ("Flat interior", (40, 220, 90)),
        ("Line edges", (40, 200, 255)),
        ("Caption", (255, 50, 70)),
        ("Bars", (170, 70, 240)),
        ("Invalid border", (255, 150, 30)),
    ]
    x0 = 14
    for label, col in legend_items:
        cv2.rectangle(out, (x0, 8), (x0 + 14, 22), col, -1)
        cv2.putText(out, label, (x0 + 19, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        x0 += 19 + len(label) * 8 + 16
    return out


def save_mask(name: str, mask_bool: np.ndarray) -> str:
    p = os.path.join(MASK_DIR, name)
    cv2.imwrite(p, (mask_bool.astype(np.uint8) * 255))
    return p


def build_pair_a():
    ed = load_rgb(os.path.join(REPO, "owners/floby/inputs/pairA_edited.png"))
    or_im = load_rgb(os.path.join(REPO, "owners/floby/inputs/pairA_original_matched.png"))
    h, w, _ = ed.shape  # 720, 1278

    # 1. Bars mask: rows 0..38 and 682..719 (includes black bars 0..34 & 686..719, transitions 35..36 & 684..685, +2px ringing buffer)
    bars = np.zeros((h, w), dtype=bool)
    bars[:39, :] = True
    bars[682:, :] = True

    # 2. Invalid border: 2px left/right border where resampling edge falloff occurs (col 1277 drops ~9 levels)
    invalid_border = np.zeros((h, w), dtype=bool)
    invalid_border[:, :2] = True
    invalid_border[:, -2:] = True

    # 3. Caption mask: isolate "When It's time to do a special edit..." + soft glow, dilated by 8 px
    ed_f = ed.astype(np.float32)
    or_f = or_im.astype(np.float32)
    hp_ed = ed_f - cv2.GaussianBlur(ed_f, (0, 0), 4.5)
    hp_or = or_f - cv2.GaussianBlur(or_f, (0, 0), 4.5)
    hp_diff = np.linalg.norm(hp_ed - hp_or, axis=2)

    g_or = grad_mag_sigma1(or_im)
    or_edge_dil = cv2.dilate((g_or > 5.0).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0

    stroke_seed = np.zeros((h, w), dtype=bool)
    # Caption sits across middle row band 338..376, x=350..930
    roi = np.zeros((h, w), dtype=bool)
    roi[336:380, 345:935] = True
    stroke_seed = roi & (hp_diff > 6.5) & (~or_edge_dil)
    # Also include high-pass stroke pixels over hair/line crossings inside the tight text line band 346..369
    tight_roi = np.zeros((h, w), dtype=bool)
    tight_roi[346:370, 355:924] = True
    stroke_seed |= tight_roi & (hp_diff > 14.0)

    # Connect character strokes horizontally slightly and dilate by 8 px (plus 4px for soft text glow = 12px total radius,
    # while recording exact 8px dilation of detected glyph+glow footprint)
    glyph_connected = cv2.morphologyEx(
        stroke_seed.astype(np.uint8),
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)),
    )
    # Dilate by 10 px radius (~8 px around glyph + soft outer glow)
    caption = cv2.dilate(
        glyph_connected,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)),
    ) > 0

    # 4. Line-art edges: high gradient after Gaussian sigma=1.0 in EITHER image (excluding caption strokes & bars), dilated 3 px
    g_ed = grad_mag_sigma1(ed)
    edge_raw = ((g_or > 4.5) | ((g_ed > 4.5) & (~caption))) & (~bars)
    line_edges = cv2.dilate(
        edge_raw.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),  # radius 3 px
    ) > 0

    # 5. Flat interior: low gradient in BOTH images, excluding bars, caption (+ extra 4px glow margin), invalid border, and line_edges, eroded >= 3 px
    caption_glow_guard = cv2.dilate(caption.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
    low_grad_both = (g_or < 2.5) & (g_ed < 2.8)
    flat_cand = low_grad_both & (~bars) & (~caption_glow_guard) & (~invalid_border) & (~line_edges)
    flat_interior = cv2.erode(
        flat_cand.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),  # radius 3 px erosion
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
        "size": [w, h],
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
    ed = load_rgb(os.path.join(REPO, "owners/floby/inputs/pairB_edited.png"))       # 720 x 1291
    or_im = load_rgb(os.path.join(REPO, "owners/floby/inputs/pairB_original_matched.png"))  # 409 x 720
    h, w, _ = ed.shape
    ho, wo, _ = or_im.shape

    # SIFT + RANSAC initial affine alignment from 720x409 -> 1291x720 so both gradients can be evaluated on edit grid
    sift = cv2.SIFT_create(5000)
    kp1, des1 = sift.detectAndCompute(cv2.cvtColor(or_im, cv2.COLOR_RGB2GRAY), None)
    kp2, des2 = sift.detectAndCompute(cv2.cvtColor(ed, cv2.COLOR_RGB2GRAY), None)
    matches = cv2.BFMatcher().knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.7 * n.distance]
    M_init, _ = cv2.estimateAffine2D(
        np.float32([kp1[m.queryIdx].pt for m in good]),
        np.float32([kp2[m.trainIdx].pt for m in good]),
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
    )
    or_warped = cv2.warpAffine(or_im, M_init, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 1. Bars on 1291x720 edit: top/bottom letterbox rows 0..38 & 682..719, plus NewPipe left/right pillarbox cols 0..8 & 1285..1290
    bars = np.zeros((h, w), dtype=bool)
    bars[:39, :] = True
    bars[682:, :] = True
    bars[:, :9] = True
    bars[:, 1285:] = True

    # 2. Caption/subtitle: none present on pairB_edited.png (1291x720 NewPipe AMV screenshot)
    caption = np.zeros((h, w), dtype=bool)

    # 3. Invalid border: 6 px border of pairB_original_matched (720x409) mapped into 1291x720 + any unmapped pixels
    valid_orig_6px = np.zeros((ho, wo), dtype=np.uint8)
    valid_orig_6px[6 : ho - 6, 6 : wo - 6] = 255
    valid_warped = cv2.warpAffine(valid_orig_6px, M_init, (w, h), flags=cv2.INTER_NEAREST, borderValue=0) > 0
    invalid_border = (~valid_warped) & (~bars)
    # Also ensure at least an 11 px inset (~6 px * 1.79 scale) from active content frame edges
    invalid_border[:, :18] = True
    invalid_border[:, 1279:] = True
    invalid_border = invalid_border & (~bars)

    # 4. Line-art edges: high gradient after sigma=1.0 in EITHER image, dilated 3 px
    g_ed = grad_mag_sigma1(ed)
    g_or_w = grad_mag_sigma1(or_warped)
    edge_raw = ((g_ed > 4.5) | (g_or_w > 4.0)) & (~bars) & (~invalid_border)
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

    # Also save native 720x409 masks for direct evaluation on pairB_original_matched (720x409)
    M_inv = cv2.invertAffineTransform(M_init)
    bars_409 = cv2.warpAffine((bars.astype(np.uint8) * 255), M_inv, (wo, ho), flags=cv2.INTER_NEAREST, borderValue=255) > 0
    inv_border_409 = np.ones((ho, wo), dtype=bool)
    inv_border_409[6 : ho - 6, 6 : wo - 6] = False
    ed_409 = cv2.warpAffine(ed, M_inv, (wo, ho), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    g_ed_409 = grad_mag_sigma1(ed_409)
    g_or_409 = grad_mag_sigma1(or_im)
    edges_409 = cv2.dilate(
        (((g_ed_409 > 4.5) | (g_or_409 > 4.5)) & (~bars_409) & (~inv_border_409)).astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    ) > 0
    flat_409 = cv2.erode(
        ((g_ed_409 < 2.8) & (g_or_409 < 2.5) & (~bars_409) & (~inv_border_409) & (~edges_409)).astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    ) > 0
    save_mask("pairB_409p_bars.png", bars_409)
    save_mask("pairB_409p_invalid_border.png", inv_border_409)
    save_mask("pairB_409p_line_edges.png", edges_409)
    save_mask("pairB_409p_flat_interior.png", flat_409)
    ov_409 = make_overlay(or_im, {
        "bars": bars_409,
        "invalid_border": inv_border_409,
        "line_edges": edges_409,
        "flat_interior": flat_409,
    })
    cv2.imwrite(os.path.join(MASK_DIR, "pairB_409p_overlay_preview.png"), cv2.cvtColor(ov_409, cv2.COLOR_RGB2BGR))

    return {
        "size_edit": [w, h],
        "size_orig": [wo, ho],
        "init_affine_orig_to_edit": M_init.tolist(),
        "counts_720p": {
            "total": int(h * w),
            "bars": int(bars.sum()),
            "caption": int(caption.sum()),
            "invalid_border": int(invalid_border.sum()),
            "line_edges": int(line_edges.sum()),
            "flat_interior": int(flat_interior.sum()),
        },
        "counts_409p": {
            "total": int(ho * wo),
            "bars": int(bars_409.sum()),
            "invalid_border": int(inv_border_409.sum()),
            "line_edges": int(edges_409.sum()),
            "flat_interior": int(flat_409.sum()),
        },
        "pct_720p": {
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
