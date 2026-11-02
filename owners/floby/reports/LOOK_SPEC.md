# LOOK_SPEC: MOTIONSALT Keyflaw Look Specification

**Document status:** Complete, machine-verified specification (`v1.0.0`)  
**Source of truth parameters:** [`look_params.json`](./look_params.json)  
**Reference ground-truth implementation:** [`look_apply.py`](./look_apply.py)  
**3D LUT export (Stage 2 colour grade only):** [`look.cube`](./look.cube) (`33 × 33 × 33`)

This document specifies the complete colour grade and "quality" processing look recovered from two MOTIONSALT anime edit frame pairs (**Pair A** `1278×720` and **Pair B** `1291×720` / `720×409`), incorporating the **Magic Bullet Looks "Dade"** selective foliage & cool-shadow colour behaviour. A downstream engineer or AI reading **only** this document (and optionally loading `look_params.json`) has every equation, constant, coordinate convention, clamping rule, uniform control mapping, and unit test vector needed to implement the `.kfpack` effect in **Keyflaw**.

---

## 1. TL;DR of the Look

The look is a **4-stage, single-pass, resolution-independent pipeline** operating in **gamma-encoded sRGB `[0.0, 1.0]`**:

1. **Crisp Anime Line-Art Unsharp Mask (Stage 1):** A 25-tap (`5×5` separable `[1, 4, 6, 4, 1] / 16` stencil) RGB unsharp mask with blur step `sigma_px = 0.003473 * H` (`2.50 px` at `720p`, `3.75 px` at `1080p`), `amount = 0.82`, and soft coring `threshold = 0.01433` (`3.65 / 255`) that deepens dark ink contours without amplifying flat-cel compression grain.
2. **Dade Colour Grade (Stage 2 — `M2_Dade_srgb`):**
   - **Per-channel sRGB Levels** (`gamma = [0.8206, 0.8892, 0.8632]`) that add punchy contrast, lift warm highlights, and anchor deep shadows.
   - **Cool Slate-Blue Shadow Toe** (`luma < 0.28`) imparting a subtle `+7..+13 / 255` cyan-blue tint in dark hair and line-art shadows.
   - **Neutral-Preserving `3×3` Colour Matrix** (`~1.20×` effective chroma boost) warming skin tones, reds, and straw-hat golds.
   - **Closed-Form Magic Bullet Looks "Dade" Opponent Hue-Chroma Shaper** that keeps warm skin, gold (`H ≈ 38°–43°`), and bright anime yellows (`H ≈ 50°–55°`) completely intact while rotating yellow-green and green foliage (`H ∈ [60°, 155°]`) by **`+38°` to `+52°` into cool bluish-green / Miami-Dade teal**, boosting deep teal-greens (`162°`), cooling sky blues (`198°`), and giving purples/plums (`315°`) a cool blue-violet undertone.
3. **Lower-Frame Darkening Multiply Gradient (Stage 3):** A smooth vertical `smoothstep` ramp starting near the upper seventh of the frame (`y0_norm = 0.1400`) and saturating in the lower quarter (`y1_norm = 0.758341`), multiplying RGB by `1.0 - r * [0.262739, 0.256392, 0.280550]` (`~25.9%` luma darkening at the bottom with a subtle warm-amber bias because Blue darkens slightly more than Red/Green).
4. **Top-Right Anisotropic Gaussian Haze Flare (Stage 4):** A broad, soft rotated 2D Gaussian glow in the upper-right quadrant (`cx ≈ 0.87–0.96`, `cy ≈ 0.02–0.18`, `rx ≈ 0.19 * H`, `ry ≈ 0.25–0.30 * H`) composited via **Screen** blend (`1 - (1 - base) * (1 - flare)`), lifting dark hair and upper-right shadows into a hazy glow without clipping bright highlights.

---

## 2. Pipeline Order & Stated Keyflaw Shader Assumptions

### 2.1 Numbered Order of Operations

Every pixel is processed in this exact order:

```text
Input Texture (gamma-encoded sRGB [0, 1])
   │
   ▼
[Stage 1] 25-Tap RGB Unsharp Mask  ──► clamped to [0.0, 1.0]
   │
   ▼
[Stage 2] Dade Colour Correction   ──► clamped >= 0.0 (unclamped > 1.0 if Stage 3 is enabled;
   │                                   clamped to [0.0, 1.0] if Stage 3 is disabled)
   ▼
[Stage 3] Vertical Multiply Grad   ──► clamped to [0.0, 1.0]
   │
   ▼
[Stage 4] Anisotropic Screen Flare ──► clamped to [0.0, 1.0]
   │
   ▼
[Master Mix] mix(raw_center_rgb, stage4_rgb, u_master_intensity) ──► Output FragColor
```

**Why Stage 1 (Unsharp Mask) comes first:**
1. **Empirical accuracy:** Across all 5 candidate pipeline permutations tested in Q7 (`USM→CC→GRAD→FLARE`, `CC→GRAD→USM→FLARE`, `CC→USM→GRAD→FLARE`, `CC→GRAD→FLARE→USM`, `GRAD→CC→USM→FLARE`), `USM → CC → GRAD → FLARE` tied for the lowest flat colour error (`mean median CIEDE2000 = 2.1963`) while achieving the **lowest edge residual (`mean Edge RMSE = 18.125 / 255`)** and **highest structural similarity (`mean Luma SSIM = 0.94028`)** on both pairs.
2. **Single-pass GLSL constraint:** Because Keyflaw executes a single fragment pass without intermediate FBOs, placing Unsharp Mask first means all 25 `texture()` taps read directly from the input video texture `u_tex`, and Stages 2–4 run **once** per fragment in pure ALU registers instead of 25 times per fragment.

### 2.2 Stated Architectural Assumptions (Confirm When Building `.kfpack`)

> **Important Assumption Notice for the Keyflaw Pack Builder:**  
> The following runtime constraints were assumed when designing this specification and **must be confirmed** against Keyflaw's `.kfpack` shader host:
> 1. **Single-pass fragment shader:** `shader.glsl` runs in a single pass per output pixel with no multi-pass ping-pong buffers.
> 2. **Uniforms + input frame only:** Only the input video frame `sampler2D` and scalar/vector uniforms from `effect.json` are available (no external 1D/3D `.cube` LUT textures or auxiliary noise/mask images).
> 3. **25-tap texture budget:** Up to 25 bilinear `texture()` lookups per fragment are fast enough for real-time mobile playback.
> 4. **Gamma-encoded sRGB `[0, 1]` sampling:** `texture(u_tex, uv).rgb` returns standard non-linear Rec.709 / sRGB values in `[0.0, 1.0]` (not linear-light float). If Keyflaw binds an `SRGB8_ALPHA8` texture that hardware-linearises on fetch, convert back to gamma-encoded sRGB before Stage 1 and linearise at output.
> 5. **Top-left normalised coordinate convention:** In all equations below, `x_norm ∈ [0, 1]` runs **left (`0.0`) to right (`1.0`)** and `y_norm ∈ [0, 1]` runs **top (`0.0`) to bottom (`1.0`)** across the full frame (including any baked-in letterbox bars). **If Keyflaw uses OpenGL bottom-left UV origin (`v_uv.y = 0` at bottom, `1` at top), compute `float y_norm = 1.0 - v_uv.y;` before Stages 3 and 4.**

---

## 3. Stage-by-Stage Specification

### Stage 1: Resolution-Independent 25-Tap RGB Unsharp Mask

- **Working colour space:** Gamma-encoded sRGB `[0.0, 1.0]`.
- **Confidence:** **High** on radius scaling (`sigma_frac_h = 0.003473`, independent fits agree within `9.5%` between Pair A `720p` and Pair B `409p` and reduce edge-profile RMSE by **`38.9%`** on Pair A, **`39.3%`** on Pair B `720p`, and **`33.6%`** on Pair B `409p`); **Medium-High** on `amount = 0.82` and soft coring `threshold = 0.01433` (jointly calibrated on 2D full-frame edge bands after separating AI-reconstruction vs recompression softness).

#### Mathematical Definition & GLSL Pseudocode

Let frame dimensions be `(W, H)` in pixels, `sigma_px = u_usm_sigma_frac_h * H`, and `w1d = [1, 4, 6, 4, 1] / 16`:

```glsl
const float USM_W1D[5] = float[5](0.0625, 0.25, 0.375, 0.25, 0.0625);

vec3 stage1_unsharp(sampler2D tex, vec2 uv, vec2 resolution,
                    float sigma_frac_h, float amount, float threshold) {
    vec3 center = clamp(texture(tex, uv).rgb, 0.0, 1.0);
    float sigma_px = sigma_frac_h * resolution.y;
    if (amount <= 1e-6 || sigma_px <= 1e-5) {
        return center;
    }

    vec2 step_uv = vec2(sigma_px) / resolution;
    vec3 blur = vec3(0.0);
    for (int j = -2; j <= 2; ++j) {
        float wj = USM_W1D[j + 2];
        for (int i = -2; i <= 2; ++i) {
            float w = wj * USM_W1D[i + 2];
            vec2 sample_uv = clamp(uv + vec2(float(i), float(j)) * step_uv,
                                   vec2(0.5) / resolution,
                                   vec2(1.0) - vec2(0.5) / resolution);
            blur += w * texture(tex, sample_uv).rgb;
        }
    }

    vec3 d = center - blur;
    vec3 d_cored = sign(d) * max(abs(d) - vec3(threshold), vec3(0.0));
    return clamp(center + amount * d_cored, 0.0, 1.0);
}
```

> **Note on UV border clamping:** Clamping `sample_uv` to `[0.5 / resolution, 1.0 - 0.5 / resolution]` (or setting `GL_CLAMP_TO_EDGE` on `u_tex`) matches `cv2.BORDER_REPLICATE` in `look_apply.py` so frame borders never bleed wrap-around texels.

#### Stage 1 Parameter Table

| Parameter | Canonical Value | Unit | Valid Range | Pixel Value (`1278×720` / `1291×720` / `720×409` / `1920×1080`) | Meaning |
|---|---:|---|---|---|
| `sigma_frac_h` | `0.003473` | fraction of `H` | `[0.0005, 0.0120]` | `2.5006 px` / `2.5006 px` / `1.4205 px` / `3.7508 px` | Tap spacing per integer step `(i, j) ∈ {-2..2}` |
| `amount` | `0.820000` | dimensionless | `[0.00, 2.50]` | — | High-frequency detail gain |
| `threshold_01` | `0.014330` | sRGB `[0..1]` | `[0.0000, 0.0800]` | `3.654 / 255` | Soft-coring deadzone suppressing flat-region codec noise |

---

### Stage 2: Closed-Form Dade Colour Correction (`M2_Dade_srgb`)

- **Working colour space:** Gamma-encoded sRGB `[0.0, 1.0]`.
- **Confidence:**
  - **High** on Levels, Shadow Toe, and `3×3` Base Matrix across `[16..251]` R, `[21..253]` G, `[25..254]` B (`held-out median CIEDE2000 = 2.2586` vs `in-sample 2.2392`, generalisation gap `+0.0194 << 1.0`; beats linear-light models on both pairs).
  - **High** on `teal_greens (162°)`, `cyan_sky (198°)`, and `violet_plum (315°)` shaper lobes (directly anchored by observed sky, Chopper cyan hat, foreground teal-green cloak, and Luffy purple sash clusters across the pairs).
  - **Medium** (domain-prior guided) on the `foliage_window` (`56°..172°`) rotation magnitude (`+43.412°`), calibrated from Magic Bullet Looks **Dade** LUT behaviour and the observed Pair B dark-green foliage interior cluster (`H_out ≈ 141°–165°`) because Pair A contains no foliage and Pair B's AI reconstruction mis-coloured the background bush as `H = 47°` golden-yellow (see Section 7).

#### Mathematical Sub-Stages (`2a` → `2d`)

Given input `x = clamp(rgb_in, 0.0, 1.0)`:

1. **Sub-stage 2a — Per-Channel Levels:**
   $$t_c = \operatorname{clamp}\!\left(\frac{x_c - \text{in\_black}_c}{\max(\text{in\_white}_c - \text{in\_black}_c,\, 10^{-4})},\, 0.0,\, 1.0\right)$$
   $$u_c = \left(\max(t_c,\, 10^{-8})\right)^{\text{gamma}_c}, \qquad v^{(0)}_c = \text{out\_black}_c + u_c \cdot (\text{out\_white}_c - \text{out\_black}_c)$$

2. **Sub-stage 2b — Dade Cool Slate-Blue Shadow Toe:**
   $$Y_{\text{in}} = 0.2126\,x_R + 0.7152\,x_G + 0.0722\,x_B$$
   $$w_{\text{toe}} = 1.0 - \operatorname{smoothstep}(0.0,\, 0.28,\, Y_{\text{in}})$$
   $$v_c = v^{(0)}_c + w_{\text{toe}} \cdot \text{shadow\_lift}_c \cdot \max(1.0 - v^{(0)}_c,\, 0.0)$$

3. **Sub-stage 2c — Neutral-Preserving `3×3` Colour Matrix:**
   $$\mathbf{m} = \mathbf{M}_{3\times 3}\,\mathbf{v} \qquad \text{(row-vector form in GLSL: } m_i = \operatorname{dot}(\text{row}_i,\, \mathbf{v})\text{)}$$

4. **Sub-stage 2d — Closed-Form Opponent-Polar Dade Hue-Chroma Shaper:**
   Convert $\mathbf{m} = (m_R, m_G, m_B)$ into the exact invertible opponent-chroma basis $(A, o_u, o_v)$, where pure neutrals have $o_u = o_v = 0$, Red is $0^\circ$, Yellow is $60^\circ$, Green is $120^\circ$, Cyan is $180^\circ$, Blue is $240^\circ$, and Magenta is $300^\circ$:
   $$A = \frac{m_R + m_G + m_B}{3}, \qquad o_u = m_R - 0.5\,(m_G + m_B), \qquad o_v = \frac{\sqrt{3}}{2}\,(m_G - m_B)$$
   $$C = \sqrt{o_u^2 + o_v^2 + 10^{-8}}, \qquad h_u = \frac{o_u}{C}, \qquad h_v = \frac{o_v}{C}$$
   $$g_C = \operatorname{smoothstep}(0.015,\, 0.060,\, C) \cdot u_{\text{dade\_strength}}$$
   Compute opponent hue angle $h_{\text{deg}} = \operatorname{mod}(\operatorname{degrees}(\operatorname{atan2}(o_v, o_u)) + 360.0,\, 360.0) \in [0, 360)$:
   - **Windowed Foliage Gate** (zero leakage at $h_{\text{deg}} \le 56^\circ$, protecting all skin, straw gold, and yellow clothing/blonde hair):
     $$w_{\text{fol}} = \operatorname{smoothstep}(56.0,\, 68.0,\, h_{\text{deg}}) \cdot \bigl(1.0 - \operatorname{smoothstep}(138.0,\, 172.0,\, h_{\text{deg}})\bigr)$$
   - **Three Smooth von-Mises Hue Lobes** ($k \in \{0, 1, 2\}$):
     $$w_k = \exp\!\Bigl(\kappa_k \cdot \bigl(h_u \cos\theta_k + h_v \sin\theta_k - 1.0\bigr)\Bigr)$$
   Accumulate total hue rotation $\Delta h$ (radians), relative chroma gain $\Delta c$, and chroma-proportional lightness offset $\Delta a$:
   $$\Delta h = g_C \cdot \left(w_{\text{fol}}\,\Delta h_{\text{fol}} + \sum_{k=0}^{2} w_k\,\Delta h_k\right)$$
   $$s_C = \max\!\left(0.0,\; 1.0 + g_C \cdot \left(w_{\text{fol}}\,\Delta c_{\text{fol}} + \sum_{k=0}^{2} w_k\,\Delta c_k\right)\right)$$
   $$A' = A + g_C \cdot C \cdot \left(w_{\text{fol}}\,\Delta a_{\text{fol}} + \sum_{k=0}^{2} w_k\,\Delta a_k\right)$$
   Rotate $(o_u, o_v)$ by $\Delta h$, scale by $s_C$, and invert the opponent transform exactly:
   $$o_u' = s_C\,(o_u \cos\Delta h - o_v \sin\Delta h), \qquad o_v' = s_C\,(o_u \sin\Delta h + o_v \cos\Delta h)$$
   $$\text{out}_R = A' + \frac{2}{3}\,o_u', \qquad \text{out}_G = A' - \frac{1}{3}\,o_u' + \frac{1}{\sqrt{3}}\,o_v', \qquad \text{out}_B = A' - \frac{1}{3}\,o_u' - \frac{1}{\sqrt{3}}\,o_v'$$
   Finally clamp negative excursions: $\text{out} = \max(\text{out},\, 0.0)$ (and if Stage 3 is disabled, $\operatorname{clamp}(\text{out},\, 0.0,\, 1.0)$).

#### GLSL Pseudocode for Stage 2

```glsl
const vec3 LUMA_W = vec3(0.2126, 0.7152, 0.0722);
const float SQRT3_2   = 0.8660254037844386;
const float INV_SQRT3 = 0.5773502691896257;

vec3 stage2_colour_correction(vec3 rgb_in, float dade_strength, bool clamp_hi) {
    vec3 x = clamp(rgb_in, 0.0, 1.0);

    // 2a. Per-channel Levels
    const vec3 IN_BLACK  = vec3(-0.079999, -0.077538,  0.035829);
    const vec3 IN_WHITE  = vec3( 0.934037,  0.929412,  0.963913);
    const vec3 GAMMA_V   = vec3( 0.820622,  0.889244,  0.863185);
    const vec3 OUT_BLACK = vec3(-0.112643, -0.119988,  0.029787);
    const vec3 OUT_WHITE = vec3( 1.017020,  1.012705,  1.080600);

    vec3 t = clamp((x - IN_BLACK) / max(IN_WHITE - IN_BLACK, vec3(1e-4)), 0.0, 1.0);
    vec3 u = pow(max(t, vec3(1e-8)), GAMMA_V);
    vec3 v = OUT_BLACK + u * (OUT_WHITE - OUT_BLACK);

    // 2b. Dade Cool Slate Shadow Toe
    const vec3 SHADOW_LIFT = vec3(-0.008286, 0.028697, 0.049749);
    float lum = dot(x, LUMA_W);
    float toe_w = 1.0 - smoothstep(0.0, 0.28, lum);
    v += (toe_w * SHADOW_LIFT) * max(vec3(1.0) - v, vec3(0.0));

    // 2c. 3x3 Base Colour Matrix (row dot products)
    vec3 m;
    m.r = dot(vec3( 1.451550, -0.243174, -0.208376), v);
    m.g = dot(vec3( 0.024565,  1.124975, -0.149540), v);
    m.b = dot(vec3(-0.208747,  0.087738,  1.121009), v);

    // 2d. Closed-Form Dade Opponent-Polar Hue-Chroma Shaper
    float A  = (m.r + m.g + m.b) * (1.0 / 3.0);
    float ou = m.r - 0.5 * (m.g + m.b);
    float ov = SQRT3_2 * (m.g - m.b);
    float C  = sqrt(ou * ou + ov * ov + 1e-8);
    float hu = ou / C;
    float hv = ov / C;

    float c_gate = smoothstep(0.015, 0.060, C) * dade_strength;

    // Windowed foliage gate: 0 below 56 deg (protects skin/gold/yellow), active across 56..172 deg
    float h_deg = mod(degrees(atan(ov, ou)) + 360.0, 360.0);
    float w_fol = smoothstep(56.0, 68.0, h_deg) * (1.0 - smoothstep(138.0, 172.0, h_deg));

    float dh = w_fol *  0.757676;
    float dc = w_fol * -0.079099;
    float da = w_fol * -0.120041;

    // Lobe 0: teal_greens (162 deg)
    float w0 = exp(5.5 * (hu * -0.951057 + hv *  0.309017 - 1.0));
    dh += w0 * -0.110860;
    dc += w0 *  0.391882;
    da += w0 *  0.180000;

    // Lobe 1: cyan_sky (198 deg)
    float w1 = exp(5.5 * (hu * -0.951057 + hv * -0.309017 - 1.0));
    dh += w1 * -0.045421;
    dc += w1 * -0.159362;
    da += w1 *  0.062555;

    // Lobe 2: violet_plum (315 deg)
    float w2 = exp(3.0 * (hu *  0.707107 + hv * -0.707107 - 1.0));
    dh += w2 * -0.325884;
    dc += w2 * -0.266123;
    da += w2 * -0.153217;

    float dh_tot = c_gate * dh;
    float sC_tot = max(0.0, 1.0 + c_gate * dc);
    float A2     = A + c_gate * C * da;

    float cd  = cos(dh_tot);
    float sd  = sin(dh_tot);
    float ou2 = sC_tot * (ou * cd - ov * sd);
    float ov2 = sC_tot * (ou * sd + ov * cd);

    vec3 out_rgb;
    out_rgb.r = A2 + (2.0 / 3.0) * ou2;
    out_rgb.g = A2 - (1.0 / 3.0) * ou2 + INV_SQRT3 * ov2;
    out_rgb.b = A2 - (1.0 / 3.0) * ou2 - INV_SQRT3 * ov2;

    out_rgb = max(out_rgb, vec3(0.0));
    return clamp_hi ? min(out_rgb, vec3(1.0)) : out_rgb;
}
```

#### Stage 2 Parameter Table

| Sub-Stage | Parameter | Canonical Value | Unit | Valid Range | Meaning |
|---|---|---|---|---|---|
| Levels | `in_black` | `[-0.079999, -0.077538, 0.035829]` | sRGB `[0..1]` | `[-0.20, 0.25]` | Input black point (crushes deep Blue `< 9/255`, lifts R/G floor pre-gamma) |
| Levels | `in_white` | `[0.934037, 0.929412, 0.963913]` | sRGB `[0..1]` | `[0.75, 1.15]` | Input white point (`~238, 237, 246 / 255`) |
| Levels | `gamma` | `[0.820622, 0.889244, 0.863185]` | exponent | `[0.50, 1.50]` | Midtone lift (`< 1.0` brightens midtones before gradient multiply) |
| Levels | `out_black` | `[-0.112643, -0.119988, 0.029787]` | sRGB `[0..1]` | `[-0.25, 0.20]` | Output black anchor (expands R/G contrast, lifts B shadow floor) |
| Levels | `out_white` | `[1.017020, 1.012705, 1.080600]` | sRGB `[0..1]` | `[0.85, 1.20]` | Highlight headroom fed into Stage 3 Multiply gradient |
| Shadow Toe | `luma_end` | `0.280000` | Rec.709 luma | `[0.10, 0.45]` | Upper luma bound of cool shadow toe (`~71 / 255`) |
| Shadow Toe | `shadow_lift_rgb` | `[-0.008286, 0.028697, 0.049749]` | sRGB offset | `[-0.10, 0.15]` | Dade cool slate-cyan shadow tint (`G +7.3`, `B +12.7 / 255` at black) |
| Matrix | `matrix_row0` | `[1.451550, -0.243174, -0.208376]` | linear coeff | row sum `= 1.0` | Red output mix (row sum `1.000000` preserves neutral axis) |
| Matrix | `matrix_row1` | `[0.024565, 1.124975, -0.149540]` | linear coeff | row sum `= 1.0` | Green output mix (row sum `1.000000`) |
| Matrix | `matrix_row2` | `[-0.208747, 0.087738, 1.121009]` | linear coeff | row sum `= 1.0` | Blue output mix (row sum `1.000000`) |
| Dade Shaper | `chroma_gate` | `[0.015, 0.060]` | opponent `C` | `[0.005, 0.15]` | Smoothly disables hue rotation on neutrals (`C <= 0.015` = exact `0`) |
| Dade Shaper | `foliage_window` | `56°..68°` rise, `138°..172°` fall | degrees | `0°..360°` | Isolates yellow-green & green foliage (`0.0` weight at `<= 56°` yellows/gold) |
| Dade Shaper | `foliage_params` | `dh=+0.757676 rad (+43.412°), dc=-0.079099, da=-0.120041` | rad, gain, luma | — | Rotates yellow-green grass into cool bluish-green / Dade teal |
| Dade Shaper | `teal_greens` | `center=162° (cos=-0.951057, sin=0.309017), kappa=5.5, dh=-0.110860, dc=+0.391882, da=+0.180000` | — | — | Enriches deep teal-green cloaks & foliage shadows |
| Dade Shaper | `cyan_sky` | `center=198° (cos=-0.951057, sin=-0.309017), kappa=5.5, dh=-0.045421, dc=-0.159362, da=+0.062555` | — | — | Keeps sky blues and cyan hats crisp and un-clipped |
| Dade Shaper | `violet_plum` | `center=315° (cos=0.707107, sin=-0.707107), kappa=3.0, dh=-0.325884, dc=-0.266123, da=-0.153217` | — | — | Shifts warm purples (`-18.672°`) toward cool Dade blue-violet |

**Observed vs Extrapolated Input Ranges (`0..255`):**
- **R:** observed `[16, 251]` (extrapolated below `16` and above `251`)
- **G:** observed `[21, 253]` (extrapolated below `21` and above `253`)
- **B:** observed `[25, 254]` (extrapolated below `25` and above `254`)

---

### Stage 3: Vertical Spatial Multiply Gradient

- **Working colour space:** Gamma-encoded sRGB (accepts Stage 2 output directly, including unclamped `> 1.0` highlight headroom, and clamps final result to `[0.0, 1.0]`).
- **Confidence:** **High** (2D spatial residual analysis proved a pure vertical ramp explains **`70.2%`** of Pair A and **`75.7%`** of Pair B spatial variance vs `6.4%` / `0.5%` for a radial vignette; reduces flat median CIEDE2000 from `12.84 → 2.25` on Pair A and `5.92 → 2.66` on Pair B, and drops Pair B's row-mean residual correlation with `y` from `-0.9428` to `-0.0340`).

#### Mathematical Definition & GLSL Pseudocode

With `y_norm ∈ [0.0, 1.0]` (`0.0` = top edge of full frame, `1.0` = bottom edge of full frame):

$$r(y_{\text{norm}}) = \operatorname{smoothstep}(y_0,\, y_1,\, y_{\text{norm}})$$
$$\text{out}_{\text{grad}} = \operatorname{clamp}\!\Bigl(\text{cc\_rgb} \cdot \bigl(\mathbf{1} - r(y_{\text{norm}}) \cdot \mathbf{s}_{\text{rgb}}\bigr),\, 0.0,\, 1.0\Bigr)$$

```glsl
vec3 stage3_gradient(vec3 cc_rgb, float y_norm, float y0, float y1, vec3 strength_rgb) {
    float r = smoothstep(y0, y1, y_norm);
    return clamp(cc_rgb * (vec3(1.0) - r * strength_rgb), 0.0, 1.0);
}
```

#### Stage 3 Parameter Table

| Parameter | Canonical Value | Unit | Valid Range | Pixel Row (`1278×720` / `1291×720` / `720×409` / `1920×1080`) | Meaning |
|---|---:|---|---|---|
| `y0_norm` | `0.140000` | norm `y` `[0..1]` | `[0.00, 0.90]` | `100.80 px` / `100.80 px` / `57.26 px` / `151.20 px` | Top row where darkening ramp begins (`r = 0` above `y0_norm`) |
| `y1_norm` | `0.758341` | norm `y` `[0..1]` | `[0.10, 1.00]` | `546.01 px` / `546.01 px` / `310.16 px` / `819.01 px` | Bottom row where darkening saturates (`r = 1` below `y1_norm`) |
| `strength_rgb` | `[0.262739, 0.256392, 0.280550]` | `[0..1]` multiply | `[0.00, 0.75]` | — | Per-channel bottom darkening (`25.95%` luma; slightly warmer lower shadows) |

---

### Stage 4: 2D Anisotropic Rotated Gaussian Haze Flare (Screen Blend)

- **Working colour space:** Gamma-encoded sRGB `[0.0, 1.0]`.
- **Global additive/screen veil needed?** **No (`false`).** Testing a full-frame uniform veil yielded `≤ 2.5 / 255` on Pair A (inside the `2.9 / 255` reconstruction noise floor) and `0.8 / 255` on Pair B, so it is excluded to keep blacks crisp.
- **Confidence:**
  - **High** on **Screen blend mode**, **2D Gaussian radial falloff**, **top-right placement** (`cx ≈ 0.87–0.96`, `cy ≈ 0.02–0.18`), and **spatial spread** (`rx ≈ 0.19 * H`, `ry ≈ 0.25–0.30 * H`), reducing low-pass spatial residual energy by **`77.2%–85.3%`** on Pair A and **`52.3%–94.7%`** (top-right quadrant) on Pair B.
  - **Low-Medium** on **static cross-clip flare colour & peak intensity**: Pair A exhibits a strong warm-golden sunlight flare (`intensity = 0.34`, `colour = [0.9706, 1.0000, 0.3529]`), whereas Pair B exhibits a subtle cool sky-tinted haze (`intensity = 0.13`, `colour = [0.3846, 0.9231, 1.0000]`). This indicates either per-clip keyframing/tint adjustment by the editor or an optical bloom plugin sampling bright top-right source pixels. We therefore specify **one cross-clip `default` preset** (which improves every metric on *both* pairs out of the box) plus the exact `pairA` and `pairB` presets, and expose `intensity`, `position`, `radius`, and `colour` as Keyflaw controls.

#### Mathematical Definition & GLSL Pseudocode

Using height-normalised offsets so the ellipse shape is invariant to aspect ratio (`aspect = W / H`):

$$\Delta x_h = (x_{\text{norm}} - c_x) \cdot \frac{W}{H}, \qquad \Delta y_h = y_{\text{norm}} - c_y$$
$$u = \frac{\Delta x_h \cos\theta + \Delta y_h \sin\theta}{\max(r_x,\, 0.02)}, \qquad v = \frac{-\Delta x_h \sin\theta + \Delta y_h \cos\theta}{\max(r_y,\, 0.02)}$$
$$\mathbf{f}_{\text{rgb}} = \operatorname{clamp}\!\left(I_{\text{flare}} \cdot \exp\!\bigl(-0.5\,(u^2 + v^2)\bigr) \cdot \mathbf{c}_{\text{flare}},\, 0.0,\, 1.0\right)$$
$$\text{out}_{\text{flare}} = \mathbf{1} - (\mathbf{1} - \text{base\_rgb}) \cdot (\mathbf{1} - \mathbf{f}_{\text{rgb}})$$

```glsl
vec3 stage4_flare(vec3 base_rgb, vec2 uv_top_left, vec2 resolution,
                  vec2 center_norm, vec2 radius_frac_h, float angle_deg,
                  vec3 flare_colour, float intensity) {
    if (intensity <= 1e-6) {
        return clamp(base_rgb, 0.0, 1.0);
    }
    float aspect = resolution.x / max(resolution.y, 1.0);
    float dx_h = (uv_top_left.x - center_norm.x) * aspect;
    float dy_h = (uv_top_left.y - center_norm.y);

    float ang = radians(angle_deg);
    float ca = cos(ang);
    float sa = sin(ang);
    float u = ( dx_h * ca + dy_h * sa) / max(radius_frac_h.x, 0.02);
    float v = (-dx_h * sa + dy_h * ca) / max(radius_frac_h.y, 0.02);

    float w = exp(-0.5 * (u * u + v * v));
    vec3 f_rgb = clamp(intensity * w * flare_colour, 0.0, 1.0);
    vec3 b = clamp(base_rgb, 0.0, 1.0);
    return clamp(vec3(1.0) - (vec3(1.0) - b) * (vec3(1.0) - f_rgb), 0.0, 1.0);
}
```

#### Stage 4 Parameter Table (Default + Per-Scene Presets)

| Parameter | `default` (Shared Cross-Clip) | `pairA` (Golden Sunlight) | `pairB` (Cool Sky) | Unit | Valid Range | Meaning |
|---|---:|---:|---:|---|---|---|
| `cx` | `0.869336` | `0.958064` | `0.897110` | norm `x` `[0..1]` | `[-0.20, 1.20]` | Horizontal flare centre (`0`=left, `1`=right) |
| `cy` | `0.081183` | `0.183344` | `0.021277` | norm `y` `[0..1]` | `[-0.20, 1.20]` | Vertical flare centre (`0`=top, `1`=bottom) |
| `rx_frac_h` | `0.185390` | `0.193505` | `0.194185` | fraction of `H` | `[0.02, 0.80]` | Principal axis 1 Gaussian sigma |
| `ry_frac_h` | `0.248768` | `0.301423` | `0.261388` | fraction of `H` | `[0.02, 0.80]` | Principal axis 2 Gaussian sigma |
| `angle_deg` | `-72.9434` | `-41.45956` | `66.823434` | degrees | `[-90.0, 90.0]` | Clockwise ellipse rotation in top-left coords |
| `colour_rgb` | `[0.437628, 1.000000, 0.984158]` | `[0.970588, 1.000000, 0.352941]` | `[0.384615, 0.923077, 1.000000]` | sRGB `[0..1]` | `[0.0, 1.0]^3` | Peak normalised tint colour |
| `intensity` | `0.118307` | `0.340000` | `0.130000` | `[0..1]` | `[0.00, 0.85]` | Peak Screen glow strength |

**Pixel Equivalents of Flare Geometry:**
- **`default` preset:**
  - At `1278×720` (Pair A): `(cx, cy) = (1111.01, 58.45) px`, `(rx, ry) = (133.48, 179.11) px`
  - At `1291×720` (Pair B edit): `(cx, cy) = (1122.31, 58.45) px`, `(rx, ry) = (133.48, 179.11) px`
  - At `720×409` (Pair B orig): `(cx, cy) = (625.92, 33.20) px`, `(rx, ry) = (75.82, 101.75) px`
- **`pairA` preset:**
  - At `1278×720`: `(cx, cy) = (1224.41, 132.01) px`, `(rx, ry) = (139.32, 217.02) px`
  - At `720×409`: `(cx, cy) = (689.81, 74.99) px`, `(rx, ry) = (79.14, 123.28) px`
- **`pairB` preset:**
  - At `1291×720`: `(cx, cy) = (1158.17, 15.32) px`, `(rx, ry) = (139.81, 188.20) px`
  - At `720×409`: `(cx, cy) = (645.92, 8.70) px`, `(rx, ry) = (79.42, 106.91) px`

---

## 4. Suggested Keyflaw Control Sheet (`effect.json`)

Expose a clean, mobile-friendly set of controls in Keyflaw so users get the exact look at default settings while being able to dial the scene-dependent flare or Dade foliage intensity in seconds:

| Control Label | Uniform Name | Type | Default | Min | Max | Step | Notes |
|---|---|---|---:|---:|---:|---:|---|
| **Master Intensity** | `u_master_intensity` | `float` | `1.00` | `0.00` | `1.00` | `0.01` | Linearly mixes ungraded input (`0.0`) with full look (`1.0`) |
| **Enable Unsharp** | `u_enable_unsharp` | `bool` | `true` | — | — | — | Bypasses 25-tap blur (`1` texture tap when `false`) |
| **Sharpness Amount** | `u_usm_amount` | `float` | `0.82` | `0.00` | `2.00` | `0.01` | Stage 1 USM gain |
| **Sharpness Radius (% H)** | `u_usm_sigma_frac_h` | `float` | `0.003473` | `0.0010` | `0.0080` | `0.0001` | UI can display `0.35%` of height (`2.5 px @ 720p`) |
| **Enable Colour Grade** | `u_enable_cc` | `bool` | `true` | — | — | — | Toggles Stage 2 `M2_Dade_srgb` |
| **Dade Foliage / Teal** | `u_dade_strength` | `float` | `1.00` | `0.00` | `1.50` | `0.01` | `1.0` = authentic Dade bluish-green grass; `0.0` = base 3×3 matrix only |
| **Enable Bottom Vignette** | `u_enable_gradient` | `bool` | `true` | — | — | — | Toggles Stage 3 vertical Multiply gradient |
| **Bottom Darken** | `u_grad_scale` | `float` | `1.00` | `0.00` | `2.00` | `0.01` | Scales `strength_rgb = u_grad_scale * [0.262739, 0.256392, 0.280550]` |
| **Gradient Start / End Y** | `u_grad_y0`, `u_grad_y1` | `float` | `0.14`, `0.7583` | `0.00` | `1.00` | `0.01` | Top-to-bottom normalised `smoothstep` bounds |
| **Enable Haze Flare** | `u_enable_flare` | `bool` | `true` | — | — | — | Toggles Stage 4 Screen glow |
| **Flare Intensity** | `u_flare_intensity` | `float` | `0.1183` | `0.00` | `0.60` | `0.01` | Use `0.34` for strong sunlit shots (Pair A) |
| **Flare Position (X, Y)** | `u_flare_center` | `vec2` | `(0.8693, 0.0812)` | `(-0.2, -0.2)` | `(1.2, 1.2)` | `0.01` | Top-left normalised coordinates |
| **Flare Radius (RX, RY)** | `u_flare_radius` | `vec2` | `(0.1854, 0.2488)` | `(0.05, 0.05)` | `(0.60, 0.60)` | `0.01` | Fractions of frame height `H` |
| **Flare Angle (deg)** | `u_flare_angle_deg` | `float` | `-72.94` | `-90.0` | `90.0` | `1.0` | Use `-41.5°` for Pair A preset |
| **Flare Tint** | `u_flare_colour` | `color` | `#70FFFB` | — | — | — | `[0.4376, 1.0, 0.9842]` default; `#F8FF5A` (`[0.9706, 1.0, 0.3529]`) for Pair A warm sunlight |

---

## 5. Shader Implementation Notes

1. **Inter-stage Clamping Rule (Critical for Exact Parity):**
   - Stage 1 (`stage1_unsharp`) **clamps** to `[0.0, 1.0]`.
   - Stage 2 (`stage2_colour_correction`) **clamps only the lower bound** (`max(rgb, 0.0)`) when `u_enable_gradient == true`, preserving values in `[1.0, 1.0806]` (`out_white`) so that Stage 3's Multiply ramp (`1.0 - r * strength_rgb`) brings bright lower-frame highlights smoothly back into `[0.0, 1.0]` without flat-topping them prematurely. When `u_enable_gradient == false` (or when baking `look.cube`), clamp Stage 2 to `[0.0, 1.0]`.
   - Stage 3 (`stage3_gradient`) and Stage 4 (`stage4_flare`) both **clamp** their outputs to `[0.0, 1.0]`.
2. **Two-Argument `atan(y, x)` & `mod` in GLSL:**
   - In GLSL, write `atan(ov, ou)` (two arguments, equivalent to C/Python `atan2(ov, ou)`), **never** `atan(ov / ou)`.
   - Wrap to `[0, 360)` via `mod(degrees(atan(ov, ou)) + 360.0, 360.0)` because GLSL `degrees(atan(ov, ou))` returns `[-180, 180]`.
3. **Safe `pow()` and `sqrt()` Guards:**
   - Mobile GPUs (`mediump` / `highp` Adreno & Mali) produce `NaN` on `pow(0.0, gamma)` or `sqrt(0.0)` derivatives. Always use **`highp float;`** in the fragment shader and retain `max(t, vec3(1e-8))` inside `pow(...)` and `+ 1e-8` inside `sqrt(ou * ou + ov * ov + 1e-8)`.
4. **Alpha Preservation:**
   - Preserve input alpha (`fragColor = vec4(final_rgb, center_rgba.a);`).

---

## 6. Machine-Verified Unit Test Vectors

Every vector below was generated directly by `look_apply.py` + `look_params.json`. A conforming GLSL shader must reproduce all floating-point outputs within `±0.002` (`≤ ±1 / 255` in 8-bit output).

### 6.1 Stage 2 Colour Correction Test Vectors (29 Vectors, `dade_strength = 1.0`, Clamped `[0, 1]`)

Includes the 10-step neutral ramp, all 6 RGBCMY cube corners, observed anime palette colours, and **Dade yellow-green → bluish-green foliage verification vectors**:

| # | Swatch Label | Input `RGB (0..255)` | Input `sRGB (0..1)` | Output `sRGB (0..1)` | Output `RGB (0..255)` |
|---:|---|---|---|---|---|
| 1 | Grey 0 (Black) | `[0, 0, 0]` | `[0.000000, 0.000000, 0.000000]` | `[0.008126, 0.020979, 0.082973]` | `[2, 5, 21]` |
| 2 | Grey 16 | `[16, 16, 16]` | `[0.062745, 0.062745, 0.062745]` | `[0.106207, 0.096686, 0.119942]` | `[27, 25, 31]` |
| 3 | Grey 32 | `[32, 32, 32]` | `[0.125490, 0.125490, 0.125490]` | `[0.189909, 0.163475, 0.191741]` | `[48, 42, 49]` |
| 4 | Grey 64 | `[64, 64, 64]` | `[0.250980, 0.250980, 0.250980]` | `[0.335401, 0.293443, 0.324252]` | `[86, 75, 83]` |
| 5 | Grey 96 | `[96, 96, 96]` | `[0.376471, 0.376471, 0.376471]` | `[0.470093, 0.433148, 0.467786]` | `[120, 110, 119]` |
| 6 | Grey 128 (Mid) | `[128, 128, 128]` | `[0.501961, 0.501961, 0.501961]` | `[0.600409, 0.569027, 0.605954]` | `[153, 145, 155]` |
| 7 | Grey 160 | `[160, 160, 160]` | `[0.627451, 0.627451, 0.627451]` | `[0.725735, 0.701001, 0.740038]` | `[185, 179, 189]` |
| 8 | Grey 192 | `[192, 192, 192]` | `[0.752941, 0.752941, 0.752941]` | `[0.845275, 0.830081, 0.870848]` | `[216, 212, 222]` |
| 9 | Grey 224 | `[224, 224, 224]` | `[0.878431, 0.878431, 0.878431]` | `[0.960025, 0.957576, 0.998589]` | `[245, 244, 255]` |
| 10 | Grey 255 (White) | `[255, 255, 255]` | `[1.000000, 1.000000, 1.000000]` | `[1.000000, 1.000000, 1.000000]` | `[255, 255, 255]` |
| 11 | Primary Red | `[255, 0, 0]` | `[1.000000, 0.000000, 0.000000]` | `[1.000000, 0.000000, 0.000000]` | `[255, 0, 0]` |
| 12 | Primary Green | `[0, 255, 0]` | `[0.000000, 1.000000, 0.000000]` | `[0.000000, 0.853871, 0.676612]` | `[0, 218, 173]` |
| 13 | Primary Blue | `[0, 0, 255]` | `[0.000000, 0.000000, 1.000000]` | `[0.000000, 0.000000, 1.000000]` | `[0, 0, 255]` |
| 14 | Secondary Yellow | `[255, 255, 0]` | `[1.000000, 1.000000, 0.000000]` | `[1.000000, 1.000000, 0.000000]` | `[255, 255, 0]` |
| 15 | Secondary Cyan | `[0, 255, 255]` | `[0.000000, 1.000000, 1.000000]` | `[0.000000, 1.000000, 1.000000]` | `[0, 255, 255]` |
| 16 | Secondary Magenta | `[255, 0, 255]` | `[1.000000, 0.000000, 1.000000]` | `[0.738946, 0.000000, 0.902887]` | `[188, 0, 230]` |
| 17 | Forehead Bright Skin | `[239, 198, 163]` | `[0.937255, 0.776471, 0.639216]` | `[1.000000, 0.860890, 0.714418]` | `[255, 220, 182]` |
| 18 | Cheek Mid Skin | `[234, 189, 147]` | `[0.917647, 0.741176, 0.576471]` | `[1.000000, 0.827848, 0.641379]` | `[255, 211, 164]` |
| 19 | Neck Deep Shadow | `[156, 98, 67]` | `[0.611765, 0.384314, 0.262745]` | `[0.830666, 0.438418, 0.284325]` | `[212, 112, 73]` |
| 20 | Straw Hat Gold | `[241, 198, 119]` | `[0.945098, 0.776471, 0.466667]` | `[1.000000, 0.889438, 0.507540]` | `[255, 227, 129]` |
| 21 | Nami/Sanji Bright Yellow | `[245, 219, 65]` | `[0.960784, 0.858824, 0.254902]` | `[1.000000, 1.000000, 0.244124]` | `[255, 255, 62]` |
| 22 | **Sunlit Yellow-Green Grass** | `[178, 204, 72]` | `[0.698039, 0.800000, 0.282353]` | `[0.512365, 1.000000, 0.410105]` | `[131, 255, 105]` |
| 23 | **Meadow Grass (Dade Shift)** | `[138, 204, 72]` | `[0.541176, 0.800000, 0.282353]` | `[0.363375, 0.901798, 0.501018]` | `[93, 230, 128]` |
| 24 | **Lush Foliage (Dade Shift)** | `[107, 204, 72]` | `[0.419608, 0.800000, 0.282353]` | `[0.232528, 0.833151, 0.573536]` | `[59, 212, 146]` |
| 25 | Foreground Cloak Teal-Green | `[68, 108, 94]` | `[0.266667, 0.423529, 0.368627]` | `[0.314076, 0.550814, 0.518001]` | `[80, 140, 132]` |
| 26 | Sky Blue | `[98, 183, 247]` | `[0.384314, 0.717647, 0.968627]` | `[0.369873, 0.846251, 1.000000]` | `[94, 216, 255]` |
| 27 | Chopper Hat Cyan | `[120, 180, 195]` | `[0.470588, 0.705882, 0.764706]` | `[0.508075, 0.834882, 0.962983]` | `[130, 213, 246]` |
| 28 | Luffy Sash Purple | `[134, 92, 174]` | `[0.525490, 0.360784, 0.682353]` | `[0.565190, 0.389754, 0.761472]` | `[144, 99, 194]` |
| 29 | Dark Hair Shadow | `[19, 27, 37]` | `[0.074510, 0.105882, 0.145098]` | `[0.103884, 0.144284, 0.234510]` | `[26, 37, 60]` |

---

### 6.2 Stage 3 Vertical Gradient Test Vectors (8 `y_norm` Positions, Input `cc_rgb = [0.80, 0.70, 0.60]`)

| # | `y_norm` (`0=top, 1=bottom`) | `smoothstep_r` | Multiplier `1 - r * strength_rgb` | Output `RGB` for `[0.80, 0.70, 0.60]` |
|---:|---:|---:|---|---|
| 1 | `0.00` | `0.000000` | `[1.000000, 1.000000, 1.000000]` | `[0.800000, 0.700000, 0.600000]` |
| 2 | `0.14` | `0.000000` | `[1.000000, 1.000000, 1.000000]` | `[0.800000, 0.700000, 0.600000]` |
| 3 | `0.25` | `0.083681` | `[0.978014, 0.978545, 0.976523]` | `[0.782411, 0.684981, 0.585914]` |
| 4 | `0.40` | `0.381726` | `[0.899706, 0.902129, 0.892907]` | `[0.719765, 0.631490, 0.535744]` |
| 5 | `0.55` | `0.735925` | `[0.806644, 0.811315, 0.793536]` | `[0.645315, 0.567920, 0.476122]` |
| 6 | `0.70` | `0.974974` | `[0.743836, 0.750025, 0.726471]` | `[0.595069, 0.525017, 0.435883]` |
| 7 | `0.76` | `1.000000` | `[0.737261, 0.743608, 0.719450]` | `[0.589809, 0.520526, 0.431670]` |
| 8 | `1.00` | `1.000000` | `[0.737261, 0.743608, 0.719450]` | `[0.589809, 0.520526, 0.431670]` |

---

### 6.3 Stage 4 Haze Flare Test Vectors (8 `(x_norm, y_norm)` Points at `1280×720`, `W/H = 16/9`, `base_rgb = [0.15, 0.18, 0.22]`)

| # | `(x_norm, y_norm)` | `default` Flare `f_rgb` | `default` Screen Out | `pairA` Flare `f_rgb` | `pairA` Screen Out |
|---:|---|---|---|---|---|
| 1 | `(0.92, 0.09)` | `[0.048358, 0.110500, 0.108750]` | `[0.191104, 0.270610, 0.304825]` | `[0.306426, 0.315712, 0.111428]` | `[0.410462, 0.438884, 0.306914]` |
| 2 | `(0.96, 0.19)` | `[0.037356, 0.085360, 0.084008]` | `[0.181753, 0.249995, 0.285526]` | `[0.329889, 0.339886, 0.119960]` | `[0.430406, 0.458707, 0.313569]` |
| 3 | `(0.85, 0.10)` | `[0.050876, 0.116254, 0.114412]` | `[0.193245, 0.275328, 0.309242]` | `[0.243682, 0.251066, 0.088612]` | `[0.357130, 0.385874, 0.289117]` |
| 4 | `(0.75, 0.20)` | `[0.026291, 0.060077, 0.059125]` | `[0.172348, 0.229263, 0.266118]` | `[0.080838, 0.083288, 0.029396]` | `[0.218713, 0.248296, 0.242929]` |
| 5 | `(0.90, 0.35)` | `[0.019363, 0.044245, 0.043544]` | `[0.166458, 0.216281, 0.253964]` | `[0.202561, 0.208699, 0.073658]` | `[0.322176, 0.351133, 0.277454]` |
| 6 | `(0.60, 0.15)` | `[0.005937, 0.013566, 0.013351]` | `[0.155046, 0.191124, 0.230414]` | `[0.006945, 0.007156, 0.002526]` | `[0.155904, 0.185868, 0.221970]` |
| 7 | `(0.50, 0.50)` | `[0.000040, 0.000091, 0.000089]` | `[0.150034, 0.180074, 0.220070]` | `[0.000025, 0.000026, 0.000009]` | `[0.150021, 0.180021, 0.220007]` |
| 8 | `(0.10, 0.85)` | `[0.000000, 0.000000, 0.000000]` | `[0.150000, 0.180000, 0.220000]` | `[0.000000, 0.000000, 0.000000]` | `[0.150000, 0.180000, 0.220000]` |

---

### 6.4 Stage 1 1D Step-Edge Unsharp Mask Test Vector (Stated Height `H = 720 px`)

Evaluated on a vertical step edge of height `H = 720` (`sigma_px = 0.003473 * 720 = 2.500560 px`, `amount = 0.82`, `threshold_01 = 0.01433`) across 21 horizontal columns `x ∈ {0..20}` (`0.20` for `x < 10`, `0.80` for `x >= 10`, clamped border replication):

| `x` | `input_1d` | `blur25_1d` | `usm_out_1d` | `x` | `input_1d` | `blur25_1d` | `usm_out_1d` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `0` | `0.200000` | `0.200000` | `0.200000` | `11` | `0.800000` | `0.612500` | `0.941999` |
| `1` | `0.200000` | `0.200000` | `0.200000` | `12` | `0.800000` | `0.687416` | `0.880568` |
| `2` | `0.200000` | `0.200000` | `0.200000` | `13` | `0.800000` | `0.762500` | `0.818999` |
| `3` | `0.200000` | `0.200000` | `0.200000` | `14` | `0.800000` | `0.762500` | `0.818999` |
| `4` | `0.200000` | `0.200042` | `0.200000` | `15` | `0.800000` | `0.799958` | `0.800000` |
| `5` | `0.200000` | `0.237500` | `0.181001` | `16` | `0.800000` | `0.800000` | `0.800000` |
| `6` | `0.200000` | `0.237500` | `0.181001` | `17` | `0.800000` | `0.800000` | `0.800000` |
| `7` | `0.200000` | `0.312584` | `0.119432` | `18` | `0.800000` | `0.800000` | `0.800000` |
| `8` | `0.200000` | `0.387500` | `0.058001` | `19` | `0.800000` | `0.800000` | `0.800000` |
| `9` | `0.200000` | `0.387500` | `0.058001` | `20` | `0.800000` | `0.800000` | `0.800000` |
| `10` | `0.800000` | `0.612500` | `0.941999` | — | — | — | — |

---

## 7. Known Limits & Caveats

1. **Scene-Dependent Haze Flare Tint & Intensity:** While the colour grade, bottom darkening gradient, and unsharp mask are consistent across both edits, the top-right Screen glow shifts from a strong warm-golden sunlight glow (`intensity = 0.34`, `#F8FF5A`) in Pair A to a subtle cool sky glow (`intensity = 0.13`, `#62ECFF`) in Pair B. Expose `u_flare_intensity` and `u_flare_colour` prominently in Keyflaw's UI so users can match sunlit vs overcast shots, or leave `default` (`intensity = 0.1183`) for a safe cross-clip look.
2. **Pair B AI-Reconstructed Bush Overlap vs Real Anime Foliage:** In `inputs/pairB_original_matched.png`, the AI reconstruction hallucinated the background bush (`x ≈ 770..965` at `720p`) as golden-yellow `RGB = [250, 213, 79]` (`H = 47.0°`), which is **warmer in hue** than Nami's yellow shirt (`RGB = [245, 219, 65]`, `H = 51.3°`) and Sanji's blonde hair (`RGB = [247, 231, 127]`, `H = 52.0°`). No spatially-invariant pixel shader can map `H = 47°` to green without also turning `H = 51°–52°` yellow clothing/hair and `H = 39°–43°` straw hats green. On **real ungraded anime footage**, grass and foliage lie at `H ≥ 65°` (`G > R`), where the Dade `foliage_window` (`smoothstep(56°, 68°, h_deg)`) cleanly rotates yellow-greens into bluish-green / teal (`+38°..+52°`) with zero leakage onto warm yellows or skin.
3. **AI-Reconstruction Colour Noise Floor (`~3 / 255`) & Extrapolated Extremes:** Matched originals carry a `~2.9 / 255` average (`7 / 255` worst-case blue skin) reconstruction drift relative to true broadcast sources, and RGB values outside `[16..251]` R, `[21..253]` G, `[25..254]` B are smooth curve extrapolations rather than directly observed cel samples.
4. **Full-Frame Normalised `y` vs Letterbox Bars:** Both reference edits come from a 720p timeline with `~4.9%` top/bottom black letterbox bars (`rows 0..34` and `686..719`). If Keyflaw applies the effect *before* adding letterbox bars on an un-letterboxed `16:9` clip, `y0_norm = 0.14` and `y1_norm = 0.7583` differ by less than `0.03` (`~2%` luma, within the noise floor) from active-picture coordinates.
