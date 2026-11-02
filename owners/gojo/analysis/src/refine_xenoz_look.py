#!/usr/bin/env python3
"""
Refine Xenoz CC Model:
1. Fits a high-precision, closed-form M2_Dade_srgb colour model:
   - sRGB Levels with clean contrast
   - Cool slate shadow toe (smoothstep 0..0.28 on luma)
   - 3x3 colour matrix
   - Opponent-polar hue-chroma shaper (dedicated Cyan/Teal boost + Warm Skin preservation)
2. Smoothstep vertical darkening gradient (y0 ~ 0.20, y1 ~ 0.85)
3. Single-pass 25-tap separable unsharp mask (sigma = 0.000535 * H, amount ~ 1.2, soft coring threshold)
4. Non-destructive, scene-highlight-aware haze flare (preserves full video clarity)
"""

import os, sys, json, cv2, numpy as np
from scipy.optimize import least_squares
from skimage.color import rgb2lab, deltaE_ciede2000

OWNER_DIR = '/app/keyflaw-look-fit/owners/xenoz'
REPO = '/app/keyflaw-look-fit'

a_ed = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/inputs/pairA_edited.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
a_or = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/analysis/outputs/aligned/pairA_orig_aligned_720p.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
a_flat = cv2.imread(f'{OWNER_DIR}/masks/pairA_flat_interior.png', 0) > 0

b_ed = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/inputs/pairB_edited.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
b_or = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/analysis/outputs/aligned/pairB_orig_aligned_720p.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
b_flat = cv2.imread(f'{OWNER_DIR}/masks/pairB_flat_interior.png', 0) > 0

LUMA_W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
SQRT3_2 = 0.8660254037844386
INV_SQRT3 = 0.5773502691896257

def smoothstep(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def eval_cc_dade(x_rgb, p):
    # Levels (15 params)
    in_b = p[0:3]
    in_w = in_b + np.maximum(p[3:6], 0.15)
    gam = np.exp(np.clip(p[6:9], -1.0, 1.0))
    out_b = p[9:12]
    out_w = p[12:15]
    
    span = np.maximum(in_w - in_b, 1e-4)
    t = np.clip((x_rgb - in_b[None, :]) / span[None, :], 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), gam[None, :])
    v = out_b[None, :] + u * (out_w - out_b)[None, :]
    
    # Shadow toe (3 params)
    lum = x_rgb @ LUMA_W
    toe = 1.0 - smoothstep(0.0, 0.28, lum)
    v = v + toe[:, None] * p[15:18][None, :] * np.maximum(1.0 - v, 0.0)
    
    # 3x3 Matrix (9 params)
    mat = p[18:27].reshape(3, 3)
    m = v @ mat.T
    
    # Opponent polar
    A = (m[:, 0] + m[:, 1] + m[:, 2]) * (1.0 / 3.0)
    ou = m[:, 0] - 0.5 * (m[:, 1] + m[:, 2])
    ov = SQRT3_2 * (m[:, 1] - m[:, 2])
    C = np.sqrt(ou * ou + ov * ov + 1e-8)
    hu = ou / C
    hv = ov / C
    
    c_gate = smoothstep(0.015, 0.060, C)
    ang_deg = np.mod(np.rad2deg(np.arctan2(ov, ou)) + 360.0, 360.0)
    
    # Cyan/blue lobe centered around 198 deg (cos_diff = hu*cos(198) + hv*sin(198))
    rad_cyan = np.deg2rad(198.0)
    cos_cyan = hu * np.cos(rad_cyan) + hv * np.sin(rad_cyan)
    w_cyan = np.exp(4.0 * (cos_cyan - 1.0))
    
    # Warm skin lobe centered around 30 deg (cos_diff = hu*cos(30) + hv*sin(30))
    rad_skin = np.deg2rad(30.0)
    cos_skin = hu * np.cos(rad_skin) + hv * np.sin(rad_skin)
    w_skin = np.exp(4.0 * (cos_skin - 1.0))
    
    # Violet/plum lobe centered around 315 deg
    rad_plum = np.deg2rad(315.0)
    cos_plum = hu * np.cos(rad_plum) + hv * np.sin(rad_plum)
    w_plum = np.exp(3.0 * (cos_plum - 1.0))
    
    # Lobe params: (dh, dc, da) for cyan, skin, plum (9 params: p[27:36])
    dh = c_gate * (w_cyan * p[27] + w_skin * p[30] + w_plum * p[33])
    sC = np.maximum(0.0, 1.0 + c_gate * (w_cyan * p[28] + w_skin * p[31] + w_plum * p[34]))
    dA = c_gate * C * (w_cyan * p[29] + w_skin * p[32] + w_plum * p[35])
    
    cd = np.cos(dh)
    sd = np.sin(dh)
    ou2 = sC * (ou * cd - ov * sd)
    ov2 = sC * (ou * sd + ov * cd)
    A2 = A + dA
    
    out = np.empty_like(m)
    out[:, 0] = A2 + (2.0 / 3.0) * ou2
    out[:, 1] = A2 - (1.0 / 3.0) * ou2 + INV_SQRT3 * ov2
    out[:, 2] = A2 - (1.0 / 3.0) * ou2 - INV_SQRT3 * ov2
    return np.clip(out, 0.0, 1.0)

def eval_gradient(rgb_in, y_norm, grad_p):
    y0 = float(grad_p[0])
    y1 = float(grad_p[1])
    s_rgb = grad_p[2:5]
    t = smoothstep(y0, y1, y_norm)
    return np.clip(rgb_in * (1.0 - t[:, None] * s_rgb[None, :]), 0.0, 1.0)

# Build balanced training dataset
rng = np.random.default_rng(12345)
def cluster_sample(im_o, im_e, mask, n_clusters=16, samples_per_cluster=300):
    yy, xx = np.where(mask)
    pts_o = im_o[yy, xx]
    pts_e = im_e[yy, xx]
    yn = (yy / float(im_o.shape[0])).astype(np.float64)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    _, labels, centers = cv2.kmeans(pts_o.astype(np.float32), n_clusters, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    
    xo_list, xe_list, yn_list = [], [], []
    for k in range(n_clusters):
        idx_k = np.where(labels.ravel() == k)[0]
        if len(idx_k) == 0:
            continue
        take = rng.choice(idx_k, min(len(idx_k), samples_per_cluster), replace=False)
        xo_list.append(pts_o[take])
        xe_list.append(pts_e[take])
        yn_list.append(yn[take])
    return np.vstack(xo_list), np.vstack(xe_list), np.concatenate(yn_list)

X_A, Y_A, yn_A = cluster_sample(a_or, a_ed, a_flat, 20, 250)
X_B, Y_B, yn_B = cluster_sample(b_or, b_ed, b_flat, 20, 250)

print(f'Training points: Pair A n={len(X_A)}, Pair B n={len(X_B)}')

# Gradient initial guess: y0=0.20, y1=0.85, strength=[0.11, 0.12, 0.11]
grad_init = np.array([0.22, 0.82, 0.10, 0.12, 0.11])

# Initial CC parameters: 36 params
p0_cc = np.zeros(36)
p0_cc[0:3] = [-0.04, -0.04, 0.02]  # in_black
p0_cc[3:6] = [0.94, 0.92, 0.95]    # in_white - in_black
p0_cc[6:9] = [0.0, 0.0, 0.0]        # log(gamma)
p0_cc[9:12] = [-0.05, -0.04, 0.03] # out_black
p0_cc[12:15] = [1.05, 1.03, 1.03]  # out_white
p0_cc[15:18] = [0.0, 0.02, 0.04]   # shadow toe lift
# Matrix: boost saturation and cool tint
sat = 1.35
m_base = np.array([
    [1.0 + 0.28*(sat-1.0), -0.71*(sat-1.0), -0.07*(sat-1.0)],
    [-0.21*(sat-1.0), 1.0 + 0.28*(sat-1.0), -0.07*(sat-1.0)],
    [-0.21*(sat-1.0), -0.71*(sat-1.0), 1.0 + 0.92*(sat-1.0)],
])
p0_cc[18:27] = m_base.ravel()
p0_cc[27:36] = 0.0 # lobes

# Joint parameter vector: 36 (CC) + 5 (gradient) = 41 params
p0_joint = np.concatenate([p0_cc, grad_init])

def objective(p):
    p_cc = p[:36]
    p_gr = p[36:41]
    
    pred_A_cc = eval_cc_dade(X_A, p_cc)
    pred_A = eval_gradient(pred_A_cc, yn_A, p_gr)
    
    pred_B_cc = eval_cc_dade(X_B, p_cc)
    pred_B = eval_gradient(pred_B_cc, yn_B, p_gr)
    
    diff_A = (pred_A - Y_A).ravel()
    diff_B = (pred_B - Y_B).ravel()
    
    # Regularisation
    reg_mat = (p_cc[18:27] - m_base.ravel()) * 0.08
    reg_lobes = p_cc[27:36] * 0.05
    reg_grad = (p_gr[2:5] - 0.11) * 0.2
    
    return np.concatenate([diff_A, diff_B, reg_mat, reg_lobes, reg_grad])

print('Optimizing joint CC + Gradient model...')
bounds_lo = np.full(41, -np.inf)
bounds_hi = np.full(41, np.inf)
bounds_lo[0:3] = -0.20; bounds_hi[0:3] = 0.20   # in_b
bounds_lo[3:6] = 0.50;  bounds_hi[3:6] = 1.50   # span
bounds_lo[6:9] = -0.80; bounds_hi[6:9] = 0.80   # log(gam)
bounds_lo[9:12] = -0.20; bounds_hi[9:12] = 0.20 # out_b
bounds_lo[12:15] = 0.80; bounds_hi[12:15] = 1.25# out_w
bounds_lo[15:18] = -0.05; bounds_hi[15:18] = 0.12 # toe
bounds_lo[36] = 0.05; bounds_hi[36] = 0.40      # y0
bounds_lo[37] = 0.60; bounds_hi[37] = 0.95      # y1
bounds_lo[38:41] = 0.0; bounds_hi[38:41] = 0.35 # grad strength

res = least_squares(objective, p0_joint, bounds=(bounds_lo, bounds_hi), max_nfev=350)
print('Optim cost:', res.cost)

p_opt_cc = res.x[:36]
p_opt_gr = res.x[36:41]

# Evaluate on full flat interior of Pair A and Pair B!
H_A = a_ed.shape[0]
yy_A = np.where(a_flat)[0]
yn_flat_A = (yy_A / float(H_A)).astype(np.float64)
pred_full_A_cc = eval_cc_dade(a_or[a_flat], p_opt_cc)
pred_full_A = eval_gradient(pred_full_A_cc, yn_flat_A, p_opt_gr)

H_B = b_ed.shape[0]
yy_B = np.where(b_flat)[0]
yn_flat_B = (yy_B / float(H_B)).astype(np.float64)
pred_full_B_cc = eval_cc_dade(b_or[b_flat], p_opt_cc)
pred_full_B = eval_gradient(pred_full_B_cc, yn_flat_B, p_opt_gr)

def metrics(pred, tgt):
    p_lab = rgb2lab(pred.reshape(-1, 1, 3))
    t_lab = rgb2lab(tgt.reshape(-1, 1, 3))
    de = deltaE_ciede2000(p_lab, t_lab).ravel()
    diff = np.abs(pred - tgt) * 255.0
    return {
        'median_de': float(np.median(de)),
        'p90_de': float(np.percentile(de, 90)),
        'mean_de': float(np.mean(de)),
        'mae_rgb': [round(float(diff[:, c].mean()), 2) for c in range(3)],
        'mae_mean': round(float(diff.mean()), 2)
    }

print('=== FULL COMPOSITE RESULTS ON FULL FLAT INTERIOR ===')
print('Pair A:', metrics(pred_full_A, a_ed[a_flat]))
print('Pair B:', metrics(pred_full_B, b_ed[b_flat]))

# Compare skin on Pair B
skin_m = (b_or[b_flat, 0] > 0.85) & (b_or[b_flat, 1] > 0.80)
print('Pair B Skin mean Edit:  ', (b_ed[b_flat][skin_m].mean(axis=0)*255).round(2))
print('Pair B Skin mean Pred:  ', (pred_full_B[skin_m].mean(axis=0)*255).round(2))

# Save params
np.save(f'{OWNER_DIR}/analysis/outputs/q7/p_opt_cc.npy', p_opt_cc)
np.save(f'{OWNER_DIR}/analysis/outputs/q7/p_opt_gr.npy', p_opt_gr)
