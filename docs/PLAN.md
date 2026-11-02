# Keyflaw Plugin-Based Look-Fit System — Architecture & Execution Plan

## 1. Repository Audit Summary

- **Repository:** `motionssalt/keyflaw-look-fit` (branch `master`, public; zero credentials stored anywhere in repo).
- **Ground-Truth Inputs (16 lossless PNGs = 8 pairs across 3 owners, never modified):**
  - `floby` (2 pairs):
    - `pairA`: `1278x720` edited vs `1278x720` original (`edge_corr ~ 0.956`; original has 35 px top/bottom letterbox bars; edited has burnt-in subtitle `"When It's time to do a special edit..."`).
    - `pairB`: `1291x720` edited vs `720x409` original (`scale ~ 1.79x` + translation; requires SIFT+RANSAC + sub-pixel ECC alignment).
  - `gojo` (4 pairs):
    - `pairA`: `1920x1080` edited vs `1364x768` original (`scale ~ 1.406x`; letterbox bars top/bottom ~94 px in 1080p).
    - `pairB`: `1920x1080` edited vs `1364x768` original (`scale ~ 1.406x`; letterbox bars ~77 px in 1080p; bright sword sparks).
    - `pairC`: `1920x1080` edited vs `1364x768` original (`scale ~ 1.406x`; close-up face).
    - `pairD`: `1920x1080` edited vs `1364x768` original (`scale ~ 1.68x` zoom/crop in edit; SIFT+RANSAC affine/similarity + ECC aligns cleanly).
  - `xenoz` (2 pairs):
    - `pairA`: `1280x720` edited vs `1376x768` original (`scale ~ 0.929x`; bright energy burst + cyan sky).
    - `pairB`: `1280x720` edited vs `1359x768` original (`scale ~ 0.947x` + shift; burnt-in subtitle `"IS THIS..."`).
- **Pair Policy:** Every pair is used equally without scoring, ranking, weighting, down-weighting, or exclusion. Alignment shift and edge correlation are recorded strictly for diagnostic logging.

---

## 2. Package Architecture (`lookfit/`)

```
lookfit/
  __init__.py
  core/
    __init__.py
    io.py              # Lossless float32 [0,1] RGB I/O, input SHA-256 immutability check, pair loader
    alignment.py       # Multi-candidate SIFT+RANSAC + multi-scale gradient ECC sub-pixel alignment
    masks.py           # Letterbox/pillarbox bars, border guard, subtitle/caption outlier mask, flat & edge masks, 96px block CV folds
    colour_spaces.py   # sRGB <-> linear RGB, CIE XYZ (D65), CIE L*a*b*, Rec.709 luma
    metrics.py         # Exact CIEDE2000, per-channel MAE, normal edge-profile RMSE, SSIM, noise spectrum/luma stats
  plugins/
    __init__.py
    base.py            # ParamSpec, Evidence, FitReport, Plugin ABC
    colour.py          # Direct 3D LUT (17^3 / 25^3, ridge + 2nd-diff Laplacian, gamma vs linear, cluster weighting) + GLSL ES 1.00 shader compression + .cube export
    unsharp_mask.py    # AE Unsharp Mask (amount, radius_frac, threshold hard/soft gate, sigma 0.5x/1x/2x, RGB vs luma, gamma vs linear, nuisance pre-blur, 1- or 2-stage)
    sharpen.py         # AE Sharpen 3x3 fixed neighbourhood (4-nbr, 8-nbr, binomial; explicitly labelled "fitted, not known")
    haze_flare.py      # Real highlight bloom (soft-knee threshold, 3-5 height-scaled blurs, R:G:B width multipliers, tint, Screen/Add/SoftLight, 3 mandatory real-bloom tests)
    grain.py           # Flat-region excess noise detector (DCT blockiness vs grain check) + luma-dependent sized grain statistics matcher
    gradient.py        # Linear/vertical tint/multiply smoothstep gradient (yTop = 1.0 - vTex.y aware)
    vignette.py        # Aspect-corrected radial falloff multiply
    black_lift.py      # Optional global veil / black-point lift (included only if detector fires beyond colour LUT)
    chromatic_aberration.py # Optional radial R/B lateral fringe shift (included only if edge-chroma detector fires)
  planner.py           # P1 detect -> evidence.json + diagnostic maps; P2 ordered stack + adjacent-swap order check
  tuner.py             # P3 sequential layer-by-layer fitting with 96px block CV acceptance margin; P4 coordinate-descent joint refinement
  export/
    __init__.py
    cube.py            # Iridas .cube 3D LUT writer + reader/verifier
    glsl_exporter.py   # GLSL ES 1.00 snippet composer, tap counter, numpy shader-port verifier, glslangValidator runner
    report_builder.py  # Markdown report + visual strips (ref | pred | tgt | signed residual, edge-halo, low-freq, noise maps)
    kfpack.py          # Keyflaw 1.4.8 suite builder (Motion Salt CC, com.motionsalt.cc) + SKILL.md validator/packer
  run.py               # End-to-end P0..P6 CLI (`python -m lookfit.run --owner <slug|all>`)
tests/
  test_core.py
  test_plugin_colour.py
  test_plugin_unsharp_mask.py
  test_plugin_sharpen.py
  test_plugin_haze_flare.py
  test_plugin_grain.py
  test_plugin_gradient_vignette.py
  test_optional_plugins.py
  test_planner_tuner.py
  test_kfpack_shader_parity.py
```

---

## 3. Pipeline Stages (`P0` – `P6`)

1. **P0 Analysis:** Align each pair to target geometry via candidate tournament (uniform resize + ECC, SIFT similarity + ECC, SIFT affine + ECC) maximising interior gradient correlation. Compute `valid_mask`, `bar_mask`, `border_mask`, `caption_mask` (detecting localized high-contrast text/stroke discrepancies such as burnt-in subtitles), `flat_mask`, `edge_mask`, and spatial `96x96` px block CV folds (5 folds).
2. **P1 Detect:** Run every plugin's `detect()` across the owner's pairs. Save `evidence.json` and diagnostic visualisations (channel residuals, edge-halo profiles, low-frequency residual map, flat-area noise map).
3. **P2 Plan:** Build candidate stack in canonical order (`colour` -> `sharpen` / `unsharp_mask` -> `haze_flare` -> `gradient` -> `vignette` -> `grain`, plus optional plugins only if triggered). Drop absent plugins. Test adjacent layer swaps (e.g. `sharpen` <-> `unsharp_mask`, `gradient` <-> `vignette`) on held-out block CV loss.
4. **P3 Layer-by-Layer Tuning:** Tune each planned plugin sequentially on top of frozen prior layers using its dedicated metric and pixel mask. Require positive held-out block CV improvement beyond margin (`min_rel_gain` / `min_abs_gain`) plus domain sanity gates (e.g. mandatory real-bloom tests for `haze_flare`, non-blockiness proof for `grain`). Reject and remove layers that do not improve held-out error, recording the exact reason.
5. **P4 Joint Refinement:** Coordinate descent over accepted layers (allowing `colour` and `sharpen`/`unsharp_mask` to adjust once downstream `haze_flare` or `gradient`/`vignette` are present). Terminate strictly when held-out joint loss stops improving.
6. **P5 & P6 Export and Honest Report:** Emit `look.json`, `look.cube`, GLSL ES 1.00 snippets with tap counts, `REPORT.md` with per-pair and per-layer median/p90 CIEDE2000, per-channel MAE, edge-profile RMSE, SSIM, comparison strips, and an evidence-backed Honest Limits section.

---

## 4. Keyflaw 1.4.8 Pack & Shader Strategy

- **Target:** Keyflaw 1.4.8 (`minAppVersion`: `"1.2.4"`, single-pass `shader.glsl`, GLSL ES 1.00, no `#version`, no `passes`, no `expandBounds`, no `COLOR` params, no dynamic array indexing).
- **Suite:** `id: "com.motionsalt.cc"`, `name: "Motion Salt CC"`, `category: "MotionSalt CC"` on suite and every effect, effects `["MS_floby_cc", "MS_gojo_cc", "MS_xenoz_cc"]`.
- **Controls:** Typed `BOOL` switches only:
  - `colourCorrection` (`"Colour Correction"`, default `1.0`)
  - `quality` (`"Quality"`, default `1.0` — enables measured sharpen/unsharp/gradient/vignette/grain layers for that owner)
  - `hazeFlare` (`"Haze Flare"`, default `1.0` — included **only** on effects where `haze_flare` was proven present and accepted)
- **Vertical Coordinate Rule:** `float yTop = 1.0 - vTex.y;` used for all vertical positions (gradients, envelopes, vignettes).
- **Tap Budget & Parity:** Keep texture taps `<= 60` per shader via shared neighbourhood/ring sampling for USM + Sharpen + Bloom. Verify zero errors in `SKILL.md` validator, clean `glslangValidator` compile (with `#version 100` prepended on temp file), and NumPy port parity vs Python plugin stack (`colour <= 1.0/255`, spatial layers `<= 2.0/255`).

---

## 5. Phase Checklist & Acceptance Criteria

- **Phase 1 (`phase_1_docs_and_plan`):** Commit `docs/PLUGIN_SYSTEM_BRIEF.md` (no secrets), `docs/PLUGIN_PARAMETER_RESEARCH.md`, `docs/PLAN.md`, and structured `BUILD_STATE.json`.
- **Phase 2 (`phase_2_core`):** Implement `lookfit/core/` + `tests/test_core.py`; verify alignment recovers known synthetic shifts/scales (< 0.1 px error), masks isolate bars/captions/edges/flats, CIEDE2000 matches reference test vectors.
- **Phase 3 (`phase_3_plugins`):** Implement all plugins in `lookfit/plugins/` + synthetic parameter-recovery unit tests (`render` with known params -> `fit` recovers parameters and reduces held-out loss; `haze_flare` passes black-frame, bright-shape, and mismatched-scene tests).
- **Phase 4 (`phase_4_planner_tuner_export`):** Implement `planner.py`, `tuner.py`, `export/`, `run.py` + integration tests.
- **Phase 5 (`phase_5_workflow`):** Commit `.github/workflows/tune.yml` (`workflow_dispatch` with `owner` input + matrix for `all`, artifact upload, small-results `[skip ci]` commit back).
- **Phase 6 (`phase_6_initial_runs`):** Run clean single-owner test (`floby`), inspect residuals & edge profiles, then run all owners (`floby`, `gojo`, `xenoz`) locally and via GitHub Actions.
- **Phase 7 (`phase_7_iterative_refinement`):** Inspect weakest layers per owner, refine plugin models/optimisers, re-run Actions until held-out error stops falling; log every iteration in `BUILD_STATE.json`.
- **Phase 8 (`phase_8_export_and_reports`):** Finalize `owners/<owner>/results/` (`look.json`, `look.cube`, GLSL snippets, `REPORT.md`, compressed diagnostic strips).
- **Phase 9 (`phase_9_keyflaw_pack_and_release`):** Build `pack/` and `releases/MotionSalt_CC.kfpack`, pass SKILL validator + `glslangValidator` + NumPy shader parity tests, publish GitHub Release (no anime frames in release assets).
- **Phase 10 (`phase_10_final_verification`):** Verify input SHA-256 checksums untouched, zero secrets in repo/history, Actions green, release live, `BUILD_STATE.json` complete.
