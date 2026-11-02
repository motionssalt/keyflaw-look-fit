#!/usr/bin/env python3
"""Q2: Sub-pixel ECC alignment audit on edge maps for Pair A and Pair B."""

import os
import json
import cv2
import numpy as np

OWNER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REPO = os.path.abspath(os.path.join(OWNER_DIR, '..', '..'))
ALIGN_DIR = os.path.join(OWNER_DIR, 'analysis', 'outputs', 'aligned')
INPUT_DIR = os.path.join(OWNER_DIR, 'inputs')
MASK_DIR = os.path.join(OWNER_DIR, 'masks')
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

def audit_pair(name, ed_name, og_name, cap_name):
    ed = load_rgb(os.path.join(INPUT_DIR, ed_name))
    og = load_rgb(os.path.join(INPUT_DIR, og_name))
    h, w, _ = ed.shape
    ho, wo, _ = og.shape

    inv = cv2.imread(os.path.join(MASK_DIR, f'{name}_invalid_border.png'), cv2.IMREAD_GRAYSCALE) > 0
    cap = cv2.imread(os.path.join(MASK_DIR, cap_name), cv2.IMREAD_GRAYSCALE) > 0
    valid = (~inv) & (~cap)

    # 1. SIFT affine initial alignment
    sift = cv2.SIFT_create(5000)
    kp1, des1 = sift.detectAndCompute(cv2.cvtColor(og, cv2.COLOR_RGB2GRAY), None)
    kp2, des2 = sift.detectAndCompute(cv2.cvtColor(ed, cv2.COLOR_RGB2GRAY), None)
    matches = cv2.BFMatcher().knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good])
    M_init, inliers = cv2.estimateAffine2D(pts1, pts2, method=cv2.RANSAC, ransacReprojThreshold=3.0)

    og_warped_init = cv2.warpAffine(og, M_init, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    e_ed = edge_map(ed, 1.0)
    e_or_init = edge_map(og_warped_init, 1.0)
    corr_init = pearson_corr(e_or_init, e_ed, valid)

    # 2. Sub-pixel ECC refinement
    t_img = (e_ed / (e_ed.max() + 1e-6)).astype(np.float32)
    i_img = (e_or_init / (e_or_init.max() + 1e-6)).astype(np.float32)
    ecc_mask = (valid.astype(np.uint8) * 255)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6)

    # Translation ECC
    W_trans = np.eye(2, 3, dtype=np.float32)
    _, W_trans = cv2.findTransformECC(t_img, i_img, W_trans, cv2.MOTION_TRANSLATION, criteria, ecc_mask, 5)
    dx_t, dy_t = float(W_trans[0, 2]), float(W_trans[1, 2])
    shift_norm_t = float(np.hypot(dx_t, dy_t))

    # Affine ECC
    W_aff = np.eye(2, 3, dtype=np.float32)
    _, W_aff = cv2.findTransformECC(t_img, i_img, W_aff, cv2.MOTION_AFFINE, criteria, ecc_mask, 5)
    og_warped_aff = cv2.warpAffine(og_warped_init, W_aff, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    e_or_aff = edge_map(og_warped_aff, 1.0)
    corr_after_aff = pearson_corr(e_or_aff, e_ed, valid)

    # Compute pixel displacement under ECC affine warp
    yy, xx = np.where(valid)
    pts = np.stack([xx.astype(np.float64), yy.astype(np.float64), np.ones_like(xx, dtype=np.float64)], axis=1)
    mapped = pts @ W_aff.T
    disp = np.hypot(mapped[:, 0] - xx, mapped[:, 1] - yy)

    # Save aligned image internally
    cv2.imwrite(os.path.join(ALIGN_DIR, f'{name}_orig_aligned_720p.png'), cv2.cvtColor(og_warped_aff, cv2.COLOR_RGB2BGR))

    return {
        'resolution_edit': [w, h],
        'resolution_orig': [wo, ho],
        'sift_inliers': int(inliers.sum()),
        'sift_affine_matrix': [[round(float(v), 6) for v in row] for row in M_init],
        'ecc_affine_matrix': [[round(float(v), 6) for v in row] for row in W_aff],
        'ecc_displacement_px': {
            'median': round(float(np.median(disp)), 4),
            'p95': round(float(np.percentile(disp, 95)), 4),
            'max': round(float(disp.max()), 4),
        },
        'edge_corr_valid_before': round(corr_init, 5),
        'edge_corr_valid_after_ecc': round(corr_after_aff, 5),
        're_warped_used': True,
    }

if __name__ == '__main__':
    res_a = audit_pair('pairA', 'pairA_edited.png', 'pairA_original_matched.png', 'pairA_caption.png')
    res_b = audit_pair('pairB', 'pairB_edited.png', 'pairB_original_matched.png', 'pairB_caption.png')
    summary = {'pairA': res_a, 'pairB': res_b}
    with open(os.path.join(ALIGN_DIR, 'alignment_audit.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
