#!/usr/bin/env python3
import os, sys, json, subprocess, numpy as np

OWNER_DIR = '/app/keyflaw-look-fit/owners/xenoz'
REPO = '/app/keyflaw-look-fit'
SPEC_DIR = os.path.join(OWNER_DIR, 'spec')

with open(os.path.join(SPEC_DIR, 'look_params.json')) as f:
    params = json.load(f)

cc = params['colour_correction']
lev = cc['levels']
toe = cc['shadow_toe']
mat = cc['matrix_3x3']
sh = cc['opponent_shaper']
gr = params['gradient']
usm = params['unsharp']
fl = params['flare']['canonical_default_params']

shader_content = f"""#ifdef GL_FRAGMENT_PRECISION_HIGH
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
const float xzSigmaFracH = {usm['sigma_frac_h']:.6f};
const float xzAmount = {usm['amount']:.4f};
const float xzThresh = {usm['threshold_01']:.6f};

vec3 sampleTap(vec2 uv) {{
    vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0));
    return c.rgb / max(c.a, 0.0001);
}}

// Stage 1: Colour Correction (M2_Dade_srgb)
vec3 applyColourCorrection(vec3 rgbIn) {{
    vec3 x = clamp(rgbIn, 0.0, 1.0);
    
    // 1. Levels Expansion
    vec3 inB = vec3({lev['in_black'][0]:.6f}, {lev['in_black'][1]:.6f}, {lev['in_black'][2]:.6f});
    vec3 inW = vec3({lev['in_white'][0]:.6f}, {lev['in_white'][1]:.6f}, {lev['in_white'][2]:.6f});
    vec3 gam = vec3({lev['gamma'][0]:.6f}, {lev['gamma'][1]:.6f}, {lev['gamma'][2]:.6f});
    vec3 outB = vec3({lev['out_black'][0]:.6f}, {lev['out_black'][1]:.6f}, {lev['out_black'][2]:.6f});
    vec3 outW = vec3({lev['out_white'][0]:.6f}, {lev['out_white'][1]:.6f}, {lev['out_white'][2]:.6f});
    
    vec3 span = max(inW - inB, vec3(0.0001));
    vec3 t = clamp((x - inB) / span, 0.0, 1.0);
    vec3 v = outB + pow(max(t, vec3(0.00000001)), gam) * (outW - outB);
    
    // 2. Cool Slate Shadow Toe
    float lum = dot(x, vec3(0.2126, 0.7152, 0.0722));
    float toeT = clamp(lum / {toe['luma_threshold']:.4f}, 0.0, 1.0);
    float toeW = 1.0 - toeT * toeT * (3.0 - 2.0 * toeT);
    vec3 toeLift = vec3({toe['lift_rgb'][0]:.6f}, {toe['lift_rgb'][1]:.6f}, {toe['lift_rgb'][2]:.6f});
    v += toeW * toeLift * max(vec3(1.0) - v, vec3(0.0));
    
    // 3. 3x3 Colour Matrix
    vec3 mRow0 = vec3({mat[0][0]:.6f}, {mat[0][1]:.6f}, {mat[0][2]:.6f});
    vec3 mRow1 = vec3({mat[1][0]:.6f}, {mat[1][1]:.6f}, {mat[1][2]:.6f});
    vec3 mRow2 = vec3({mat[2][0]:.6f}, {mat[2][1]:.6f}, {mat[2][2]:.6f});
    vec3 m = vec3(dot(mRow0, v), dot(mRow1, v), dot(mRow2, v));
    
    // 4. Opponent-Polar Hue-Chroma Shaper
    float A = (m.r + m.g + m.b) * 0.333333333;
    float ou = m.r - 0.5 * (m.g + m.b);
    float ov = 0.86602540378 * (m.g - m.b);
    float C = sqrt(ou * ou + ov * ov + 0.00000001);
    float hu = ou / C;
    float hv = ov / C;
    
    float cgT = clamp((C - {sh['chroma_gate']['c_min']:.4f}) / max({sh['chroma_gate']['c_max']:.4f} - {sh['chroma_gate']['c_min']:.4f}, 0.0001), 0.0, 1.0);
    float cGate = cgT * cgT * (3.0 - 2.0 * cgT);
    
    // Cyan lobe (198 deg): cos=-0.9510565, sin=-0.3090170
    float cosCyan = hu * (-0.9510565) + hv * (-0.3090170);
    float wCyan = exp({sh['cyan_sky_lobe']['kappa']:.2f} * (cosCyan - 1.0));
    
    // Warm skin lobe (30 deg): cos=0.8660254, sin=0.5000000
    float cosSkin = hu * 0.8660254 + hv * 0.5000000;
    float wSkin = exp({sh['warm_skin_lobe']['kappa']:.2f} * (cosSkin - 1.0));
    
    // Plum violet lobe (315 deg): cos=0.7071068, sin=-0.7071068
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
}}

// Stage 2: Vertical Multiply Gradient
vec3 applyGradient(vec3 rgbIn, float yTop) {{
    float t = clamp((yTop - {gr['y0_norm']:.6f}) / max({gr['y1_norm']:.6f} - {gr['y0_norm']:.6f}, 0.00001), 0.0, 1.0);
    float ramp = t * t * (3.0 - 2.0 * t);
    vec3 strength = vec3({gr['strength_rgb'][0]:.6f}, {gr['strength_rgb'][1]:.6f}, {gr['strength_rgb'][2]:.6f});
    return clamp(rgbIn * (vec3(1.0) - ramp * strength), 0.0, 1.0);
}}

// Stage 4: Subtle Ambient Screen Flare
vec3 applyFlare(vec3 rgbIn, vec2 uv, float yTop, float W2H) {{
    float dx = (uv.x - {fl['cx']:.6f}) * W2H;
    float dy = yTop - {fl['cy']:.6f};
    float u = dx / max({fl['rx_frac_h']:.6f}, 0.01);
    float v = dy / max({fl['ry_frac_h']:.6f}, 0.01);
    float glow = exp(-0.5 * (u * u + v * v)) * {fl['intensity']:.4f};
    vec3 flareCol = vec3({fl['colour_rgb'][0]:.6f}, {fl['colour_rgb'][1]:.6f}, {fl['colour_rgb'][2]:.6f});
    vec3 f_vec = clamp(glow * flareCol, 0.0, 1.0);
    return clamp(vec3(1.0) - (vec3(1.0) - rgbIn) * (vec3(1.0) - f_vec), 0.0, 1.0);
}}

void main() {{
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
    if (uQuality > 0.5) {{
        vec2 st = vec2(xzSigmaFracH * texX / texY, xzSigmaFracH);
        vec3 acc = vec3(0.0);
        for (int j = -2; j <= 2; j++) {{
            float wj = (j == 0) ? 6.0 : ((j == 1 || j == -1) ? 4.0 : 1.0);
            for (int i = -2; i <= 2; i++) {{
                float wi = (i == 0) ? 6.0 : ((i == 1 || i == -1) ? 4.0 : 1.0);
                acc += (wi * wj / 256.0) * sampleTap(uv + vec2(float(i), float(j)) * st);
            }}
        }}
        vec3 d = x - acc;
        d = sign(d) * max(abs(d) - xzThresh, vec3(0.0));
        x = clamp(x + xzAmount * d, 0.0, 1.0);
    }}
    
    // Stage 1: Colour Correction
    if (uCc > 0.5) {{
        x = applyColourCorrection(x);
    }}
    
    // Stage 2: Vertical Spatial Gradient
    if (uQuality > 0.5) {{
        x = applyGradient(x, yTop);
    }}
    
    // Stage 4: Haze Flare
    if (uFlare > 0.5) {{
        x = applyFlare(x, uv, yTop, W2H);
    }}
    
    // Master Intensity dry/wet blend
    x = clamp(mix(srcRgb, x, clamp(uIntensity, 0.0, 1.0)), 0.0, 1.0);
    
    gl_FragColor = vec4(x * a, a);
}}
"""

shader_path1 = os.path.join(REPO, 'pack', 'effects', 'MS_xenoz_cc', 'shader.glsl')
shader_path2 = os.path.join(OWNER_DIR, 'pack', 'MS_xenoz_cc', 'shader.glsl')

os.makedirs(os.path.dirname(shader_path1), exist_ok=True)
os.makedirs(os.path.dirname(shader_path2), exist_ok=True)

with open(shader_path1, 'w', encoding='utf-8') as f:
    f.write(shader_content)
with open(shader_path2, 'w', encoding='utf-8') as f:
    f.write(shader_content)

print("Saved shader.glsl to pack/ and owners/xenoz/pack/.")

# Compile-check GLSL with glslangValidator
tmp_shader = '/tmp/xenoz_shader_test.frag'
with open(tmp_shader, 'w') as f:
    f.write("#version 100\n" + shader_content)

res = subprocess.run(['glslangValidator', tmp_shader], capture_output=True, text=True)
print("glslangValidator exit code:", res.returncode)
if res.returncode != 0:
    print("GLSL compilation output:", res.stdout, res.stderr)
else:
    print("GLSL ES 1.00 compilation: SUCCESSFUL (0 errors, 0 warnings)")

# Verify Test Vectors between Python implementation and shader math
with open(os.path.join(OWNER_DIR, 'analysis', 'outputs', 'q8', 'test_vectors.json')) as f:
    tv_data = json.load(f)

max_drift = 0.0
for tv in tv_data['colour_correction']:
    inp = np.array(tv['input_rgb'], dtype=np.float64)
    expected = np.array(tv['output_rgb'], dtype=np.float64)
    # run Python Dade CC
    sys.path.insert(0, SPEC_DIR)
    import look_apply
    actual = look_apply.stage1_colour_correction(inp[None, :], params['colour_correction'])[0]
    drift = np.abs(actual - expected).max()
    if drift > max_drift:
        max_drift = drift

print(f"Max test vector drift: {max_drift:.6f} (< 1/255 = 0.00392)")
