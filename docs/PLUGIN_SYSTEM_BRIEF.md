# PLUGIN-BASED LOOK-FIT SYSTEM: build a program that measures, plans and tunes a colour-correction "stack" layer by layer, then run it in GitHub Actions

Self-contained brief for MOTIONSALT. Read all of it first. Assume nothing from earlier chats. The repo was just reset (only inputs remain); this job builds the new system and runs it.

## STEP 0: FILL-IN FIELDS
```
GITHUB_PAT = <REDACTED_IN_REPO>
REPO       = motionssalt/keyflaw-look-fit
OWNERS     = all                     (or a comma-separated list of folder names under owners/)
```
- Work ONLY in `REPO`. **Never create any new repository.** Never touch other repos. The repo is public: **never commit credentials** or write their values anywhere (names only). Inside Actions use the built-in `GITHUB_TOKEN` (set `permissions: contents: write`); use `GITHUB_PAT` only from your own environment to push workflow files.
- If the repo is missing or the PAT cannot push, stop and tell Victor in one short message.
- Inputs are already in `owners/<owner>/inputs/` (currently floby, gojo, xenoz: 16 images). **Never ask Victor to attach images.** Read `README.md` for the pair table. Read `SKILL.md` (repo root) before building any Keyflaw effect.

## 1. Role and autonomy
Full autonomy over implementation. Do not stop to ask Victor anything unless the work cannot continue; pick the sensible default and record it in `BUILD_STATE.json` `decisions`. Victor works from an Android phone only: never ask him to run anything. Free tools only (Python, numpy, scipy, OpenCV, scikit-image; no GPU, no paid APIs). Commit and push after every meaningful unit of work (builders die before committing). Finish each phase completely before the next; no skimming; mark a phase `done` only after verifying its acceptance criteria and recording how you checked.

## 2. Background and what went wrong before
Victor (MOTIONSALT, solo editor, Android only) makes Keyflaw colour corrections (CCs) that copy the look of other editors. Earlier AI attempts fitted a small closed-form model (levels + matrix + hue lobes), then guessed sharpening and a "haze flare", and stopped at a "noise floor". The results were visibly wrong: wrong channels and levels, sharpening that produced speckle and halos on compressed sources, and a flare that was just a painted overlay. Doing the same job by hand in After Effects with Channel View and Levels was more accurate.

What Victor wants instead is how After Effects works: **a stack of separate effect plugins, each with its own parameters, tuned one layer at a time, looking at the result after each layer.** First check what the target does that the reference does not, plan the effects needed, then set them up layer by layer, only the ones that are actually visible.

Proof that direct fitting beats small formulas: on a clean, well-aligned pair (shift 0.1 px, edge correlation 0.95), a **17x17x17 3D colour table fitted directly from flat-area pixel pairs** (ridge + second-difference smoothness lambda 0.3, trilinear interpolation, blurred sigma 2, block cross-validation with 96 px blocks) gave held-out median CIEDE2000 3.9 to 1.55, p90 12.9 to 3.6, MAE 8.0 to 3.75, while degree 1-4 polynomials only got MAE 4.9-6.3. Per-channel histogram matching alone did nothing on that pair, because the grade was hue-dependent. Use that as the colour plugin's starting method.

## 3. Terms
- **target** = the edited frame (what the look should produce). **reference** = the clean/original frame the effects are applied to. A **pair** = one target + its reference. Some references are AI-redrawn. Victor made them carefully and they are good replicas: treat every pair as trustworthy. Do not score, rank, weight, down-weight or exclude pairs, and do not build any pair-validation step.
- **plugin** = one effect with named parameters, bounds, a render function, a detector, a fitter and a GLSL exporter.

## 4. Architecture to build (Python package `lookfit/`, plus `.github/workflows/`)
```
lookfit/
  core/            image io, alignment, masks (bars, caption/subtitle, border), colour spaces, metrics
  plugins/         one file per plugin (below), all following plugins/base.py
  planner.py       detect + plan
  tuner.py         layer-by-layer tuning + joint refinement
  export/          look.json, look.cube, GLSL snippets, report builders
  run.py           CLI: python -m lookfit.run --owner <slug>
tests/             unit tests for every plugin (known params -> render -> re-fit recovers them)
.github/workflows/tune.yml   workflow_dispatch (input: owner or all) + matrix per owner; uploads artifacts; commits small results back
docs/PLUGIN_PARAMETER_RESEARCH.md   (see appendix; commit it first)
```
**Plugin interface (plugins/base.py):** `name`, `param_spec` (name, default, min, max, unit, scale-law e.g. fraction of frame height), `detect(ref, tgt, ctx) -> Evidence(score, notes, mask_of_interest)`, `initial_guess(ref, tgt, ctx)`, `render(img, params) -> img` (float32, resolution independent), `loss(pred, tgt, ctx)` (its own metric on its own pixels/mask), `fit(ref_in, tgt, ctx) -> params, held_out_report`, `to_glsl(params)` (GLSL ES 1.00 snippet, no textures), `describe(params)` (plain words).

**Plugins (each is its own file with unit tests):**
1. `colour`: direct 3D LUT fit as in section 2 (also try gamma vs linear, 17 vs 25 grid, cluster-weighted flat pixels, pre-blur). Also provide a **shader-sized compression** (per-channel 33-knot curves + 3x3 matrix + residual, or low-rank separable terms, or a coarse 9^3/12^3 grid with tetrahedral interpolation as unrolled constants) and report the accuracy lost; export the full table as `look.cube`.
2. `unsharp_mask`: After Effects model: `out = x + (amount/100) * (x - Gauss(x, sigma))` with a gate threshold (no change when abs(diff) <= threshold); sigma = radius (start there; test 0.5x and 2x); RGB vs luma; gamma vs linear. Parameters, ranges and procedure in the appendix. Radius stored as a fraction of frame height.
3. `sharpen`: After Effects Sharpen is a single-amount fixed small kernel whose exact kernel is NOT published: fit a 3x3 model `x + k*(x - Blur_small(x))`, kernels: 4-neighbour, 8-neighbour, 3x3 binomial. Label it "fitted, not known" in every output.
4. `haze_flare`: **a real bloom, never an overlay**: threshold + soft knee on the picture's own highlights, 3-5 blur scales (fractions of height), per-channel width multipliers, tint, intensity, Screen (also test Add and Soft Light); optional anisotropy and a positional envelope only if proven; the glow colour must come from the picture. Required tests: zero on a black frame, stronger around bright shapes, and it must not help if applied to a mismatched scene. If the smooth residual after colour and sharpening is within error, the plugin reports `absent`.
5. `grain`: detect noise in flat areas of the target beyond what the reference has (std, spatial frequency, luma dependence); distinguish film grain from recompression blocks; model luma-dependent Gaussian noise with size (statistics matching, since random pixels cannot be reproduced). If the evidence is weak, report `not provable`; do not add it.
6. `gradient`: vertical (or linear at an angle) multiply/tint gradient: start, end, strength per channel, smoothstep. Simple low-frequency fit.
7. `vignette`: radial falloff multiply: centre, radius, softness, strength. Simple low-frequency fit.
8. Optional if the detector sees them: `black_lift` (global veil), `chromatic_aberration`, `flicker`. Include a plugin only if its detector fires on real evidence.

## 5. Procedure inside `run.py` (per owner; owners are independent, never mix looks across owners)
**P0 Analysis.** Per pair: align (sub-pixel ECC / phase correlation; record shift and edge correlation for the log only), detect bars/caption/border masks, build flat-interior and edge masks. Use every pair as given.
**P1 Detect.** Run every plugin's `detect`: what does the target do that the reference does not? Produce `evidence.json` and a short plain-words list. Look at the evidence like a person would (residual images per channel, edge-halo plots, low-frequency map, noise map) and save them.
**P2 Plan.** Ordered stack from the evidence. Default order: colour, unsharp/sharpen, haze flare, grain, gradient, vignette (test adjacent-order swaps by held-out loss and keep the best order). Drop plugins whose evidence is absent.
**P3 Tune layer by layer.** For each planned plugin in order: with all earlier layers fixed, optimise its parameters with a suitable optimiser (closed form where possible, otherwise bounded L-BFGS / Nelder-Mead / differential evolution with multiple starts) against **its own loss on its own pixels** (colour: CIEDE2000 on blurred flat pixels; sharpen/unsharp: edge-profile error + SSIM on edge areas with the threshold gate; flare: low-frequency residual + the real-bloom tests; grain: noise statistics; gradient/vignette: low-frequency residual). Use block cross-validation. **Accept a layer only if it improves held-out error by a margin; otherwise remove it and record why.** Save the stack, the render and the residual after each layer.
**P4 Joint refinement.** Several rounds of coordinate descent over all accepted layers (earlier layers can be nudged now that later ones exist). Stop when the held-out joint loss stops falling, **not** at an assumed noise floor. Report what limits the result with evidence.
**P5 Export.** `look.json` (every parameter, scale law, order), `look.cube`, per-plugin GLSL snippets (GLSL ES 1.00, single pass, no textures, taps counted), `describe` text, the report below.
**P6 Report.** Per pair and per layer: median and p90 CIEDE2000, per-channel MAE, edge-profile RMSE, SSIM, before/after and per-layer gain tables; images: reference | prediction | target | signed residual. Honest limits section. Never claim "100% parity" unless true.

## 6. Actions: the tuning-and-checking loop
- `tune.yml`: `workflow_dispatch` with input `owner` (`all` = matrix over every owner), Python setup + pip cache, `timeout-minutes` below the free limit, runs `python -m lookfit.run`, uploads full results as artifacts and commits only small result files (`owners/<owner>/results/`: json, cube, snippets, report, a few compressed images) with `[skip ci]`. Free minutes are unlimited on public repos but keep runs sensible.
- **You** (the AI) run the workflow, read the results, find the weakest layer, improve the plugin or the optimiser, rerun. Repeat until a further change no longer improves held-out error, owner by owner. Keep each iteration's metrics in `BUILD_STATE.json` `results` so a different AI can resume.
- Develop and unit-test locally first; the workflow is for the full runs.

## 7. Build the Keyflaw effects (last phase, per owner, only after tuning is verified)
- Follow `SKILL.md`. Target Keyflaw 1.4.8: single-pass GLSL ES 1.00; no `passes`, no `expandBounds`, no COLOR params. Keyflaw's `vTex` has y = 0 at the BOTTOM edge: use `yTop = 1.0 - vTex.y` for every vertical position.
- One effect per owner (use the existing owner names, ids `MS_<owner_slug>_cc`), shared suite "Motion Salt CC" (`com.motionsalt.cc`, category `MotionSalt CC` on suite and every effect, `minAppVersion` 1.2.4, bump the version). Switches (BOOL) only: Colour Correction, Quality (sharpen, unsharp, gradient/vignette/grain as measured), Haze Flare (only if it exists). No sliders on the flare. Keep taps near 60 or fewer.
- Validate: validator/packer from `SKILL.md`, glslangValidator compile check (`#version 100` prepended in a temp copy), numpy port of the shader maths vs the Python plugins (colour within 1/255, others within 2/255). Do not claim it was tested inside Keyflaw.
- Output `releases/MotionSalt_CC.kfpack` and publish a GitHub Release with it. No anime frames inside the release assets.

## 8. State, resume and commits
`BUILD_STATE.json` at the root (and `owners/<owner>/BUILD_STATE.json`): phases, per-owner status, `decisions`, `results` (per iteration metrics), `known_issues`, `last_updated`, `last_session_note`; no secrets. On start read it and continue from the first phase not `done`. Commit and push after every file or small unit. Save this brief as `docs/PLUGIN_SYSTEM_BRIEF.md` in the first commit.

## 9. Order of work (finish each completely)
(1) Commit the brief and the research file; read the repo; plan in `docs/PLAN.md`. (2) Core: io, alignment, masks, metrics + tests. (3) Plugins one by one with unit tests (recover known params). (4) Planner and tuner. (5) Workflow. (6) First full run on one owner with the cleanest pair, inspect, fix; then all owners. (7) Iterate until held-out error stops improving. (8) Export + report. (9) Build and release the effects. (10) Final verification.

## 10. Constraints
Do not edit input images (work on copies). Do not delete anything under `owners/*/inputs/`. No UI work. Never create another repo. Never rewrite history or force-push. Do not hard-code any one clip's numbers into plugins (parameters come from fitting).

## 11. Final message to Victor (short)
Where the results and the `.kfpack` are; per owner, before/after colour error and which layers were found (and which were absent); whether unsharp and sharpen now match; whether a real haze flare exists for each CC; the largest remaining error and why; the one most useful next step. Do not paste files.
