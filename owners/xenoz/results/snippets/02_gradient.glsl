// --- Plugin: gradient (multiply, uses yTop = 1.0 - uv.y, 0 extra taps) ---
vec3 msApplyGradient(vec3 col, vec2 uv) {
    float yTop = 1.0 - uv.y;
    float t = 0.5 + (uv.x - 0.5) * 0.181429 + (yTop - 0.5) * -0.983404;
    float u = clamp((t - (0.355400)) / 0.434400, 0.0, 1.0);
    float s = u * u * (3.0 - 2.0 * u);
    return clamp(col * (vec3(1.0) + s * vec3(0.043210, 0.049380, 0.045500)), 0.0, 1.0);
}
