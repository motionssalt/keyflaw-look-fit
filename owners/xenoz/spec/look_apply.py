#!/usr/bin/env python3
"""
look_apply.py — Reference ground-truth implementation of LOOK_SPEC.md for Xenoz's CC.
Usage:
    python look_apply.py in.png out.png
    python look_apply.py in.png out.png --flare-preset pairA
    python look_apply.py in.png out.png --flare-preset pairB
    python look_apply.py in.png out.png --flare-preset off
    python look_apply.py in.png out.png --master-intensity 1.0

Reads all parameters from `look_params.json` (in the same directory by default) and applies
the exact 4-stage pipeline:
  Stage 1: Colour Correction (Linear-light Levels + Saturation Matrix + 17-knot Monotonic Splines)
  Stage 2: Vertical Spatial Multiply Gradient (smoothstep falloff with subtle RGB shadow tint)
  Stage 3: 25-tap (5x5 separable [1,4,6,4,1]/16) RGB Unsharp Mask
  Stage 4: 2D Anisotropic Gaussian Screen Haze Flare
"""

import os
import sys
import json
import argparse
import cv2
import numpy as np

LUMA_W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
W1D_5 = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32) / 16.0
K2D_25 = np.outer(W1D_5, W1D_5).astype(np.float32)

def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, np.power((x + 0.055) / 1.055, 2.4))

def linear_to_srgb(y: np.ndarray) -> np.ndarray:
    y = np.clip(y, 0.0, 1.0)
    return np.where(y <= 0.0031308, y * 12.92, 1.055 * np.power(np.maximum(y, 1e-12), 1.0 / 2.4) - 0.055)

def stage1_colour_correction(x_srgb01: np.ndarray, cc_params: dict) -> np.ndarray:
    orig_shape = x_srgb01.shape
    x = x_srgb01.reshape(-1, 3).astype(np.float64)
    w = srgb_to_linear(x)

    lev = cc_params["levels"]
    in_b = np.array(lev["in_black"], dtype=np.float64)[None, :]
    in_w = np.array(lev["in_white"], dtype=np.float64)[None, :]
    gam = np.array(lev["gamma"], dtype=np.float64)[None, :]
    out_b = np.array(lev["out_black"], dtype=np.float64)[None, :]
    out_w = np.array(lev["out_white"], dtype=np.float64)[None, :]

    span = np.maximum(in_w - in_b, 1e-4)
    t = np.clip((w - in_b) / span, 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), gam)
    v = out_b + u * (out_w - out_b)

    mat = np.array(cc_params["matrix_3x3"], dtype=np.float64)
    v = v @ mat.T
    v = np.clip(v, 0.0, 1.0)

    xk = np.array(cc_params["curve_knots_x"], dtype=np.float64)
    knots_rgb = cc_params["curve_knots_rgb"]
    out_v = np.empty_like(v)
    for c, ch in enumerate(["R", "G", "B"]):
        yk = np.array(knots_rgb[ch], dtype=np.float64)
        out_v[:, c] = np.interp(v[:, c], xk, yk)

    v = np.clip(out_v, 0.0, 1.0)
    out_srgb = linear_to_srgb(v)
    return np.clip(out_srgb, 0.0, 1.0).reshape(orig_shape)

def stage2_gradient(rgb01: np.ndarray, grad_params: dict) -> np.ndarray:
    H = rgb01.shape[0]
    yn = (np.arange(H, dtype=np.float64) / float(H))[:, None, None]
    y0 = float(grad_params["y0_norm"])
    y1 = float(grad_params["y1_norm"])
    s = np.array(grad_params["strength_rgb"], dtype=np.float64).reshape(1, 1, 3)

    span = max(y1 - y0, 1e-5)
    t = np.clip((yn - y0) / span, 0.0, 1.0)
    ramp = t * t * (3.0 - 2.0 * t)
    return np.clip(rgb01 * (1.0 - ramp * s), 0.0, 1.0)

def blur_25tap_2d(img: np.ndarray, sigma_px: float) -> np.ndarray:
    if sigma_px <= 1e-4:
        return img.copy()
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    acc = np.zeros_like(img, dtype=np.float32)
    for j_idx, j in enumerate((-2, -1, 0, 1, 2)):
        ym = np.clip(yy + j * sigma_px, 0.0, H - 1.0)
        for i_idx, i in enumerate((-2, -1, 0, 1, 2)):
            xm = np.clip(xx + i * sigma_px, 0.0, W - 1.0)
            w = float(K2D_25[j_idx, i_idx])
            acc += w * cv2.remap(img.astype(np.float32), xm, ym, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return acc

def stage3_unsharp_mask(rgb01: np.ndarray, usm_params: dict) -> np.ndarray:
    H = rgb01.shape[0]
    sigma_px = float(usm_params["sigma_frac_h"] * H)
    amount = float(usm_params["amount"])
    threshold = float(usm_params["threshold_01"])

    if amount <= 1e-6 or sigma_px <= 1e-4:
        return np.clip(rgb01, 0.0, 1.0)

    b = blur_25tap_2d(rgb01.astype(np.float32), sigma_px).astype(np.float64)
    d = rgb01 - b
    if threshold > 1e-6:
        d = np.sign(d) * np.maximum(np.abs(d) - threshold, 0.0)
    return np.clip(rgb01 + amount * d, 0.0, 1.0)

def stage4_flare(rgb01: np.ndarray, flare_params: dict) -> np.ndarray:
    if not flare_params or flare_params.get("intensity", 0.0) <= 1e-6:
        return rgb01
    H, W = rgb01.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    dx_h = (xx - float(flare_params["cx"]) * W) / float(H)
    dy_h = (yy - float(flare_params["cy"]) * H) / float(H)

    ang = np.deg2rad(float(flare_params.get("angle_deg", 0.0)))
    ca, sa = np.cos(ang), np.sin(ang)
    rx = max(float(flare_params["rx_frac_h"]), 0.02)
    ry = max(float(flare_params["ry_frac_h"]), 0.02)

    u = (dx_h * ca + dy_h * sa) / rx
    v = (-dx_h * sa + dy_h * ca) / ry
    d2 = u * u + v * v
    w = np.exp(-0.5 * d2)[..., None]

    col = np.array(flare_params["colour_rgb"], dtype=np.float64).reshape(1, 1, 3)
    f_vec = np.clip(float(flare_params["intensity"]) * w * col, 0.0, 1.0)

    # Screen blend: 1 - (1 - a)*(1 - b)
    return np.clip(1.0 - (1.0 - rgb01) * (1.0 - f_vec), 0.0, 1.0)

def apply_look(img_rgb01: np.ndarray, params: dict, flare_preset: str = "pairA",
               master_intensity: float = 1.0, enable_cc: bool = True,
               enable_grad: bool = True, enable_usm: bool = True, enable_flare: bool = True) -> np.ndarray:
    orig = np.clip(img_rgb01.astype(np.float64), 0.0, 1.0)
    x = orig.copy()

    # Stage 1: Colour Correction
    if enable_cc:
        x = stage1_colour_correction(x, params["colour_correction"])

    # Stage 2: Gradient
    if enable_grad:
        x = stage2_gradient(x, params["gradient"])

    # Stage 3: Unsharp Mask
    if enable_usm:
        x = stage3_unsharp_mask(x, params["unsharp"])

    # Stage 4: Flare
    if enable_flare and flare_preset != "off":
        if flare_preset == "pairA" or flare_preset == "canonical":
            fp = params["flare"]["canonical_default_params"]
        elif flare_preset == "pairB":
            fp = params["flare"]["pairB_fitted_params"]
        else:
            fp = params["flare"]["canonical_default_params"]
        x = stage4_flare(x, fp)

    if abs(master_intensity - 1.0) > 1e-4:
        x = np.clip(orig * (1.0 - master_intensity) + x * master_intensity, 0.0, 1.0)

    return np.clip(x, 0.0, 1.0)

def main():
    parser = argparse.ArgumentParser(description="Apply Xenoz CC look to an image.")
    parser.add_argument("input_image", help="Input image path (RGB/PNG/JPG)")
    parser.add_argument("output_image", help="Output path to save result")
    parser.add_argument("--params", default="", help="Path to look_params.json")
    parser.add_argument("--flare-preset", default="pairA", choices=["pairA", "pairB", "canonical", "off"], help="Flare preset")
    parser.add_argument("--master-intensity", type=float, default=1.0, help="Overall intensity [0..1]")
    parser.add_argument("--no-cc", action="store_true", help="Disable Colour Correction")
    parser.add_argument("--no-grad", action="store_true", help="Disable Gradient")
    parser.add_argument("--no-usm", action="store_true", help="Disable Unsharp Mask")
    parser.add_argument("--no-flare", action="store_true", help="Disable Flare")
    args = parser.parse_args()

    params_path = args.params or os.path.join(os.path.dirname(__file__), "look_params.json")
    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    bgr = cv2.imread(args.input_image)
    if bgr is None:
        sys.exit(f"Could not load image: {args.input_image}")
    rgb01 = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0

    out01 = apply_look(
        rgb01,
        params,
        flare_preset=args.flare_preset,
        master_intensity=args.master_intensity,
        enable_cc=not args.no_cc,
        enable_grad=not args.no_grad,
        enable_usm=not args.no_usm,
        enable_flare=not args.no_flare,
    )

    out_bgr = cv2.cvtColor(np.round(out01 * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
    os.makedirs(os.path.dirname(os.path.abspath(args.output_image)), exist_ok=True)
    cv2.imwrite(args.output_image, out_bgr)
    print(f"Saved: {args.output_image}")

if __name__ == "__main__":
    main()
