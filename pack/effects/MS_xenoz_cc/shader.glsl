#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform sampler2D uTexture;
varying vec2 vTex;
uniform float uTime;
uniform vec2 uTexelSize;

// Keyflaw Controls
uniform float uCc;
uniform float uQuality;
uniform float uFlare;
uniform float uIntensity;

// Constants for 25-tap Unsharp Mask
const float xzSigmaFracH = 0.000535; // Blur radius as fraction of height
const float xzAmount = 3.0;          // High-pass boost
const float xzThresh = 0.006590;     // Coring threshold (1.68 / 255)

vec3 sampleTap(vec2 uv) {
    vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0));
    return c.rgb / max(c.a, 0.0001);
}

// Convert sRGB to Linear
vec3 srgbToLinear(vec3 c) {
    vec3 c0 = c / 12.92;
    vec3 c1 = pow(max((c + 0.055) / 1.055, vec3(0.00000001)), vec3(2.4));
    return mix(c0, c1, step(vec3(0.04045), c));
}

// Convert Linear to sRGB
vec3 linearToSrgb(vec3 c) {
    vec3 c0 = c * 12.92;
    vec3 c1 = 1.055 * pow(max(c, vec3(0.00000001)), vec3(1.0 / 2.4)) - 0.055;
    return mix(c0, c1, step(vec3(0.0031308), c));
}

// Piecewise Linear Spline Evaluator for Red channel
float evalSplineR(float x) {
    float s = clamp(x, 0.0, 1.0) * 16.0;
    if (s < 8.0) {
        if (s < 4.0) {
            if (s < 2.0) {
                if (s < 1.0) return mix(0.002211, 0.034315, s);
                return mix(0.034315, 0.056511, s - 1.0);
            } else {
                if (s < 3.0) return mix(0.056511, 0.078239, s - 2.0);
                return mix(0.078239, 0.211251, s - 3.0);
            }
        } else {
            if (s < 6.0) {
                if (s < 5.0) return mix(0.211251, 0.219826, s - 4.0);
                return mix(0.219826, 0.327422, s - 5.0);
            } else {
                if (s < 7.0) return mix(0.327422, 0.435065, s - 6.0);
                return mix(0.435065, 0.501375, s - 7.0);
            }
        }
    } else {
        if (s < 12.0) {
            if (s < 10.0) {
                if (s < 9.0) return mix(0.501375, 0.507213, s - 8.0);
                return mix(0.507213, 0.513778, s - 9.0);
            } else {
                if (s < 11.0) return mix(0.513778, 0.608417, s - 10.0);
                return mix(0.608417, 0.703812, s - 11.0);
            }
        } else {
            if (s < 14.0) {
                if (s < 13.0) return mix(0.703812, 0.798546, s - 12.0);
                return mix(0.798546, 0.891579, s - 13.0);
            } else {
                if (s < 15.0) return mix(0.891579, 0.944570, s - 14.0);
                return mix(0.944570, 0.998716, s - 15.0);
            }
        }
    }
}

// Piecewise Linear Spline Evaluator for Green channel
float evalSplineG(float x) {
    float s = clamp(x, 0.0, 1.0) * 16.0;
    if (s < 8.0) {
        if (s < 4.0) {
            if (s < 2.0) {
                if (s < 1.0) return mix(0.002476, 0.036310, s);
                return mix(0.036310, 0.099874, s - 1.0);
            } else {
                if (s < 3.0) return mix(0.099874, 0.199782, s - 2.0);
                return mix(0.199782, 0.256170, s - 3.0);
            }
        } else {
            if (s < 6.0) {
                if (s < 5.0) return mix(0.256170, 0.258343, s - 4.0);
                return mix(0.258343, 0.322150, s - 5.0);
            } else {
                if (s < 7.0) return mix(0.322150, 0.385051, s - 6.0);
                return mix(0.385051, 0.537921, s - 7.0);
            }
        }
    } else {
        if (s < 12.0) {
            if (s < 10.0) {
                if (s < 9.0) return mix(0.537921, 0.576072, s - 8.0);
                return mix(0.576072, 0.613322, s - 9.0);
            } else {
                if (s < 11.0) return mix(0.613322, 0.650356, s - 10.0);
                return mix(0.650356, 0.688095, s - 11.0);
            }
        } else {
            if (s < 14.0) {
                if (s < 13.0) return mix(0.688095, 0.755144, s - 12.0);
                return mix(0.755144, 0.820146, s - 13.0);
            } else {
                if (s < 15.0) return mix(0.820146, 0.977927, s - 14.0);
                return mix(0.977927, 0.998540, s - 15.0);
            }
        }
    }
}

// Piecewise Linear Spline Evaluator for Blue channel
float evalSplineB(float x) {
    float s = clamp(x, 0.0, 1.0) * 16.0;
    if (s < 8.0) {
        if (s < 4.0) {
            if (s < 2.0) {
                if (s < 1.0) return mix(0.000834, 0.026932, s);
                return mix(0.026932, 0.078904, s - 1.0);
            } else {
                if (s < 3.0) return mix(0.078904, 0.180359, s - 2.0);
                return mix(0.180359, 0.218283, s - 3.0);
            }
        } else {
            if (s < 6.0) {
                if (s < 5.0) return mix(0.218283, 0.297963, s - 4.0);
                return mix(0.297963, 0.378248, s - 5.0);
            } else {
                if (s < 7.0) return mix(0.378248, 0.457639, s - 6.0);
                return mix(0.457639, 0.467386, s - 7.0);
            }
        }
    } else {
        if (s < 12.0) {
            if (s < 10.0) {
                if (s < 9.0) return mix(0.467386, 0.474853, s - 8.0);
                return mix(0.474853, 0.660959, s - 9.0);
            } else {
                if (s < 11.0) return mix(0.660959, 0.713462, s - 10.0);
                return mix(0.713462, 0.817572, s - 11.0);
            }
        } else {
            if (s < 14.0) {
                if (s < 13.0) return mix(0.817572, 0.870244, s - 12.0);
                return mix(0.870244, 0.954786, s - 13.0);
            } else {
                if (s < 15.0) return mix(0.954786, 0.977025, s - 14.0);
                return mix(0.977025, 0.999431, s - 15.0);
            }
        }
    }
}

// Stage 1: Colour Correction
vec3 applyColourCorrection(vec3 rgbIn) {
    vec3 w = srgbToLinear(clamp(rgbIn, 0.0, 1.0));
    
    // Levels expansion in linear space
    vec3 inB = vec3(-0.101004, -0.043329, 0.014020);
    vec3 inW = vec3(0.904790, 0.891216, 0.930482);
    vec3 gam = vec3(1.148331, 0.924251, 0.850588);
    vec3 outB = vec3(-0.052240, -0.044284, 0.029805);
    vec3 outW = vec3(1.054894, 1.032638, 1.028508);
    
    vec3 t = clamp((w - inB) / max(inW - inB, vec3(0.0001)), 0.0, 1.0);
    vec3 v = outB + pow(max(t, vec3(0.00000001)), gam) * (outW - outB);
    
    // 3x3 Matrix transform
    vec3 mRow0 = vec3(1.533419, -0.611780, 0.078361);
    vec3 mRow1 = vec3(0.106358, 0.616635, 0.277007);
    vec3 mRow2 = vec3(0.089059, -1.054469, 1.965411);
    vec3 vm = clamp(vec3(dot(mRow0, v), dot(mRow1, v), dot(mRow2, v)), 0.0, 1.0);
    
    // 17-knot Monotonic Splines
    vec3 curv;
    curv.r = evalSplineR(vm.r);
    curv.g = evalSplineG(vm.g);
    curv.b = evalSplineB(vm.b);
    curv = clamp(curv, 0.0, 1.0);
    
    // Linear back to sRGB
    return clamp(linearToSrgb(curv), 0.0, 1.0);
}

// Stage 2: Vertical Multiply Gradient
vec3 applyGradient(vec3 rgbIn, float yTop) {
    float t = clamp((yTop - 0.226816) / max(0.775967 - 0.226816, 0.00001), 0.0, 1.0);
    float ramp = t * t * (3.0 - 2.0 * t);
    vec3 strength = vec3(0.089249, 0.109361, 0.101978);
    return clamp(rgbIn * (vec3(1.0) - ramp * strength), 0.0, 1.0);
}

// Stage 4: 2D Gaussian Screen Haze Flare
vec3 applyFlare(vec3 rgbIn, vec2 uv, float yTop, float W2H) {
    float dx = (uv.x - 0.402688) * W2H;
    float dy = yTop - (-0.200000);
    float d2 = (dx * dx + dy * dy) / max(0.85 * 0.85, 0.0001);
    float glow = exp(-0.5 * d2) * 0.411355;
    vec3 flareCol = vec3(0.019327, 0.198772, 1.0);
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
    
    // Stage 3 (Pre-filter): 25-tap Unsharp Mask
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
