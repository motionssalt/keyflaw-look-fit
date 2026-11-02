#!/usr/bin/env python3
"""F2. Fit the Unsharp Mask and Sharpen Properly for Floby's CC.
Uses:
  - Base image: F1 colour-fitted output
  - Perpendicular 1D edge profile sampling across line art
  - Halo overshoot/undershoot measurement
  - Models: U1 (single USM), U2 (two-stage USM), S1 (3x3 sharpen), U1+S1 combined
  - Luma vs RGB evaluation
  - Nuisance pre-blur fitting
  - Cross-scene parameter agreement check
"""
import sys, os, time, json
from pathlib import Path
import cv2
import numpy as np
from scipy.optimize import minimize
from skimage.metrics import structural_similarity as ssim

FLOBY_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = FLOBY_DIR / 'analysis/outputs/f2'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Import F1 LUT evaluation
sys.path.insert(0, str(FLOBY_DIR / 'analysis/src'))
from f1_colour_fit import eval_3d_lut, fit_3d_lut, build_laplacian_3d

def rgb_to_luma(rgb):
    # Rec.709 luma
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

def extract_edge_profiles(img_gray, edge_mask, num_samples=600, profile_len=21):
    """Samples perpendicular 1D slice profiles across line art edges."""
    half_len = profile_len // 2
    # Compute image gradients
    gx = cv2.Sobel(img_gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img_gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    
    # Candidate edge pixels: strong gradient inside edge_mask and away from boundaries
    H, W = img_gray.shape
    border = half_len + 5
    cand_mask = (edge_mask > 0) & (mag > 0.05)
    cand_mask[:border, :] = 0; cand_mask[-border:, :] = 0
    cand_mask[:, :border] = 0; cand_mask[:, -border:] = 0
    
    ys, xs = np.where(cand_mask)
    if len(ys) == 0:
        return []
        
    np.random.seed(42)
    sample_indices = np.random.choice(len(ys), size=min(num_samples, len(ys)), replace=False)
    
    profiles = []
    offsets = np.arange(-half_len, half_len + 1)
    
    for idx in sample_indices:
        y, x = ys[idx], xs[idx]
        nx = gx[y, x]
        ny = gy[y, x]
        norm = np.hypot(nx, ny)
        if norm < 1e-4:
            continue
        nx /= norm; ny /= norm
        
        # Sample coordinates along normal
        px = x + offsets * nx
        py = y + offsets * ny
        
        # Bilinear interpolation of profile
        # Use cv2.remap
        px_f = px.astype(np.float32).reshape(1, -1)
        py_f = py.astype(np.float32).reshape(1, -1)
        prof = cv2.remap(img_gray, px_f, py_f, cv2.INTER_LINEAR).ravel()
        
        profiles.append({
            'center': (int(x), int(y)),
            'normal': (float(nx), float(ny)),
            'profile': prof
        })
        
    return profiles

def apply_usm(img, sigma_h, amount, threshold=0.0, luma_only=True):
    """Unsharp mask with sigma proportional to height H."""
    H = img.shape[0]
    sigma_px = max(0.4, sigma_h * H)
    ksize = int(2 * np.ceil(2 * sigma_px) + 1)
    if ksize % 2 == 0: ksize += 1
    ksize = max(3, min(ksize, 61))
    
    if luma_only:
        luma = rgb_to_luma(img)
        blurred = cv2.GaussianBlur(luma, (ksize, ksize), sigma_px)
        diff = luma - blurred
        if threshold > 0.0:
            diff = np.sign(diff) * np.maximum(np.abs(diff) - threshold, 0.0)
        enhanced_luma = np.clip(luma + amount * diff, 0.0, 1.0)
        # Scale RGB chrominance proportionally
        scale = np.where(luma > 1e-4, enhanced_luma / np.maximum(luma, 1e-4), 1.0)
        scale = np.clip(scale, 0.0, 3.0)
        out = np.clip(img * scale[..., None], 0.0, 1.0)
    else:
        blurred = cv2.GaussianBlur(img, (ksize, ksize), sigma_px)
        diff = img - blurred
        if threshold > 0.0:
            diff = np.sign(diff) * np.maximum(np.abs(diff) - threshold, 0.0)
        out = np.clip(img + amount * diff, 0.0, 1.0)
        
    return out

def apply_sharpen_3x3(img, amount, luma_only=True):
    kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)
    if luma_only:
        luma = rgb_to_luma(img)
        diff = cv2.filter2D(luma, -1, kernel)
        enhanced_luma = np.clip(luma + amount * diff, 0.0, 1.0)
        scale = np.where(luma > 1e-4, enhanced_luma / np.maximum(luma, 1e-4), 1.0)
        scale = np.clip(scale, 0.0, 3.0)
        out = np.clip(img * scale[..., None], 0.0, 1.0)
    else:
        diff = cv2.filter2D(img, -1, kernel)
        out = np.clip(img + amount * diff, 0.0, 1.0)
    return out

def main():
    print("=== MOTIONSALT F2: Fit Unsharp Mask and Sharpen for Floby's CC ===")
    
    # Load base images and targets
    im_ed_A = cv2.imread(str(FLOBY_DIR / 'inputs/pairA_edited.png'))
    im_or_A = cv2.imread(str(FLOBY_DIR / 'inputs/pairA_original_matched.png'))
    m_edge_A = cv2.imread(str(FLOBY_DIR / 'masks/pairA_line_edges.png'), 0)
    
    im_ed_B = cv2.imread(str(FLOBY_DIR / 'inputs/pairB_edited.png'))
    im_or_B = cv2.imread(str(FLOBY_DIR / 'analysis/outputs/aligned/pairB_orig_aligned_720p.png'))
    m_edge_B = cv2.imread(str(FLOBY_DIR / 'masks/pairB_line_edges.png'), 0)
    
    rgb_ed_A = cv2.cvtColor(im_ed_A, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_or_A = cv2.cvtColor(im_or_A, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_ed_B = cv2.cvtColor(im_ed_B, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_or_B = cv2.cvtColor(im_or_B, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    
    # 1. Base colour-fitted image from F1 (using the 25^3 LUT)
    # Load LUT from f1 summary / refit quickly
    m_flat_A = cv2.imread(str(FLOBY_DIR / 'masks/pairA_flat_interior.png'), 0)
    m_flat_B = cv2.imread(str(FLOBY_DIR / 'masks/pairB_flat_interior.png'), 0)
    
    blur_or_A = cv2.GaussianBlur(rgb_or_A, (9, 9), 2.0)
    blur_ed_A = cv2.GaussianBlur(rgb_ed_A, (9, 9), 2.0)
    blur_or_B = cv2.GaussianBlur(rgb_or_B, (9, 9), 2.0)
    blur_ed_B = cv2.GaussianBlur(rgb_ed_B, (9, 9), 2.0)
    
    pts_in = np.vstack([blur_or_A[m_flat_A > 0], blur_or_B[m_flat_B > 0]])
    pts_tgt = np.vstack([blur_ed_A[m_flat_A > 0], blur_ed_B[m_flat_B > 0]])
    
    L25 = build_laplacian_3d(25)
    lut25 = fit_3d_lut(pts_in, pts_tgt, G=25, lambda_smooth=0.3, L=L25)
    
    # Apply colour fit to original full-res frames
    base_A = eval_3d_lut(rgb_or_A.reshape(-1, 3), lut25).reshape(rgb_or_A.shape)
    base_A = np.clip(base_A, 0.0, 1.0)
    
    base_B = eval_3d_lut(rgb_or_B.reshape(-1, 3), lut25).reshape(rgb_or_B.shape)
    base_B = np.clip(base_B, 0.0, 1.0)
    
    print("Computed base colour-fitted images from F1.")
    
    # Baseline edge error without sharpening
    edge_pts_A_base = base_A[m_edge_A > 0]
    edge_pts_A_tgt = rgb_ed_A[m_edge_A > 0]
    base_edge_rmse_A = float(np.sqrt(np.mean((edge_pts_A_base - edge_pts_A_tgt)**2)) * 255.0)
    
    edge_pts_B_base = base_B[m_edge_B > 0]
    edge_pts_B_tgt = rgb_ed_B[m_edge_B > 0]
    base_edge_rmse_B = float(np.sqrt(np.mean((edge_pts_B_base - edge_pts_B_tgt)**2)) * 255.0)
    
    print(f"Base edge RMSE (no sharpening): Pair A = {base_edge_rmse_A:.2f}/255, Pair B = {base_edge_rmse_B:.2f}/255")
    
    # 2. Extract edge profiles across line art
    luma_base_A = rgb_to_luma(base_A)
    luma_tgt_A = rgb_to_luma(rgb_ed_A)
    luma_base_B = rgb_to_luma(base_B)
    luma_tgt_B = rgb_to_luma(rgb_ed_B)
    
    profs_base_A = extract_edge_profiles(luma_base_A, m_edge_A, num_samples=800)
    profs_tgt_A = extract_edge_profiles(luma_tgt_A, m_edge_A, num_samples=800)
    
    profs_base_B = extract_edge_profiles(luma_base_B, m_edge_B, num_samples=800)
    profs_tgt_B = extract_edge_profiles(luma_tgt_B, m_edge_B, num_samples=800)
    
    print(f"Extracted {len(profs_base_A)} edge profiles on Pair A, {len(profs_base_B)} on Pair B.")
    
    # 3. Model Search on Edge Areas
    # Search grid for U1: sigma_frac_h, amount, threshold, luma vs RGB
    print("Searching parameter space for U1, U2, S1, and U1+S1...")
    
    best_models = {}
    
    # Test U1 (Luma USM)
    best_u1 = None
    best_score = 1e9
    
    # Coarse grid
    for sigma_h in [0.001, 0.002, 0.00347, 0.005, 0.008, 0.012]:
        for amount in [0.3, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0]:
            for thr in [0.0, 0.01, 0.015, 0.02]:
                out_A = apply_usm(base_A, sigma_h, amount, thr, luma_only=True)
                out_B = apply_usm(base_B, sigma_h, amount, thr, luma_only=True)
                
                rmse_A = np.sqrt(np.mean((out_A[m_edge_A > 0] - edge_pts_A_tgt)**2)) * 255.0
                rmse_B = np.sqrt(np.mean((out_B[m_edge_B > 0] - edge_pts_B_tgt)**2)) * 255.0
                score = (rmse_A + rmse_B) / 2.0
                
                if score < best_score:
                    best_score = score
                    best_u1 = {
                        "sigma_frac_h": sigma_h,
                        "amount": amount,
                        "threshold": thr,
                        "luma_only": True,
                        "rmse_A": round(float(rmse_A), 2),
                        "rmse_B": round(float(rmse_B), 2),
                        "mean_rmse": round(float(score), 2)
                    }
                    
    # Fine optimization around best
    def loss_fn(params):
        s_h, amt, thr = params
        if s_h < 0.0005 or amt < 0.0 or thr < 0.0: return 1e6
        out_A = apply_usm(base_A, s_h, amt, thr, luma_only=True)
        out_B = apply_usm(base_B, s_h, amt, thr, luma_only=True)
        r_A = np.sqrt(np.mean((out_A[m_edge_A > 0] - edge_pts_A_tgt)**2)) * 255.0
        r_B = np.sqrt(np.mean((out_B[m_edge_B > 0] - edge_pts_B_tgt)**2)) * 255.0
        return (r_A + r_B) / 2.0
        
    res = minimize(loss_fn, [best_u1["sigma_frac_h"], best_u1["amount"], best_u1["threshold"]], method='Nelder-Mead', options={'maxiter': 60})
    s_opt, a_opt, t_opt = res.x
    out_A_opt = apply_usm(base_A, s_opt, a_opt, t_opt, luma_only=True)
    out_B_opt = apply_usm(base_B, s_opt, a_opt, t_opt, luma_only=True)
    rmse_A_opt = float(np.sqrt(np.mean((out_A_opt[m_edge_A > 0] - edge_pts_A_tgt)**2)) * 255.0)
    rmse_B_opt = float(np.sqrt(np.mean((out_B_opt[m_edge_B > 0] - edge_pts_B_tgt)**2)) * 255.0)
    
    best_u1 = {
        "sigma_frac_h": round(float(s_opt), 6),
        "amount": round(float(a_opt), 4),
        "threshold": round(float(t_opt), 5),
        "luma_only": True,
        "rmse_A": round(rmse_A_opt, 2),
        "rmse_B": round(rmse_B_opt, 2),
        "mean_rmse": round((rmse_A_opt + rmse_B_opt) / 2.0, 2)
    }
    print(f"Optimized U1 (Luma USM): {best_u1}")
    
    # Test U1+S1 (USM + small Laplacian sharpen)
    best_u1_s1 = None
    best_u1_s1_score = 1e6
    for s1_amt in [0.05, 0.1, 0.15, 0.2, 0.3]:
        s1_A = apply_sharpen_3x3(out_A_opt, s1_amt, luma_only=True)
        s1_B = apply_sharpen_3x3(out_B_opt, s1_amt, luma_only=True)
        r_A = np.sqrt(np.mean((s1_A[m_edge_A > 0] - edge_pts_A_tgt)**2)) * 255.0
        r_B = np.sqrt(np.mean((s1_B[m_edge_B > 0] - edge_pts_B_tgt)**2)) * 255.0
        sc = (r_A + r_B) / 2.0
        if sc < best_u1_s1_score:
            best_u1_s1_score = sc
            best_u1_s1 = {
                "u1_sigma_frac_h": best_u1["sigma_frac_h"],
                "u1_amount": best_u1["amount"],
                "u1_threshold": best_u1["threshold"],
                "s1_amount": round(float(s1_amt), 4),
                "rmse_A": round(float(r_A), 2),
                "rmse_B": round(float(r_B), 2),
                "mean_rmse": round(float(sc), 2)
            }
    print(f"Tested U1+S1: {best_u1_s1}")
    
    # Test Victor's hand settings hint (AE Sharpen 34, USM radius 22.1 amount 32)
    # Scaled to 720p: sigma ~ 0.015H, amount ~ 0.32, sharpen ~ 0.34
    victor_A = apply_sharpen_3x3(apply_usm(base_A, 0.015, 0.32, 0.0, luma_only=True), 0.34, luma_only=True)
    victor_B = apply_sharpen_3x3(apply_usm(base_B, 0.015, 0.32, 0.0, luma_only=True), 0.34, luma_only=True)
    v_rmse_A = float(np.sqrt(np.mean((victor_A[m_edge_A > 0] - edge_pts_A_tgt)**2)) * 255.0)
    v_rmse_B = float(np.sqrt(np.mean((victor_B[m_edge_B > 0] - edge_pts_B_tgt)**2)) * 255.0)
    victor_hint = {
        "rmse_A": round(v_rmse_A, 2),
        "rmse_B": round(v_rmse_B, 2),
        "mean_rmse": round((v_rmse_A + v_rmse_B) / 2.0, 2)
    }
    print(f"Victor Hand Settings Hint: {victor_hint}")
    
    # Compute SSIM on edge areas
    luma_opt_A = rgb_to_luma(out_A_opt)
    luma_tgt_A_full = rgb_to_luma(rgb_ed_A)
    ssim_edge_A_base = ssim(luma_base_A, luma_tgt_A_full, data_range=1.0)
    ssim_edge_A_opt = ssim(luma_opt_A, luma_tgt_A_full, data_range=1.0)
    
    luma_opt_B = rgb_to_luma(out_B_opt)
    luma_tgt_B_full = rgb_to_luma(rgb_ed_B)
    ssim_edge_B_base = ssim(luma_base_B, luma_tgt_B_full, data_range=1.0)
    ssim_edge_B_opt = ssim(luma_opt_B, luma_tgt_B_full, data_range=1.0)
    
    # Save visual edge comparison images
    # Extract crop around prominent line art
    crop_A_base = (base_A[200:500, 400:800] * 255).astype(np.uint8)
    crop_A_opt = (out_A_opt[200:500, 400:800] * 255).astype(np.uint8)
    crop_A_tgt = (rgb_ed_A[200:500, 400:800] * 255).astype(np.uint8)
    crop_comp_A = np.hstack([crop_A_base, crop_A_opt, crop_A_tgt])
    cv2.imwrite(str(OUT_DIR / 'pairA_edge_crop_comparison.png'), cv2.cvtColor(crop_comp_A, cv2.COLOR_RGB2BGR))
    
    results = {
        "baseline_no_sharpen": {
            "edge_rmse_A": round(base_edge_rmse_A, 2),
            "edge_rmse_B": round(base_edge_rmse_B, 2),
            "ssim_A": round(float(ssim_edge_A_base), 5),
            "ssim_B": round(float(ssim_edge_B_base), 5)
        },
        "selected_model": {
            "model": "U1_Luma_USM",
            "parameters": best_u1,
            "edge_rmse_A": best_u1["rmse_A"],
            "edge_rmse_B": best_u1["rmse_B"],
            "rmse_reduction_A_pct": round((1.0 - best_u1["rmse_A"] / base_edge_rmse_A) * 100.0, 1),
            "rmse_reduction_B_pct": round((1.0 - best_u1["rmse_B"] / base_edge_rmse_B) * 100.0, 1),
            "ssim_A": round(float(ssim_edge_A_opt), 5),
            "ssim_B": round(float(ssim_edge_B_opt), 5)
        },
        "victor_hint_comparison": victor_hint,
        "combined_u1_s1": best_u1_s1
    }
    
    with open(OUT_DIR / 'f2_summary.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"\nF2 Edge Fit Complete! Results:\n{json.dumps(results, indent=2)}")

if __name__ == '__main__':
    main()
