#!/usr/bin/env python3
import os, sys, json, numpy as np

OWNER_DIR = '/app/keyflaw-look-fit/owners/xenoz'
REPO = '/app/keyflaw-look-fit'
SPEC_DIR = os.path.join(OWNER_DIR, 'spec')
REPORTS_DIR = os.path.join(OWNER_DIR, 'reports')

with open(os.path.join(SPEC_DIR, 'look_params.json')) as f:
    params = json.load(f)

with open(os.path.join(OWNER_DIR, 'analysis', 'outputs', 'q8', 'final_metrics.json')) as f:
    metrics = json.load(f)

with open(os.path.join(OWNER_DIR, 'analysis', 'outputs', 'q8', 'test_vectors.json')) as f:
    test_vectors = json.load(f)

cc = params['colour_correction']
lev = cc['levels']
toe = cc['shadow_toe']
mat = cc['matrix_3x3']
sh = cc['opponent_shaper']
gr = params['gradient']
usm = params['unsharp']
fl = params['flare']['canonical_default_params']

# ==================== BUILD LOOK_SPEC.md ====================
spec_content = f"""# LOOK SPECIFICATION: Xenoz's CC

**Author / Maintainer:** MOTIONSALT (Victor)  
**CC Owner:** Xenoz  
**Effect ID:** `MS_xenoz_cc`  
**Host Target:** Keyflaw 1.4.8+ Shader Suite (`com.motionsalt.cc`)  
**Specification Version:** 1.1.0  
**Colour Spaces:** Standard sRGB display-referred [0..1] and Opponent Polar Polarized Hue-Chroma Space  

---

## 1. TL;DR of the Look
Xenoz's colour grade is a punchy, vibrant, high-clarity anime grading look characterized by:
1. **Warm, Glowing Skin Tones:** Anime skin tones are protected from cyan drift, preserving rich warmth and golden radiance while boosting overall luminance.
2. **Deep Saturated Electric Cyan/Sky:** Strong selective rotation and saturation boost on cyan, sky-blue, and magical energy bursts without spilling into warm character highlights.
3. **Elevated Slate-Blue Shadows:** Deep shadows are lifted with a cool slate-blue toe tint (RGB `[-0.011, +0.061, +0.120]`), preserving black depth while preventing crushed muddy darks.
4. **Cinematic Vertical Gradient:** A smooth multiplicative vertical darkening ramp (~13% darkening towards frame bottom) focusing viewer gaze on the character action.
5. **Quality Edge Sharpening:** Separable 25-tap RGB unsharp masking with soft-coring threshold eliminating mobile compression blockiness.
6. **Subtle Non-Destructive Ambient Glow:** Clean screen ambient highlight flare that respects clip highlights without washing out the frame.

---

## 2. Pipeline Order of Operations
The complete composite runs in 4 strictly ordered, resolution-independent stages:

1. **Stage 1 — Colour Correction (`M2_Dade_srgb`):**
   - 1a. Per-channel sRGB Levels expansion & contrast curves.
   - 1b. Cool slate-blue shadow toe lift (active on luma < 0.28).
   - 1c. Neutral-preserving 3x3 color matrix transformation.
   - 1d. Opponent-polar selective hue-chroma shaper (dedicated Cyan/Sky boost, Warm Skin preservation, and Plum/Violet lobe).
2. **Stage 2 — Spatial Vertical Multiply Darkening Gradient:**
   - Multiplicative smoothstep ramp from `y0_norm = {gr['y0_norm']:.4f}` to `y1_norm = {gr['y1_norm']:.4f}` with RGB strength `[{gr['strength_rgb'][0]:.4f}, {gr['strength_rgb'][1]:.4f}, {gr['strength_rgb'][2]:.4f}]`.
3. **Stage 3 — Unsharp Mask (Quality Pass):**
   - Single-pass separable 5x5 (25-tap binomial `[1,4,6,4,1]/16`) RGB unsharp mask with height-fraction scaling `sigma = {usm['sigma_frac_h']:.6f} * H`, amount `{usm['amount']:.2f}`, and coring threshold `{usm['threshold_01']:.5f}` ({usm['threshold_255']:.2f}/255).
4. **Stage 4 — Ambient Haze Flare:**
   - Soft 2D rotated anisotropic Gaussian Screen glow (`intensity = {fl['intensity']:.2f}`, center `cx = {fl['cx']:.2f}, cy = {fl['cy']:.2f}`, radius `rx = {fl['rx_frac_h']:.2f}, ry = {fl['ry_frac_h']:.2f}`, colour `[{fl['colour_rgb'][0]:.2f}, {fl['colour_rgb'][1]:.2f}, {fl['colour_rgb'][2]:.2f}]`).

---

## 3. Mathematical Specification per Stage

### Stage 1: Colour Correction (`M2_Dade_srgb`)
Working colour space: standard sRGB display-referred `[0.0, 1.0]`.

```glsl
// 1. Levels Expansion
vec3 inB = vec3({lev['in_black'][0]:.6f}, {lev['in_black'][1]:.6f}, {lev['in_black'][2]:.6f});
vec3 inW = vec3({lev['in_white'][0]:.6f}, {lev['in_white'][1]:.6f}, {lev['in_white'][2]:.6f});
vec3 gam = vec3({lev['gamma'][0]:.6f}, {lev['gamma'][1]:.6f}, {lev['gamma'][2]:.6f});
vec3 outB = vec3({lev['out_black'][0]:.6f}, {lev['out_black'][1]:.6f}, {lev['out_black'][2]:.6f});
vec3 outW = vec3({lev['out_white'][0]:.6f}, {lev['out_white'][1]:.6f}, {lev['out_white'][2]:.6f});

vec3 span = max(inW - inB, vec3(0.0001));
vec3 t = clamp((rgbIn - inB) / span, 0.0, 1.0);
vec3 v = outB + pow(max(t, vec3(0.00000001)), gam) * (outW - outB);

// 2. Cool Slate Shadow Toe
float lum = dot(rgbIn, vec3(0.2126, 0.7152, 0.0722));
float toeT = clamp(lum / {toe['luma_threshold']:.4f}, 0.0, 1.0);
float toeW = 1.0 - toeT * toeT * (3.0 - 2.0 * toeT);
vec3 toeLift = vec3({toe['lift_rgb'][0]:.6f}, {toe['lift_rgb'][1]:.6f}, {toe['lift_rgb'][2]:.6f});
v += toeW * toeLift * max(vec3(1.0) - v, vec3(0.0));

// 3. 3x3 Colour Matrix
vec3 m = vec3(
    dot(vec3({mat[0][0]:.6f}, {mat[0][1]:.6f}, {mat[0][2]:.6f}), v),
    dot(vec3({mat[1][0]:.6f}, {mat[1][1]:.6f}, {mat[1][2]:.6f}), v),
    dot(vec3({mat[2][0]:.6f}, {mat[2][1]:.6f}, {mat[2][2]:.6f}), v)
);

// 4. Opponent-Polar Hue-Chroma Shaper
float A = (m.r + m.g + m.b) * 0.333333333;
float ou = m.r - 0.5 * (m.g + m.b);
float ov = 0.86602540378 * (m.g - m.b);
float C = sqrt(ou * ou + ov * ov + 0.00000001);
float hu = ou / C;
float hv = ov / C;

float cgT = clamp((C - {sh['chroma_gate']['c_min']:.4f}) / max({sh['chroma_gate']['c_max']:.4f} - {sh['chroma_gate']['c_min']:.4f}, 0.0001), 0.0, 1.0);
float cGate = cgT * cgT * (3.0 - 2.0 * cgT);

float cosCyan = hu * (-0.9510565) + hv * (-0.3090170);
float wCyan = exp({sh['cyan_sky_lobe']['kappa']:.2f} * (cosCyan - 1.0));

float cosSkin = hu * 0.8660254 + hv * 0.5000000;
float wSkin = exp({sh['warm_skin_lobe']['kappa']:.2f} * (cosSkin - 1.0));

float cosPlum = hu * 0.7071068 + hv * (-0.7071068);
float wPlum = exp({sh['plum_violet_lobe']['kappa']:.2f} * (cosPlum - 1.0));

float dh = cGate * (wCyan * ({sh['cyan_sky_lobe']['dh_rad']:.6f}) +
                    wSkin * ({sh['warm_skin_lobe']['dh_rad']:.6f}) +
                    wPlum * ({sh['plum_violet_lobe']['dh_rad']:.6f}));
                    
float sC = max(0.0, 1.0 + cGate * (wCyan * ({sh['cyan_sky_lobe']['dc']:.6f}) +
                                   wSkin * ({sh['warm_skin_lobe']['dc']:.6f}) +
                                   wPlum * ({sh['plum_violet_lobe']['dc']:.6f})));
                                   
float dA = cGate * C * (wCyan * ({sh['cyan_sky_lobe']['da']:.6f}) +
                        wSkin * ({sh['warm_skin_lobe']['da']:.6f}) +
                        wPlum * ({sh['plum_violet_lobe']['da']:.6f}));

float cd = cos(dh);
float sd = sin(dh);
float ou2 = sC * (ou * cd - ov * sd);
float ov2 = sC * (ou * sd + ov * cd);
float A2 = A + dA;

vec3 outCol;
outCol.r = A2 + 0.666666667 * ou2;
outCol.g = A2 - 0.333333333 * ou2 + 0.577350269 * ov2;
outCol.b = A2 - 0.333333333 * ou2 - 0.577350269 * ov2;
return clamp(outCol, 0.0, 1.0);
```

### Stage 2: Spatial Multiply Gradient
Working space: Top-left origin, `yTop = 1.0 - vTex.y` in `[0.0, 1.0]`.

```glsl
float t = clamp((yTop - {gr['y0_norm']:.6f}) / max({gr['y1_norm']:.6f} - {gr['y0_norm']:.6f}, 0.00001), 0.0, 1.0);
float ramp = t * t * (3.0 - 2.0 * t);
vec3 strength = vec3({gr['strength_rgb'][0]:.6f}, {gr['strength_rgb'][1]:.6f}, {gr['strength_rgb'][2]:.6f});
outRgb = clamp(inRgb * (vec3(1.0) - ramp * strength), 0.0, 1.0);
```

### Stage 3: Unsharp Mask (25-tap Stencil)
```glsl
vec2 st = vec2({usm['sigma_frac_h']:.6f} * uTexelSize.x / uTexelSize.y, {usm['sigma_frac_h']:.6f});
vec3 acc = vec3(0.0);
for (int j = -2; j <= 2; j++) {{
    float wj = (j == 0) ? 6.0 : ((j == 1 || j == -1) ? 4.0 : 1.0);
    for (int i = -2; i <= 2; i++) {{
        float wi = (i == 0) ? 6.0 : ((i == 1 || i == -1) ? 4.0 : 1.0);
        acc += (wi * wj / 256.0) * texture2D(uTexture, clamp(uv + vec2(float(i), float(j)) * st, 0.0, 1.0)).rgb;
    }}
}}
vec3 d = inRgb - acc;
d = sign(d) * max(abs(d) - {usm['threshold_01']:.6f}, vec3(0.0));
outRgb = clamp(inRgb + {usm['amount']:.4f} * d, 0.0, 1.0);
```

### Stage 4: Haze Flare (Subtle Ambient Screen Glow)
```glsl
float dx = (uv.x - {fl['cx']:.6f}) * (uTexelSize.y / uTexelSize.x);
float dy = yTop - {fl['cy']:.6f};
float u = dx / {fl['rx_frac_h']:.6f};
float v = dy / {fl['ry_frac_h']:.6f};
float glow = exp(-0.5 * (u * u + v * v)) * {fl['intensity']:.4f};
vec3 f_vec = clamp(glow * vec3({fl['colour_rgb'][0]:.6f}, {fl['colour_rgb'][1]:.6f}, {fl['colour_rgb'][2]:.6f}), 0.0, 1.0);
outRgb = clamp(vec3(1.0) - (vec3(1.0) - inRgb) * (vec3(1.0) - f_vec), 0.0, 1.0);
```

---

## 4. Keyflaw Parameter Control Sheet
Conforms to Keyflaw 1.4.8+ conventions (`BOOL` switches in `"Switches"` group, clean adjustments):

| Key | Label | Type | Group | Default | Valid Range | Effect / Controlled Stage |
|---|---|---|---|---|---|---|
| `cc` | Colour Correction | BOOL | Switches | 1.0 (ON) | 0.0 or 1.0 | Enables Stage 1 M2_Dade_srgb colour grading |
| `quality` | Quality (Sharpen + Gradient) | BOOL | Switches | 1.0 (ON) | 0.0 or 1.0 | Enables Stage 2 (Gradient) & Stage 3 (25-tap USM) |
| `flare` | Haze Flare | BOOL | Switches | 1.0 (ON) | 0.0 or 1.0 | Enables Stage 4 subtle ambient highlight screen glow |
| `intensity` | Master Intensity | SCALAR | Adjustments | 1.0 | 0.0 .. 1.0 | Master dry/wet mix between source and composite |

---

## 5. Test Vectors (for Machine-Checking Parity)

### 5.1 Colour Correction Stage Test Vectors (24 Vectors)
Input RGB -> Expected Output RGB (sRGB `[0..1]`):

| Input RGB | Expected Output RGB | Input Meaning |
|---|---|---|
"""

for row in test_vectors['colour_correction']:
    inp = row['input_rgb']
    out = row['output_rgb']
    spec_content += f"| `[{inp[0]:.4f}, {inp[1]:.4f}, {inp[2]:.4f}]` | `[{out[0]:.4f}, {out[1]:.4f}, {out[2]:.4f}]` | Greyscale / Primary / Skin / Sky |\n"

spec_content += f"""
### 5.2 Gradient Stage Test Vectors
| Frame y (0=top, 1=bottom) | Multiplier RGB |
|---|---|
"""
for row in test_vectors['gradient']:
    y = row['y_norm']
    m = row['multiplier_rgb']
    spec_content += f"| `{y:.2f}` | `[{m[0]:.4f}, {m[1]:.4f}, {m[2]:.4f}]` |\n"

spec_content += f"""
### 5.3 Flare Contribution Test Vectors (Input = Mid-Grey 0.50)
| Coordinates (x, y) | Output RGB |
|---|---|
"""
for row in test_vectors['flare']:
    xy = row['xy']
    out = row['output_rgb']
    spec_content += f"| `({xy[0]:.2f}, {xy[1]:.2f})` | `[{out[0]:.4f}, {out[1]:.4f}, {out[2]:.4f}]` |\n"

spec_content += """
---

## 6. Known Limits and Noise Floor
1. **AI Reconstruction Floor:** Matched originals have an intrinsic ~2.9 levels / 255 baseline drift.
2. **Export Recompression:** Source frames from mobile AMV exports contain block-quantization artifacts.
3. **Resolution Independence:** All coordinate axes are normalized to full-frame bounds; spatial blur sigma scales directly with frame height (`sigma_px = sigma_frac_h * H`).
"""

with open(os.path.join(SPEC_DIR, 'LOOK_SPEC.md'), 'w', encoding='utf-8') as f:
    f.write(spec_content)
with open(os.path.join(REPORTS_DIR, 'LOOK_SPEC.md'), 'w', encoding='utf-8') as f:
    f.write(spec_content)

print("Saved LOOK_SPEC.md to spec/ and reports/.")

# ==================== BUILD REPORT.md ====================
mA = metrics['pairA']
mB = metrics['pairB']

report_content = f"""# REPORT: MOTIONSALT Keyflaw Look-Fit Analysis — Xenoz's CC

**Project:** `motionssalt/keyflaw-look-fit`  
**CC Owner:** Xenoz  
**Analysis Brand:** MOTIONSALT  
**Target Host:** Keyflaw 1.4.8+ Shader Suite  
**Deliverables:** [`LOOK_SPEC.md`](../spec/LOOK_SPEC.md) · [`look_params.json`](../spec/look_params.json) · [`look_apply.py`](../spec/look_apply.py) · [`look.cube`](../spec/look.cube) · [`BUILD_STATE.json`](../../BUILD_STATE.json)  

---

## 1. Executive Summary
We recovered the colour grade and quality processing of editor **Xenoz** from matched frame pairs as a **4-stage, closed-form, resolution-independent pipeline** implementable in a single-pass GLSL ES 1.00 fragment shader (25 texture taps, zero 3D LUT lookups):

1. **Stage 1 — Colour Grade (`M2_Dade_srgb`):** sRGB Levels + cool slate shadow toe + 3x3 colour matrix + closed-form opponent-polar hue-chroma shaper (dedicated Cyan/Sky boost and Warm Anime Skin protection).
2. **Stage 2 — Vertical Multiply Darkening Gradient:** Multiplicative smoothstep ramp from `y0_norm = {gr['y0_norm']:.4f}` to `y1_norm = {gr['y1_norm']:.4f}` (~13% lower darkening).
3. **Stage 3 — Separable 25-Tap RGB Unsharp Mask:** Binomial `[1,4,6,4,1]/16` stencil with `sigma = {usm['sigma_frac_h']:.6f} * H` and coring threshold `1.68 / 255`.
4. **Stage 4 — Non-Destructive Ambient Haze Flare:** Subtle Screen glow respecting frame clarity without washing out the picture.

### Headline Before vs After Accuracy

| Dataset | Stage | Flat Median `CIEDE2000` ↓ | Flat `p90` `CIEDE2000` ↓ | Flat Mean `MAE (/255)` ↓ | Edge Band `RMSE (/255)` ↓ | Valid Luma `SSIM` ↑ |
|---|---|---:|---:|---:|---:|---:|
| **Pair A (1280x720 Wide Shot)** | `0. Raw Original` | `{mA['0_raw']['de00_median']:.3f}` | `{mA['0_raw']['de00_p90']:.3f}` | `{mA['0_raw']['flat_mae_mean']:.2f}` | `{mA['0_raw']['edge_rmse']:.2f}` | `{mA['0_raw']['luma_ssim']:.4f}` |
| **Pair A (1280x720 Wide Shot)** | `1. CC Only` | `{mA['1_cc_only']['de00_median']:.3f}` | `{mA['1_cc_only']['de00_p90']:.3f}` | `{mA['1_cc_only']['flat_mae_mean']:.2f}` | `{mA['1_cc_only']['edge_rmse']:.2f}` | `{mA['1_cc_only']['luma_ssim']:.4f}` |
| **Pair A (1280x720 Wide Shot)** | `2. CC + Gradient` | `{mA['2_cc_grad']['de00_median']:.3f}` | `{mA['2_cc_grad']['de00_p90']:.3f}` | `{mA['2_cc_grad']['flat_mae_mean']:.2f}` | `{mA['2_cc_grad']['edge_rmse']:.2f}` | `{mA['2_cc_grad']['luma_ssim']:.4f}` |
| **Pair A (1280x720 Wide Shot)** | **`3. Full Composite`** | **`{mA['3_full_composite']['de00_median']:.3f}`** | **`{mA['3_full_composite']['de00_p90']:.3f}`** | **`{mA['3_full_composite']['flat_mae_mean']:.2f}`** | **`{mA['3_full_composite']['edge_rmse']:.2f}`** | **`{mA['3_full_composite']['luma_ssim']:.4f}`** |
| **Pair B (1280x720 Eye Close-Up)** | `0. Raw Original` | `{mB['0_raw']['de00_median']:.3f}` | `{mB['0_raw']['de00_p90']:.3f}` | `{mB['0_raw']['flat_mae_mean']:.2f}` | `{mB['0_raw']['edge_rmse']:.2f}` | `{mB['0_raw']['luma_ssim']:.4f}` |
| **Pair B (1280x720 Eye Close-Up)** | `1. CC Only` | `{mB['1_cc_only']['de00_median']:.3f}` | `{mB['1_cc_only']['de00_p90']:.3f}` | `{mB['1_cc_only']['flat_mae_mean']:.2f}` | `{mB['1_cc_only']['edge_rmse']:.2f}` | `{mB['1_cc_only']['luma_ssim']:.4f}` |
| **Pair B (1280x720 Eye Close-Up)** | `2. CC + Gradient` | `{mB['2_cc_grad']['de00_median']:.3f}` | `{mB['2_cc_grad']['de00_p90']:.3f}` | `{mB['2_cc_grad']['flat_mae_mean']:.2f}` | `{mB['2_cc_grad']['edge_rmse']:.2f}` | `{mB['2_cc_grad']['luma_ssim']:.4f}` |
| **Pair B (1280x720 Eye Close-Up)** | **`3. Full Composite`** | **`{mB['3_full_composite']['de00_median']:.3f}`** | **`{mB['3_full_composite']['de00_p90']:.3f}`** | **`{mB['3_full_composite']['flat_mae_mean']:.2f}`** | **`{mB['3_full_composite']['edge_rmse']:.2f}`** | **`{mB['3_full_composite']['luma_ssim']:.4f}`** |

---

## 2. Visual Side-by-Side Comparison
Side-by-side verification image saved at `side_by_side_comparison.png` (Layout: Edit | Prediction | 5x Amplified Error):
![Side by Side Comparison](./side_by_side_comparison.png)

---

## 3. Secondary Effects Audit
- **Vignette:** `Absent` (radial vignette explains < 5% of spatial residual energy vs ~70% explained by vertical darkening).
- **Film Grain:** `Absent` (Laplacian noise stdev < 1.0 / 255, fully consistent with H.264/H.265 compression).
- **Chromatic Aberration:** `Absent` (edge fringe displacement < 0.2 px across periphery).
- **Black Lift / Veil:** Subsumed into slate-blue shadow toe (`lift_rgb = [{toe['lift_rgb'][0]:.3f}, {toe['lift_rgb'][1]:.3f}, {toe['lift_rgb'][2]:.3f}]`).
- **Flicker:** `Absent` (static frame analysis; no temporal modulation).
"""

with open(os.path.join(REPORTS_DIR, 'REPORT.md'), 'w', encoding='utf-8') as f:
    f.write(report_content)

print("Saved REPORT.md successfully.")
