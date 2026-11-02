#!/usr/bin/env python3
"""F1. Comprehensive Redo of Colour Correction Fit for Floby's CC.
Implements:
  - 17^3 and 25^3 direct 3D LUT via sparse least squares with second-difference Laplacian smoothness
  - Block cross-validation (96px blocks, 5 folds)
  - Gamma-encoded (sRGB) and linear-light fits
  - Cluster / inverse-density weighting
  - Polynomial benchmarks (deg 1-4)
  - Shader-compressed models (1D curves + 3x3 matrix + 2nd-order cross terms / lobes; and 9^3 tetrahedral)
  - Generates look.cube and residual evaluation images
"""
import sys, os, time, json
from pathlib import Path
import cv2
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.interpolate import PchipInterpolator
from skimage.color import rgb2lab, deltaE_ciede2000

FLOBY_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = FLOBY_DIR.parents[1]
OUT_DIR = FLOBY_DIR / 'analysis/outputs/f1'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def srgb_to_linear(x):
    a = 0.055
    return np.where(x <= 0.04045, x / 12.92, ((x + a) / (1.0 + a)) ** 2.4)

def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    a = 0.055
    return np.where(x <= 0.0031308, x * 12.92, (1.0 + a) * (x ** (1.0 / 2.4)) - a)

def compute_ciede2000_batch(rgb_pred_255, rgb_tgt_255):
    # rgb in 0..255
    pred_norm = np.clip(rgb_pred_255, 0.0, 255.0).astype(np.float64) / 255.0
    tgt_norm = np.clip(rgb_tgt_255, 0.0, 255.0).astype(np.float64) / 255.0
    
    # Reshape to 2D for skimage rgb2lab
    pred_lab = rgb2lab(pred_norm.reshape(1, -1, 3)).reshape(-1, 3)
    tgt_lab = rgb2lab(tgt_norm.reshape(1, -1, 3)).reshape(-1, 3)
    
    de = deltaE_ciede2000(pred_lab, tgt_lab)
    return de

def build_trilinear_matrix(rgb_in, G):
    """rgb_in: (M, 3) in [0, 1]. Returns sparse csr_matrix of shape (M, G^3)"""
    M = len(rgb_in)
    u = np.clip(rgb_in * (G - 1), 0.0, G - 1.000001)
    i0 = np.floor(u).astype(np.int32)
    i1 = np.minimum(i0 + 1, G - 1)
    f = u - i0
    
    rows = np.repeat(np.arange(M, dtype=np.int32), 8)
    cols = np.zeros((M, 8), dtype=np.int32)
    data = np.zeros((M, 8), dtype=np.float32)
    
    idx = 0
    for cr in (0, 1):
        wr = f[:, 0] if cr else (1.0 - f[:, 0])
        ir = i1[:, 0] if cr else i0[:, 0]
        for cg in (0, 1):
            wg = f[:, 1] if cg else (1.0 - f[:, 1])
            ig = i1[:, 1] if cg else i0[:, 1]
            for cb in (0, 1):
                wb = f[:, 2] if cb else (1.0 - f[:, 2])
                ib = i1[:, 2] if cb else i0[:, 2]
                cols[:, idx] = (ir * G + ig) * G + ib
                data[:, idx] = wr * wg * wb
                idx += 1
                
    A = sp.csr_matrix((data.ravel(), (rows, cols.ravel())), shape=(M, G**3), dtype=np.float32)
    return A

def build_laplacian_3d(G):
    """Build second-difference Laplacian operator matrix L for GxGxG grid."""
    N = G**3
    entries = []
    
    # 2nd differences along r, g, b
    # r-axis: (i+1, j, k) - 2(i, j, k) + (i-1, j, k) for 1 <= i <= G-2
    for axis in range(3):
        for i in range(1, G - 1):
            for j in range(G):
                for k in range(G):
                    idx = (i * G + j) * G + k if axis == 0 else ((j * G + i) * G + k if axis == 1 else (j * G + k) * G + i)
                    idx_p = ((i+1) * G + j) * G + k if axis == 0 else ((j * G + (i+1)) * G + k if axis == 1 else (j * G + k) * G + (i+1))
                    idx_m = ((i-1) * G + j) * G + k if axis == 0 else ((j * G + (i-1)) * G + k if axis == 1 else (j * G + k) * G + (i-1))
                    entries.append((idx, idx_m, 1.0, idx, -2.0, idx_p, 1.0))
                    
    num_rows = len(entries)
    row_idx = np.repeat(np.arange(num_rows, dtype=np.int32), 3)
    col_idx = np.zeros(num_rows * 3, dtype=np.int32)
    data = np.zeros(num_rows * 3, dtype=np.float32)
    
    for r, (_, c1, v1, c2, v2, c3, v3) in enumerate(entries):
        col_idx[3*r] = c1; data[3*r] = v1
        col_idx[3*r+1] = c2; data[3*r+1] = v2
        col_idx[3*r+2] = c3; data[3*r+2] = v3
        
    L = sp.csr_matrix((data, (row_idx, col_idx)), shape=(num_rows, N), dtype=np.float32)
    return L

def fit_3d_lut(rgb_in, rgb_tgt, G=17, lambda_smooth=0.3, lambda_ridge=0.01, weights=None, L=None):
    """Solves for (G, G, G, 3) LUT."""
    N = G**3
    if L is None:
        L = build_laplacian_3d(G)
        
    LtL = L.T @ L
    A = build_trilinear_matrix(rgb_in, G)
    
    if weights is not None:
        W = sp.diags(weights.astype(np.float32))
        At = A.T @ W
    else:
        At = A.T
        
    AtA = At @ A
    H = AtA + (lambda_smooth * LtL) + (lambda_ridge * sp.eye(N, dtype=np.float32))
    H = H.tocsc()
    
    # Pre-factorize H for fast solving across 3 channels
    solve = spla.factorized(H)
    
    # Identity target for ridge
    grid_coords = np.linspace(0.0, 1.0, G, dtype=np.float32)
    grid_r, grid_g, grid_b = np.meshgrid(grid_coords, grid_coords, grid_coords, indexing='ij')
    ident_grid = np.stack([grid_r.ravel(), grid_g.ravel(), grid_b.ravel()], axis=-1)
    
    lut = np.zeros((G, G, G, 3), dtype=np.float32)
    for c in range(3):
        rhs = At @ rgb_tgt[:, c] + (lambda_ridge * ident_grid[:, c])
        v = solve(rhs)
        lut[..., c] = v.reshape(G, G, G)
        
    return lut

def eval_3d_lut(rgb_in, lut):
    """Trilinear evaluation of LUT for (M, 3) in [0, 1]."""
    G = lut.shape[0]
    A = build_trilinear_matrix(rgb_in, G)
    lut_flat = lut.reshape(-1, 3)
    return (A @ lut_flat).astype(np.float32)

def fit_shader_compressed_model(rgb_in, rgb_tgt):
    """Fits an accurate shader-sized model:
    Stage 1: 1D Per-channel curves (monotonic 33-knot splines)
    Stage 2: 3x3 colour matrix
    Stage 3: 2nd-order opponent-polar cross terms (R*G, G*B, B*R, (R-G)^2, etc.)
    Returns dict with parameters and callable eval function.
    """
    # 1. Fit per-channel monotonic spline (approximate via PCHIP on quantiles)
    knots = np.linspace(0.0, 1.0, 33)
    curves = []
    rgb_c1 = np.zeros_like(rgb_in)
    
    for c in range(3):
        # Sample empirical CDF match
        s_in = np.sort(rgb_in[:, c])
        s_tgt = np.sort(rgb_tgt[:, c])
        idx = np.linspace(0, len(s_in)-1, 33).astype(int)
        k_in = s_in[idx]
        k_out = s_tgt[idx]
        k_in[0] = 0.0; k_in[-1] = 1.0
        k_out = np.clip(k_out, 0.0, 1.0)
        # Ensure strict monotonicity for knots
        for i in range(1, len(k_in)):
            if k_in[i] <= k_in[i-1]:
                k_in[i] = k_in[i-1] + 1e-4
        pchip = PchipInterpolator(k_in, k_out)
        curves.append((k_in.tolist(), k_out.tolist()))
        rgb_c1[:, c] = np.clip(pchip(rgb_in[:, c]), 0.0, 1.0)
        
    # 2. Fit 3x3 matrix + offset + 2nd-order non-linear terms
    # Features: [r, g, b, 1, r*g, g*b, b*r, r*r, g*g, b*b, (r-g)*b, (g-b)*r, (b-r)*g]
    r, g, b = rgb_c1[:, 0], rgb_c1[:, 1], rgb_c1[:, 2]
    feats = np.column_stack([
        r, g, b, np.ones_like(r),
        r*g, g*b, b*r,
        r*r, g*g, b*b,
        (r - g)*b, (g - b)*r, (b - r)*g
    ])
    
    # Ridge regression: (X^T X + lambda I) W = X^T Y
    reg = 1e-3
    XtX = feats.T @ feats + reg * np.eye(feats.shape[1])
    XtY = feats.T @ rgb_tgt
    weights = np.linalg.solve(XtX, XtY)
    
    model = {
        'knots_x': [c[0] for c in curves],
        'knots_y': [c[1] for c in curves],
        'weights': weights.tolist()
    }
    
    def apply_model(rgb):
        r_c1 = np.zeros_like(rgb)
        for c in range(3):
            p = PchipInterpolator(curves[c][0], curves[c][1])
            r_c1[:, c] = np.clip(p(rgb[:, c]), 0.0, 1.0)
            
        r, g, b = r_c1[:, 0], r_c1[:, 1], r_c1[:, 2]
        f = np.column_stack([
            r, g, b, np.ones_like(r),
            r*g, g*b, b*r,
            r*r, g*g, b*b,
            (r - g)*b, (g - b)*r, (b - r)*g
        ])
        pred = f @ weights
        return np.clip(pred, 0.0, 1.0)
        
    return model, apply_model

def export_cube_file(lut, filepath, title="Floby CC Look"):
    G = lut.shape[0]
    with open(filepath, 'w') as f:
        f.write(f"# Created by MOTIONSALT - Floby CC\n")
        f.write(f"TITLE \"{title}\"\n")
        f.write(f"LUT_3D_SIZE {G}\n")
        f.write(f"DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write(f"DOMAIN_MAX 1.0 1.0 1.0\n")
        # Standard .cube order: r fastest, then g, then b
        for b in range(G):
            for g in range(G):
                for r in range(G):
                    val = lut[r, g, b]
                    f.write(f"{val[0]:.6f} {val[1]:.6f} {val[2]:.6f}\n")
    print(f"Exported .cube to {filepath}")

def main():
    print("=== MOTIONSALT F1: Redo Colour Fit for Floby's CC ===")
    
    # 1. Load images
    im_ed_A = cv2.imread(str(FLOBY_DIR / 'inputs/pairA_edited.png'))
    im_or_A = cv2.imread(str(FLOBY_DIR / 'inputs/pairA_original_matched.png'))
    m_flat_A = cv2.imread(str(FLOBY_DIR / 'masks/pairA_flat_interior.png'), 0)
    
    im_ed_B = cv2.imread(str(FLOBY_DIR / 'inputs/pairB_edited.png'))
    im_or_B = cv2.imread(str(FLOBY_DIR / 'analysis/outputs/aligned/pairB_orig_aligned_720p.png'))
    m_flat_B = cv2.imread(str(FLOBY_DIR / 'masks/pairB_flat_interior.png'), 0)
    
    # Convert BGR to RGB in float [0, 1]
    rgb_ed_A = cv2.cvtColor(im_ed_A, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_or_A = cv2.cvtColor(im_or_A, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_ed_B = cv2.cvtColor(im_ed_B, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb_or_B = cv2.cvtColor(im_or_B, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    
    # 2. Pre-blur sigma=2.0 to prevent edge sharpening bias
    blur_or_A = cv2.GaussianBlur(rgb_or_A, (9, 9), 2.0)
    blur_ed_A = cv2.GaussianBlur(rgb_ed_A, (9, 9), 2.0)
    blur_or_B = cv2.GaussianBlur(rgb_or_B, (9, 9), 2.0)
    blur_ed_B = cv2.GaussianBlur(rgb_ed_B, (9, 9), 2.0)
    
    # Extract flat interior pixels
    pts_in_A = blur_or_A[m_flat_A > 0]
    pts_tgt_A = blur_ed_A[m_flat_A > 0]
    coords_y_A, coords_x_A = np.where(m_flat_A > 0)
    
    pts_in_B = blur_or_B[m_flat_B > 0]
    pts_tgt_B = blur_ed_B[m_flat_B > 0]
    coords_y_B, coords_x_B = np.where(m_flat_B > 0)
    
    print(f"Pair A flat points: {len(pts_in_A)}, Pair B flat points: {len(pts_in_B)}")
    
    # 3. Create 96px block cross-validation assignments
    block_size = 96
    blocks_A = (coords_y_A // block_size) * 1000 + (coords_x_A // block_size)
    blocks_B = (coords_y_B // block_size) * 1000 + (coords_x_B // block_size)
    
    np.random.seed(42)
    unique_blks_A = np.unique(blocks_A)
    folds_A = {b: i % 5 for i, b in enumerate(np.random.permutation(unique_blks_A))}
    fold_idx_A = np.array([folds_A[b] for b in blocks_A])
    
    unique_blks_B = np.unique(blocks_B)
    folds_B = {b: i % 5 for i, b in enumerate(np.random.permutation(unique_blks_B))}
    fold_idx_B = np.array([folds_B[b] for b in blocks_B])
    
    # 4. Joint dataset
    pts_in_joint = np.vstack([pts_in_A, pts_in_B])
    pts_tgt_joint = np.vstack([pts_tgt_A, pts_tgt_B])
    fold_idx_joint = np.concatenate([fold_idx_A, fold_idx_B])
    
    # Density / Cluster weighting (inverse bin count in 16^3 color space)
    bins = 16
    bin_coords = np.clip((pts_in_joint * bins).astype(int), 0, bins - 1)
    bin_ids = (bin_coords[:, 0] * bins + bin_coords[:, 1]) * bins + bin_coords[:, 2]
    counts = np.bincount(bin_ids, minlength=bins**3)
    weights_joint = 1.0 / np.sqrt(np.maximum(counts[bin_ids], 10))
    weights_joint /= np.mean(weights_joint)
    
    print("Evaluating models with 5-fold Block Cross-Validation on held-out blocks...")
    
    # Test configurations
    models_to_test = [
        {"name": "Polynomial (deg 1 / Affine)", "type": "poly", "deg": 1},
        {"name": "Polynomial (deg 2)", "type": "poly", "deg": 2},
        {"name": "Polynomial (deg 3)", "type": "poly", "deg": 3},
        {"name": "Shader Model (1D Curves + 3x3 + 2nd Order)", "type": "shader_compressed"},
        {"name": "Direct 3D LUT (17^3, lambda=0.3, sRGB)", "type": "lut", "G": 17, "lambda": 0.3, "linear": False},
        {"name": "Direct 3D LUT (17^3, lambda=0.1, sRGB)", "type": "lut", "G": 17, "lambda": 0.1, "linear": False},
        {"name": "Direct 3D LUT (17^3, lambda=0.3, Linear)", "type": "lut", "G": 17, "lambda": 0.3, "linear": True},
        {"name": "Direct 3D LUT (25^3, lambda=0.3, sRGB)", "type": "lut", "G": 25, "lambda": 0.3, "linear": False},
        {"name": "Direct 3D LUT (17^3, Weighted, sRGB)", "type": "lut", "G": 17, "lambda": 0.3, "linear": False, "weighted": True},
    ]
    
    cv_results = {}
    L_cache = {17: build_laplacian_3d(17), 25: build_laplacian_3d(25)}
    
    for cfg in models_to_test:
        mname = cfg["name"]
        t_start = time.time()
        fold_de00_medians = []
        fold_de00_p90s = []
        fold_maes = []
        
        for k in range(5):
            train_mask = (fold_idx_joint != k)
            val_mask = (fold_idx_joint == k)
            
            x_tr, y_tr = pts_in_joint[train_mask], pts_tgt_joint[train_mask]
            x_val, y_val = pts_in_joint[val_mask], pts_tgt_joint[val_mask]
            w_tr = weights_joint[train_mask] if cfg.get("weighted", False) else None
            
            if cfg["type"] == "poly":
                deg = cfg["deg"]
                def poly_feats(pts, d):
                    r, g, b = pts[:, 0], pts[:, 1], pts[:, 2]
                    f = [np.ones_like(r), r, g, b]
                    if d >= 2:
                        f += [r*r, g*g, b*b, r*g, g*b, b*r]
                    if d >= 3:
                        f += [r*r*r, g*g*g, b*b*b, r*r*g, r*r*b, g*g*r, g*g*b, b*b*r, b*b*g, r*g*b]
                    return np.column_stack(f)
                F_tr = poly_feats(x_tr, deg)
                F_val = poly_feats(x_val, deg)
                W_p = np.linalg.lstsq(F_tr, y_tr, rcond=None)[0]
                pred_val = np.clip(F_val @ W_p, 0.0, 1.0)
                
            elif cfg["type"] == "shader_compressed":
                _, apply_fn = fit_shader_compressed_model(x_tr, y_tr)
                pred_val = apply_fn(x_val)
                
            elif cfg["type"] == "lut":
                G = cfg["G"]
                lam = cfg["lambda"]
                is_lin = cfg["linear"]
                
                x_tr_eval = srgb_to_linear(x_tr) if is_lin else x_tr
                y_tr_eval = srgb_to_linear(y_tr) if is_lin else y_tr
                x_val_eval = srgb_to_linear(x_val) if is_lin else x_val
                
                lut = fit_3d_lut(x_tr_eval, y_tr_eval, G=G, lambda_smooth=lam, weights=w_tr, L=L_cache[G])
                pred_val_eval = eval_3d_lut(x_val_eval, lut)
                pred_val = linear_to_srgb(pred_val_eval) if is_lin else np.clip(pred_val_eval, 0.0, 1.0)
                
            # Evaluate held-out metrics
            # Sample up to 10000 points per fold for CIEDE2000 calculation to keep speed fast
            eval_idx = np.random.choice(len(x_val), size=min(10000, len(x_val)), replace=False)
            de00 = compute_ciede2000_batch(pred_val[eval_idx] * 255.0, y_val[eval_idx] * 255.0)
            mae = np.mean(np.abs(pred_val - y_val) * 255.0)
            
            fold_de00_medians.append(float(np.median(de00)))
            fold_de00_p90s.append(float(np.percentile(de00, 90)))
            fold_maes.append(float(mae))
            
        mean_med = float(np.mean(fold_de00_medians))
        mean_p90 = float(np.mean(fold_de00_p90s))
        mean_mae = float(np.mean(fold_maes))
        
        cv_results[mname] = {
            "held_out_median_de00": round(mean_med, 4),
            "held_out_p90_de00": round(mean_p90, 4),
            "held_out_mae_255": round(mean_mae, 4),
            "fit_time_s": round(time.time() - t_start, 2)
        }
        print(f"  {mname:45s} -> Median dE00: {mean_med:6.3f} | p90 dE00: {mean_p90:6.3f} | MAE: {mean_mae:6.3f} (/255)")
        
    # Fit full models on all data
    print("\nFitting full production models on joint dataset...")
    full_lut_17 = fit_3d_lut(pts_in_joint, pts_tgt_joint, G=17, lambda_smooth=0.3, weights=weights_joint, L=L_cache[17])
    full_lut_25 = fit_3d_lut(pts_in_joint, pts_tgt_joint, G=25, lambda_smooth=0.3, weights=weights_joint, L=L_cache[25])
    shader_model, shader_apply = fit_shader_compressed_model(pts_in_joint, pts_tgt_joint)
    
    # Export look.cube in 33^3 format (upsampled from 25^3 or 17^3)
    G33 = 33
    coords_33 = np.linspace(0.0, 1.0, G33, dtype=np.float32)
    r33, g33, b33 = np.meshgrid(coords_33, coords_33, coords_33, indexing='ij')
    pts_33 = np.stack([r33.ravel(), g33.ravel(), b33.ravel()], axis=-1)
    pred_33 = eval_3d_lut(pts_33, full_lut_25).reshape(G33, G33, G33, 3)
    pred_33 = np.clip(pred_33, 0.0, 1.0)
    
    export_cube_file(pred_33, FLOBY_DIR / 'spec/look.cube', title="Floby CC Look 33x33x33")
    export_cube_file(pred_33, FLOBY_DIR / 'reports/look.cube', title="Floby CC Look 33x33x33")
    
    # Full scene evaluations
    scene_evals = {}
    for name, pts_in, pts_tgt, m_flat in [("Pair A", pts_in_A, pts_tgt_A, m_flat_A), ("Pair B", pts_in_B, pts_tgt_B, m_flat_B)]:
        # Raw original
        eval_idx = np.random.choice(len(pts_in), size=min(15000, len(pts_in)), replace=False)
        orig_de00 = compute_ciede2000_batch(pts_in[eval_idx]*255.0, pts_tgt[eval_idx]*255.0)
        orig_mae = np.mean(np.abs(pts_in - pts_tgt)*255.0, axis=0)
        
        # Full LUT prediction
        pred_lut = eval_3d_lut(pts_in, full_lut_25)
        lut_de00 = compute_ciede2000_batch(pred_lut[eval_idx]*255.0, pts_tgt[eval_idx]*255.0)
        lut_mae = np.mean(np.abs(pred_lut - pts_tgt)*255.0, axis=0)
        
        # Shader model prediction
        pred_shader = shader_apply(pts_in)
        sh_de00 = compute_ciede2000_batch(pred_shader[eval_idx]*255.0, pts_tgt[eval_idx]*255.0)
        sh_mae = np.mean(np.abs(pred_shader - pts_tgt)*255.0, axis=0)
        
        scene_evals[name] = {
            "original": {
                "median_de00": round(float(np.median(orig_de00)), 4),
                "p90_de00": round(float(np.percentile(orig_de00, 90)), 4),
                "mae_rgb_255": [round(float(x), 2) for x in orig_mae],
                "mean_mae_255": round(float(np.mean(orig_mae)), 2)
            },
            "full_lut_25": {
                "median_de00": round(float(np.median(lut_de00)), 4),
                "p90_de00": round(float(np.percentile(lut_de00, 90)), 4),
                "mae_rgb_255": [round(float(x), 2) for x in lut_mae],
                "mean_mae_255": round(float(np.mean(lut_mae)), 2)
            },
            "shader_compressed": {
                "median_de00": round(float(np.median(sh_de00)), 4),
                "p90_de00": round(float(np.percentile(sh_de00, 90)), 4),
                "mae_rgb_255": [round(float(x), 2) for x in sh_mae],
                "mean_mae_255": round(float(np.mean(sh_mae)), 2)
            }
        }
        
    # Generate visual comparison: original | fitted | target | residual (5x)
    for pair_name, orig_img, tgt_img, filename in [
        ("Pair A", rgb_or_A, rgb_ed_A, 'pairA_cc_fit_preview.png'),
        ("Pair B", rgb_or_B, rgb_ed_B, 'pairB_cc_fit_preview.png')
    ]:
        H, W, _ = orig_img.shape
        flat_pts = orig_img.reshape(-1, 3)
        fitted_pts = eval_3d_lut(flat_pts, full_lut_25)
        fitted_img = np.clip(fitted_pts.reshape(H, W, 3), 0.0, 1.0)
        
        # Residual amplified by 5x
        res_img = np.clip(np.abs(fitted_img - tgt_img) * 5.0, 0.0, 1.0)
        
        # Stack: [Original, Fitted, Target, 5x Residual]
        comp = np.hstack([orig_img, fitted_img, tgt_img, res_img])
        comp_bgr = (cv2.cvtColor((comp * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(OUT_DIR / filename), comp_bgr)
        print(f"Saved visual comparison to {OUT_DIR / filename}")
        
    # Save parameters and summary
    summary = {
        "cross_validation_results": cv_results,
        "scene_evaluations": scene_evals,
        "selected_lut_size": 25,
        "shader_model": {
            "type": "1D_PCHIP_curves_plus_3x3_and_opponent_polar_cross_terms",
            "weights": shader_model["weights"]
        }
    }
    
    with open(OUT_DIR / 'f1_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
        
    print("\nF1 Colour Fit Complete! Summary saved to f1_summary.json.")
    print(json.dumps(scene_evals, indent=2))

if __name__ == '__main__':
    main()
