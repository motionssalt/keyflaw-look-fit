// --- Plugin: unsharp_mask (20 extra taps, gate=hard, mode=luma/srgb) ---
// Expects helper: vec3 msFetchGraded(vec2 uv);
vec3 msUsmToLinear(vec3 c) {
    vec3 lo = c / 12.92;
    vec3 hi = pow(max((c + 0.055) / 1.055, vec3(0.0)), vec3(2.4));
    return mix(hi, lo, step(c, vec3(0.04045)));
}
vec3 msUsmToSrgb(vec3 c) {
    vec3 lo = c * 12.92;
    vec3 hi = 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055;
    return mix(hi, lo, step(c, vec3(0.0031308)));
}
vec3 msUsmGateVec(vec3 d, float thr) {

    return d * (vec3(1.0) - step(abs(d), vec3(thr)));
}
vec3 msApplyUnsharpMask(vec3 centerCol, vec2 uv, vec2 texelSize) {
    float invAspect = texelSize.x / max(texelSize.y, 0.00001);
    vec3 work = centerCol;
    vec3 blur1 = 0.100395 * work;
    blur1 += 0.066841 * msFetchGraded(uv + vec2(0.003448 * invAspect, 0.000000));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(0.002438 * invAspect, 0.002438));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(0.000000 * invAspect, 0.003448));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(-0.002438 * invAspect, 0.002438));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(-0.003448 * invAspect, 0.000000));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(-0.002438 * invAspect, -0.002438));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(-0.000000 * invAspect, -0.003448));
    blur1 += 0.066841 * msFetchGraded(uv + vec2(0.002438 * invAspect, -0.002438));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(0.006950 * invAspect, 0.001862));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(0.005088 * invAspect, 0.005088));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(0.001862 * invAspect, 0.006950));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(-0.001862 * invAspect, 0.006950));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(-0.005088 * invAspect, 0.005088));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(-0.006950 * invAspect, 0.001862));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(-0.006950 * invAspect, -0.001862));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(-0.005088 * invAspect, -0.005088));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(-0.001862 * invAspect, -0.006950));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(0.001862 * invAspect, -0.006950));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(0.005088 * invAspect, -0.005088));
    blur1 += 0.030406 * msFetchGraded(uv + vec2(0.006950 * invAspect, -0.001862));
    vec3 lw = vec3(0.2126, 0.7152, 0.0722);
    vec3 g1 = msUsmGateVec(vec3(dot(work - blur1, lw)), 0.019608);
    work = work + 0.610910 * g1;
    work = clamp(work, 0.0, 1.0);
    return work;
}
