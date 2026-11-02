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
    
    return clamp(outCol, 0.0, 1.0);
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
        for (int j = -2; j <= 2; j++) {
            float wj = (j == 0) ? 6.0 : ((j == 1 || j == -1) ? 4.0 : 1.0);
            for (int i = -2; i <= 2; i++) {
                float wi = (i == 0) ? 6.0 : ((i == 1 || i == -1) ? 4.0 : 1.0);
                acc += (wi * wj / 256.0) * sampleTap(uv + vec2(float(i), float(j)) * st);
            }
        }
        vec3 d = x - acc;
        d = sign(d) * max(abs(d) - xzThresh, vec3(0.0));
        x = clamp(x + xzAmount * d, 0.0, 1.0);
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
