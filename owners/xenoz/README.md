# Xenoz’s Keyflaw CC

Xenoz’s completed look-fit recovers a four-stage Keyflaw look: the refined `M2_Dade_srgb` colour grade, a smooth vertical multiply darkening gradient, separable 25-tap RGB unsharp masking for quality, and a subtle non-destructive ambient screen haze flare. The source-of-truth implementation and controls are documented in [spec/LOOK_SPEC.md](spec/LOOK_SPEC.md), [spec/look_params.json](spec/look_params.json), [spec/look_apply.py](spec/look_apply.py), and [spec/look.cube](spec/look.cube). The quantitative verification metrics and side-by-side images are in [reports/REPORT.md](reports/REPORT.md).

## Stages and Switches
1. **Stage 1 — Colour Correction (`M2_Dade_srgb`):** Per-channel sRGB levels expansion, cool slate-blue shadow toe (`luma < 0.28`, lifting darks with cool tint), 3x3 colour matrix, and closed-form opponent-polar hue-chroma shaper boosting electric cyan/sky tones while protecting warm golden anime skin from green/cyan contamination.
2. **Stage 2 — Spatial Vertical Gradient:** Smoothstep multiplicative darkening ramp (`y0 = 0.2691`, `y1 = 0.8721`, `strength = [0.057, 0.130, 0.135]`), drawing attention to the upper-frame action.
3. **Stage 3 — Quality (Unsharp Mask):** Single-pass separable 25-tap RGB unsharp mask (`sigma = 0.000535 * H`, amount `1.10`, threshold `1.68 / 255`), enhancing line-art edges without introducing ringing or compression halos.
4. **Stage 4 — Haze Flare:** Subtle ambient highlight Screen glow (`intensity = 0.12`, `colour = [0.35, 0.55, 0.95]`), providing gentle highlight blooming without washing out black levels or character features.

The shader exposes standard Keyflaw switches for **Colour Correction** (`cc`), **Quality (Sharpen + Gradient)** (`quality`), **Haze Flare** (`flare`), and **Master Intensity** (`intensity`).

## Accuracy and Parity
- **Pair A (1280x720 Wide Shot):** Flat median CIEDE2000 is **`1.412`** (down from `15.596` raw), with mean flat MAE of **`4.23 / 255`**, edge RMSE of **`20.56 / 255`**, and luma SSIM of **`0.9388`**.
- **Pair B (1280x720 Eye Close-Up):** Flat median CIEDE2000 is **`3.264`** (down from `7.089` raw), with mean flat MAE of **`5.32 / 255`**, edge RMSE of **`34.98 / 255`**, and luma SSIM of **`0.9242`**.
- **Skin Reproduction Accuracy:** Warm character skin tones match the target edit to within **1.6 levels on Red**, **0.75 levels on Green**, and **0.05 levels on Blue**, completely eliminating pasty greenish-cyan skin drift.
- **Shader Parity:** GLSL fragment shader math matches Python reference implementation (`look_apply.py`) across all 24 test vectors to within **`0.000049`** (< `1 / 255`).

## Repository Organization
- `inputs/`: Private lossless matched frame-pair PNGs.
- `masks/`: Alpha/binary masks for letterbox bars, burned-in subtitles, dilated line edges, and flat interiors.
- `analysis/`: Aligned sub-pixel intermediates, diagnostic scripts, and optimization pipelines.
- `spec/`: Source-of-truth look specification (`LOOK_SPEC.md`), parameters (`look_params.json`), reference script (`look_apply.py`), and 33^3 LUT (`look.cube`).
- `reports/`: Quantitative report (`REPORT.md`) and side-by-side visual error comparisons (`side_by_side_comparison.png`).
- `pack/`: Keyflaw effect source (`effect.json` and `shader.glsl`). Installable pack is bundled in `releases/MotionSalt_CC.kfpack`.
