# Repository tidy notes

## Inventory

Repository: `motionssalt/keyflaw-look-fit` (private, default branch `master`).

The repository contains the completed Floby analysis for eight stages (Q1–Q8): four input frame-pair PNGs, masks and mask metadata, aligned/intermediate outputs, fit and verification scripts, the look specification, parameters, reference implementation, 3D LUT, quantitative report, existing documentation, and `BUILD_STATE.json`.

No `.kfpack`, `suite.json`, `effect.json`, or `shader.glsl` exists in the repository. No prompt files or reusable cross-owner tools exist. The existing `.gitignore` is retained at the repository root.

## Categorisation plan

- `inputs/` → `owners/floby/inputs/`
- `masks/` → `owners/floby/masks/`
- `outputs/` and `src/` → `owners/floby/analysis/`
- `REPORT.md` → `owners/floby/reports/REPORT.md`
- `LOOK_SPEC.md`, `look_params.json`, `look_apply.py`, `look.cube` → `owners/floby/spec/`
- `docs/BUILD_PROMPT.md` and `docs/manifest.md` remain under `docs/`; this note remains there too.
- No `owners/floby/pack/`, `tools/`, or `prompts/` content will be invented because none exists.

## Uncertainty and decisions

- The `outputs/` and `src/` trees are analysis artifacts, including intermediate results and scratch/fit code, so they belong in `owners/floby/analysis/`.
- `look_apply.py` is a source-of-truth implementation and therefore moves with the other spec deliverables, not with analysis scripts.
- `look.cube` is a source-of-truth deliverable even though it contains the Stage 2 LUT only; it moves to `owners/floby/spec/`.
- Anime frames and derived frame images stay in the private repository under `owners/floby/inputs/` and analysis directories. They will not be uploaded to the release.
- The release will note that the `.kfpack` and pack source are not present and therefore cannot be attached.

## Path-fix plan

After moving, update analysis scripts to resolve the repository root from their new location. Update documentation links and the reference script's parameter lookup for the new `owners/floby/spec/` location. Run `look_apply.py` from its new location and run the parity verifier from analysis against the moved source-of-truth files.
