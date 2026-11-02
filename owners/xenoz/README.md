# Keyflaw Look-Fit: Xenoz's CC

Recover editor **Xenoz**'s colour grade and quality processing from frame pairs for Keyflaw shader pack specification.

## Project Background
Victor is a solo developer and motion designer working under the brand **MOTIONSALT**. He makes colour corrections (CCs) for **Keyflaw**, a video editing app that loads custom shader effects as `.kfpack` packs.

This repository conducts the **measuring step**: analyzing frame pairs (the edited export screenshot and the geometrically matched reconstructed clean frame) to produce a precise, machine-checkable look specification (`LOOK_SPEC.md`, `look_params.json`, `look_apply.py`, and `look.cube`).

## Pipeline Architecture
1. **Q1. Setup, inputs, masks**: Validate input frames, compute letterbox bars, subtitle/caption masks, line-art edges, and flat-interior sampling masks.
2. **Q2. Alignment audit**: Sub-pixel ECC alignment verification on high-frequency edge maps.
3. **Q3. Colour correction fit**: Model selection between per-channel Levels (M1), Levels + 3x3 colour matrix (M2), and monotonic splines (M3) across sRGB vs Linear spaces.
4. **Q4. Spatial gradient discovery**: 2D polynomial surface fit and vertical darkening ramp parameterization.
5. **Q5. Unsharp mask recovery**: Halo signature fitting with nuisance pre-blur accounting for mobile recompression.
6. **Q6. Haze flare / glow**: Low-frequency residual analysis, corner glow positioning, additive/screen blending.
7. **Q6b. Secondary effects**: Testing for vignette, grain, chromatic aberration, black lift/veil.
8. **Q7. Order of operations & joint composite**: Global optimization and stage ablation metrics.
9. **Q8. Deliverables & verification**: `LOOK_SPEC.md`, `look_params.json`, `look_apply.py`, `look.cube`, and `REPORT.md`.

## Current Status
- **Current Phase**: `Q1 (Setup, inputs, masks)`
- **Status**: `blocked` (Awaiting attachment of Xenoz frame pairs in `inputs/`)
