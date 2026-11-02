#!/usr/bin/env python3
"""F3. Low-Frequency Gradient / Vignette / Veil Check for Floby's CC.
Uses:
  - Base image: F1 colour-fit + F2 unsharp mask
  - Low-frequency residual (sigma = 0.03 * H = 21.6 px)
  - Models tested:
      (G1) Vertical multiply gradient (smoothstep from y0 to y1 with strength RGB)
      (G2) Radial vignette (quadratic falloff from center)
      (G3) Global additive/multiplicative veil
  - Top-left y-origin in coordinates (y=0 at top, y=1 at bottom)
"""
import sys, os, time, json
from pathlib import Path
import cv2
import numpy as np
from scipy.optimize import minimize

FLOBY_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = FLOBY_DIR / 'analysis/outputs/f3'
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(FLOBY_DIR / 'analysis/src'))
from f1_colour_fit import eval_3d_lut, fit_3d_lut, build_laplacian_3d
from f2_edge_fit import apply_usm

def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / np.maximum(edge1 - edge0, 1e-5), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def main():
    print("=== MOTIONSALT F3: Gradient / Vignette / Veil Check for Floby's CC ===")
    
    # 1. Load inputs and masks
    im_ed_A = cv2.imread(str(FLOBY_DIR / 'inputs/pairA_edited.png'))
    im_or_A = cv2.imread(str(FLOBY_DIR / 'inputs/pairA_original_matched.png'))
    m_flat_A = cv2.imread(str(FLOBY_DIR / 'masks/pairA_flat_interior.png'), 0)
    m_bars_A = cv2.imread(str(FLOBY_DIR / 'masks/pairA_bars.png'), 0)
    
    im_ed_B = cv2.imread(str(FLOBY_DIR / 'inputs/pairB_edited.png'))
    im_or_B = cv2.imread(str(FLOBY_DIR / 'analysis/outputs/aligned/pairB_orig_aligned_720p.png'))
    m_flat_B = cv2.imread(str(FLOBY_DIR / 'masks/pairB_flat_interior.png'), 0)
    m_bars_B = cv2.imread(str(FLOBY_DIR / 'masks/pairB_bars.png'), 0)
    
    rgb_ed_A = cv2.cvtColor(im_ed_A, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_or_A = cv2.cvtColor(im_or_A, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_ed_B = cv2.cvtColor(im_ed_B, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_or_B = cv2.cvtColor(im_or_B, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    
    # Valid picture area mask (exclude bars and border)
    valid_A = (m_bars_A == 0) & (m_flat_A > 0)
    valid_B = (m_bars_B == 0) & (m_flat_B > 0)
    
    # 2. Build F1 + F2 base
    L25 = build_laplacian_3d(25)
    blur_or_A = cv2.GaussianBlur(rgb_or_A, (9, 9), 2.0)
    blur_ed_A = cv2.GaussianBlur(rgb_ed_A, (9, 9), 2.0)
    blur_or_B = cv2.GaussianBlur(rgb_or_B, (9, 9), 2.0)
    blur_ed_B = cv2.GaussianBlur(rgb_ed_B, (9, 9), 2.0)
    pts_in = np.vstack([blur_or_A[m_flat_A > 0], blur_or_B[m_flat_B > 0]])
    pts_tgt = np.vstack([blur_ed_A[m_flat_A > 0], blur_ed_B[m_flat_B > 0]])
    lut25 = fit_3d_lut(pts_in, pts_tgt, G=25, lambda_smooth=0.3, L=L25)
    
    base_A = eval_3d_lut(rgb_or_A.reshape(-1, 3), lut25).reshape(rgb_or_A.shape)
    base_A = apply_usm(base_A, 0.005512, 0.2029, 0.01024, luma_only=True)
    
    base_B = eval_3d_lut(rgb_or_B.reshape(-1, 3), lut25).reshape(rgb_or_B.shape)
    base_B = apply_usm(base_B, 0.005512, 0.2029, 0.01024, luma_only=True)
    
    # 3. Compute low-frequency residuals (sigma = 0.03 * H = 21.6 px)
    sigma_lf = 21.6
    ksize_lf = 87
    
    res_A = rgb_ed_A - base_A
    res_B = rgb_ed_B - base_B
    
    res_lf_A = cv2.GaussianBlur(res_A, (ksize_lf, ksize_lf), sigma_lf)
    res_lf_B = cv2.GaussianBlur(res_B, (ksize_lf, ksize_lf), sigma_lf)
    
    # Baseline LF residual energy
    lf_var_A = float(np.mean((res_lf_A[valid_A])**2))
    lf_var_B = float(np.mean((res_lf_B[valid_B])**2))
    print(f"Low-frequency residual variance: Pair A = {lf_var_A*255**2:.2f}, Pair B = {lf_var_B*255**2:.2f}")
    
    # 4. Model Testing
    # Coordinate grids: top-left origin (y=0 at top, y=1 at bottom)
    H_A, W_A, _ = rgb_or_A.shape
    y_norm_A = np.linspace(0.0, 1.0, H_A, dtype=np.float32).reshape(-1, 1)
    y_grid_A = np.repeat(y_norm_A, W_A, axis=1)
    
    H_B, W_B, _ = rgb_or_B.shape
    y_norm_B = np.linspace(0.0, 1.0, H_B, dtype=np.float32).reshape(-1, 1)
    y_grid_B = np.repeat(y_norm_B, W_B, axis=1)
    
    # Hypothesis G1: Vertical Multiply Gradient
    # out = base * (1.0 - strength * smoothstep(y0, y1, y_grid))
    print("\nFitting Hypothesis G1: Vertical Multiply Gradient...")
    def loss_grad(params):
        y0, y1, s_r, s_g, s_b = params
        if y0 >= y1 or any(s < 0.0 or s > 0.8 for s in (s_r, s_g, s_b)): return 1e6
        
        ramp_A = smoothstep(y0, y1, y_grid_A)[..., None]
        mult_A = 1.0 - ramp_A * np.array([s_r, s_g, s_b])
        pred_A = base_A * mult_A
        err_A = np.mean((pred_A[valid_A] - rgb_ed_A[valid_A])**2)
        
        ramp_B = smoothstep(y0, y1, y_grid_B)[..., None]
        mult_B = 1.0 - ramp_B * np.array([s_r, s_g, s_b])
        pred_B = base_B * mult_B
        err_B = np.mean((pred_B[valid_B] - rgb_ed_B[valid_B])**2)
        
        return (err_A + err_B) / 2.0
        
    res_g = minimize(loss_grad, [0.15, 0.80, 0.10, 0.10, 0.10], method='Nelder-Mead', options={'maxiter': 150})
    y0_opt, y1_opt, sr_opt, sg_opt, sb_opt = res_g.x
    
    # Check if gradient clearly reduces residual on BOTH scenes
    ramp_A = smoothstep(y0_opt, y1_opt, y_grid_A)[..., None]
    pred_g_A = base_A * (1.0 - ramp_A * np.array([sr_opt, sg_opt, sb_opt]))
    base_mae_A = np.mean(np.abs(base_A[valid_A] - rgb_ed_A[valid_A]) * 255.0)
    grad_mae_A = np.mean(np.abs(pred_g_A[valid_A] - rgb_ed_A[valid_A]) * 255.0)
    
    ramp_B = smoothstep(y0_opt, y1_opt, y_grid_B)[..., None]
    pred_g_B = base_B * (1.0 - ramp_B * np.array([sr_opt, sg_opt, sb_opt]))
    base_mae_B = np.mean(np.abs(base_B[valid_B] - rgb_ed_B[valid_B]) * 255.0)
    grad_mae_B = np.mean(np.abs(pred_g_B[valid_B] - rgb_ed_B[valid_B]) * 255.0)
    
    print(f"G1 Gradient: y0={y0_opt:.4f}, y1={y1_opt:.4f}, strength=[{sr_opt:.4f}, {sg_opt:.4f}, {sb_opt:.4f}]")
    print(f"  Pair A MAE: {base_mae_A:.3f} -> {grad_mae_A:.3f} (/255)")
    print(f"  Pair B MAE: {base_mae_B:.3f} -> {grad_mae_B:.3f} (/255)")
    
    # Hypothesis G2: Radial Vignette
    # out = base * (1.0 - v_strength * r_sq)
    x_norm_A = np.linspace(-1.0, 1.0, W_A, dtype=np.float32).reshape(1, -1)
    y_norm_c_A = np.linspace(-1.0, 1.0, H_A, dtype=np.float32).reshape(-1, 1)
    r_sq_A = (x_norm_A**2 + y_norm_c_A**2)[..., None]
    
    x_norm_B = np.linspace(-1.0, 1.0, W_B, dtype=np.float32).reshape(1, -1)
    y_norm_c_B = np.linspace(-1.0, 1.0, H_B, dtype=np.float32).reshape(-1, 1)
    r_sq_B = (x_norm_B**2 + y_norm_c_B**2)[..., None]
    
    def loss_vignette(v):
        p_A = base_A * (1.0 - v * r_sq_A)
        p_B = base_B * (1.0 - v * r_sq_B)
        return (np.mean((p_A[valid_A] - rgb_ed_A[valid_A])**2) + np.mean((p_B[valid_B] - rgb_ed_B[valid_B])**2)) / 2.0
        
    res_v = minimize(loss_vignette, [0.05], method='Nelder-Mead')
    v_opt = float(res_v.x[0])
    pred_v_A = base_A * (1.0 - v_opt * r_sq_A)
    pred_v_B = base_B * (1.0 - v_opt * r_sq_B)
    vig_mae_A = np.mean(np.abs(pred_v_A[valid_A] - rgb_ed_A[valid_A]) * 255.0)
    vig_mae_B = np.mean(np.abs(pred_v_B[valid_B] - rgb_ed_B[valid_B]) * 255.0)
    print(f"G2 Vignette: strength={v_opt:.4f}")
    print(f"  Pair A MAE: {base_mae_A:.3f} -> {vig_mae_A:.3f} (/255)")
    print(f"  Pair B MAE: {base_mae_B:.3f} -> {vig_mae_B:.3f} (/255)")
    
    # Hypothesis G3: Global Veil / Lift
    veil_A = np.mean(rgb_ed_A[valid_A] - base_A[valid_A], axis=0)
    veil_B = np.mean(rgb_ed_B[valid_B] - base_B[valid_B], axis=0)
    print(f"G3 Global Veil / Mean Residual: Pair A = {veil_A * 255.0}, Pair B = {veil_B * 255.0}")
    
    # Evaluation: Does any model reduce residual on all scenes?
    # Notice: on Pair A, vertical darkening gives a slight improvement, but on Pair B with 3D LUT it is nearly negligible (< 0.2/255)
    # The gradient strength is subtle: ~6-8% bottom darkening
    keep_gradient = (grad_mae_A < base_mae_A) and (grad_mae_B < base_mae_B)
    
    gradient_spec = {
        "status": "subtle_vertical_darkening" if keep_gradient else "absent",
        "y_origin": "top_left",
        "y0_top": round(float(y0_opt), 4),
        "y1_top": round(float(y1_opt), 4),
        "strength_rgb": [round(float(s), 4) for s in (sr_opt, sg_opt, sb_opt)],
        "vignette": "absent" if abs(v_opt) < 0.03 else "detected",
        "global_veil": "subsumed_by_3D_LUT",
        "metrics": {
            "pairA_mae_before": round(float(base_mae_A), 3),
            "pairA_mae_after": round(float(grad_mae_A), 3),
            "pairB_mae_before": round(float(base_mae_B), 3),
            "pairB_mae_after": round(float(grad_mae_B), 3)
        }
    }
    
    with open(OUT_DIR / 'f3_summary.json', 'w') as f:
        json.dump(gradient_spec, f, indent=2)
        
    print(f"\nF3 Gradient Check Complete! Spec:\n{json.dumps(gradient_spec, indent=2)}")

if __name__ == '__main__':
    main()
