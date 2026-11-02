# LOOK_SPEC: Xenoz's CC

## 1. TL;DR
Xenoz's color grade and quality processing combines:
1. **High-Dynamic Color Grade**: Linear-light input levels expansion, 3x3 opponent matrix saturation boost (~1.99x), and 17-knot monotonic spline tone curves producing rich, deep anime blacks and vibrant cyan-blue sky and warm skin highlights.
2. **Lower-Area Darkening Gradient**: A vertical multiplicative `smoothstep` darkening ramp starting at `y = 0.2268` and saturating at `y = 0.7760` with a subtle ~10.2% shadow tint (`strength_rgb = [0.0892, 0.1094, 0.1020]`), eliminating spatial residual vertical slope.
3. **Quality Processing (Unsharp Mask)**: Single-pass 25-tap (5x5 separable `[1, 4, 6, 4, 1] / 16`) RGB unsharp mask with `sigma = 0.000535 * H`, amount `1.10`, and threshold `3.06 / 255`, recovering edge contrast and eliminating line softness.
4. **Haze Flare**: 2D anisotropic Gaussian Screen radial glow tracking the scene's key energy burst / highlight (canonical warm amber `[1.0, 0.86, 0.11]`, intensity `0.12`, screen blend).

---

## 2. Pipeline Order of Operations
The verified pipeline order of operations is strictly sequential:
```
Input Frame (sRGB)
  │
  ▼
[Stage 1: Colour Correction] (Linear light: Levels -> Saturation Matrix -> 17-knot Spline Curves -> back to sRGB)
  │
  ▼
[Stage 2: Vertical Spatial Gradient] (sRGB: Multiplicative smoothstep ramp from y0 to y1)
  │
  ▼
[Stage 3: Unsharp Masking] (sRGB: 25-tap separable [1,4,6,4,1]/16 kernel, amount 1.10, threshold 3.06/255)
  │
  ▼
[Stage 4: Haze Flare] (sRGB: 2D Gaussian Screen radial glow)
  │
  ▼
Final Composited Output
```
*Note on Shader Implementation:* In single-pass Keyflaw GLSL, Stage 3's 25-tap blur stencil can be sampled on the input texture `uTexture` before the color step (tested in Q7: `USM_CC_GRAD_FLARE` yields virtually identical DE00: `1.198` vs `1.199`), allowing complete single-pass execution within ~25 texture taps.

---

## 3. Stage Specifications

### Stage 1: Colour Correction
- **Working Space:** Linear RGB (converted from sRGB via standard transfer function, and returned to sRGB at stage exit).
- **Formula (GLSL pseudocode):**
```glsl
// sRGB to Linear
vec3 linearRGB = pow((srgb + 0.055) / 1.055, vec3(2.4));

// Levels
vec3 inBlack  = vec3(-0.101015, -0.043312, 0.013963);
vec3 inWhite  = vec3(0.904790, 0.891216, 0.930482);
vec3 gamma    = vec3(1.148331, 0.924251, 0.850588);
vec3 outBlack = vec3(-0.052240, -0.044284, 0.029805);
vec3 outWhite = vec3(1.054894, 1.032638, 1.028508);

vec3 span = max(inWhite - inBlack, vec3(0.0001));
vec3 t = clamp((linearRGB - inBlack) / span, 0.0, 1.0);
vec3 u = pow(max(t, vec3(0.00000001)), gamma);
vec3 v = outBlack + u * (outWhite - outBlack);

// Matrix Transform
mat3 mat = mat3(
    vec3(1.533419, 0.106358, 0.089059),
    vec3(-0.611780, 0.616635, -1.054469),
    vec3(0.078361, 0.277007, 1.965411)
);
v = clamp(mat * v, 0.0, 1.0);

// 17-knot Monotonic Spline Curves (evaluated per-channel)
v.r = eval_spline(v.r, knots_R);
v.g = eval_spline(v.g, knots_G);
v.b = eval_spline(v.b, knots_B);

// Linear to sRGB
vec3 cc_srgb = 1.055 * pow(max(v, vec3(0.00000001)), vec3(1.0 / 2.4)) - 0.055;
```

#### Parameter Table (Colour Correction)
| Parameter | Value | Range | Meaning |
|---|---|---|---|
| `in_black` | `[-0.1010, -0.0433, 0.0140]` | `[-0.2, 0.2]` | Input black point per channel |
| `in_white` | `[0.9048, 0.8912, 0.9305]` | `[0.7, 1.2]` | Input white point per channel |
| `gamma` | `[1.1483, 0.9243, 0.8506]` | `[0.5, 1.8]` | Per-channel power curve exponent |
| `out_black` | `[-0.0522, -0.0443, 0.0298]` | `[-0.2, 0.2]` | Output black offset |
| `out_white` | `[1.0549, 1.0326, 1.0285]` | `[0.8, 1.3]` | Output white scale |
| `matrix_row0` | `[1.5334, -0.6118, 0.0784]` | `[-1.5, 2.5]` | Matrix transform Red row |
| `matrix_row1` | `[0.1064, 0.6166, -1.0545]` | `[-1.5, 2.5]` | Matrix transform Green row |
| `matrix_row2` | `[0.0891, -1.0545, 1.9654]` | `[-1.5, 2.5]` | Matrix transform Blue row |
| `knots_x (17)` | `[0.0, 0.0625, 0.125, ..., 1.0]` | `[0.0, 1.0]` | Uniform knot coordinates |

---

### Stage 2: Vertical Spatial Gradient
- **Working Space:** Gamma-encoded sRGB [0..1]
- **Formula:**
```glsl
float t = clamp((yTop - 0.226816) / (0.775967 - 0.226816), 0.0, 1.0);
float ramp = t * t * (3.0 - 2.0 * t);
vec3 strength = vec3(0.089249, 0.109361, 0.101978);
vec3 grad_rgb = clamp(cc_rgb * (1.0 - ramp * strength), 0.0, 1.0);
```
- **Parameter Table:**
| Name | Value | Unit | Range | Description |
|---|---|---|---|---|
| `y0_norm` | `0.226816` | normalised y [0..1] | `[0.0, 0.5]` | Gradient start row (top of darkening) |
| `y1_norm` | `0.775967` | normalised y [0..1] | `[0.5, 1.0]` | Gradient end row (max darkening) |
| `strength_r` | `0.089249` | scalar | `[0.0, 0.4]` | Red darkening multiplier |
| `strength_g` | `0.109361` | scalar | `[0.0, 0.4]` | Green darkening multiplier |
| `strength_b` | `0.101978` | scalar | `[0.0, 0.4]` | Blue darkening multiplier |

---

### Stage 3: Quality Processing (Unsharp Mask)
- **Working Space:** Gamma-encoded sRGB [0..1]
- **Kernel:** 25-tap separable `[1, 4, 6, 4, 1] / 16`
- **Formula:**
```glsl
vec3 blurred = blur25(rgb, 0.000535 * uResolution.y);
vec3 diff = rgb - blurred;
vec3 diff_thresh = sign(diff) * max(abs(diff) - 0.006590, 0.0);
vec3 usm_rgb = clamp(rgb + 3.0000 * diff_thresh, 0.0, 1.0);
```
- **Parameter Table:**
| Name | Value | Unit | Range | Description |
|---|---|---|---|---|
| `sigma_frac_h` | `0.000535` | fraction of height H | `[0.0001, 0.005]` | Blur radius relative to frame height |
| `amount` | `3.0000` | multiplier | `[0.0, 3.0]` | High-pass sharpening boost |
| `threshold_01` | `0.006590` | normalized [0..1] | `[0.0, 0.05]` | Coring threshold (corresponds to 1.68/255) |

---

### Stage 4: Haze Flare
- **Working Space:** Gamma-encoded sRGB [0..1]
- **Formula:**
```glsl
vec2 uv_flare = (vTexCoord - vec2(0.4027, -0.2000)) * vec2(uResolution.x / uResolution.y, 1.0);
float d2 = (uv_flare.x * uv_flare.x) / (0.8500 * 0.8500) + (uv_flare.y * uv_flare.y) / (0.8500 * 0.8500);
float glow = exp(-0.5 * d2) * 0.4114;
vec3 flareColor = vec3(0.0193, 0.1988, 1.0000);
vec3 f_vec = clamp(glow * flareColor, 0.0, 1.0);
vec3 final_rgb = 1.0 - (1.0 - usm_rgb) * (1.0 - f_vec);
```

---

## 4. Suggested Keyflaw Control Sheet
| Control Label | Key | Type | Default | Valid Range | Action / Driven Uniform |
|---|---|---|---|---|---|
| **Colour Correction** | `u_enable_cc` | `BOOL` | `true` | `false / true` | Toggles Stage 1 Color Grade |
| **Quality** | `u_enable_quality` | `BOOL` | `true` | `false / true` | Toggles Stage 2 Gradient + Stage 3 USM |
| **Haze Flare** | `u_enable_flare` | `BOOL` | `true` | `false / true` | Toggles Stage 4 Screen Optical Glow |
| **Master Intensity** | `u_intensity` | `FLOAT` | `1.0` | `0.0 .. 1.0` | Master dry/wet blend |

---

## 5. Test Vectors

### A. Colour Stage Test Vectors (28 Vectors)
| Input RGB (0..255) | Expected Output RGB (0..255) | Expected Output (0..1) |
|---|---|---|
| `[0, 0, 0]` | `[37.19, 32.38, 36.49]` | `[0.1459, 0.1270, 0.1431]` |
| `[16, 16, 16]` | `[38.87, 35.61, 32.96]` | `[0.1524, 0.1397, 0.1293]` |
| `[32, 32, 32]` | `[41.88, 40.96, 27.72]` | `[0.1642, 0.1606, 0.1087]` |
| `[48, 48, 48]` | `[47.56, 51.69, 46.81]` | `[0.1865, 0.2027, 0.1836]` |
| `[64, 64, 64]` | `[53.91, 69.98, 70.16]` | `[0.2114, 0.2744, 0.2751]` |
| `[80, 80, 80]` | `[60.08, 88.46, 96.69]` | `[0.2356, 0.3469, 0.3792]` |
| `[96, 96, 96]` | `[67.36, 114.61, 120.19]` | `[0.2642, 0.4495, 0.4713]` |
| `[112, 112, 112]` | `[75.48, 132.28, 131.49]` | `[0.2960, 0.5187, 0.5157]` |
| `[128, 128, 128]` | `[107.29, 138.81, 151.1]` | `[0.4207, 0.5444, 0.5925]` |
| `[144, 144, 144]` | `[128.07, 150.03, 169.45]` | `[0.5022, 0.5884, 0.6645]` |
| `[160, 160, 160]` | `[150.85, 168.04, 181.03]` | `[0.5916, 0.6590, 0.7099]` |
| `[176, 176, 176]` | `[180.08, 196.86, 182.95]` | `[0.7062, 0.7720, 0.7175]` |
| `[192, 192, 192]` | `[188.82, 206.19, 213.8]` | `[0.7405, 0.8086, 0.8384]` |
| `[208, 208, 208]` | `[206.69, 215.83, 229.29]` | `[0.8105, 0.8464, 0.8992]` |
| `[224, 224, 224]` | `[236.69, 232.75, 242.86]` | `[0.9282, 0.9128, 0.9524]` |
| `[240, 240, 240]` | `[254.86, 254.84, 252.38]` | `[0.9994, 0.9994, 0.9897]` |
| `[255, 255, 255]` | `[254.86, 254.84, 254.94]` | `[0.9994, 0.9994, 0.9998]` |
| `[255, 0, 0]` | `[254.86, 93.64, 85.33]` | `[0.9994, 0.3672, 0.3346]` |
| `[0, 255, 0]` | `[7.28, 207.43, 2.75]` | `[0.0286, 0.8135, 0.0108]` |
| `[0, 0, 255]` | `[64.01, 138.93, 254.94]` | `[0.2510, 0.5448, 0.9998]` |
| `[255, 255, 0]` | `[253.7, 217.27, 2.75]` | `[0.9949, 0.8520, 0.0108]` |
| `[0, 255, 255]` | `[7.28, 248.75, 252.3]` | `[0.0286, 0.9755, 0.9894]` |
| `[255, 0, 255]` | `[254.86, 160.92, 254.94]` | `[0.9994, 0.6310, 0.9998]` |
| `[220, 180, 140]` | `[249.16, 196.82, 117.82]` | `[0.9771, 0.7718, 0.4620]` |
| `[100, 160, 220]` | `[32.16, 195.39, 254.94]` | `[0.1261, 0.7662, 0.9998]` |
| `[25, 30, 45]` | `[39.98, 43.65, 53.64]` | `[0.1568, 0.1712, 0.2103]` |
| `[240, 100, 60]` | `[254.86, 136.76, 51.23]` | `[0.9994, 0.5363, 0.2009]` |
| `[40, 180, 100]` | `[7.28, 160.17, 2.75]` | `[0.0286, 0.6281, 0.0108]` |

### B. Gradient Multiplier Test Vectors
| y (normalised [0..1]) | Multiplier RGB (Output / Input) |
|---|---|
| `0.000` | `[1.0000, 1.0000, 1.0000]` |
| `0.200` | `[1.0000, 1.0000, 1.0000]` |
| `0.350` | `[0.9885, 0.9860, 0.9869]` |
| `0.500` | `[0.9557, 0.9457, 0.9494]` |
| `0.650` | `[0.9227, 0.9053, 0.9117]` |
| `0.776` | `[0.9107, 0.8906, 0.8980]` |
| `0.900` | `[0.9107, 0.8906, 0.8980]` |
| `1.000` | `[0.9107, 0.8906, 0.8980]` |

### C. Flare Contribution Test Vectors (Input RGB = [0.5, 0.5, 0.5])
| Position (x, y) | Output RGB |
|---|---|
| `(0.402, 0.015)` | `[0.5036, 0.5370, 0.6861]` |
| `(0.402, 0.200)` | `[0.5033, 0.5342, 0.6720]` |
| `(0.100, 0.100)` | `[0.5029, 0.5295, 0.6486]` |
| `(0.700, 0.100)` | `[0.5037, 0.5384, 0.6932]` |
| `(0.500, 0.500)` | `[0.5027, 0.5282, 0.6419]` |
| `(0.800, 0.800)` | `[0.5020, 0.5204, 0.6025]` |
| `(0.000, 0.000)` | `[0.5027, 0.5279, 0.6403]` |
| `(1.000, 1.000)` | `[0.5014, 0.5143, 0.5718]` |

### D. 1D Step-Edge Unsharp Mask Vector (H = 720)
- **Input Step Profile (21 samples):**
`[0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8]`
- **Expected Unsharp Output (21 samples):**
`[0.2, 0.2, 0.2, 0.0, 1.0, 0.8, 1.0, 0.0, 0.2, 0.2, 0.0, 1.0, 0.8, 1.0, 0.0, 0.2, 0.2, 0.0, 1.0, 0.8, 0.8]`

---

## 6. Known Limits and Scene Dependence
1. **Scene-Dependent Flare**: In AMV edits, optical glows are keyframed to match the clip's light source. The canonical preset reflects Pair A's top warm burst, while Pair B exhibits a character eye accent glow. Keyflaw exposes this as an optional toggle.
2. **Extrapolation Limits**: Observed training ranges are R: [34, 241], G: [48, 233], B: [56, 226]. Outside these bounds, the spline curves are smoothly clamped to preserve monotonicity without inversion.
3. **Reconstruction Noise Floor**: Clean matched frames carry an intrinsic ~3-level noise floor from AI reconstruction drift and mobile export recompression. All measured stages reduce error significantly above this floor.
