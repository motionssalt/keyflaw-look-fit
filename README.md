# keyflaw-look-fit

Quantitative recovery of colour correction, spatial gradient darkening, unsharp masking, and haze flare from two anime frame pairs for **MOTIONSALT** / **Keyflaw**.

- **`LOOK_SPEC.md`** — Complete shader-ready look specification, parameter tables, control sheet, and unit test vectors.
- **`look_params.json`** — Machine-readable source of truth for all fitted parameters.
- **`look_apply.py`** — Reference Python implementation matching `LOOK_SPEC.md`.
- **`look.cube`** — 33x33x33 3D LUT of the colour-correction stage.
- **`REPORT.md`** — Quantitative validation metrics, stage ablations, cross-validation, and visual comparisons.
- **`BUILD_STATE.json`** — Machine-readable build state and interim/final results.
