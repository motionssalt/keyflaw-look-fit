# Floby’s Keyflaw CC

Floby’s completed look-fit recovers a four-stage Keyflaw look: RGB unsharp masking for quality, the `M2_Dade_srgb` colour correction, a vertical multiply gradient, and a top-right anisotropic Gaussian screen haze flare. The source-of-truth implementation and controls are in [spec/LOOK_SPEC.md](spec/LOOK_SPEC.md), [spec/look_params.json](spec/look_params.json), [spec/look_apply.py](spec/look_apply.py), and [spec/look.cube](spec/look.cube). The quantitative results are in [reports/REPORT.md](reports/REPORT.md).

## Stages and switches

The quality stage is a 25-tap RGB unsharp mask. Colour correction combines sRGB levels, a cool slate-blue shadow toe, a neutral-preserving matrix, and a Dade-style selective hue/chroma shaper. The spatial stage is a smooth vertical multiply gradient, and the final stage is a top-right screen flare. The reference implementation exposes switches for unsharp, colour correction, gradient, flare, Dade strength, master intensity, and flare preset (`default`, `pairA`, or `pairB`).

## Accuracy and caveats

On the held-out validation, median CIEDE2000 is `2.2586`, versus `2.2392` in-sample, a gap of only `0.0194`. With the scene flare, the reported median CIEDE2000 is `2.1516` for Pair A, `2.2394` for Pair B at 720p, and `2.0665` for Pair B at native 409p. The report’s honest caveats are that matched originals are AI reconstructions with a residual colour/recompression floor, Pair B contains a hallucinated golden-yellow bush that cannot be corrected spatially without affecting real yellow clothing and hair, and flare tint/intensity vary by scene.

## Repository stages

`inputs/` holds the four private matched frame-pair PNGs. `masks/` holds masks and overlay previews. `analysis/` holds aligned/intermediate outputs and the fit and parity scripts. `reports/` holds the quantitative report. `spec/` holds the source-of-truth deliverables. Anime frames remain private in the repository and are not release assets.

No `.kfpack`, `suite.json`, `effect.json`, or `shader.glsl` was found in this repository, so the release contains no pack or pack-source download. When a pack is built later, the intended install flow is to download the `.kfpack` from the release and import it into Keyflaw.
