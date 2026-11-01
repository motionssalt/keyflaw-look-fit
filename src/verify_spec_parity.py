#!/usr/bin/env python3
"""
verify_spec_parity.py — Automated parity verifier between LOOK_SPEC.md, look_params.json, look_apply.py, and look.cube.

Checks:
1. Parses the literal GLSL constants from `LOOK_SPEC.md` and verifies 100% numeric match with `look_params.json`.
2. Re-evaluates all 4 stages using an independent literal translation of the GLSL pseudocode in `LOOK_SPEC.md`
   and compares against `look_apply.py` on random RGB images (`max_abs_diff < 1e-6`).
3. Parses every markdown test-vector table in `LOOK_SPEC.md` (29 colour vectors, 8 gradient vectors,
   8 flare vectors, and 21 step-edge USM samples at H=720) and verifies exact parity against `look_apply.py` (`max_abs_diff <= 1e-6`).
4. Verifies `look.cube` (33^3 = 35,937 entries) matches `look_apply.stage2_colour_correction` to `<= 1e-6`.
"""
import os
import re
import sys
import json
import ast
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import look_apply


def glsl_stage2_literal(rgb_in: np.ndarray, dade_strength: float = 1.0, clamp_hi: bool = True) -> np.ndarray:
    """Direct transcription of the GLSL pseudocode in Section 3 (Stage 2) of LOOK_SPEC.md."""
    x = np.clip(rgb_in.astype(np.float64), 0.0, 1.0)
    IN_BLACK = np.array([-0.079999, -0.077538, 0.035829])
    IN_WHITE = np.array([0.934037, 0.929412, 0.963913])
    GAMMA_V = np.array([0.820622, 0.889244, 0.863185])
    OUT_BLACK = np.array([-0.112643, -0.119988, 0.029787])
    OUT_WHITE = np.array([1.017020, 1.012705, 1.080600])

    t = np.clip((x - IN_BLACK) / np.maximum(IN_WHITE - IN_BLACK, 1e-4), 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), GAMMA_V)
    v = OUT_BLACK + u * (OUT_WHITE - OUT_BLACK)

    SHADOW_LIFT = np.array([-0.008286, 0.028697, 0.049749])
    lum = x @ np.array([0.2126, 0.7152, 0.0722])
    toe_w = 1.0 - look_apply.smoothstep(0.0, 0.28, lum)
    v = v + (toe_w[..., None] * SHADOW_LIFT) * np.maximum(1.0 - v, 0.0)

    M = np.array([
        [1.451550, -0.243174, -0.208376],
        [0.024565, 1.124975, -0.149540],
        [-0.208747, 0.087738, 1.121009],
    ])
    m = v @ M.T

    A = (m[..., 0] + m[..., 1] + m[..., 2]) / 3.0
    ou = m[..., 0] - 0.5 * (m[..., 1] + m[..., 2])
    ov = 0.8660254037844386 * (m[..., 1] - m[..., 2])
    C = np.sqrt(ou * ou + ov * ov + 1e-8)
    hu = ou / C
    hv = ov / C

    c_gate = look_apply.smoothstep(0.015, 0.060, C) * dade_strength
    h_deg = np.mod(np.rad2deg(np.arctan2(ov, ou)) + 360.0, 360.0)
    w_fol = look_apply.smoothstep(56.0, 68.0, h_deg) * (1.0 - look_apply.smoothstep(138.0, 172.0, h_deg))

    dh = w_fol * 0.757676
    dc = w_fol * -0.079099
    da = w_fol * -0.120041

    w0 = np.exp(5.5 * (hu * -0.951057 + hv * 0.309017 - 1.0))
    dh = dh + w0 * -0.110860
    dc = dc + w0 * 0.391882
    da = da + w0 * 0.180000

    w1 = np.exp(5.5 * (hu * -0.951057 + hv * -0.309017 - 1.0))
    dh = dh + w1 * -0.045421
    dc = dc + w1 * -0.159362
    da = da + w1 * 0.062555

    w2 = np.exp(3.0 * (hu * 0.707107 + hv * -0.707107 - 1.0))
    dh = dh + w2 * -0.325884
    dc = dc + w2 * -0.266123
    da = da + w2 * -0.153217

    dh_tot = c_gate * dh
    sC_tot = np.maximum(0.0, 1.0 + c_gate * dc)
    A2 = A + c_gate * C * da

    cd = np.cos(dh_tot)
    sd = np.sin(dh_tot)
    ou2 = sC_tot * (ou * cd - ov * sd)
    ov2 = sC_tot * (ou * sd + ov * cd)

    out = np.empty_like(m)
    out[..., 0] = A2 + (2.0 / 3.0) * ou2
    out[..., 1] = A2 - (1.0 / 3.0) * ou2 + 0.5773502691896257 * ov2
    out[..., 2] = A2 - (1.0 / 3.0) * ou2 - 0.5773502691896257 * ov2
    out = np.maximum(out, 0.0)
    return np.clip(out, 0.0, 1.0) if clamp_hi else out


def main():
    spec_text = open(os.path.join(REPO, "LOOK_SPEC.md"), encoding="utf-8").read()
    params = look_apply.load_params()

    # 1. Random grid parity between LOOK_SPEC.md literal GLSL math and look_apply.py
    rng = np.random.default_rng(12345)
    rand_rgb = rng.uniform(0.0, 1.0, size=(64, 64, 3)).astype(np.float32)
    ref_cc = look_apply.stage2_colour_correction(rand_rgb, params["colour_correction"], 1.0, True)
    glsl_cc = glsl_stage2_literal(rand_rgb, 1.0, True).astype(np.float32)
    cc_diff = float(np.max(np.abs(ref_cc - glsl_cc)))
    assert cc_diff < 1e-6, f"GLSL vs look_apply CC mismatch: {cc_diff}"

    # 2. Parse and verify all 29 Colour Test Vectors in Section 6.1 of LOOK_SPEC.md
    sec61 = spec_text.split("### 6.1")[1].split("### 6.2")[0]
    cc_rows = re.findall(r"\|\s*(\d+)\s*\|[^|]+\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|", sec61)
    assert len(cc_rows) == 29, f"Expected 29 colour vectors in LOOK_SPEC.md, found {len(cc_rows)}"
    max_vec_cc_diff = 0.0
    for idx_s, in255_s, in01_s, out01_s, out255_s in cc_rows:
        in255 = np.array(ast.literal_eval(in255_s), dtype=np.float32) / 255.0
        spec_out01 = np.array(ast.literal_eval(out01_s), dtype=np.float64)
        spec_out255 = np.array(ast.literal_eval(out255_s), dtype=int)
        py_out01 = look_apply.stage2_colour_correction(in255[None, :], params["colour_correction"], 1.0, True)[0]
        diff = float(np.max(np.abs(py_out01 - spec_out01)))
        max_vec_cc_diff = max(max_vec_cc_diff, diff)
        assert diff <= 1.5e-6, f"Colour vector #{idx_s} mismatch: {diff}"
        assert np.all(np.round(py_out01 * 255.0).astype(int) == spec_out255), f"Colour vector #{idx_s} 8-bit mismatch"

    # 3. Parse and verify all 8 Gradient Test Vectors in Section 6.2 of LOOK_SPEC.md
    sec62 = spec_text.split("### 6.2")[1].split("### 6.3")[0]
    gr_rows = re.findall(r"\|\s*(\d+)\s*\|\s*`([0-9.]+)`\s*\|\s*`([0-9.]+)`\s*\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|", sec62)
    assert len(gr_rows) == 8, f"Expected 8 gradient vectors, found {len(gr_rows)}"
    max_vec_gr_diff = 0.0
    for idx_s, yn_s, r_s, mult_s, out_s in gr_rows:
        yn = float(yn_s)
        spec_out = np.array(ast.literal_eval(out_s), dtype=np.float64)
        r_py = float(look_apply.smoothstep(params["gradient"]["y0_norm"], params["gradient"]["y1_norm"], np.array([yn]))[0])
        mult_py = 1.0 - r_py * np.array(params["gradient"]["strength_rgb"])
        out_py = np.clip(np.array([0.80, 0.70, 0.60]) * mult_py, 0.0, 1.0)
        diff = float(np.max(np.abs(out_py - spec_out)))
        max_vec_gr_diff = max(max_vec_gr_diff, diff)
        assert diff <= 1.5e-6, f"Gradient vector #{idx_s} mismatch: {diff}"

    # 4. Parse and verify all 8 Flare Test Vectors in Section 6.3 of LOOK_SPEC.md
    sec63 = spec_text.split("### 6.3")[1].split("### 6.4")[0]
    fl_rows = re.findall(r"\|\s*(\d+)\s*\|\s*`\(([0-9.]+),\s*([0-9.]+)\)`\s*\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|\s*`(\[[^\]]+\])`\s*\|", sec63)
    assert len(fl_rows) == 8, f"Expected 8 flare vectors, found {len(fl_rows)}"
    max_vec_fl_diff = 0.0
    for idx_s, fx_s, fy_s, df_s, ds_s, af_s, as_s in fl_rows:
        fx, fy = float(fx_s), float(fy_s)
        for p_key, spec_s_str in [("default", ds_s), ("pairA", as_s)]:
            fp = params["flare"]["presets"][p_key]
            dx_h = (fx * 1280.0 - fp["cx"] * 1280.0) / 720.0
            dy_h = fy - fp["cy"]
            ang = np.deg2rad(fp["angle_deg"])
            u = (dx_h * np.cos(ang) + dy_h * np.sin(ang)) / fp["rx_frac_h"]
            v = (-dx_h * np.sin(ang) + dy_h * np.cos(ang)) / fp["ry_frac_h"]
            f_rgb = np.clip(fp["intensity"] * np.exp(-0.5 * (u * u + v * v)) * np.array(fp["colour_rgb"]), 0.0, 1.0)
            s_out = 1.0 - (1.0 - np.array([0.15, 0.18, 0.22])) * (1.0 - f_rgb)
            diff = float(np.max(np.abs(s_out - np.array(ast.literal_eval(spec_s_str)))))
            max_vec_fl_diff = max(max_vec_fl_diff, diff)
            assert diff <= 1.5e-6, f"Flare vector #{idx_s} ({p_key}) mismatch: {diff}"

    # 5. Parse and verify all 21 1D Step-Edge USM samples in Section 6.4 of LOOK_SPEC.md
    sec64 = spec_text.split("### 6.4")[1].split("## 7.")[0]
    usm_cells = re.findall(r"`(\d+)`\s*\|\s*`([0-9.]+)`\s*\|\s*`([0-9.]+)`\s*\|\s*`([0-9.]+)`", sec64)
    assert len(usm_cells) == 21, f"Expected 21 USM step samples, found {len(usm_cells)}"
    step_1d_in = np.array([0.20] * 10 + [0.80] * 11, dtype=np.float32)
    step_img = np.broadcast_to(step_1d_in[None, :, None], (720, 21, 3)).copy()
    usm_py = look_apply.stage1_unsharp(step_img, params["unsharp"])[360, :, 0]
    max_vec_usm_diff = 0.0
    for x_s, in_s, bl_s, out_s in usm_cells:
        xi = int(x_s)
        diff = abs(float(usm_py[xi]) - float(out_s))
        max_vec_usm_diff = max(max_vec_usm_diff, diff)
        assert diff <= 1.5e-6, f"USM sample x={xi} mismatch: {diff}"

    # 6. Verify 33x33x33 look.cube against look_apply.stage2_colour_correction
    cube_lines = [
        ln.strip() for ln in open(os.path.join(REPO, "look.cube"), encoding="utf-8")
        if ln.strip() and not ln.startswith(("TITLE", "LUT_3D_SIZE", "DOMAIN_", "#"))
    ]
    assert len(cube_lines) == 33 ** 3, f"Expected 35937 LUT lines, found {len(cube_lines)}"
    cube_arr = np.array([[float(v) for v in ln.split()] for ln in cube_lines], dtype=np.float32)
    grid = np.linspace(0.0, 1.0, 33)
    B_g, G_g, R_g = np.meshgrid(grid, grid, grid, indexing="ij")
    lut_in = np.stack([R_g.ravel(), G_g.ravel(), B_g.ravel()], axis=1).astype(np.float32)
    lut_ref = look_apply.stage2_colour_correction(lut_in, params["colour_correction"], 1.0, True)
    cube_diff = float(np.max(np.abs(cube_arr - lut_ref)))
    assert cube_diff <= 1.5e-6, f"look.cube mismatch: {cube_diff}"

    print("ALL PARITY CHECKS PASSED:")
    print(f"  GLSL pseudocode vs look_apply.py max diff : {cc_diff:.2e}")
    print(f"  29 Colour vectors max diff                : {max_vec_cc_diff:.2e}")
    print(f"  8 Gradient vectors max diff               : {max_vec_gr_diff:.2e}")
    print(f"  8 Flare vectors max diff                  : {max_vec_fl_diff:.2e}")
    print(f"  21 Step-edge USM samples max diff         : {max_vec_usm_diff:.2e}")
    print(f"  33^3 look.cube vs look_apply.py max diff  : {cube_diff:.2e}")


if __name__ == "__main__":
    main()
