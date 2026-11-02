#!/usr/bin/env python3
"""
Q8 Deliverables Generator & End-to-End Verification:
1. Builds `look_params.json` (canonical machine-readable source of truth in repo root).
2. Regenerates `look.cube` directly from `look_apply.stage2_colour_correction` to guarantee 100% parity.
3. Invokes `python3 look_apply.py` CLI on matched originals and verifies reproduced metrics.
4. Generates exact unit test vectors (28 colour vectors, 8 gradient y-vectors, 8 flare (x,y)-vectors,
   and 21-sample 1D step-edge USM vector at H=720) directly from `look_apply.py`.
5. Renders side-by-side comparison panels (Edited | Prediction | Residual) and Dade foliage swatch strip.
"""
import os
import sys
import json
import subprocess
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.metrics import structural_similarity as ssim

OWNER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO = os.path.abspath(os.path.join(OWNER_DIR, "..", ".."))
sys.path.insert(0, os.path.join(OWNER_DIR, "spec"))
sys.path.insert(0, os.path.join(REPO, "owners", "xenoz", "analysis", "src"))

import look_apply
from q7_dade_refine import (
    LUMA_W, unpack_dade_params, FOLIAGE_H_START0, FOLIAGE_H_START1,
    FOLIAGE_H_END0, FOLIAGE_H_END1, LOBE_DEG, LOBE_COS, LOBE_SIN, LOBE_KAPPA,
)
from q4_gradient import row_residual_y_corr

OUT_Q8 = os.path.join(REPO, "analysis", "outputs", "q8")
os.makedirs(OUT_Q8, exist_ok=True)


def load_rgb01(rel_path: str) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(os.path.join(REPO, rel_path)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def compute_metrics(pred01: np.ndarray, ed01: np.ndarray, flat_m: np.ndarray,
                    valid_m: np.ndarray, edge_m: np.ndarray, de_stride: int = 2) -> dict:
    p_f = np.clip(pred01[flat_m], 0.0, 1.0)
    e_f = np.clip(ed01[flat_m], 0.0, 1.0)
    p_sub, e_sub = p_f[::de_stride], e_f[::de_stride]
    if len(p_sub) > 90000:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(p_sub), 90000, replace=False)
        p_sub, e_sub = p_sub[idx], e_sub[idx]
    lab_p = rgb2lab(p_sub.reshape(-1, 1, 3)).reshape(-1, 3)
    lab_e = rgb2lab(e_sub.reshape(-1, 1, 3)).reshape(-1, 3)
    de = deltaE_ciede2000(lab_p, lab_e)

    mae_rgb = np.mean(np.abs(p_f - e_f), axis=0) * 255.0
    mae_val = np.mean(np.abs(pred01[valid_m] - ed01[valid_m]), axis=0) * 255.0
    edge_rmse = float(np.sqrt(np.mean((pred01[edge_m] - ed01[edge_m]) ** 2)) * 255.0)

    Yp = (np.clip(pred01, 0.0, 1.0) @ LUMA_W.astype(np.float32)).astype(np.float32)
    Ye = (np.clip(ed01, 0.0, 1.0) @ LUMA_W.astype(np.float32)).astype(np.float32)
    _, s_map = ssim(Ye, Yp, data_range=1.0, full=True)
    return {
        "de00_median": round(float(np.median(de)), 4),
        "de00_p90": round(float(np.percentile(de, 90)), 4),
        "de00_mean": round(float(np.mean(de)), 4),
        "flat_mae_rgb_255": [round(float(v), 3) for v in mae_rgb],
        "flat_mae_mean_255": round(float(mae_rgb.mean()), 3),
        "valid_mae_mean_255": round(float(mae_val.mean()), 3),
        "edge_rmse_255": round(edge_rmse, 3),
        "luma_ssim_valid": round(float(s_map[valid_m].mean()), 5),
    }


def add_px_equivs(fp: dict) -> dict:
    out = dict(fp)
    out["pixel_equivalents"] = {
        "pairA_1278x720": {
            "cx_px": round(fp["cx"] * 1278.0, 2),
            "cy_px": round(fp["cy"] * 720.0, 2),
            "rx_px": round(fp["rx_frac_h"] * 720.0, 2),
            "ry_px": round(fp["ry_frac_h"] * 720.0, 2),
        },
        "pairB_edit_1291x720": {
            "cx_px": round(fp["cx"] * 1291.0, 2),
            "cy_px": round(fp["cy"] * 720.0, 2),
            "rx_px": round(fp["rx_frac_h"] * 720.0, 2),
            "ry_px": round(fp["ry_frac_h"] * 720.0, 2),
        },
        "pairB_orig_720x409": {
            "cx_px": round(fp["cx"] * 720.0, 2),
            "cy_px": round(fp["cy"] * 409.0, 2),
            "rx_px": round(fp["rx_frac_h"] * 409.0, 2),
            "ry_px": round(fp["ry_frac_h"] * 409.0, 2),
        },
    }
    return out


def main():
    th = np.load(os.path.join(REPO, "owners/xenoz/analysis/outputs/q7/theta_cc_final.npy"))
    g = np.load(os.path.join(REPO, "owners/xenoz/analysis/outputs/q7/grad_final.npy"))
    q7_sum = json.load(open(os.path.join(REPO, "owners/xenoz/analysis/outputs/q7/q7_summary.json")))
    usm_q5 = json.load(open(os.path.join(REPO, "owners/xenoz/analysis/outputs/q5/usm_q5.json")))

    p = unpack_dade_params(th)
    y0_f = round(float(g[0]), 6)
    y1_f = round(float(min(1.0, g[0] + g[1])), 6)

    # Fit a clean in-frame top-right shared default flare (cx in [0.85, 0.96], cy in [0.04, 0.20])
    # so default zero-flag `look_apply.py` has physically intuitive coordinates AND beats CC-only & Original on both pairs!
    a_ed = load_rgb01("owners/xenoz/inputs/pairA_edited.png")
    a_or = load_rgb01("owners/xenoz/inputs/pairA_original_matched.png")
    a_flat = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairA_flat_interior.png"), 0) > 0
    a_bars = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairA_bars.png"), 0) > 0
    a_cap = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairA_caption.png"), 0) > 0
    a_inv = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairA_invalid_border.png"), 0) > 0
    a_line = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairA_line_edges.png"), 0) > 0
    a_val = ~(a_bars | a_cap | a_inv)
    a_edge = a_line & a_val

    b_ed = load_rgb01("owners/xenoz/inputs/pairB_edited.png")
    b_or = load_rgb01("owners/xenoz/analysis/outputs/aligned/pairB_orig_aligned_720p.png")
    b_flat = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_flat_interior.png"), 0) > 0
    b_bars = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_bars.png"), 0) > 0
    b_inv = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_invalid_border.png"), 0) > 0
    b_line = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_line_edges.png"), 0) > 0
    b_val = ~(b_bars | b_inv)
    yb, xb = np.mgrid[0:720, 0:1291]
    b_edge = b_line & b_val & (xb < 760)
    b_fit_clean = b_flat & (~((xb >= 770) & (xb <= 965)))

    b4_ed = load_rgb01("owners/xenoz/analysis/outputs/aligned/pairB_edit_aligned_409p.png")
    b4_or = load_rgb01("owners/xenoz/inputs/pairB_original_matched.png")
    b4_flat = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_409p_flat_interior.png"), 0) > 0
    b4_bars = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_409p_bars.png"), 0) > 0
    b4_inv = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_409p_invalid_border.png"), 0) > 0
    b4_line = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_409p_line_edges.png"), 0) > 0
    b4_val = ~(b4_bars | b4_inv)
    yb4, xb4 = np.mgrid[0:409, 0:720]
    b4_edge = b4_line & b4_val & (xb4 < 425)

    cc_dict = {
        "model_type": "M2_Dade_srgb",
        "colour_space": "srgb",
        "levels": {
            "in_black": [round(float(v), 6) for v in p["in_black"]],
            "in_white": [round(float(v), 6) for v in p["in_white"]],
            "gamma": [round(float(v), 6) for v in p["gamma"]],
            "out_black": [round(float(v), 6) for v in p["out_black"]],
            "out_white": [round(float(v), 6) for v in p["out_white"]],
        },
        "shadow_toe": {
            "luma_end": 0.28,
            "shadow_lift_rgb": [round(float(v), 6) for v in p["shadow_lift_rgb"]],
        },
        "saturation_equiv": round(float(p["sat"]), 6),
        "matrix_3x3": [[round(float(v), 6) for v in row] for row in p["matrix"]],
        "dade_hue_shaper": {
            "chroma_gate_start": 0.015,
            "chroma_gate_end": 0.060,
            "foliage_window": {
                "h_start0_deg": float(FOLIAGE_H_START0),
                "h_start1_deg": float(FOLIAGE_H_START1),
                "h_end0_deg": float(FOLIAGE_H_END0),
                "h_end1_deg": float(FOLIAGE_H_END1),
                "dh_rad": round(float(p["foliage_dh_rad"]), 6),
                "dh_deg": round(float(np.rad2deg(p["foliage_dh_rad"])), 3),
                "dc_gain": round(float(p["foliage_dc"]), 6),
                "da_luma": round(float(p["foliage_da"]), 6),
            },
            "von_mises_lobes": [
                {
                    "name": nm,
                    "center_deg": float(LOBE_DEG[i]),
                    "cos_center": round(float(LOBE_COS[i]), 6),
                    "sin_center": round(float(LOBE_SIN[i]), 6),
                    "kappa": float(LOBE_KAPPA[i]),
                    "dh_rad": round(float(p["lobe_dh_rad"][i]), 6),
                    "dh_deg": round(float(np.rad2deg(p["lobe_dh_rad"][i])), 3),
                    "dc_gain": round(float(p["lobe_dc"][i]), 6),
                    "da_luma": round(float(p["lobe_da"][i]), 6),
                }
                for i, nm in enumerate(["teal_greens", "cyan_sky", "violet_plum"])
            ],
        },
        "observed_input_range_srgb_0_255": [
            {"channel": "R", "min_255": 16.0, "max_255": 251.0, "extrapolated_below_255": 16.0, "extrapolated_above_255": 251.0},
            {"channel": "G", "min_255": 21.0, "max_255": 253.0, "extrapolated_below_255": 21.0, "extrapolated_above_255": 253.0},
            {"channel": "B", "min_255": 25.0, "max_255": 254.0, "extrapolated_below_255": 25.0, "extrapolated_above_255": 254.0},
        ],
    }

    grad_dict = {
        "hypothesis": "H1_vertical_spatial_multiply_gradient",
        "coordinate_reference": "Full frame height including letterbox bars (normalised y in [0, 1], 0 = top row, 1 = bottom row)",
        "y0_norm": y0_f,
        "y1_norm": y1_f,
        "falloff_curve": "smoothstep",
        "blend_mode": "multiply",
        "strength_rgb": [round(float(x), 6) for x in g[2:5]],
        "strength_luma_equiv": round(float(g[2:5] @ LUMA_W), 6),
        "pixel_rows_at_resolutions": {
            "pairA_1278x720": {"y0_px": round(y0_f * 720.0, 2), "y1_px": round(y1_f * 720.0, 2)},
            "pairB_edit_1291x720": {"y0_px": round(y0_f * 720.0, 2), "y1_px": round(y1_f * 720.0, 2)},
            "pairB_orig_720x409": {"y0_px": round(y0_f * 409.0, 2), "y1_px": round(y1_f * 409.0, 2)},
        },
    }

    usm_dict = {
        "mode": "rgb",
        "colour_space": "gamma-encoded sRGB [0..1] (Stage 1 pre-CC)",
        "kernel": "single-pass 25-tap (5x5 separable [1,4,6,4,1]/16 with bilinear UV offset = vec2(i,j) * sigma_px / resolution)",
        "scaling_law": "constant_fraction_of_height",
        "sigma_frac_h": 0.003473,
        "sigma_px_at_resolutions": {
            "pairA_1278x720": round(0.003473 * 720.0, 4),
            "pairB_edit_1291x720": round(0.003473 * 720.0, 4),
            "pairB_orig_720x409": round(0.003473 * 409.0, 4),
            "fhd_1920x1080": round(0.003473 * 1080.0, 4),
        },
        "amount": 0.82,
        "threshold_01": 0.01433,
        "threshold_255": 3.654,
        "amount_1d_with_nuisance_preblur": round(float(usm_q5["amount"]), 4),
        "edge_profile_rmse_reduction_pct": usm_q5["edge_profile_rmse_reduction_pct"],
    }

    flA_preset = add_px_equivs({
        k: round(float(v), 6) if isinstance(v, (int, float)) else [round(float(x), 6) for x in v]
        for k, v in q7_sum["final_parameters"]["flare_pairA_preset"].items()
    })
    flB_preset = add_px_equivs({
        k: round(float(v), 6) if isinstance(v, (int, float)) else [round(float(x), 6) for x in v]
        for k, v in q7_sum["final_parameters"]["flare_pairB_preset"].items()
    })

    # Fit shared in-frame default flare (cx in [0.85, 0.97], cy in [0.02, 0.18]) WITHOUT rounding inside objective!
    rng = np.random.default_rng(77)
    ya_i, xa_i = np.where(a_flat)
    ia = rng.choice(len(ya_i), 4500, replace=False)
    yb_i, xb_i = np.where(b_fit_clean)
    ib = rng.choice(len(yb_i), 4500, replace=False)

    baseA_3 = look_apply.stage3_gradient(
        look_apply.stage2_colour_correction(look_apply.stage1_unsharp(a_or, usm_dict), cc_dict, 1.0, False),
        grad_dict,
    )
    baseB_3 = look_apply.stage3_gradient(
        look_apply.stage2_colour_correction(look_apply.stage1_unsharp(b_or, usm_dict), cc_dict, 1.0, False),
        grad_dict,
    )

    bA_s, eA_s = baseA_3[ya_i[ia], xa_i[ia]], a_ed[ya_i[ia], xa_i[ia]]
    xhA_s, ynA_s = xa_i[ia] / 720.0, ya_i[ia] / 720.0
    bB_s, eB_s = baseB_3[yb_i[ib], xb_i[ib]], b_ed[yb_i[ib], xb_i[ib]]
    xhB_s, ynB_s = xb_i[ib] / 720.0, yb_i[ib] / 720.0

    def eval_sh_raw(bp, xh, yn, asp, fv):
        cx, cy, rx, ry, ang, r, gg, b = fv
        dx = xh - cx * asp
        dy = yn - cy
        ca, sa = np.cos(ang), np.sin(ang)
        u = (dx * ca + dy * sa) / rx
        v = (-dx * sa + dy * ca) / ry
        w = np.exp(-0.5 * (u * u + v * v))[:, None]
        f = np.clip(w * np.maximum([r, gg, b], 0.0)[None, :], 0.0, 1.0)
        return 1.0 - (1.0 - bp) * (1.0 - f)

    def finalize_sh(fv):
        cx, cy, rx, ry, ang, r, gg, b = fv
        c = np.maximum([r, gg, b], 0.0)
        mx = float(np.max(c))
        col = [round(float(x / mx), 6) for x in c] if mx > 1e-6 else [1.0, 1.0, 1.0]
        return {
            "cx": round(float(cx), 6), "cy": round(float(cy), 6),
            "rx_frac_h": round(float(rx), 6), "ry_frac_h": round(float(ry), 6),
            "angle_deg": round(float(np.rad2deg(ang)), 4),
            "colour_rgb": col, "intensity": round(mx, 6),
        }

    sol_sh = least_squares(
        lambda fv: np.concatenate([
            (eval_sh_raw(bA_s, xhA_s, ynA_s, 1278.0 / 720.0, fv) - eA_s).ravel() * 1.0,
            (eval_sh_raw(bB_s, xhB_s, ynB_s, 1291.0 / 720.0, fv) - eB_s).ravel() * 1.45,
        ]),
        [0.92, 0.08, 0.16, 0.24, -0.35, 0.17, 0.21, 0.12],
        bounds=([0.85, 0.02, 0.10, 0.12, -1.3, 0.0, 0.0, 0.0], [0.98, 0.20, 0.36, 0.40, 1.3, 0.45, 0.45, 0.45]),
        loss="soft_l1",
        f_scale=0.04,
        max_nfev=250,
    )
    fl_default = add_px_equivs(finalize_sh(sol_sh.x))

    look_params = {
        "schema_version": "1.0.0",
        "project": "MOTIONSALT Keyflaw Look-Fit",
        "order_of_operations": [
            "1_unsharp_mask_25tap_rgb",
            "2_colour_correction_dade_srgb",
            "3_vertical_multiply_gradient",
            "4_anisotropic_gaussian_screen_flare",
        ],
        "assumptions": {
            "shader_architecture": "Single-pass GLSL fragment shader (to be confirmed by Keyflaw pack builder)",
            "inputs_available": "Input video frame texture + uniform controls only (no extra LUT/auxiliary textures, no multi-pass)",
            "max_texture_taps": 25,
            "working_colour_space": "Gamma-encoded sRGB [0.0, 1.0]",
            "uv_origin_convention": "Normalised (x, y) in [0, 1] with (0, 0) = top-left and (1, 1) = bottom-right (flip y if host uses bottom-left OpenGL UV origin)",
        },
        "unsharp": usm_dict,
        "colour_correction": cc_dict,
        "gradient": grad_dict,
        "flare": {
            "model": "2D anisotropic rotated Gaussian radial glow",
            "falloff_curve": "gaussian",
            "blend_mode": "screen",
            "global_veil_needed": False,
            "default_preset": "default",
            "presets": {
                "default": fl_default,
                "pairA": flA_preset,
                "pairB": flB_preset,
            },
        },
    }

    params_path = os.path.join(REPO, "spec", "look_params.json")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(look_params, f, indent=2)

    # Regenerate 33x33x33 look.cube directly from look_apply.stage2_colour_correction!
    grid = np.linspace(0.0, 1.0, 33)
    B_g, G_g, R_g = np.meshgrid(grid, grid, grid, indexing="ij")
    lut_in = np.stack([R_g.ravel(), G_g.ravel(), B_g.ravel()], axis=1).astype(np.float32)
    lut_out = look_apply.stage2_colour_correction(lut_in, cc_dict, dade_strength=1.0, clamp_output=True)
    with open(os.path.join(REPO, "spec", "look.cube"), "w", encoding="utf-8") as f:
        f.write('TITLE "MOTIONSALT_Keyflaw_Look_Dade_CC"\n')
        f.write("LUT_3D_SIZE 33\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for r_v, g_v, b_v in lut_out:
            f.write(f"{r_v:.6f} {g_v:.6f} {b_v:.6f}\n")

    # Run look_apply.py via CLI on both matched originals and aligned Pair B!
    cli_runs = [
        ("owners/xenoz/inputs/pairA_original_matched.png", "owners/xenoz/analysis/outputs/q8/pairA_pred_default.png", "default"),
        ("owners/xenoz/inputs/pairA_original_matched.png", "owners/xenoz/analysis/outputs/q8/pairA_pred_scene.png", "pairA"),
        ("owners/xenoz/inputs/pairB_original_matched.png", "owners/xenoz/analysis/outputs/q8/pairB_409p_pred_default.png", "default"),
        ("owners/xenoz/inputs/pairB_original_matched.png", "owners/xenoz/analysis/outputs/q8/pairB_409p_pred_scene.png", "pairB"),
        ("owners/xenoz/analysis/outputs/aligned/pairB_orig_aligned_720p.png", "owners/xenoz/analysis/outputs/q8/pairB_720p_pred_default.png", "default"),
        ("owners/xenoz/analysis/outputs/aligned/pairB_orig_aligned_720p.png", "owners/xenoz/analysis/outputs/q8/pairB_720p_pred_scene.png", "pairB"),
    ]
    for inp_rel, out_rel, preset in cli_runs:
        cmd = [sys.executable, os.path.join(REPO, "spec", "look_apply.py"), os.path.join(REPO, inp_rel), os.path.join(REPO, out_rel), "--flare-preset", preset]
        subprocess.run(cmd, check=True)

    # Re-evaluate complete stage progression metrics using exact look_apply functions + CLI outputs!
    def eval_stages(or_im, ed_im, fm, vm, em, scene_preset_name, cli_def_rel, cli_scn_rel):
        s0 = or_im
        s1_cc = look_apply.apply_look(or_im, look_params, enable_unsharp=False, enable_cc=True, enable_gradient=False, enable_flare=False)
        s2_cg = look_apply.apply_look(or_im, look_params, enable_unsharp=False, enable_cc=True, enable_gradient=True, enable_flare=False)
        s3_cgu = look_apply.apply_look(or_im, look_params, enable_unsharp=True, enable_cc=True, enable_gradient=True, enable_flare=False)
        s4_def = load_rgb01(cli_def_rel)
        s5_scn = load_rgb01(cli_scn_rel)
        st = {
            "0_original": compute_metrics(s0, ed_im, fm, vm, em),
            "1_cc_only": compute_metrics(s1_cc, ed_im, fm, vm, em),
            "2_cc_plus_gradient": compute_metrics(s2_cg, ed_im, fm, vm, em),
            "3_cc_grad_plus_unsharp": compute_metrics(s3_cgu, ed_im, fm, vm, em),
            "4_full_composite_default_flare": compute_metrics(s4_def, ed_im, fm, vm, em),
            "5_full_composite_scene_flare": compute_metrics(s5_scn, ed_im, fm, vm, em),
        }
        return st, s4_def, s5_scn

    m_A, pA_def, pA_scn = eval_stages(a_or, a_ed, a_flat, a_val, a_edge, "pairA", "owners/xenoz/analysis/outputs/q8/pairA_pred_default.png", "owners/xenoz/analysis/outputs/q8/pairA_pred_scene.png")
    m_B_all, pB_def, pB_scn = eval_stages(b_or, b_ed, b_flat, b_val, b_edge, "pairB", "owners/xenoz/analysis/outputs/q8/pairB_720p_pred_default.png", "owners/xenoz/analysis/outputs/q8/pairB_720p_pred_scene.png")
    m_B_nb, _, _ = eval_stages(b_or, b_ed, b_fit_clean, b_val & (~((xb >= 770) & (xb <= 965))), b_edge, "pairB", "owners/xenoz/analysis/outputs/q8/pairB_720p_pred_default.png", "owners/xenoz/analysis/outputs/q8/pairB_720p_pred_scene.png")
    m_B4, pB4_def, pB4_scn = eval_stages(b4_or, b4_ed, b4_flat, b4_val, b4_edge, "pairB", "owners/xenoz/analysis/outputs/q8/pairB_409p_pred_default.png", "owners/xenoz/analysis/outputs/q8/pairB_409p_pred_scene.png")

    # Verify row-mean y correlation after full look on both pairs!
    ya_g, xa_g = np.mgrid[0:720, 0:1278]
    corr_A_post = row_residual_y_corr(pA_scn, a_ed, a_flat)
    corr_A_left_unflared = row_residual_y_corr(pA_scn, a_ed, a_flat & (xa_g < 700))
    corr_B_post = row_residual_y_corr(pB_scn, b_ed, b_fit_clean)
    print("Post-composite row-mean y correlation: Pair A =", round(corr_A_post["corr_luma_y"], 4), "(left unflared:", round(corr_A_left_unflared["corr_luma_y"], 4), ")| Pair B =", round(corr_B_post["corr_luma_y"], 4))

    # Generate side-by-side panels (Edited | Prediction | Residual) for Pair A, Pair B (720p), Pair B (409p)
    def save_side_by_side(ed_im, pr_im, v_mask, bars_mask, title_prefix, out_name):
        fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.2), dpi=140)
        ed_disp = np.where(bars_mask[..., None], 0.0, np.clip(ed_im, 0.0, 1.0))
        pr_disp = np.where(bars_mask[..., None], 0.0, np.clip(pr_im, 0.0, 1.0))
        axes[0].imshow(ed_disp)
        axes[0].set_title(f"{title_prefix} — Edited Target", fontsize=10.5, fontweight="bold")
        axes[0].axis("off")

        axes[1].imshow(pr_disp)
        axes[1].set_title(f"{title_prefix} — Look-Fit Prediction (look_apply.py)", fontsize=10.5, fontweight="bold")
        axes[1].axis("off")

        err_255 = np.mean(np.abs(pr_im - ed_im), axis=-1) * 255.0
        err_masked = np.where(v_mask, err_255, 0.0)
        im_hm = axes[2].imshow(err_masked, cmap="magma", vmin=0.0, vmax=45.0)
        axes[2].set_title(f"Abs Residual (Valid MAE = {err_255[v_mask].mean():.2f} / 255)", fontsize=10.5, fontweight="bold")
        axes[2].axis("off")
        plt.colorbar(im_hm, ax=axes[2], fraction=0.042, pad=0.02, label="|Pred - Edit| (0..255)")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_Q8, out_name))
        plt.close(fig)

    save_side_by_side(a_ed, pA_scn, a_val, a_bars, "Pair A (1278x720)", "pairA_side_by_side.png")
    save_side_by_side(b_ed, pB_scn, b_val, b_bars, "Pair B (1291x720 Aligned)", "pairB_side_by_side.png")
    save_side_by_side(b4_ed, pB4_scn, b4_val, b4_bars, "Pair B (720x409 Native)", "pairB_409p_side_by_side.png")

    # Generate Dade Foliage & Palette Swatch Comparison Figure!
    swatch_defs = [
        ("Skin Warm", [234, 189, 147]),
        ("Straw Gold", [241, 198, 119]),
        ("Blonde/Shirt", [245, 219, 65]),
        ("Yellow-Grass", [178, 204, 72]),
        ("Meadow Grass", [138, 204, 72]),
        ("Lush Foliage", [107, 204, 72]),
        ("Cloak Green", [68, 108, 94]),
        ("Chopper Cyan", [120, 180, 195]),
        ("Sky Blue", [98, 183, 247]),
        ("Purple Sash", [134, 92, 174]),
        ("Dark Hair", [19, 27, 37]),
    ]
    sw_in = np.array([s[1] for s in swatch_defs], dtype=np.float32) / 255.0
    sw_nodade = look_apply.stage2_colour_correction(sw_in, cc_dict, dade_strength=0.0, clamp_output=True)
    sw_dade = look_apply.stage2_colour_correction(sw_in, cc_dict, dade_strength=1.0, clamp_output=True)

    fig, ax = plt.subplots(figsize=(13.5, 3.6), dpi=140)
    strip = np.zeros((3, len(swatch_defs), 3), dtype=np.float32)
    strip[0] = sw_in
    strip[1] = sw_nodade
    strip[2] = sw_dade
    ax.imshow(strip, aspect="auto")
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["1. Input (Ungraded)", "2. Base Matrix Only (dade=0)", "3. Full Dade CC (dade=1.0)"], fontsize=9.5, fontweight="bold")
    ax.set_xticks(range(len(swatch_defs)))
    ax.set_xticklabels([s[0] for s in swatch_defs], rotation=22, ha="right", fontsize=9)
    for r_i in range(3):
        for c_i in range(len(swatch_defs)):
            rgb_u8 = np.round(strip[r_i, c_i] * 255.0).astype(int)
            lum_v = float(strip[r_i, c_i] @ LUMA_W)
            txt_col = "black" if lum_v > 0.48 else "white"
            ax.text(c_i, r_i, f"{rgb_u8[0]},{rgb_u8[1]},{rgb_u8[2]}", ha="center", va="center", color=txt_col, fontsize=7.5, fontweight="bold")
    ax.set_title("Magic Bullet Looks 'Dade' Hue-Chroma Shaper Verification: Warm Golds Preserved, Yellow-Green Grass -> Bluish-Green", fontsize=10.5, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_Q8, "dade_foliage_swatch_comparison.png"))
    plt.close(fig)

    # =========================================================================
    # UNIT TEST VECTORS (computed directly from look_apply.py functions!)
    # =========================================================================
    # 1. 28 Colour-Stage Test Vectors
    cc_test_inputs_255 = [
        ("Grey 0 (Black)", [0, 0, 0]),
        ("Grey 16", [16, 16, 16]),
        ("Grey 32", [32, 32, 32]),
        ("Grey 64", [64, 64, 64]),
        ("Grey 96", [96, 96, 96]),
        ("Grey 128 (Mid)", [128, 128, 128]),
        ("Grey 160", [160, 160, 160]),
        ("Grey 192", [192, 192, 192]),
        ("Grey 224", [224, 224, 224]),
        ("Grey 255 (White)", [255, 255, 255]),
        ("Primary Red", [255, 0, 0]),
        ("Primary Green", [0, 255, 0]),
        ("Primary Blue", [0, 0, 255]),
        ("Secondary Yellow", [255, 255, 0]),
        ("Secondary Cyan", [0, 255, 255]),
        ("Secondary Magenta", [255, 0, 255]),
        ("Forehead Bright Skin", [239, 198, 163]),
        ("Cheek Mid Skin", [234, 189, 147]),
        ("Neck Deep Shadow", [156, 98, 67]),
        ("Straw Hat Gold", [241, 198, 119]),
        ("Nami/Sanji Bright Yellow", [245, 219, 65]),
        ("Sunlit Yellow-Green Grass", [178, 204, 72]),
        ("Meadow Grass (Dade Shift)", [138, 204, 72]),
        ("Lush Foliage (Dade Shift)", [107, 204, 72]),
        ("Foreground Cloak Teal-Green", [68, 108, 94]),
        ("Sky Blue", [98, 183, 247]),
        ("Chopper Hat Cyan", [120, 180, 195]),
        ("Luffy Sash Purple", [134, 92, 174]),
        ("Dark Hair Shadow", [19, 27, 37]),
    ]
    cc_vectors = []
    for label, rgb255 in cc_test_inputs_255:
        x01 = np.array([rgb255], dtype=np.float32) / 255.0
        y01 = look_apply.stage2_colour_correction(x01, cc_dict, dade_strength=1.0, clamp_output=True)[0]
        cc_vectors.append({
            "label": label,
            "in_255": rgb255,
            "in_01": [round(float(v), 6) for v in x01[0]],
            "out_01": [round(float(v), 6) for v in y01],
            "out_255": [int(round(float(v) * 255.0)) for v in y01],
        })

    # 2. 8 Vertical Gradient Test Vectors (for reference input cc_rgb = [0.80, 0.70, 0.60])
    grad_y_pts = [0.00, 0.14, 0.25, 0.40, 0.55, 0.70, 0.76, 1.00]
    grad_vectors = []
    ref_cc = np.array([0.80, 0.70, 0.60], dtype=np.float64)
    for y_n in grad_y_pts:
        r_val = float(look_apply.smoothstep(grad_dict["y0_norm"], grad_dict["y1_norm"], np.array([y_n]))[0])
        mult = 1.0 - r_val * np.array(grad_dict["strength_rgb"], dtype=np.float64)
        out_g = np.clip(ref_cc * mult, 0.0, 1.0)
        grad_vectors.append({
            "y_norm": y_n,
            "smoothstep_r": round(r_val, 6),
            "multiplier_rgb": [round(float(m), 6) for m in mult],
            "out_for_0.8_0.7_0.6": [round(float(o), 6) for o in out_g],
        })

    # 3. 8 Haze Flare Test Vectors on 1280x720 (aspect = 16/9 = 1.777778) for base_rgb = [0.15, 0.18, 0.22]
    flare_xy_pts = [
        (0.92, 0.09),
        (0.96, 0.19),
        (0.85, 0.10),
        (0.75, 0.20),
        (0.90, 0.35),
        (0.60, 0.15),
        (0.50, 0.50),
        (0.10, 0.85),
    ]
    flare_vectors = []
    base_pt = np.array([0.15, 0.18, 0.22], dtype=np.float64)
    W_ref, H_ref = 1280.0, 720.0
    for fx, fy in flare_xy_pts:
        row_entry = {"x_norm": fx, "y_norm": fy}
        for p_key, fp in [("default", fl_default), ("pairA", flA_preset)]:
            dx_h = (fx * W_ref - fp["cx"] * W_ref) / H_ref
            dy_h = (fy * H_ref - fp["cy"] * H_ref) / H_ref
            ang = np.deg2rad(fp["angle_deg"])
            ca, sa = np.cos(ang), np.sin(ang)
            u = (dx_h * ca + dy_h * sa) / fp["rx_frac_h"]
            v = (-dx_h * sa + dy_h * ca) / fp["ry_frac_h"]
            w = float(np.exp(-0.5 * (u * u + v * v)))
            f_rgb = np.clip(fp["intensity"] * w * np.array(fp["colour_rgb"]), 0.0, 1.0)
            s_out = 1.0 - (1.0 - base_pt) * (1.0 - f_rgb)
            row_entry[f"{p_key}_flare_rgb"] = [round(float(z), 6) for z in f_rgb]
            row_entry[f"{p_key}_screen_out"] = [round(float(z), 6) for z in s_out]
        flare_vectors.append(row_entry)

    # 4. 1D Step-Edge Unsharp Test Vector at H = 720 (W = 21, H = 720 constant vertical edge at x = 10)
    # Create a 720 x 21 image where cols 0..9 = 0.20 and cols 10..20 = 0.80, run exact look_apply.stage1_unsharp!
    step_1d_in = np.array([0.20] * 10 + [0.80] * 11, dtype=np.float32)
    step_img = np.broadcast_to(step_1d_in[None, :, None], (720, 21, 3)).copy()
    blur_img = look_apply.blur_25tap_2d(step_img, usm_dict["sigma_frac_h"] * 720.0)
    usm_img = look_apply.stage1_unsharp(step_img, usm_dict)
    usm_1d_vector = {
        "stated_height_px": 720,
        "sigma_px": round(usm_dict["sigma_frac_h"] * 720.0, 6),
        "amount": usm_dict["amount"],
        "threshold_01": usm_dict["threshold_01"],
        "x_indices": list(range(21)),
        "input_1d": [round(float(v), 6) for v in step_img[360, :, 0]],
        "blur25_1d": [round(float(v), 6) for v in blur_img[360, :, 0]],
        "usm_out_1d": [round(float(v), 6) for v in usm_img[360, :, 0]],
    }

    verified_bundle = {
        "metrics": {
            "pairA_720p": m_A,
            "pairB_720p_all_flat": m_B_all,
            "pairB_720p_excluding_ai_bush": m_B_nb,
            "pairB_409p_native_orig_scale": m_B4,
        },
        "post_composite_row_y_corr": {
            "pairA": round(float(corr_A_post["corr_luma_y"]), 4),
            "pairA_left_unflared": round(float(corr_A_left_unflared["corr_luma_y"]), 4),
            "pairB": round(float(corr_B_post["corr_luma_y"]), 4),
        },
        "test_vectors": {
            "colour_stage_29_vectors": cc_vectors,
            "gradient_stage_8_vectors": grad_vectors,
            "flare_stage_8_vectors": flare_vectors,
            "unsharp_stage_1d_step_H720": usm_1d_vector,
        },
    }
    with open(os.path.join(OUT_Q8, "verified_vectors_and_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(verified_bundle, f, indent=2)

    print("=== VERIFIED METRICS FROM CLI look_apply.py ===")
    for ds_name, ds_m in verified_bundle["metrics"].items():
        print(f"[{ds_name}]")
        for st_k, st_v in ds_m.items():
            print(f"  {st_k:34s}: DE00_med={st_v['de00_median']:.4f}, p90={st_v['de00_p90']:.4f}, MAE={st_v['flat_mae_mean_255']:.3f}, Edge={st_v['edge_rmse_255']:.3f}, SSIM={st_v['luma_ssim_valid']:.5f}")


if __name__ == "__main__":
    main()
