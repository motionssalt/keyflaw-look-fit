#!/usr/bin/env python3
"""Q2: Sub-pixel ECC alignment audit on edge maps for Pair A and Pair B."""
import os
import json
import cv2
import numpy as np

REPO = "/tmp/keyflaw-look-fit"
ALIGN_DIR = os.path.join(REPO, "outputs", "aligned")
os.makedirs(ALIGN_DIR, exist_ok=True)


def load_rgb(path: str) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def edge_map(rgb: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    if sigma > 0:
        gray = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma, sigmaY=sigma)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    return np.hypot(gx, gy)


def pearson_corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray = None) -> float:
    if mask is not None:
        x = a[mask].astype(np.float64)
        y = b[mask].astype(np.float64)
    else:
        x = a.ravel().astype(np.float64)
        y = b.ravel().astype(np.float64)
    x = x - x.mean()
    y = y - y.mean()
    denom = np.sqrt(np.dot(x, x) * np.dot(y, y))
    return float(np.dot(x, y) / denom) if denom > 0 else 0.0


def audit_pair_a():
    ed = load_rgb(os.path.join(REPO, "inputs/pairA_edited.png"))
    or_im = load_rgb(os.path.join(REPO, "inputs/pairA_original_matched.png"))
    h, w, _ = ed.shape

    bars = cv2.imread(os.path.join(REPO, "masks/pairA_bars.png"), cv2.IMREAD_GRAYSCALE) > 0
    cap = cv2.imread(os.path.join(REPO, "masks/pairA_caption.png"), cv2.IMREAD_GRAYSCALE) > 0
    inv = cv2.imread(os.path.join(REPO, "masks/pairA_invalid_border.png"), cv2.IMREAD_GRAYSCALE) > 0
    valid = (~bars) & (~cap) & (~inv)

    e_ed = edge_map(ed, sigma=1.0)
    e_or = edge_map(or_im, sigma=1.0)

    corr_full_raw = pearson_corr(e_or, e_ed, None)
    corr_valid_before = pearson_corr(e_or, e_ed, valid)

    # Normalize edge maps for ECC
    t_img = (e_ed / (e_ed.max() + 1e-6)).astype(np.float32)
    i_img = (e_or / (e_or.max() + 1e-6)).astype(np.float32)
    ecc_mask = (valid.astype(np.uint8) * 255)

    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 500, 1e-7)

    # 1. Pure translation ECC
    W_trans = np.eye(2, 3, dtype=np.float32)
    _, W_trans = cv2.findTransformECC(t_img, i_img, W_trans, cv2.MOTION_TRANSLATION, criteria, ecc_mask, 5)
    dx_t, dy_t = float(W_trans[0, 2]), float(W_trans[1, 2])
    shift_norm_t = float(np.hypot(dx_t, dy_t))

    # 2. Full affine ECC
    W_aff = np.eye(2, 3, dtype=np.float32)
    _, W_aff = cv2.findTransformECC(t_img, i_img, W_aff, cv2.MOTION_AFFINE, criteria, ecc_mask, 5)
    # Note: findTransformECC maps template (ed) -> input (or_im) when called as (template=ed, input=or_im) with WARP_INVERSE_MAP;
    # let's verify direction explicitly with warpAffine(..., WARP_INVERSE_MAP)!
    or_warped_aff = cv2.warpAffine(or_im, W_aff, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    e_or_after = edge_map(or_warped_aff, sigma=1.0)
    corr_valid_after_aff = pearson_corr(e_or_after, e_ed, valid)

    or_warped_trans = cv2.warpAffine(or_im, W_trans, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    e_or_after_t = edge_map(or_warped_trans, sigma=1.0)
    corr_valid_after_t = pearson_corr(e_or_after_t, e_ed, valid)

    # Compute max pixel displacement across valid pixels under W_aff (inverse map: x_or = W_aff @ [x_ed, y_ed, 1])
    yy, xx = np.where(valid)
    pts = np.stack([xx.astype(np.float64), yy.astype(np.float64), np.ones_like(xx, dtype=np.float64)], axis=1)
    mapped = pts @ W_aff.T
    disp = np.hypot(mapped[:, 0] - xx, mapped[:, 1] - yy)
    median_disp = float(np.median(disp))
    p95_disp = float(np.percentile(disp, 95))
    max_disp = float(disp.max())

    # Threshold in Q2: 0.5 px for Pair A
    use_rewarp = max_disp > 0.5
    if use_rewarp:
        cv2.imwrite(os.path.join(ALIGN_DIR, "pairA_orig_aligned.png"), cv2.cvtColor(or_warped_aff, cv2.COLOR_RGB2BGR))

    return {
        "resolution": [w, h],
        "translation_shift_px": {"dx": round(dx_t, 4), "dy": round(dy_t, 4), "norm": round(shift_norm_t, 4)},
        "affine_displacement_px": {
            "median": round(median_disp, 4),
            "p95": round(p95_disp, 4),
            "max": round(max_disp, 4),
        },
        "affine_matrix_ed_to_or": [[round(float(v), 6) for v in row] for row in W_aff],
        "edge_corr_full_unmasked_before": round(corr_full_raw, 5),
        "edge_corr_valid_before": round(corr_valid_before, 5),
        "edge_corr_valid_after_translation": round(corr_valid_after_t, 5),
        "edge_corr_valid_after_affine": round(corr_valid_after_aff, 5),
        "threshold_px": 0.5,
        "re_warped_used": bool(use_rewarp),
    }


def audit_pair_b():
    ed = load_rgb(os.path.join(REPO, "inputs/pairB_edited.png"))       # 720 x 1291
    or_im = load_rgb(os.path.join(REPO, "inputs/pairB_original_matched.png"))  # 409 x 720
    h, w, _ = ed.shape
    ho, wo, _ = or_im.shape

    bars = cv2.imread(os.path.join(REPO, "masks/pairB_bars.png"), cv2.IMREAD_GRAYSCALE) > 0
    inv = cv2.imread(os.path.join(REPO, "masks/pairB_invalid_border.png"), cv2.IMREAD_GRAYSCALE) > 0
    valid = (~bars) & (~inv)

    e_ed = edge_map(ed, sigma=1.0)

    # Baseline 0: naive resize of 720x409 -> 1291x720 (shows why raw unaligned inputs cannot be compared pixel-wise)
    or_naive = cv2.resize(or_im, (w, h), interpolation=cv2.INTER_CUBIC)
    e_or_naive = edge_map(or_naive, sigma=1.0)
    corr_naive = pearson_corr(e_or_naive, e_ed, valid)

    # Step 1: SIFT + RANSAC initial affine M_sift (maps orig 720x409 -> edit 1291x720)
    sift = cv2.SIFT_create(5000)
    kp1, des1 = sift.detectAndCompute(cv2.cvtColor(or_im, cv2.COLOR_RGB2GRAY), None)
    kp2, des2 = sift.detectAndCompute(cv2.cvtColor(ed, cv2.COLOR_RGB2GRAY), None)
    matches = cv2.BFMatcher().knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.7 * n.distance]
    M_sift, inliers = cv2.estimateAffine2D(
        np.float32([kp1[m.queryIdx].pt for m in good]),
        np.float32([kp2[m.trainIdx].pt for m in good]),
        method=cv2.RANSAC,
        ransacReprojThreshold=2.5,
    )
    or_sift = cv2.warpAffine(or_im, M_sift, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    e_or_sift = edge_map(or_sift, sigma=1.0)
    corr_sift = pearson_corr(e_or_sift, e_ed, valid)

    # Step 2: Sub-pixel ECC refinement on edge maps!
    # findTransformECC with WARP_INVERSE_MAP expects W mapping template (ed) -> input (or_im),
    # OR we can refine residual affine on (or_sift -> ed) directly on the 1291x720 grid and compose!
    # Composing on 1291x720 grid avoids scale conditioning issues in ECC Gauss-Newton!
    t_img = (e_ed / (e_ed.max() + 1e-6)).astype(np.float32)
    i_img = (e_or_sift / (e_or_sift.max() + 1e-6)).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 800, 1e-7)

    # Test ECC mask A: full valid region vs ECC mask B: valid region excluding AI-redrawn bush/cloak (x < 775)
    ecc_mask_full = (valid.astype(np.uint8) * 255)
    valid_faithful = valid.copy()
    valid_faithful[:, 775:] = False
    ecc_mask_faithful = (valid_faithful.astype(np.uint8) * 255)

    W_res_full = np.eye(2, 3, dtype=np.float32)
    _, W_res_full = cv2.findTransformECC(t_img, i_img, W_res_full, cv2.MOTION_AFFINE, criteria, ecc_mask_full, 5)
    W_res_faith = np.eye(2, 3, dtype=np.float32)
    _, W_res_faith = cv2.findTransformECC(t_img, i_img, W_res_faith, cv2.MOTION_AFFINE, criteria, ecc_mask_faithful, 5)

    # Compose M_orig_to_edit = inv(W_res_3x3) @ M_sift_3x3
    def compose_orig_to_edit(W_ed_to_sift):
        W3 = np.vstack([W_ed_to_sift.astype(np.float64), [0.0, 0.0, 1.0]])
        M3 = np.vstack([M_sift.astype(np.float64), [0.0, 0.0, 1.0]])
        # x_sift = W3 @ x_ed => x_ed = inv(W3) @ x_sift = inv(W3) @ M3 @ x_orig
        M_comp = np.linalg.inv(W3) @ M3
        return M_comp[:2, :]

    M_ecc_full = compose_orig_to_edit(W_res_full)
    M_ecc_faith = compose_orig_to_edit(W_res_faith)

    or_ecc_full = cv2.warpAffine(or_im, M_ecc_full, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    or_ecc_faith = cv2.warpAffine(or_im, M_ecc_faith, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)

    corr_ecc_full_all = pearson_corr(edge_map(or_ecc_full, 1.0), e_ed, valid)
    corr_ecc_faith_all = pearson_corr(edge_map(or_ecc_faith, 1.0), e_ed, valid)
    corr_ecc_full_left = pearson_corr(edge_map(or_ecc_full, 1.0), e_ed, valid_faithful)
    corr_ecc_faith_left = pearson_corr(edge_map(or_ecc_faith, 1.0), e_ed, valid_faithful)

    # Pick whichever gives higher overall valid edge correlation
    if corr_ecc_full_all >= corr_ecc_faith_all:
        M_best = M_ecc_full
        or_best = or_ecc_full
        chosen_ecc = "full_valid_mask"
        W_res_chosen = W_res_full
    else:
        M_best = M_ecc_faith
        or_best = or_ecc_faith
        chosen_ecc = "faithful_character_mask_x_lt_775"
        W_res_chosen = W_res_faith

    corr_best_all = pearson_corr(edge_map(or_best, 1.0), e_ed, valid)
    corr_best_faithful = pearson_corr(edge_map(or_best, 1.0), e_ed, valid_faithful)

    # Measure displacement between SIFT and ECC on 720p grid, and total displacement vs naive resize
    yy, xx = np.where(valid)
    pts = np.stack([xx.astype(np.float64), yy.astype(np.float64), np.ones_like(xx, dtype=np.float64)], axis=1)
    mapped_res = pts @ W_res_chosen.T
    disp_sift_to_ecc = np.hypot(mapped_res[:, 0] - xx, mapped_res[:, 1] - yy)

    # Save aligned copies (NEVER overwriting inputs/)
    cv2.imwrite(os.path.join(ALIGN_DIR, "pairB_orig_aligned_720p.png"), cv2.cvtColor(or_best, cv2.COLOR_RGB2BGR))

    M_edit_to_orig = cv2.invertAffineTransform(M_best)
    ed_409 = cv2.warpAffine(ed, M_edit_to_orig, (wo, ho), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(os.path.join(ALIGN_DIR, "pairB_edit_aligned_409p.png"), cv2.cvtColor(ed_409, cv2.COLOR_RGB2BGR))

    # Also measure edge correlation on 409p native original grid!
    bars_409 = cv2.imread(os.path.join(REPO, "masks/pairB_409p_bars.png"), cv2.IMREAD_GRAYSCALE) > 0
    inv_409 = cv2.imread(os.path.join(REPO, "masks/pairB_409p_invalid_border.png"), cv2.IMREAD_GRAYSCALE) > 0
    valid_409 = (~bars_409) & (~inv_409)
    corr_409_after = pearson_corr(edge_map(or_im, 1.0), edge_map(ed_409, 1.0), valid_409)
    ed_409_naive = cv2.resize(ed, (wo, ho), interpolation=cv2.INTER_AREA)
    corr_409_naive = pearson_corr(edge_map(or_im, 1.0), edge_map(ed_409_naive, 1.0), valid_409)

    # Scale & anisotropy decomposition of M_best
    sx = float(np.hypot(M_best[0, 0], M_best[1, 0]))
    sy = float(np.hypot(M_best[0, 1], M_best[1, 1]))
    anisotropy_pct = abs(sx - sy) / ((sx + sy) * 0.5) * 100.0

    return {
        "resolution_edit": [w, h],
        "resolution_orig": [wo, ho],
        "scale_orig_to_edit": {"sx": round(sx, 6), "sy": round(sy, 6), "anisotropy_pct": round(anisotropy_pct, 3)},
        "scale_edit_to_orig": {"sx": round(1.0 / sx, 6), "sy": round(1.0 / sy, 6)},
        "affine_orig_to_edit": [[round(float(v), 6) for v in row] for row in M_best],
        "affine_edit_to_orig": [[round(float(v), 6) for v in row] for row in M_edit_to_orig],
        "ecc_refinement_over_sift_px": {
            "median": round(float(np.median(disp_sift_to_ecc)), 4),
            "p95": round(float(np.percentile(disp_sift_to_ecc, 95)), 4),
            "max": round(float(disp_sift_to_ecc.max()), 4),
            "chosen_mask": chosen_ecc,
        },
        "edge_corr_720p_naive_before": round(corr_naive, 5),
        "edge_corr_720p_sift_interim": round(corr_sift, 5),
        "edge_corr_720p_ecc_after": round(corr_best_all, 5),
        "edge_corr_720p_ecc_faithful_x_lt_775": round(corr_best_faithful, 5),
        "edge_corr_409p_naive_before": round(corr_409_naive, 5),
        "edge_corr_409p_ecc_after": round(corr_409_after, 5),
        "threshold_px": 1.0,
        "re_warped_used": True,
        "aligned_files": [
            "outputs/aligned/pairB_orig_aligned_720p.png",
            "outputs/aligned/pairB_edit_aligned_409p.png",
        ],
    }


if __name__ == "__main__":
    res = {"pairA": audit_pair_a(), "pairB": audit_pair_b()}
    with open(os.path.join(ALIGN_DIR, "alignment_audit.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))
