#!/usr/bin/env python3
"""
look_apply.py: Standalone reference implementation of LOOK_SPEC.md for Xenoz's CC.
Usage:
    python look_apply.py in.png out.png
    python look_apply.py in.png out.png --no-flare
    python look_apply.py in.png out.png --no-usm
    python look_apply.py in.png out.png --master-intensity 1.0

Reads all parameters from `look_params.json` (in the same directory by default) and applies
the exact 4-stage pipeline:
  Stage 1: Colour Correction (sRGB Levels + Cool Slate Shadow Toe + 3x3 Matrix + Opponent-Polar Shaper)
  Stage 2: Vertical Spatial Multiply Gradient (smoothstep falloff)
  Stage 3: 25-tap (5x5 separable [1,4,6,4,1]/16) RGB Unsharp Mask
  Stage 4: Subtle 2D Gaussian Screen Haze Flare
"""

import os, sys, json, argparse, cv2, numpy as np

LUMA_W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
SQRT3_2 = 0.8660254037844386
INV_SQRT3 = 0.5773502691896257
W1D_5 = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32) / 16.0
K2D_25 = np.outer(W1D_5, W1D_5).astype(np.float32)

def smoothstep_np(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def stage1_colour_correction(x_srgb01: np.ndarray, cc_params: dict) -> np.ndarray:
    orig_shape = x_srgb01.shape
    x = np.clip(x_srgb01.reshape(-1, 3).astype(np.float64), 0.0, 1.0)
    
    # Levels
    lev = cc_params["levels"]
    in_b = np.array(lev["in_black"], dtype=np.float64)[None, :]
    in_w = np.array(lev["in_white"], dtype=np.float64)[None, :]
    gam = np.array(lev["gamma"], dtype=np.float64)[None, :]
    out_b = np.array(lev["out_black"], dtype=np.float64)[None, :]
    out_w = np.array(lev["out_white"], dtype=np.float64)[None, :]
    
    span = np.maximum(in_w - in_b, 1e-4)
    t = np.clip((x - in_b) / span, 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), gam)
    v = out_b + u * (out_w - out_b)
    
    # Shadow toe
    lum = x @ LUMA_W
    toe_w = 1.0 - smoothstep_np(0.0, float(cc_params["shadow_toe"]["luma_threshold"]), lum)
    toe_lift = np.array(cc_params["shadow_toe"]["lift_rgb"], dtype=np.float64)[None, :]
    v = v + toe_w[:, None] * toe_lift * np.maximum(1.0 - v, 0.0)
    
    # 3x3 Matrix
    mat = np.array(cc_params["matrix_3x3"], dtype=np.float64)
    m = v @ mat.T
    
    # Opponent-polar shaper
    A = (m[:, 0] + m[:, 1] + m[:, 2]) * (1.0 / 3.0)
    ou = m[:, 0] - 0.5 * (m[:, 1] + m[:, 2])
    ov = SQRT3_2 * (m[:, 1] - m[:, 2])
    C = np.sqrt(ou * ou + ov * ov + 1e-8)
    hu = ou / C
    hv = ov / C
    
    shaper = cc_params["opponent_shaper"]
    cg = shaper["chroma_gate"]
    c_gate = smoothstep_np(float(cg["c_min"]), float(cg["c_max"]), C)
    
    rad_cyan = np.deg2rad(float(shaper["cyan_sky_lobe"]["center_deg"]))
    w_cyan = np.exp(float(shaper["cyan_sky_lobe"]["kappa"]) * (hu * np.cos(rad_cyan) + hv * np.sin(rad_cyan) - 1.0))
    
    rad_skin = np.deg2rad(float(shaper["warm_skin_lobe"]["center_deg"]))
    w_skin = np.exp(float(shaper["warm_skin_lobe"]["kappa"]) * (hu * np.cos(rad_skin) + hv * np.sin(rad_skin) - 1.0))
    
    rad_plum = np.deg2rad(float(shaper["plum_violet_lobe"]["center_deg"]))
    w_plum = np.exp(float(shaper["plum_violet_lobe"]["kappa"]) * (hu * np.cos(rad_plum) + hv * np.sin(rad_plum) - 1.0))
    
    cy = shaper["cyan_sky_lobe"]
    sk = shaper["warm_skin_lobe"]
    pl = shaper["plum_violet_lobe"]
    
    dh = c_gate * (w_cyan * float(cy["dh_rad"]) + w_skin * float(sk["dh_rad"]) + w_plum * float(pl["dh_rad"]))
    sC = np.maximum(0.0, 1.0 + c_gate * (w_cyan * float(cy["dc"]) + w_skin * float(sk["dc"]) + w_plum * float(pl["dc"])))
    dA = c_gate * C * (w_cyan * float(cy["da"]) + w_skin * float(sk["da"]) + w_plum * float(pl["da"]))
    
    cd = np.cos(dh)
    sd = np.sin(dh)
    ou2 = sC * (ou * cd - ov * sd)
    ov2 = sC * (ou * sd + ov * cd)
    A2 = A + dA
    
    out = np.empty_like(m)
    out[:, 0] = A2 + (2.0 / 3.0) * ou2
    out[:, 1] = A2 - (1.0 / 3.0) * ou2 + INV_SQRT3 * ov2
    out[:, 2] = A2 - (1.0 / 3.0) * ou2 - INV_SQRT3 * ov2
    return np.clip(out, 0.0, 1.0).reshape(orig_shape)

def stage2_gradient(rgb01: np.ndarray, grad_params: dict) -> np.ndarray:
    H = rgb01.shape[0]
    yn = (np.arange(H, dtype=np.float64) / float(H))[:, None, None]
    y0 = float(grad_params["y0_norm"])
    y1 = float(grad_params["y1_norm"])
    s = np.array(grad_params["strength_rgb"], dtype=np.float64).reshape(1, 1, 3)
    t = smoothstep_np(y0, y1, yn)
    return np.clip(rgb01 * (1.0 - t * s), 0.0, 1.0)

def stage3_unsharp_mask(rgb01: np.ndarray, usm_params: dict) -> np.ndarray:
    H, W = rgb01.shape[:2]
    sigma_px = float(usm_params["sigma_frac_h"] * H)
    amount = float(usm_params["amount"])
    threshold = float(usm_params.get("threshold_01", 0.0))
    if amount <= 1e-6 or sigma_px <= 1e-4:
        return np.clip(rgb01, 0.0, 1.0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    acc = np.zeros_like(rgb01, dtype=np.float32)
    for j_idx, j in enumerate((-2, -1, 0, 1, 2)):
        ym = np.clip(yy + j * sigma_px, 0.0, H - 1.0)
        for i_idx, i in enumerate((-2, -1, 0, 1, 2)):
            xm = np.clip(xx + i * sigma_px, 0.0, W - 1.0)
            acc += float(K2D_25[j_idx, i_idx]) * cv2.remap(rgb01.astype(np.float32), xm, ym, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    d = rgb01 - acc
    if threshold > 1e-5:
        d = np.sign(d) * np.maximum(np.abs(d) - threshold, 0.0)
    return np.clip(rgb01 + amount * d, 0.0, 1.0)

def stage4_flare(rgb01: np.ndarray, flare_params: dict) -> np.ndarray:
    if not flare_params or float(flare_params.get("intensity", 0.0)) <= 1e-6:
        return rgb01
    H, W = rgb01.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    dx_h = (xx - float(flare_params["cx"]) * W) / float(H)
    dy_h = (yy - float(flare_params["cy"]) * H) / float(H)
    rx = max(float(flare_params.get("rx_frac_h", 0.45)), 0.02)
    ry = max(float(flare_params.get("ry_frac_h", 0.35)), 0.02)
    u = dx_h / rx
    v = dy_h / ry
    d2 = u * u + v * v
    w = np.exp(-0.5 * d2)[..., None]
    col = np.array(flare_params["colour_rgb"], dtype=np.float64).reshape(1, 1, 3)
    f_vec = np.clip(float(flare_params["intensity"]) * w * col, 0.0, 1.0)
    return np.clip(1.0 - (1.0 - rgb01) * (1.0 - f_vec), 0.0, 1.0)

def apply_look(img_rgb01: np.ndarray, params: dict, master_intensity: float = 1.0,
               enable_cc: bool = True, enable_grad: bool = True,
               enable_usm: bool = True, enable_flare: bool = True) -> np.ndarray:
    orig = np.clip(img_rgb01.astype(np.float64), 0.0, 1.0)
    x = orig.copy()
    if enable_cc:
        x = stage1_colour_correction(x, params["colour_correction"])
    if enable_grad:
        x = stage2_gradient(x, params["gradient"])
    if enable_usm:
        x = stage3_unsharp_mask(x, params["unsharp"])
    if enable_flare and "canonical_default_params" in params.get("flare", {}):
        x = stage4_flare(x, params["flare"]["canonical_default_params"])
    if abs(master_intensity - 1.0) > 1e-4:
        x = np.clip(orig * (1.0 - master_intensity) + x * master_intensity, 0.0, 1.0)
    return np.clip(x, 0.0, 1.0)

def main():
    parser = argparse.ArgumentParser(description="Apply Xenoz CC look to an image.")
    parser.add_argument("input_image", help="Input image path (RGB/PNG/JPG)")
    parser.add_argument("output_image", help="Output path to save result")
    parser.add_argument("--params", default="", help="Path to look_params.json")
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
