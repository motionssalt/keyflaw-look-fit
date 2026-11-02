#!/usr/bin/env python3
import os, sys, json, cv2, numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.metrics import structural_similarity as ssim

OWNER_DIR = '/app/keyflaw-look-fit/owners/xenoz'
REPO = '/app/keyflaw-look-fit'
SPEC_DIR = os.path.join(OWNER_DIR, 'spec')
REPORTS_DIR = os.path.join(OWNER_DIR, 'reports')

sys.path.insert(0, SPEC_DIR)
import look_apply

with open(os.path.join(SPEC_DIR, 'look_params.json')) as f:
    params = json.load(f)

# 1. Export 33x33x33 look.cube
size = 33
pts = np.linspace(0.0, 1.0, size)
B_mesh, G_mesh, R_mesh = np.meshgrid(pts, pts, pts, indexing='ij')
grid_rgb = np.stack([R_mesh.ravel(), G_mesh.ravel(), B_mesh.ravel()], axis=1)

cc_grid = look_apply.stage1_colour_correction(grid_rgb, params['colour_correction'])
cube_lines = [
    'TITLE "Xenoz CC Color Grade"',
    'LUT_3D_SIZE 33',
    'DOMAIN_MIN 0.0 0.0 0.0',
    'DOMAIN_MAX 1.0 1.0 1.0'
]
for row in cc_grid:
    cube_lines.append(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}")

cube_text = "\n".join(cube_lines) + "\n"
with open(os.path.join(SPEC_DIR, 'look.cube'), 'w', encoding='utf-8') as f:
    f.write(cube_text)
with open(os.path.join(REPORTS_DIR, 'look.cube'), 'w', encoding='utf-8') as f:
    f.write(cube_text)
print(f"Exported 33x33x33 look.cube ({len(cube_lines)} lines).")

# 2. Compute Test Vectors
tv_inputs = [
    # Grayscale steps
    [0.0, 0.0, 0.0], [0.1, 0.1, 0.1], [0.2, 0.2, 0.2], [0.3, 0.3, 0.3],
    [0.4, 0.4, 0.4], [0.5, 0.5, 0.5], [0.6, 0.6, 0.6], [0.7, 0.7, 0.7],
    [0.8, 0.8, 0.8], [0.9, 0.9, 0.9], [1.0, 1.0, 1.0],
    # Primaries & Secondaries
    [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
    [1.0, 1.0, 0.0], [0.0, 1.0, 1.0], [1.0, 0.0, 1.0],
    # Anime skin & Sky tones
    [0.930, 0.899, 0.848], # Pair B skin
    [0.932, 0.888, 0.810], # Pair A skin
    [0.175, 0.366, 0.665], # Pair A cyan sky
    [0.441, 0.508, 0.763], # Pair B iris
    [0.484, 0.095, 0.086], # Pair B red burst
    [0.194, 0.227, 0.266], # Shadow slate
    [0.087, 0.012, 0.013], # Deep dark
]
tv_in_arr = np.array(tv_inputs, dtype=np.float64)
tv_out_arr = look_apply.stage1_colour_correction(tv_in_arr, params['colour_correction'])

test_vectors_cc = []
for i in range(len(tv_inputs)):
    test_vectors_cc.append({
        "input_rgb": [round(float(v), 4) for v in tv_inputs[i]],
        "output_rgb": [round(float(v), 4) for v in tv_out_arr[i]]
    })

# Gradient test vectors (y -> multiplier)
y_steps = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
grad_tvs = []
for y in y_steps:
    t = look_apply.smoothstep_np(params['gradient']['y0_norm'], params['gradient']['y1_norm'], y)
    s = np.array(params['gradient']['strength_rgb'])
    mult = 1.0 - t * s
    grad_tvs.append({"y_norm": y, "multiplier_rgb": [round(float(v), 4) for v in mult]})

# Flare test vectors
flare_tvs = []
for x, y in [(0.5, 0.05), (0.1, 0.1), (0.9, 0.1), (0.5, 0.5), (0.1, 0.9), (0.9, 0.9)]:
    pt_in = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float64)
    # create small image with that coordinate
    fp = params['flare']['canonical_default_params']
    dx = (x - fp['cx']) * (720.0 / 720.0) # aspect 1.0
    dy = y - fp['cy']
    d2 = (dx / fp['rx_frac_h'])**2 + (dy / fp['ry_frac_h'])**2
    w = np.exp(-0.5 * d2)
    f_vec = np.clip(fp['intensity'] * w * np.array(fp['colour_rgb']), 0.0, 1.0)
    out = 1.0 - (1.0 - 0.5) * (1.0 - f_vec)
    flare_tvs.append({"xy": [x, y], "input_mid_grey": 0.5, "output_rgb": [round(float(v), 4) for v in out]})

with open(os.path.join(OWNER_DIR, 'analysis', 'outputs', 'q8', 'test_vectors.json'), 'w') as f:
    json.dump({
        "colour_correction": test_vectors_cc,
        "gradient": grad_tvs,
        "flare": flare_tvs
    }, f, indent=2)
print("Saved test_vectors.json.")

# 3. Apply look to Pair A and Pair B and compute full report metrics
a_ed = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/inputs/pairA_edited.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
a_or = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/analysis/outputs/aligned/pairA_orig_aligned_720p.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
a_flat = cv2.imread(f'{OWNER_DIR}/masks/pairA_flat_interior.png', 0) > 0
a_line = cv2.imread(f'{OWNER_DIR}/masks/pairA_line_edges.png', 0) > 0

b_ed = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/inputs/pairB_edited.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
b_or = cv2.cvtColor(cv2.imread(f'{OWNER_DIR}/analysis/outputs/aligned/pairB_orig_aligned_720p.png'), cv2.COLOR_BGR2RGB).astype(np.float64)/255.0
b_flat = cv2.imread(f'{OWNER_DIR}/masks/pairB_flat_interior.png', 0) > 0
b_line = cv2.imread(f'{OWNER_DIR}/masks/pairB_line_edges.png', 0) > 0

# Stage ablation on Pair A:
outA_raw = a_or
outA_cc = look_apply.stage1_colour_correction(a_or, params['colour_correction'])
outA_grad = look_apply.stage2_gradient(outA_cc, params['gradient'])
outA_usm = look_apply.stage3_unsharp_mask(outA_grad, params['unsharp'])
outA_full = look_apply.apply_look(a_or, params)

outB_raw = b_or
outB_cc = look_apply.stage1_colour_correction(b_or, params['colour_correction'])
outB_grad = look_apply.stage2_gradient(outB_cc, params['gradient'])
outB_usm = look_apply.stage3_unsharp_mask(outB_grad, params['unsharp'])
outB_full = look_apply.apply_look(b_or, params)

# Save applied images
cv2.imwrite(f'{OWNER_DIR}/analysis/outputs/q8/pairA_applied.png', cv2.cvtColor((outA_full*255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
cv2.imwrite(f'{OWNER_DIR}/analysis/outputs/q8/pairB_applied.png', cv2.cvtColor((outB_full*255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))

def compute_all_metrics(pred, ed, flat_m, line_m):
    p_lab = rgb2lab(pred[flat_m].reshape(-1, 1, 3))
    t_lab = rgb2lab(ed[flat_m].reshape(-1, 1, 3))
    de = deltaE_ciede2000(p_lab, t_lab).ravel()
    diff = np.abs(pred[flat_m] - ed[flat_m]) * 255.0
    rmse = np.sqrt(np.mean((pred[line_m] - ed[line_m])**2)) * 255.0
    luma_p = pred @ look_apply.LUMA_W
    luma_t = ed @ look_apply.LUMA_W
    s = ssim(luma_p, luma_t, data_range=1.0)
    return {
        "de00_median": round(float(np.median(de)), 3),
        "de00_p90": round(float(np.percentile(de, 90)), 3),
        "de00_mean": round(float(np.mean(de)), 3),
        "flat_mae_rgb": [round(float(diff[:, c].mean()), 2) for c in range(3)],
        "flat_mae_mean": round(float(diff.mean()), 2),
        "edge_rmse": round(float(rmse), 2),
        "luma_ssim": round(float(s), 4)
    }

metrics_table = {
    "pairA": {
        "0_raw": compute_all_metrics(outA_raw, a_ed, a_flat, a_line),
        "1_cc_only": compute_all_metrics(outA_cc, a_ed, a_flat, a_line),
        "2_cc_grad": compute_all_metrics(outA_grad, a_ed, a_flat, a_line),
        "3_full_composite": compute_all_metrics(outA_full, a_ed, a_flat, a_line)
    },
    "pairB": {
        "0_raw": compute_all_metrics(outB_raw, b_ed, b_flat, b_line),
        "1_cc_only": compute_all_metrics(outB_cc, b_ed, b_flat, b_line),
        "2_cc_grad": compute_all_metrics(outB_grad, b_ed, b_flat, b_line),
        "3_full_composite": compute_all_metrics(outB_full, b_ed, b_flat, b_line)
    }
}

with open(f'{OWNER_DIR}/analysis/outputs/q8/final_metrics.json', 'w') as f:
    json.dump(metrics_table, f, indent=2)

print("=== FINAL METRICS ===")
print("Pair A Full:", metrics_table["pairA"]["3_full_composite"])
print("Pair B Full:", metrics_table["pairB"]["3_full_composite"])

# 4. Generate side-by-side comparison images
# Format: Edit | Prediction | Absolute Residual (5x amplified)
def make_sbs(ed_rgb, pred_rgb, mask):
    diff = np.abs(ed_rgb - pred_rgb) * 5.0
    diff = np.clip(diff, 0.0, 1.0)
    sbs = np.hstack([ed_rgb, pred_rgb, diff])
    return (sbs * 255).round().astype(np.uint8)

sbsA = make_sbs(a_ed, outA_full, a_flat)
sbsB = make_sbs(b_ed, outB_full, b_flat)
sbs_full = np.vstack([sbsA, sbsB])
cv2.imwrite(f'{REPORTS_DIR}/side_by_side_comparison.png', cv2.cvtColor(sbs_full, cv2.COLOR_RGB2BGR))
print("Saved side_by_side_comparison.png")
