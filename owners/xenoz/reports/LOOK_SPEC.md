# LOOK SPECIFICATION: Xenoz's CC — v1.1.1 burn-safety patch

MOTIONSALT · effect `MS_xenoz_cc` · shared suite `com.motionsalt.cc` · Keyflaw 1.4.8.
Source of truth: `look_params.json`; executable reference: `look_apply.py`.

## 1. Summary and scope
Retains the existing sRGB levels, cool shadow toe, colour matrix, opponent-polar hue/chroma shaping, vertical darkening, sharpening and ambient Screen flare. **New engineering safeguards compress the grading displacement before gamut clipping and prevent sharpening from creating local over/undershoot.** These safeguards are not newly inferred properties of Xenoz's editing preset.

The old unconstrained matrix/shaper exceeds [0,1] on 37.21% and 66.78% of all aligned A/B pixels (including invalid regions). On the valid masked regions it exceeds gamut on 37.40% / 64.18%. Hard-clamping those results is a plausible cause of the user's burnt-looking highlights. The exact reported clip/app symptom remains unverified.

This is maintenance of an existing completed fit, not a repeat or certification of Q1–Q8. The original reconstruction drift (~3/255 typical, up to ~7/255/channel) and local AI redraw remain. Static frames cannot establish absence of temporal flicker. The prior colour matrix is not neutral-preserving, and the grey curve is not guaranteed monotonic. The safety patch does not repair those underlying fitting limitations or claim unseen-scene parity.

## 2. Actual runtime order
1. Unpremultiply input. If Quality is ON, apply 25-tap input RGB unsharp, thresholded and **clamped to the same taps' local per-channel minimum/maximum**.
2. If Colour Correction is ON: original levels → toe → matrix → opponent shaper → **source-anchored gamut compression**, then numerical clamp.
3. If Quality is ON: multiply the vertical RGB gradient.
4. If Haze Flare is ON: existing anisotropic Gaussian Screen flare.
5. Mix dry/wet using Master Intensity, clamp numerically, premultiply and preserve input alpha.

Sharpening before the nonlinear CC is the existing single-pass runtime approximation, not algebraically equivalent to the original measured CC→gradient→USM order. The reference now follows runtime exactly; historical reference outputs used the other order. Spatial coordinates are full-frame, including letterbox bars; top-left y=0, bottom y=1. Pixel centres are `(column+0.5)/width`, `(row+0.5)/height`. `yTop=1-vTex.y`.

## 3. Exact GLSL implementation (complete pseudocode / shader)
All colour maths are in gamma-encoded sRGB [0,1], not linear light. The levels use `pow(t,gamma)`, not `pow(t,1/gamma)`. All fitted constants and the safeguard are explicit below. This block is checked byte-for-byte against the packaged shader.

```glsl
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform sampler2D uTexture;
varying vec2 vTex;
uniform float uTime;
uniform vec2 uTexelSize;

// User Parameter Switches (Keyflaw 1.4.8+)
uniform float uCc;
uniform float uQuality;
uniform float uFlare;
uniform float uIntensity;

// Constants for 25-tap Unsharp Mask
const float xzSigmaFracH = 0.000535;
const float xzAmount = 1.1000;
const float xzThresh = 0.006590;

vec3 sampleTap(vec2 uv) {
    vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0));
    return c.rgb / max(c.a, 0.0001);
}

// v1.1.1 engineering safeguard: shared RGB displacement compression.
vec3 xzGamutSafe(vec3 source, vec3 candidate) {
    vec3 delta = candidate - source;
    vec3 upper = max(source, vec3(0.996078431373));
    vec3 lower = min(source, vec3(0.003921568627));
    vec3 room = mix(source - lower, upper - source, step(vec3(0.0), delta));
    vec3 ratio3 = abs(delta) / max(room, vec3(0.00001));
    float ratio = max(ratio3.r, max(ratio3.g, ratio3.b));
    float compressed = 0.8 + 0.2 * (1.0 - exp(-max(ratio - 0.8, 0.0) / 0.2));
    float scale = (ratio > 0.8) ? compressed / max(ratio, 0.00001) : 1.0;
    return clamp(source + delta * scale, 0.0, 1.0);
}

// Stage 1: Colour Correction (M2_Dade_srgb)
vec3 applyColourCorrection(vec3 rgbIn) {
    vec3 x = clamp(rgbIn, 0.0, 1.0);
    
    // 1. Levels Expansion
    vec3 inB = vec3(0.000300, -0.093120, 0.073239);
    vec3 inW = vec3(0.945100, 0.922091, 0.895012);
    vec3 gam = vec3(1.682652, 1.824267, 0.938911);
    vec3 outB = vec3(0.199788, 0.144363, 0.135760);
    vec3 outW = vec3(1.179506, 1.152492, 1.249824);
    
    vec3 span = max(inW - inB, vec3(0.0001));
    vec3 t = clamp((x - inB) / span, 0.0, 1.0);
    vec3 v = outB + pow(max(t, vec3(0.00000001)), gam) * (outW - outB);
    
    // 2. Cool Slate Shadow Toe
    float lum = dot(x, vec3(0.2126, 0.7152, 0.0722));
    float toeT = clamp(lum / 0.2800, 0.0, 1.0);
    float toeW = 1.0 - toeT * toeT * (3.0 - 2.0 * toeT);
    vec3 toeLift = vec3(-0.010808, 0.060847, 0.119867);
    v += toeW * toeLift * max(vec3(1.0) - v, vec3(0.0));
    
    // 3. 3x3 Colour Matrix
    vec3 mRow0 = vec3(-0.451142, -1.147089, 2.023277);
    vec3 mRow1 = vec3(-2.777678, -0.486145, 3.500240);
    vec3 mRow2 = vec3(-2.361577, -2.134604, 4.553602);
    vec3 m = vec3(dot(mRow0, v), dot(mRow1, v), dot(mRow2, v));
    
    // 4. Opponent-Polar Hue-Chroma Shaper
    float A = (m.r + m.g + m.b) * 0.333333333;
    float ou = m.r - 0.5 * (m.g + m.b);
    float ov = 0.86602540378 * (m.g - m.b);
    float C = sqrt(ou * ou + ov * ov + 0.00000001);
    float hu = ou / C;
    float hv = ov / C;
    
    float cgT = clamp((C - 0.0150) / max(0.0600 - 0.0150, 0.0001), 0.0, 1.0);
    float cGate = cgT * cgT * (3.0 - 2.0 * cgT);
    
    // Cyan lobe (198 deg): cos=-0.9510565, sin=-0.3090170
    float cosCyan = hu * (-0.9510565) + hv * (-0.3090170);
    float wCyan = exp(4.00 * (cosCyan - 1.0));
    
    // Warm skin lobe (30 deg): cos=0.8660254, sin=0.5000000
    float cosSkin = hu * 0.8660254 + hv * 0.5000000;
    float wSkin = exp(4.00 * (cosSkin - 1.0));
    
    // Plum violet lobe (315 deg): cos=0.7071068, sin=-0.7071068
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
    
    return xzGamutSafe(x, outCol);
}

// Stage 2: Vertical Multiply Gradient
vec3 applyGradient(vec3 rgbIn, float yTop) {
    float t = clamp((yTop - 0.269079) / max(0.872060 - 0.269079, 0.00001), 0.0, 1.0);
    float ramp = t * t * (3.0 - 2.0 * t);
    vec3 strength = vec3(0.057212, 0.129601, 0.135450);
    return clamp(rgbIn * (vec3(1.0) - ramp * strength), 0.0, 1.0);
}

// Stage 4: Subtle Ambient Screen Flare
vec3 applyFlare(vec3 rgbIn, vec2 uv, float yTop, float W2H) {
    float dx = (uv.x - 0.500000) * W2H;
    float dy = yTop - 0.050000;
    float u = dx / max(0.450000, 0.01);
    float v = dy / max(0.350000, 0.01);
    float glow = exp(-0.5 * (u * u + v * v)) * 0.1200;
    vec3 flareCol = vec3(0.350000, 0.550000, 0.950000);
    vec3 f_vec = clamp(glow * flareCol, 0.0, 1.0);
    return clamp(vec3(1.0) - (vec3(1.0) - rgbIn) * (vec3(1.0) - f_vec), 0.0, 1.0);
}

void main() {
    vec2 uv = clamp(vTex, 0.0, 1.0);
    vec4 src = texture2D(uTexture, uv);
    float a = src.a;
    vec3 srcRgb = src.rgb / max(a, 0.0001);
    
    float texX = max(uTexelSize.x, 0.000001);
    float texY = max(uTexelSize.y, 0.000001);
    float W2H = texY / texX; // frame width / frame height
    float yTop = 1.0 - uv.y; // vTex.y=0 is bottom edge, yTop=0 is top edge
    
    vec3 x = srcRgb;
    
    // Stage 3: Unsharp Mask (quality pass on source or input)
    if (uQuality > 0.5) {
        vec2 st = vec2(xzSigmaFracH * texX / texY, xzSigmaFracH);
        vec3 acc = vec3(0.0);
        vec3 localMin = x;
        vec3 localMax = x;
        for (int j = -2; j <= 2; j++) {
            float wj = (j == 0) ? 6.0 : ((j == 1 || j == -1) ? 4.0 : 1.0);
            for (int i = -2; i <= 2; i++) {
                float wi = (i == 0) ? 6.0 : ((i == 1 || i == -1) ? 4.0 : 1.0);
                vec3 tap = sampleTap(uv + vec2(float(i), float(j)) * st);
                acc += (wi * wj / 256.0) * tap;
                localMin = min(localMin, tap);
                localMax = max(localMax, tap);
            }
        }
        vec3 d = x - acc;
        d = sign(d) * max(abs(d) - xzThresh, vec3(0.0));
        x = clamp(x + xzAmount * d, localMin, localMax);
    }
    
    // Stage 1: Colour Correction
    if (uCc > 0.5) {
        x = applyColourCorrection(x);
    }
    
    // Stage 2: Vertical Spatial Gradient
    if (uQuality > 0.5) {
        x = applyGradient(x, yTop);
    }
    
    // Stage 4: Haze Flare
    if (uFlare > 0.5) {
        x = applyFlare(x, uv, yTop, W2H);
    }
    
    // Master Intensity dry/wet blend
    x = clamp(mix(srcRgb, x, clamp(uIntensity, 0.0, 1.0)), 0.0, 1.0);
    
    gl_FragColor = vec4(x * a, a);
}
```

### Gamut safeguard interpretation
Let `s` be the grade's input (after optional source USM), `c` its unclamped candidate, and `d=c-s`. For each channel choose `upper=max(s,254/255)`, `lower=min(s,1/255)` and directional room `h=(d>=0 ? upper-s : s-lower)`. Define `r=max_channels(abs(d)/max(h,1e-5))`.
For `r<=0.8`, scale=1. Otherwise `compressed=0.8+0.2*(1-exp(-(r-0.8)/0.2))`, scale=`compressed/max(r,1e-5)`. Result=`clamp(s+scale*d,0,1)`. A single RGB scale preserves the grading-displacement direction, **not an exact perceptual hue**. Already saturated source colours are not reconstructable; this is bounded fallback, not highlight recovery. The final numerical clamp can still bind in the tiny epsilon region or for already saturated inputs; the claim is reduced hard clipping, not zero clipping for every possible source.

### Confidence
| Component | Confidence | Evidence / qualification |
|---|---|---|
| Existing CC constants | Medium on supplied scenes, low outside them | Preserved base fit; large negative matrix coefficients and excursions demonstrate poor unconstrained extrapolation. Not refitted here. |
| Gamut safeguard | High numerical; subjective approval pending | 35,937 colour samples and both frame pairs, with independent shader evaluation. Knee 0.8 and 1/255 margin are deliberate safety choices. |
| USM halo limiter | High numerical; strength medium | Synthetic 0.2→0.8 step at H=409,720,1080 has no new extrema. Amount 1.1 retained, not remeasured. |
| Gradient | Medium | Existing spatial fit retained; no new measurement. |
| Flare | Low | Existing fixed blue ambient Screen glow retained unchanged. Earlier analysis described scene dependence; runtime is NOT highlight-tracking and is not proven optimal on new clips. |
| Other effects | Not changed / not re-certified | Existing vignette/grain/CA findings not retested. Temporal flicker is not provable from two still pairs. |

## 4. Complete numeric parameter table
Canonical values below are from JSON; GLSL constants are rounded to at least six decimals (verified error <1/255). Unitless unless noted. JSON holds full precision.

| JSON parameter | Value | Unit / validity |
|---|---|---|
| `colour_correction.levels.in_black` | `[0.00030032747620917114, -0.09311952575026178, 0.07323927180437503]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.levels.in_white` | `[0.9450997462367785, 0.922091177328185, 0.8950115029960453]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.levels.gamma` | `[1.6826524301537116, 1.8242667941848931, 0.938911282032249]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.levels.out_black` | `[0.19978798504448497, 0.14436278660877533, 0.13575995210249803]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.levels.out_white` | `[1.1795058932368079, 1.152492329504375, 1.2498240203647792]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.shadow_toe.luma_threshold` | `0.28` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.shadow_toe.lift_rgb` | `[-0.010807980431261717, 0.06084662676544976, 0.11986705573773752]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.matrix_3x3` | `[[-0.45114229247209575, -1.1470888529938412, 2.023276592496606], [-2.7776779615587857, -0.48614518737337287, 3.500239698293216], [-2.361576772867952, -2.1346036555365404, 4.55360172025641]]` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.chroma_gate.c_min` | `0.015` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.chroma_gate.c_max` | `0.06` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.cyan_sky_lobe.center_deg` | `198.0` | degrees |
| `colour_correction.opponent_shaper.cyan_sky_lobe.kappa` | `4.0` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.cyan_sky_lobe.dh_rad` | `0.21330528429098827` | radians |
| `colour_correction.opponent_shaper.cyan_sky_lobe.dc` | `-0.44083874888235147` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.cyan_sky_lobe.da` | `-1.2506082126341593` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.warm_skin_lobe.center_deg` | `30.0` | degrees |
| `colour_correction.opponent_shaper.warm_skin_lobe.kappa` | `4.0` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.warm_skin_lobe.dh_rad` | `0.06066944904606935` | radians |
| `colour_correction.opponent_shaper.warm_skin_lobe.dc` | `-0.2776265109858796` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.warm_skin_lobe.da` | `1.9989258341031901` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.plum_violet_lobe.center_deg` | `315.0` | degrees |
| `colour_correction.opponent_shaper.plum_violet_lobe.kappa` | `3.0` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.plum_violet_lobe.dh_rad` | `0.2563995635389732` | radians |
| `colour_correction.opponent_shaper.plum_violet_lobe.dc` | `-0.10803235370721671` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.opponent_shaper.plum_violet_lobe.da` | `0.6291185545610564` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.gamut_safety.knee` | `0.8` | ratio, 0<knee<1 |
| `colour_correction.gamut_safety.margin_01` | `0.00392156862745098` | sRGB [0,1] units; internal fit may exceed gamut |
| `colour_correction.gamut_safety.epsilon` | `1e-05` | sRGB [0,1] units; internal fit may exceed gamut |
| `gradient.y0_norm` | `0.26907882821051904` | normalised full-frame coordinates [0,1] |
| `gradient.y1_norm` | `0.8720604819609442` | normalised full-frame coordinates [0,1] |
| `gradient.strength_rgb` | `[0.05721166641061615, 0.12960085546358716, 0.1354503637000828]` | sRGB [0,1] units; internal fit may exceed gamut |
| `unsharp.sigma_frac_h` | `0.000535` | fraction of frame height; >0 |
| `unsharp.amount` | `1.1` | dimensionless, retained 1.1; original search 0..3 |
| `unsharp.threshold_01` | `0.00659` | sRGB [0,1] units; internal fit may exceed gamut |
| `unsharp.threshold_255` | `1.68` | sRGB [0,1] units; internal fit may exceed gamut |
| `flare.canonical_default_params.cx` | `0.5` | normalised full-frame coordinates [0,1] |
| `flare.canonical_default_params.cy` | `0.05` | normalised full-frame coordinates [0,1] |
| `flare.canonical_default_params.rx_frac_h` | `0.45` | fraction of frame height; >0 |
| `flare.canonical_default_params.ry_frac_h` | `0.35` | fraction of frame height; >0 |
| `flare.canonical_default_params.angle_deg` | `0.0` | degrees |
| `flare.canonical_default_params.colour_rgb` | `[0.35, 0.55, 0.95]` | sRGB [0,1] units; internal fit may exceed gamut |
| `flare.canonical_default_params.intensity` | `0.12` | sRGB [0,1] units; internal fit may exceed gamut |

USM sigma at H=409/720/1080 is 0.218815/0.385200/0.577800 px. At H=720 gradient endpoints are 193.7368 px and 627.8835 px; at any H multiply the normalised value by H. Flare radii at H=720 are 324 and 252 px. All radii are fractions of **height**, including horizontal radius. Flare dx must include W/H.

## 5. Controls and implementation limits
| Control | Type | Min | Max | Default | Drives |
|---|---|---:|---:|---:|---|
| Colour Correction | BOOL | 0 | 1 | 1 | CC and inseparable gamut safeguard |
| Quality (Sharpen + Gradient) | BOOL | 0 | 1 | 1 | USM + anti-halo + gradient |
| Haze Flare | BOOL | 0 | 1 | 1 | Retained ambient flare |
| Master Intensity | Slider | 0 | 1 | 1 | Dry/wet blend of complete result |

Controls remain unchanged; no new sliders. Three BOOLs are in Switches, Master Intensity in Adjustments. No multipass, expandBounds, COLOR controls, extra samplers or LUT textures. 25 blur taps + 1 centre fetch = **26 texture fetches** at Quality ON; no extra taps for the extrema limiter. Full transparency is preserved. Premultiplied input, bilinear sampling and sRGB texture values are assumptions to confirm in Keyflaw. Radius scales with height. Python uses exact bilinear interpolation, not OpenCV's quantised interpolation table.

## 6. Machine-checkable test vectors
All inputs/outputs below are sRGB [0,1]. Tables rounded to 9 decimals; full precision in `../analysis/outputs/burn_safety_v1.1.1/test_vectors.json`. `verify_spec_parity.py` checks these tables, the shader, JSON and cube.

### 6.1 Colour stage
| Input RGB | Expected RGB |
|---|---|
| `[0.0, 0.0, 0.0]` | `[0.144592651, 0.18320669, 0.175914425]` |
| `[0.062745098, 0.062745098, 0.062745098]` | `[0.126564412, 0.135561363, 0.095698131]` |
| `[0.125490196, 0.125490196, 0.125490196]` | `[0.179044533, 0.205464538, 0.204571051]` |
| `[0.188235294, 0.188235294, 0.188235294]` | `[0.196089628, 0.2140587, 0.247602843]` |
| `[0.250980392, 0.250980392, 0.250980392]` | `[0.237541132, 0.265429767, 0.327954756]` |
| `[0.31372549, 0.31372549, 0.31372549]` | `[0.27091367, 0.316316945, 0.402444239]` |
| `[0.376470588, 0.376470588, 0.376470588]` | `[0.307981504, 0.367485429, 0.469912628]` |
| `[0.439215686, 0.439215686, 0.439215686]` | `[0.349815289, 0.418593893, 0.529903056]` |
| `[0.501960784, 0.501960784, 0.501960784]` | `[0.395892563, 0.469476057, 0.582478331]` |
| `[0.564705882, 0.564705882, 0.564705882]` | `[0.445904541, 0.520130383, 0.627869919]` |
| `[0.62745098, 0.62745098, 0.62745098]` | `[0.499701153, 0.570695668, 0.666448079]` |
| `[0.690196078, 0.690196078, 0.690196078]` | `[0.557372632, 0.621601131, 0.698905126]` |
| `[0.752941176, 0.752941176, 0.752941176]` | `[0.619662431, 0.674240846, 0.727004308]` |
| `[0.815686275, 0.815686275, 0.815686275]` | `[0.690137099, 0.734955002, 0.757287709]` |
| `[0.878431373, 0.878431373, 0.878431373]` | `[0.769674479, 0.813589631, 0.781082631]` |
| `[0.941176471, 0.941176471, 0.941176471]` | `[0.995855865, 0.949623253, 0.898932241]` |
| `[1.0, 1.0, 1.0]` | `[1.0, 0.999990611, 0.999972082]` |
| `[1.0, 0.0, 0.0]` | `[1.0, 1.801e-06, 1.351e-06]` |
| `[0.0, 1.0, 0.0]` | `[0.0, 0.999993941, 0.0]` |
| `[0.0, 0.0, 1.0]` | `[2.548e-06, 1.1944e-05, 1.0]` |
| `[1.0, 1.0, 0.0]` | `[1.0, 1.0, 4.957e-06]` |
| `[0.0, 1.0, 1.0]` | `[7.83e-07, 1.0, 1.0]` |
| `[1.0, 0.0, 1.0]` | `[1.0, 7.559e-06, 1.0]` |
| `[0.93, 0.899, 0.848]` | `[0.99605888, 0.92247146, 0.852419498]` |
| `[0.175, 0.366, 0.665]` | `[0.108786961, 0.532944462, 0.96828287]` |
| `[0.087, 0.012, 0.013]` | `[0.143017011, 0.144471904, 0.134211008]` |

### 6.2 Vertical gradient
| yTop | Multiplier RGB |
|---|---|
| `0` | `[1.0, 1.0, 1.0]` |
| `0.2` | `[1.0, 1.0, 1.0]` |
| `0.4` | `[0.993079919, 0.984324029, 0.983616497]` |
| `0.6` | `[0.967218888, 0.925741367, 0.922389719]` |
| `0.8` | `[0.945044312, 0.875509584, 0.869890734]` |
| `1` | `[0.942788334, 0.870399145, 0.864549636]` |

### 6.3 Flare at W/H=1280/720, input RGB=(0.5,0.5,0.5)
| (x,yTop) | Flare RGB before Screen | Expected RGB |
|---|---|---|
| `[0.5, 0.05]` | `[0.042, 0.066, 0.114]` | `[0.521, 0.533, 0.557]` |
| `[0.1, 0.1]` | `[0.011927843, 0.018743753, 0.032375573]` | `[0.505963921, 0.509371876, 0.516187786]` |
| `[0.9, 0.1]` | `[0.011927843, 0.018743753, 0.032375573]` | `[0.505963921, 0.509371876, 0.516187786]` |
| `[0.5, 0.5]` | `[0.018377719, 0.028879273, 0.04988238]` | `[0.509188859, 0.514439636, 0.52494119]` |
| `[0.1, 0.9]` | `[0.000631347, 0.000992116, 0.001713655]` | `[0.500315673, 0.500496058, 0.500856828]` |
| `[0.9, 0.9]` | `[0.000631347, 0.000992116, 0.001713655]` | `[0.500315673, 0.500496058, 0.500856828]` |

### 6.4 Isolated anti-halo USM, H=720, row-constant 21-pixel 1D step
| Column | Input | Expected |
|---|---|---|
| `0` | `0.200000000` | `0.200000000` |
| `1` | `0.200000000` | `0.200000000` |
| `2` | `0.200000000` | `0.200000000` |
| `3` | `0.200000000` | `0.200000000` |
| `4` | `0.200000000` | `0.200000000` |
| `5` | `0.200000000` | `0.200000000` |
| `6` | `0.200000000` | `0.200000000` |
| `7` | `0.200000000` | `0.200000000` |
| `8` | `0.200000000` | `0.200000000` |
| `9` | `0.200000000` | `0.200000000` |
| `10` | `0.800000000` | `0.800000000` |
| `11` | `0.800000000` | `0.800000000` |
| `12` | `0.800000000` | `0.800000000` |
| `13` | `0.800000000` | `0.800000000` |
| `14` | `0.800000000` | `0.800000000` |
| `15` | `0.800000000` | `0.800000000` |
| `16` | `0.800000000` | `0.800000000` |
| `17` | `0.800000000` | `0.800000000` |
| `18` | `0.800000000` | `0.800000000` |
| `19` | `0.800000000` | `0.800000000` |
| `20` | `0.800000000` | `0.800000000` |

The hard step's expected output has no new halo by design; textured transitions can still sharpen within local extrema. The 33³ cube includes colour correction and gamut safety only, not spatial or sharpening effects.

## 7. Known limits and release verification
Reducing burning trades some reference-frame colour fit for headroom and detail. This patch is not claimed to beat the old composite on every fit metric. Use the maintenance report for measured before/after values, not historical Q8 metrics. The only source frames are AI-reconstructed and aligned; exact parity is impossible. No temporal effect can be verified here. The flare is fixed, scene-dependent defaults and gamut-knee strength are least certain perceptually. GLSL ES 1.00 compilation and offscreen software shader tests do not establish correct import, colour-space or rendering behaviour inside Keyflaw 1.4.8.
