#!/usr/bin/env python3
"""
Generate complete deliverables for Xenoz CC:
- look_params.json
- look_apply.py
- look.cube (33^3)
- LOOK_SPEC.md
- REPORT.md
- side_by_side_comparison.png
- GLSL shader (MS_xenoz_cc/shader.glsl)
- MotionSalt_CC.kfpack
"""

import os, sys, json, cv2, numpy as np, zipfile, subprocess
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.metrics import structural_similarity as ssim

OWNER_DIR = '/app/keyflaw-look-fit/owners/xenoz'
REPO = '/app/keyflaw-look-fit'
SPEC_DIR = os.path.join(OWNER_DIR, 'spec')
REPORTS_DIR = os.path.join(OWNER_DIR, 'reports')
PACK_DIR = os.path.join(REPO, 'pack')
RELEASES_DIR = os.path.join(REPO, 'releases')

p_cc = np.load(f'{OWNER_DIR}/analysis/outputs/q7/p_opt_cc.npy')
p_gr = np.load(f'{OWNER_DIR}/analysis/outputs/q7/p_opt_gr.npy')

in_b = [float(v) for v in p_cc[0:3]]
span = [float(np.maximum(v, 0.15)) for v in p_cc[3:6]]
in_w = [float(in_b[i] + span[i]) for i in range(3)]
gam = [float(np.exp(np.clip(v, -1.0, 1.0))) for v in p_cc[6:9]]
out_b = [float(v) for v in p_cc[9:12]]
out_w = [float(v) for v in p_cc[12:15]]
toe = [float(v) for v in p_cc[15:18]]
mat = [[float(v) for v in row] for row in p_cc[18:27].reshape(3, 3)]

cyan_lobes = [float(v) for v in p_cc[27:30]]
skin_lobes = [float(v) for v in p_cc[30:33]]
plum_lobes = [float(v) for v in p_cc[33:36]]

grad_y0 = float(p_gr[0])
grad_y1 = float(p_gr[1])
grad_s = [float(v) for v in p_gr[2:5]]

# Canonical flare: soft subtle top-corner ambient glow
flare_canonical = {
    "cx": 0.50,
    "cy": 0.05,
    "rx_frac_h": 0.45,
    "ry_frac_h": 0.35,
    "angle_deg": 0.0,
    "colour_rgb": [0.35, 0.55, 0.95],
    "intensity": 0.12,
    "source_basis": "Subtle soft ambient highlight glow (non-destructive; does not pollute skin or shadow depth)"
}

look_params = {
    "schema_version": "1.1.0",
    "project": "MOTIONSALT Keyflaw Look-Fit",
    "cc_owner": "Xenoz",
    "owner_slug": "xenoz",
    "effect_name": "Xenoz's CC",
    "effect_id": "MS_xenoz_cc",
    "order_of_operations": [
        "1_colour_correction_dade_srgb",
        "2_vertical_multiply_gradient",
        "3_unsharp_mask_25tap_rgb",
        "4_subtle_ambient_haze_flare"
    ],
    "colour_correction": {
        "model": "M2_Dade_srgb",
        "colour_space": "sRGB display-referred [0..1]",
        "levels": {
            "in_black": in_b,
            "in_white": in_w,
            "gamma": gam,
            "out_black": out_b,
            "out_white": out_w
        },
        "shadow_toe": {
            "luma_threshold": 0.28,
            "lift_rgb": toe
        },
        "matrix_3x3": mat,
        "opponent_shaper": {
            "space": "opponent_polar (ou = R - 0.5*(G+B), ov = 0.866025*(G-B), C = sqrt(ou^2 + ov^2))",
            "chroma_gate": {"c_min": 0.015, "c_max": 0.060},
            "cyan_sky_lobe": {"center_deg": 198.0, "kappa": 4.0, "dh_rad": cyan_lobes[0], "dc": cyan_lobes[1], "da": cyan_lobes[2]},
            "warm_skin_lobe": {"center_deg": 30.0, "kappa": 4.0, "dh_rad": skin_lobes[0], "dc": skin_lobes[1], "da": skin_lobes[2]},
            "plum_violet_lobe": {"center_deg": 315.0, "kappa": 3.0, "dh_rad": plum_lobes[0], "dc": plum_lobes[1], "da": plum_lobes[2]}
        }
    },
    "gradient": {
        "type": "H1_vertical_spatial_multiply_gradient",
        "coordinate_reference": "Full frame height [0, 1] (0 = top row, 1 = bottom row)",
        "y0_norm": grad_y0,
        "y1_norm": grad_y1,
        "falloff_curve": "smoothstep",
        "blend_mode": "multiply",
        "strength_rgb": grad_s
    },
    "unsharp": {
        "mode": "rgb",
        "kernel": "single-pass 25-tap (5x5 separable [1,4,6,4,1]/16)",
        "scaling_law": "constant_fraction_of_height",
        "sigma_frac_h": 0.000535,
        "amount": 1.10,
        "threshold_01": 0.00659,
        "threshold_255": 1.68
    },
    "flare": {
        "status": "subtle_ambient_glow",
        "model": "2D anisotropic Gaussian Screen glow",
        "canonical_default_params": flare_canonical
    }
}

# 1. Save look_params.json
with open(os.path.join(SPEC_DIR, 'look_params.json'), 'w', encoding='utf-8') as f:
    json.dump(look_params, f, indent=2)
with open(os.path.join(REPORTS_DIR, 'look_params.json'), 'w', encoding='utf-8') as f:
    json.dump(look_params, f, indent=2)

print('Saved look_params.json successfully.')
