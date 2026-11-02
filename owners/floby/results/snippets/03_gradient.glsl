// --- Plugin: gradient (tint, uses yTop = 1.0 - uv.y, 0 extra taps) ---
vec3 msApplyGradient(vec3 col, vec2 uv) {
    float yTop = 1.0 - uv.y;
    float t = 0.5 + (uv.x - 0.5) * 0.018674 + (yTop - 0.5) * -0.999826;
    float u = clamp((t - (0.377200)) / 0.372900, 0.0, 1.0);
    float s = u * u * (3.0 - 2.0 * u);
    return clamp(col + s * vec3(0.076380, 0.081240, 0.081400), 0.0, 1.0);
}
