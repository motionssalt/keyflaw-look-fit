# LOOK SPECIFICATION: Xenoz's CC

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
   - Multiplicative smoothstep ramp from `y0_norm = 0.2691` to `y1_norm = 0.8721` with RGB strength `[0.0572, 0.1296, 0.1355]`.
3. **Stage 3 — Unsharp Mask (Quality Pass):**
   - Single-pass separable 5x5 (25-tap binomial `[1,4,6,4,1]/16`) RGB unsharp mask with height-fraction scaling `sigma = 0.000535 * H`, amount `1.10`, and coring threshold `0.00659` (1.68/255).
4. **Stage 4 — Ambient Haze Flare:**
   - Soft 2D rotated anisotropic Gaussian Screen glow (`intensity = 0.12`, center `cx = 0.50, cy = 0.05`, radius `rx = 0.45, ry = 0.35`, colour `[0.35, 0.55, 0.95]`).

---

## 3. Mathematical Specification per Stage

### Stage 1: Colour Correction (`M2_Dade_srgb`)
Working colour space: standard sRGB display-referred `[0.0, 1.0]`.

```glsl
// 1. Levels Expansion
vec3 inB = vec3(0.000300, -0.093120, 0.073239);
vec3 inW = vec3(0.945100, 0.922091, 0.895012);
vec3 gam = vec3(1.682652, 1.824267, 0.938911);
vec3 outB = vec3(0.199788, 0.144363, 0.135760);
vec3 outW = vec3(1.179506, 1.152492, 1.249824);

vec3 span = max(inW - inB, vec3(0.0001));
vec3 t = clamp((rgbIn - inB) / span, 0.0, 1.0);
vec3 v = outB + pow(max(t, vec3(0.00000001)), gam) * (outW - outB);

// 2. Cool Slate Shadow Toe
float lum = dot(rgbIn, vec3(0.2126, 0.7152, 0.0722));
float toeT = clamp(lum / 0.2800, 0.0, 1.0);
float toeW = 1.0 - toeT * toeT * (3.0 - 2.0 * toeT);
vec3 toeLift = vec3(-0.010808, 0.060847, 0.119867);
v += toeW * toeLift * max(vec3(1.0) - v, vec3(0.0));

// 3. 3x3 Colour Matrix
vec3 m = vec3(
    dot(vec3(-0.451142, -1.147089, 2.023277), v),
    dot(vec3(-2.777678, -0.486145, 3.500240), v),
    dot(vec3(-2.361577, -2.134604, 4.553602), v)
);

// 4. Opponent-Polar Hue-Chroma Shaper
float A = (m.r + m.g + m.b) * 0.333333333;
float ou = m.r - 0.5 * (m.g + m.b);
float ov = 0.86602540378 * (m.g - m.b);
float C = sqrt(ou * ou + ov * ov + 0.00000001);
float hu = ou / C;
float hv = ov / C;

float cgT = clamp((C - 0.0150) / max(0.0600 - 0.0150, 0.0001), 0.0, 1.0);
float cGate = cgT * cgT * (3.0 - 2.0 * cgT);

float cosCyan = hu * (-0.9510565) + hv * (-0.3090170);
float wCyan = exp(4.00 * (cosCyan - 1.0));

float cosSkin = hu * 0.8660254 + hv * 0.5000000;
float wSkin = exp(4.00 * (cosSkin - 1.0));

float cosPlum = hu * 0.7071068 + hv * (-0.7071068);
float wPlum = exp(3.00 * (cosPlum - 1.0));

float dh = cGate * (wCyan * (0.213305) +
                    wSkin * (0.060669) +
                    wPlum * (0.256400));
                    
float sC = max(0.0, 1.0 + cGate * (wCyan * (-0.440839) +
                                   wSkin * (-0.277627) +
                                   wPlum * (-0.108032)));
                                   
float dA = cGate * C * (wCyan * (-1.250608) +
                        wSkin * (1.998926) +
                        wPlum * (0.629119));

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
float t = clamp((yTop - 0.269079) / max(0.872060 - 0.269079, 0.00001), 0.0, 1.0);
float ramp = t * t * (3.0 - 2.0 * t);
vec3 strength = vec3(0.057212, 0.129601, 0.135450);
outRgb = clamp(inRgb * (vec3(1.0) - ramp * strength), 0.0, 1.0);
```

### Stage 3: Unsharp Mask (25-tap Stencil)
```glsl
vec2 st = vec2(0.000535 * uTexelSize.x / uTexelSize.y, 0.000535);
vec3 acc = vec3(0.0);
for (int j = -2; j <= 2; j++) {
    float wj = (j == 0) ? 6.0 : ((j == 1 || j == -1) ? 4.0 : 1.0);
    for (int i = -2; i <= 2; i++) {
        float wi = (i == 0) ? 6.0 : ((i == 1 || i == -1) ? 4.0 : 1.0);
        acc += (wi * wj / 256.0) * texture2D(uTexture, clamp(uv + vec2(float(i), float(j)) * st, 0.0, 1.0)).rgb;
    }
}
vec3 d = inRgb - acc;
d = sign(d) * max(abs(d) - 0.006590, vec3(0.0));
outRgb = clamp(inRgb + 1.1000 * d, 0.0, 1.0);
```

### Stage 4: Haze Flare (Subtle Ambient Screen Glow)
```glsl
float dx = (uv.x - 0.500000) * (uTexelSize.y / uTexelSize.x);
float dy = yTop - 0.050000;
float u = dx / 0.450000;
float v = dy / 0.350000;
float glow = exp(-0.5 * (u * u + v * v)) * 0.1200;
vec3 f_vec = clamp(glow * vec3(0.350000, 0.550000, 0.950000), 0.0, 1.0);
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
| `[0.0000, 0.0000, 0.0000]` | `[0.1446, 0.1832, 0.1759]` | Greyscale / Primary / Skin / Sky |
| `[0.1000, 0.1000, 0.1000]` | `[0.1470, 0.1643, 0.1418]` | Greyscale / Primary / Skin / Sky |
| `[0.2000, 0.2000, 0.2000]` | `[0.2043, 0.2235, 0.2628]` | Greyscale / Primary / Skin / Sky |
| `[0.3000, 0.3000, 0.3000]` | `[0.2635, 0.3052, 0.3867]` | Greyscale / Primary / Skin / Sky |
| `[0.4000, 0.4000, 0.4000]` | `[0.3231, 0.3867, 0.4933]` | Greyscale / Primary / Skin / Sky |
| `[0.5000, 0.5000, 0.5000]` | `[0.3944, 0.4679, 0.5809]` | Greyscale / Primary / Skin / Sky |
| `[0.6000, 0.6000, 0.6000]` | `[0.4757, 0.5486, 0.6504]` | Greyscale / Primary / Skin / Sky |
| `[0.7000, 0.7000, 0.7000]` | `[0.5668, 0.6296, 0.7035]` | Greyscale / Primary / Skin / Sky |
| `[0.8000, 0.8000, 0.8000]` | `[0.6712, 0.7181, 0.7486]` | Greyscale / Primary / Skin / Sky |
| `[0.9000, 0.9000, 0.9000]` | `[0.7822, 0.7993, 0.7442]` | Greyscale / Primary / Skin / Sky |
| `[1.0000, 1.0000, 1.0000]` | `[1.0000, 0.9593, 0.8791]` | Greyscale / Primary / Skin / Sky |
| `[1.0000, 0.0000, 0.0000]` | `[1.0000, 0.1816, 0.1362]` | Greyscale / Primary / Skin / Sky |
| `[0.0000, 1.0000, 0.0000]` | `[0.0000, 0.1611, 0.0000]` | Greyscale / Primary / Skin / Sky |
| `[0.0000, 0.0000, 1.0000]` | `[0.1612, 0.7560, 1.0000]` | Greyscale / Primary / Skin / Sky |
| `[1.0000, 1.0000, 0.0000]` | `[1.0000, 1.0000, 1.0000]` | Greyscale / Primary / Skin / Sky |
| `[0.0000, 1.0000, 1.0000]` | `[0.0453, 1.0000, 1.0000]` | Greyscale / Primary / Skin / Sky |
| `[1.0000, 0.0000, 1.0000]` | `[1.0000, 1.0000, 1.0000]` | Greyscale / Primary / Skin / Sky |
| `[0.9300, 0.8990, 0.8480]` | `[1.0000, 0.9484, 0.8573]` | Greyscale / Primary / Skin / Sky |
| `[0.9320, 0.8880, 0.8100]` | `[1.0000, 0.9681, 0.8530]` | Greyscale / Primary / Skin / Sky |
| `[0.1750, 0.3660, 0.6650]` | `[0.1046, 0.5434, 0.9873]` | Greyscale / Primary / Skin / Sky |
| `[0.4410, 0.5080, 0.7630]` | `[0.2989, 0.6412, 1.0000]` | Greyscale / Primary / Skin / Sky |
| `[0.4840, 0.0950, 0.0860]` | `[0.7830, 0.2006, 0.1509]` | Greyscale / Primary / Skin / Sky |
| `[0.1940, 0.2270, 0.2660]` | `[0.1884, 0.2644, 0.3616]` | Greyscale / Primary / Skin / Sky |
| `[0.0870, 0.0120, 0.0130]` | `[0.1430, 0.1445, 0.1342]` | Greyscale / Primary / Skin / Sky |

### 5.2 Gradient Stage Test Vectors
| Frame y (0=top, 1=bottom) | Multiplier RGB |
|---|---|
| `0.00` | `[1.0000, 1.0000, 1.0000]` |
| `0.20` | `[1.0000, 1.0000, 1.0000]` |
| `0.40` | `[0.9931, 0.9843, 0.9836]` |
| `0.60` | `[0.9672, 0.9257, 0.9224]` |
| `0.80` | `[0.9450, 0.8755, 0.8699]` |
| `1.00` | `[0.9428, 0.8704, 0.8645]` |

### 5.3 Flare Contribution Test Vectors (Input = Mid-Grey 0.50)
| Coordinates (x, y) | Output RGB |
|---|---|
| `(0.50, 0.05)` | `[0.5210, 0.5330, 0.5570]` |
| `(0.10, 0.10)` | `[0.5140, 0.5220, 0.5380]` |
| `(0.90, 0.10)` | `[0.5140, 0.5220, 0.5380]` |
| `(0.50, 0.50)` | `[0.5092, 0.5144, 0.5249]` |
| `(0.10, 0.90)` | `[0.5007, 0.5012, 0.5020]` |
| `(0.90, 0.90)` | `[0.5007, 0.5012, 0.5020]` |

---

## 6. Known Limits and Noise Floor
1. **AI Reconstruction Floor:** Matched originals have an intrinsic ~2.9 levels / 255 baseline drift.
2. **Export Recompression:** Source frames from mobile AMV exports contain block-quantization artifacts.
3. **Resolution Independence:** All coordinate axes are normalized to full-frame bounds; spatial blur sigma scales directly with frame height (`sigma_px = sigma_frac_h * H`).
