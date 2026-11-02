#!/usr/bin/env python3
"""
look_apply.py — Reference ground-truth implementation of LOOK_SPEC.md for MOTIONSALT / Keyflaw.

Usage:
    python look_apply.py in.png out.png
    python look_apply.py in.png out.png --flare-preset pairA
    python look_apply.py in.png out.png --flare-preset pairB
    python look_apply.py in.png out.png --dade-strength 1.0 --master-intensity 1.0

Reads all parameters from `look_params.json` (in the same directory by default) and applies
the exact 4-stage single-pass pipeline in gamma-encoded sRGB [0, 1]:
  Stage 1: 25-tap (5x5 separable [1,4,6,4,1]/16) RGB Unsharp Mask (radius = sigma_frac_h * H)
  Stage 2: Dade Colour Correction (Levels + Cool Slate Shadow Toe + 3x3 Matrix + Closed-Form Opponent Hue-Chroma Shaper)
  Stage 3: Vertical Spatial Multiply Gradient (smoothstep from y0_norm to y1_norm)
  Stage 4: 2D Anisotropic Rotated Gaussian Screen Haze Flare
"""
import os
import sys
import json
import argparse
import cv2
import numpy as np

LUMA_W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
SQRT3_2 = 0.8660254037844386
INV_SQRT3 = 0.5773502691896257

W1D_5 = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32) / 16.0
K2D_25 = np.outer(W1D_5, W1D_5).astype(np.float32)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    span = max(float(edge1 - edge0), 1e-6)
    t = np.clip((x - edge0) / span, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def blur_25tap_2d(img01: np.ndarray, sigma_px: float) -> np.ndarray:
    """
    Exact single-pass 25-tap (5x5) bilinear-offset stencil matching GLSL:
      offset_uv(i, j) = vec2(i, j) * sigma_px / vec2(W, H),  i, j in {-2, -1, 0, 1, 2}
      weights = outer([1, 4, 6, 4, 1] / 16, [1, 4, 6, 4, 1] / 16)
    """
    if sigma_px <= 1e-5:
        return img01.astype(np.float32).copy()
    H, W = img01.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    src = img01.astype(np.float32)
    acc = np.zeros_like(src, dtype=np.float32)
    for j_idx, j in enumerate((-2, -1, 0, 1, 2)):
        ym = np.clip(yy + j * sigma_px, 0.0, H - 1.0)
        for i_idx, i in enumerate((-2, -1, 0, 1, 2)):
            xm = np.clip(xx + i * sigma_px, 0.0, W - 1.0)
            w = float(K2D_25[j_idx, i_idx])
            acc += w * cv2.remap(src, xm, ym, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return acc


def stage1_unsharp(img01: np.ndarray, usm_params: dict) -> np.ndarray:
    """Stage 1: Resolution-independent 25-tap RGB Unsharp Mask with soft coring threshold."""
    amount = float(usm_params["amount"])
    sigma_frac_h = float(usm_params["sigma_frac_h"])
    threshold = float(usm_params["threshold_01"])
    H = img01.shape[0]
    sigma_px = sigma_frac_h * float(H)
    if amount <= 1e-6 or sigma_px <= 1e-5:
        return np.clip(img01, 0.0, 1.0).astype(np.float32)

    blurred = blur_25tap_2d(img01, sigma_px)
    d = img01.astype(np.float32) - blurred
    if threshold > 1e-7:
        d = np.sign(d) * np.maximum(np.abs(d) - threshold, 0.0)
    return np.clip(img01.astype(np.float32) + amount * d, 0.0, 1.0)


def stage2_colour_correction(
    img01: np.ndarray,
    cc_params: dict,
    dade_strength: float = 1.0,
    clamp_output: bool = False,
) -> np.ndarray:
    """
    Stage 2: Closed-form Dade Colour Correction in gamma-encoded sRGB.
      2a. Per-channel Levels: in_black, in_white, gamma, out_black, out_white
      2b. Cool Dade Slate-Blue Shadow Toe (smoothstep 0..luma_end on input luma)
      2c. 3x3 Base Colour Matrix
      2d. Closed-Form Opponent-Polar Dade Hue-Chroma Shaper (windowed foliage yellow-green ->
          bluish-green gate + 3 smooth von-Mises hue lobes for teal, cyan, and violet)
    Note: When followed immediately by Stage 3 (Multiply Gradient) inside a single-pass shader,
    unclamped highlight headroom (> 1.0) is preserved into Stage 3 and clamped after Stage 3.
    When evaluated standalone (e.g. LUT export or CC unit test vectors), set clamp_output=True.
    """
    orig_shape = img01.shape
    x = np.clip(img01.reshape(-1, 3).astype(np.float64), 0.0, 1.0)

    lv = cc_params["levels"]
    in_black = np.asarray(lv["in_black"], dtype=np.float64)
    in_white = np.asarray(lv["in_white"], dtype=np.float64)
    gamma = np.asarray(lv["gamma"], dtype=np.float64)
    out_black = np.asarray(lv["out_black"], dtype=np.float64)
    out_white = np.asarray(lv["out_white"], dtype=np.float64)

    # 2a. Per-channel Levels
    span = np.maximum(in_white - in_black, 1e-4)
    t = np.clip((x - in_black[None, :]) / span[None, :], 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), gamma[None, :])
    v = out_black[None, :] + u * (out_white - out_black)[None, :]

    # 2b. Dade Cool Slate Shadow Toe
    toe_cfg = cc_params["shadow_toe"]
    luma_end = float(toe_cfg["luma_end"])
    sh_lift = np.asarray(toe_cfg["shadow_lift_rgb"], dtype=np.float64)
    lum = x @ LUMA_W
    toe_w = 1.0 - smoothstep(0.0, luma_end, lum)
    v = v + (toe_w[:, None] * sh_lift[None, :]) * np.maximum(1.0 - v, 0.0)

    # 2c. 3x3 Base Colour Matrix
    M = np.asarray(cc_params["matrix_3x3"], dtype=np.float64)
    m = v @ M.T

    # 2d. Closed-Form Dade Opponent-Polar Hue-Chroma Shaper
    shaper = cc_params["dade_hue_shaper"]
    A = (m[:, 0] + m[:, 1] + m[:, 2]) * (1.0 / 3.0)
    ou = m[:, 0] - 0.5 * (m[:, 1] + m[:, 2])
    ov = SQRT3_2 * (m[:, 1] - m[:, 2])
    C = np.sqrt(ou * ou + ov * ov + 1e-8)
    hu = ou / C
    hv = ov / C

    c_gate = smoothstep(
        float(shaper["chroma_gate_start"]),
        float(shaper["chroma_gate_end"]),
        C,
    ) * float(dade_strength)

    fw = shaper["foliage_window"]
    h_deg = np.mod(np.rad2deg(np.arctan2(ov, ou)) + 360.0, 360.0)
    w_fol = smoothstep(float(fw["h_start0_deg"]), float(fw["h_start1_deg"]), h_deg) * (
        1.0 - smoothstep(float(fw["h_end0_deg"]), float(fw["h_end1_deg"]), h_deg)
    )

    dh = w_fol * float(fw["dh_rad"])
    dc = w_fol * float(fw["dc_gain"])
    da = w_fol * float(fw["da_luma"])

    for lobe in shaper["von_mises_lobes"]:
        c0 = float(lobe["cos_center"])
        s0 = float(lobe["sin_center"])
        kap = float(lobe["kappa"])
        w_l = np.exp(kap * (hu * c0 + hv * s0 - 1.0))
        dh = dh + w_l * float(lobe["dh_rad"])
        dc = dc + w_l * float(lobe["dc_gain"])
        da = da + w_l * float(lobe["da_luma"])

    dh_tot = c_gate * dh
    sC_tot = np.maximum(0.0, 1.0 + c_gate * dc)
    dA_tot = c_gate * C * da

    cd = np.cos(dh_tot)
    sd = np.sin(dh_tot)
    ou2 = sC_tot * (ou * cd - ov * sd)
    ov2 = sC_tot * (ou * sd + ov * cd)
    A2 = A + dA_tot

    out = np.empty_like(m)
    out[:, 0] = A2 + (2.0 / 3.0) * ou2
    out[:, 1] = A2 - (1.0 / 3.0) * ou2 + INV_SQRT3 * ov2
    out[:, 2] = A2 - (1.0 / 3.0) * ou2 - INV_SQRT3 * ov2
    out = np.maximum(out, 0.0)
    if clamp_output:
        out = np.clip(out, 0.0, 1.0)
    return out.reshape(orig_shape).astype(np.float32)


def stage3_gradient(cc_img: np.ndarray, grad_params: dict) -> np.ndarray:
    """
    Stage 3: Vertical Spatial Multiply Gradient.
      y_norm = y / H  in [0, 1] (0 = top row, 1 = bottom row, full frame including bars)
      r = smoothstep(y0_norm, y1_norm, y_norm)
      out = clamp(cc_img * (1.0 - r * strength_rgb), 0.0, 1.0)
    """
    H = cc_img.shape[0]
    y_norm = (np.arange(H, dtype=np.float64) / float(H))[:, None, None]
    r = smoothstep(float(grad_params["y0_norm"]), float(grad_params["y1_norm"]), y_norm)
    strength = np.asarray(grad_params["strength_rgb"], dtype=np.float64).reshape(1, 1, 3)
    out = cc_img.astype(np.float64) * (1.0 - r * strength)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def stage4_flare(base_img: np.ndarray, flare_params: dict) -> np.ndarray:
    """
    Stage 4: 2D Anisotropic Rotated Gaussian Haze Flare with Screen Blend.
      dx_h = (x / W - cx) * (W / H)
      dy_h = (y / H - cy)
      u = ( dx_h * cos(angle) + dy_h * sin(angle)) / rx_frac_h
      v = (-dx_h * sin(angle) + dy_h * cos(angle)) / ry_frac_h
      f_rgb = clamp(intensity * exp(-0.5 * (u^2 + v^2)) * colour_rgb, 0.0, 1.0)
      out = 1.0 - (1.0 - base) * (1.0 - f_rgb)
    """
    intensity = float(flare_params["intensity"])
    if intensity <= 1e-6:
        return np.clip(base_img, 0.0, 1.0).astype(np.float32)

    H, W = base_img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    dx_h = (xx - float(flare_params["cx"]) * float(W)) / float(H)
    dy_h = (yy - float(flare_params["cy"]) * float(H)) / float(H)

    ang = np.deg2rad(float(flare_params["angle_deg"]))
    ca, sa = float(np.cos(ang)), float(np.sin(ang))
    rx = max(float(flare_params["rx_frac_h"]), 0.02)
    ry = max(float(flare_params["ry_frac_h"]), 0.02)

    u = (dx_h * ca + dy_h * sa) / rx
    v = (-dx_h * sa + dy_h * ca) / ry
    w = np.exp(-0.5 * (u * u + v * v))[..., None]
    col = np.asarray(flare_params["colour_rgb"], dtype=np.float64).reshape(1, 1, 3)
    f_rgb = np.clip(intensity * w * col, 0.0, 1.0)

    b = np.clip(base_img.astype(np.float64), 0.0, 1.0)
    out = 1.0 - (1.0 - b) * (1.0 - f_rgb)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def apply_look(
    img01: np.ndarray,
    params: dict,
    flare_preset: str = "default",
    dade_strength: float = 1.0,
    master_intensity: float = 1.0,
    enable_unsharp: bool = True,
    enable_cc: bool = True,
    enable_gradient: bool = True,
    enable_flare: bool = True,
) -> np.ndarray:
    """Applies the complete 4-stage MOTIONSALT / Keyflaw look pipeline to an RGB [0, 1] image."""
    raw = np.clip(img01.astype(np.float32), 0.0, 1.0)
    x = raw

    if enable_unsharp:
        x = stage1_unsharp(x, params["unsharp"])

    if enable_cc:
        x = stage2_colour_correction(
            x,
            params["colour_correction"],
            dade_strength=dade_strength,
            clamp_output=(not enable_gradient),
        )

    if enable_gradient:
        x = stage3_gradient(x, params["gradient"])
    else:
        x = np.clip(x, 0.0, 1.0).astype(np.float32)

    if enable_flare and flare_preset != "none":
        presets = params["flare"]["presets"]
        if flare_preset not in presets:
            raise ValueError(f"Unknown flare preset '{flare_preset}'. Available: {list(presets.keys())}")
        x = stage4_flare(x, presets[flare_preset])

    if abs(master_intensity - 1.0) > 1e-6:
        m = float(np.clip(master_intensity, 0.0, 1.0))
        x = raw * (1.0 - m) + x * m

    return np.clip(x, 0.0, 1.0).astype(np.float32)


def load_params(params_path: str = None) -> dict:
    if params_path is None:
        params_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "look_params.json")
    with open(params_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Apply the MOTIONSALT Keyflaw Look-Fit pipeline to an image.")
    parser.add_argument("input", help="Input RGB/BGR image path (e.g. in.png)")
    parser.add_argument("output", help="Output PNG/image path (e.g. out.png)")
    parser.add_argument("--params", default=None, help="Path to look_params.json (default: ./look_params.json)")
    parser.add_argument(
        "--flare-preset",
        choices=["default", "pairA", "pairB", "none"],
        default="default",
        help="Flare preset: 'default' (shared cross-clip glow), 'pairA' (golden sunlight), 'pairB' (cool sky), or 'none'",
    )
    parser.add_argument("--dade-strength", type=float, default=1.0, help="Dade selective hue-chroma strength (default: 1.0)")
    parser.add_argument("--master-intensity", type=float, default=1.0, help="Overall effect blend 0..1 (default: 1.0)")
    parser.add_argument("--disable-unsharp", action="store_true", help="Disable Stage 1 Unsharp Mask")
    parser.add_argument("--disable-cc", action="store_true", help="Disable Stage 2 Colour Correction")
    parser.add_argument("--disable-gradient", action="store_true", help="Disable Stage 3 Vertical Gradient")
    parser.add_argument("--disable-flare", action="store_true", help="Disable Stage 4 Haze Flare")
    args = parser.parse_args()

    bgr = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if bgr is None:
        sys.stderr.write(f"Error: Could not read input image '{args.input}'\n")
        sys.exit(1)

    rgb01 = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    params = load_params(args.params)
    out01 = apply_look(
        rgb01,
        params,
        flare_preset=args.flare_preset,
        dade_strength=args.dade_strength,
        master_intensity=args.master_intensity,
        enable_unsharp=not args.disable_unsharp,
        enable_cc=not args.disable_cc,
        enable_gradient=not args.disable_gradient,
        enable_flare=not args.disable_flare,
    )
    out_u8 = np.round(np.clip(out01, 0.0, 1.0) * 255.0).astype(np.uint8)
    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    cv2.imwrite(args.output, cv2.cvtColor(out_u8, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    main()
