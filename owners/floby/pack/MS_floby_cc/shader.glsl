#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform sampler2D uTexture;
varying vec2 vTex;
uniform float uTime;
uniform vec2 uTexelSize;
uniform float uCc;
uniform float uQuality;
uniform float uHaze;

const float fcSigma = 0.003473;   // USM radius as fraction of height
const float fcAmount = 0.82;
const float fcThresh = 0.01433;

vec3 fcTap(vec2 uv) {
    vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0));
    return c.rgb / max(c.a, 0.0001);
}

float fcSmooth(float a, float b, float x) {
    float t = clamp((x - a) / max(b - a, 0.000001), 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

float fcHash(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

// smooth random value in -1..1 (Sapphire-style random flicker)
float fcFlicker(float t) {
    float i = floor(t);
    float f = fract(t);
    f = f * f * (3.0 - 2.0 * f);
    float a = fcHash(i + 0.123 * 17.0);
    float b = fcHash(i + 1.0 + 0.123 * 17.0);
    return mix(a, b, f) * 2.0 - 1.0;
}

vec3 fcGrade(vec3 xin) {
    vec3 x = clamp(xin, 0.0, 1.0);
    vec3 inB = vec3(-0.079999, -0.077538, 0.035829);
    vec3 inW = vec3(0.934037, 0.929412, 0.963913);
    vec3 gam = vec3(0.820622, 0.889244, 0.863185);
    vec3 outB = vec3(-0.112643, -0.119988, 0.029787);
    vec3 outW = vec3(1.01702, 1.012705, 1.0806);
    vec3 t = clamp((x - inB) / max(inW - inB, vec3(0.0001)), 0.0, 1.0);
    vec3 v = outB + pow(max(t, vec3(0.00000001)), gam) * (outW - outB);

    float lum = dot(x, vec3(0.2126, 0.7152, 0.0722));
    float toe = 1.0 - fcSmooth(0.0, 0.28, lum);
    v += toe * vec3(-0.008286, 0.028697, 0.049749) * max(1.0 - v, 0.0);

    vec3 m = vec3(dot(vec3(1.45155, -0.243174, -0.208376), v),
                  dot(vec3(0.024565, 1.124975, -0.14954), v),
                  dot(vec3(-0.208747, 0.087738, 1.121009), v));

    float A = (m.r + m.g + m.b) * 0.333333333;
    float ou = m.r - 0.5 * (m.g + m.b);
    float ov = 0.8660254 * (m.g - m.b);
    float C = sqrt(ou * ou + ov * ov + 0.00000001);
    float hu = ou / C;
    float hv = ov / C;
    float gate = fcSmooth(0.015, 0.06, C);

    float hAng = atan(ov, abs(ou) < 0.000001 ? 0.000001 : ou);
    float hDeg = mod(degrees(hAng) + 360.0, 360.0);
    float wf = fcSmooth(56.0, 68.0, hDeg) * (1.0 - fcSmooth(138.0, 172.0, hDeg));
    float dh = wf * 0.757676;
    float dc = wf * -0.079099;
    float da = wf * -0.120041;

    float w1 = exp(5.5 * (hu * -0.951057 + hv * 0.309017 - 1.0));
    dh += w1 * -0.11086; dc += w1 * 0.391882; da += w1 * 0.18;
    float w2 = exp(5.5 * (hu * -0.951057 + hv * -0.309017 - 1.0));
    dh += w2 * -0.045421; dc += w2 * -0.159362; da += w2 * 0.062555;
    float w3 = exp(3.0 * (hu * 0.707107 + hv * -0.707107 - 1.0));
    dh += w3 * -0.325884; dc += w3 * -0.266123; da += w3 * -0.153217;

    float dhT = gate * dh;
    float sC = max(0.0, 1.0 + gate * dc);
    float dA = gate * C * da;
    float cd = cos(dhT);
    float sd = sin(dhT);
    float ou2 = sC * (ou * cd - ov * sd);
    float ov2 = sC * (ou * sd + ov * cd);
    float A2 = A + dA;
    vec3 o;
    o.r = A2 + 0.666666667 * ou2;
    o.g = A2 - 0.333333333 * ou2 + 0.577350269 * ov2;
    o.b = A2 - 0.333333333 * ou2 - 0.577350269 * ov2;
    return max(o, vec3(0.0));
}

float fcEnv(vec2 p, float W2H) {
    // p = (x, y_top) in 0..1 ; default haze geometry
    float dx = (p.x - 0.869336) * W2H;
    float dy = p.y - 0.081183;
    float ca = 0.293316;   // cos(-72.9434 deg)
    float sa = -0.956015;  // sin(-72.9434 deg)
    float u = (dx * ca + dy * sa) / 0.18539;
    float v = (-dx * sa + dy * ca) / 0.248768;
    return exp(-0.5 * (u * u + v * v));
}

void main() {
    vec2 uv = clamp(vTex, 0.0, 1.0);
    vec4 src = texture2D(uTexture, uv);
    float a = src.a;
    vec3 x = src.rgb / max(a, 0.0001);

    float texX = max(uTexelSize.x, 0.000001);
    float texY = max(uTexelSize.y, 0.000001);
    float H = 1.0 / texY;
    float W2H = texY / texX;          // width / height

    bool qual = uQuality > 0.5;

    // ---- Quality: original USM (25 taps), then Sharpen 34 and Unsharp Mask r22.1 / 32 ----
    if (qual) {
        vec2 st = vec2(fcSigma * texX / texY, fcSigma);
        vec3 acc = vec3(0.0);
        for (int j = -2; j <= 2; j++) {
            float wj = (j == 0) ? 6.0 : ((j == 1 || j == -1) ? 4.0 : 1.0);
            for (int i = -2; i <= 2; i++) {
                float wi = (i == 0) ? 6.0 : ((i == 1 || i == -1) ? 4.0 : 1.0);
                acc += (wi * wj / 256.0) * fcTap(uv + vec2(float(i), float(j)) * st);
            }
        }
        vec3 d = x - acc;
        d = sign(d) * max(abs(d) - fcThresh, vec3(0.0));
        vec3 base = clamp(x + fcAmount * d, 0.0, 1.0);

        // Sharpen (amount 34): 4-neighbour Laplacian at 1 texel
        vec3 nb = 0.25 * (fcTap(uv + vec2(texX, 0.0)) + fcTap(uv - vec2(texX, 0.0)) +
                          fcTap(uv + vec2(0.0, texY)) + fcTap(uv - vec2(0.0, texY)));
        vec3 sharp = 0.34 * (x - nb);

        // Unsharp Mask (radius 22.1 @1080p scaled by height, amount 32): Gaussian, sigma = radius/2
        float sg = 22.1 * 0.5 * (H / 1080.0);
        vec2 s1 = vec2(sg * texX, sg * texY);
        vec2 s2 = 2.0 * s1;
        float k = 0.70710678;
        vec3 g = 1.0 * x;
        float wsum = 1.0;
        float w1 = 0.60653066;
        g += w1 * (fcTap(uv + vec2(s1.x, 0.0)) + fcTap(uv - vec2(s1.x, 0.0)) +
                   fcTap(uv + vec2(0.0, s1.y)) + fcTap(uv - vec2(0.0, s1.y)) +
                   fcTap(uv + k * s1) + fcTap(uv - k * s1) +
                   fcTap(uv + vec2(k * s1.x, -k * s1.y)) + fcTap(uv + vec2(-k * s1.x, k * s1.y)));
        wsum += 8.0 * w1;
        float w2 = 0.13533528;
        g += w2 * (fcTap(uv + vec2(s2.x, 0.0)) + fcTap(uv - vec2(s2.x, 0.0)) +
                   fcTap(uv + vec2(0.0, s2.y)) + fcTap(uv - vec2(0.0, s2.y)));
        wsum += 4.0 * w2;
        g /= wsum;
        vec3 usm = 0.32 * (x - g);

        x = clamp(base + sharp + usm, 0.0, 1.0);
    }

    // ---- Colour Correction + Flicker ----
    if (uCc > 0.5) {
        x = fcGrade(x);
        float fl = 1.0 + 0.04 * fcFlicker(uTime * 39.0);
        x *= fl;
    }

    // ---- Quality: vertical multiply gradient ----
    float yTop = 1.0 - uv.y; // vTex y=0 is the bottom edge
    if (qual) {
        float r = fcSmooth(0.14, 0.758341, yTop);
        x = x * (vec3(1.0) - r * vec3(0.262739, 0.256392, 0.28055));
    }
    x = clamp(x, 0.0, 1.0);

    // ---- Haze Flare: Gaussian glow, tinted by the picture's own highlights, screened ----
    if (uHaze > 0.5) {
        float ca = 0.293316;
        float sa = -0.956015;
        vec3 tint = vec3(0.0);
        float ws = 0.0;
        for (int j = -1; j <= 1; j++) {
            for (int i = -1; i <= 1; i++) {
                float pu = float(i) * 1.2;
                float pv = float(j) * 1.2;
                float w = exp(-0.5 * (pu * pu + pv * pv));
                float dxh = pu * 0.18539 * ca - pv * 0.248768 * sa;
                float dyh = pu * 0.18539 * sa + pv * 0.248768 * ca;
                float px = 0.869336 + dxh / W2H;
                float py = 0.081183 + dyh;
                float pyT = 1.0 - py;
                vec2 q = vec2(px, pyT);
                vec2 o3 = vec2(3.0 * texX, 3.0 * texY);
                vec3 s = 0.5 * (fcTap(q + o3) + fcTap(q - o3));
                tint += w * max(s - 0.2, vec3(0.0));
                ws += w;
            }
        }
        tint /= max(ws, 0.0001);
        float e = fcEnv(vec2(uv.x, yTop), W2H);
        vec3 f = clamp(1.1 * e * tint, 0.0, 1.0);
        x = vec3(1.0) - (vec3(1.0) - x) * (vec3(1.0) - f);
    }

    x = clamp(x, 0.0, 1.0);
    gl_FragColor = vec4(x * a, a);
}
