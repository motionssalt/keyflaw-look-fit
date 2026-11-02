# Repository Reset Notes

## 1. Overview and Rationale
This repository (`motionssalt/keyflaw-look-fit`) previously contained preliminary look-fit models, scripts, LUTs, shader sources, and build artifacts for several Keyflaw colour corrections (CCs) across multiple editors (`floby`, `gojo`, `xenoz`). The earlier fits and effects were produced using preliminary monolithic fits and have been decommissioned.

A fresh plugin-based tuning system will be constructed in subsequent phases. To allow a clean slate, all generated outputs, intermediate analyses, masks, specifications, reports, built packs, and GitHub Releases have been purged.

**Only the ground-truth input frame pairs, the root `SKILL.md` (Keyflaw effect-builder skill), `prompts/`, and `.gitignore` are retained.**

> **Note on Git History:** Consistent with the reset directives, the repository itself was not deleted, no branches were deleted, git history was not rewritten, and no force-pushes were performed. Previous commits and historical revisions remain accessible in git history, while the working tree on `master` has been cleanly reset.

---

## 2. Input Inventory and Checksums
All 16 raw input images (8 matched pairs across 3 CC owners) were verified and preserved byte-for-byte with original filenames and directory hierarchy.

| Owner | Relative Path | Resolution | Size (Bytes) | Shot Description | SHA-256 Checksum |
|---|---|---|---|---|---|
| `floby` | `owners/floby/inputs/pairA_edited.png` | 1278x720 | 580,392 | Luffy close-up under straw hat (Floby AMV edit with subtitle "When It's time to do a special edit...") | `067714ec4bea3e97ffa9c1c17dfaf60bb43a3cb7ff6999e396614010a64aa43d` |
| `floby` | `owners/floby/inputs/pairA_original_matched.png` | 1278x720 | 751,625 | Luffy close-up under straw hat (matched clean original frame) | `2f14811d8a9760f4a94b1ae236d57162dd773bc47e38a3e44c46b2599bf6720f` |
| `floby` | `owners/floby/inputs/pairB_edited.png` | 1291x720 | 878,648 | Anime characters scene with cloaks and foliage (Floby AMV edit) | `bd4d3ea2133f38ce6e3e48a8e7d23031d8ba2675cb98b7778311883a849eda78` |
| `floby` | `owners/floby/inputs/pairB_original_matched.png` | 720x409 | 429,360 | Anime characters scene with cloaks and foliage (matched clean original frame) | `1c647de78a06a653331d3f7dd2ee87b16b0f17ddeb07a66a87cb3f4a72f64744` |
| `gojo` | `owners/gojo/inputs/pairA_edited.png` | 1920x1080 | 1,043,171 | Tanjiro head back, closed eyes (Gojo AMV edit) | `6a3f7c7ddf3b0177fa5233754909235fc4a047820e3a57b18d3f0899950fb497` |
| `gojo` | `owners/gojo/inputs/pairA_original_matched.png` | 1364x768 | 629,075 | Tanjiro head back, closed eyes (matched clean original frame) | `d037d7892d26abd760acc715d1f4b908a4a7f2f06f39a8512a43f739fe72cabb` |
| `gojo` | `owners/gojo/inputs/pairB_edited.png` | 1920x1080 | 1,327,116 | Tanjiro sword swing with sparks in forest (Gojo AMV edit) | `90f96d2ee9f3b8f99982fd4ad872be456807745a008577b6710dc9a583d5a509` |
| `gojo` | `owners/gojo/inputs/pairB_original_matched.png` | 1364x768 | 931,301 | Tanjiro sword swing with sparks in forest (matched clean original frame) | `42697d8a374f5d1f00c4e1a2e223759e003334406f1228f3a71f0ecd83166fee` |
| `gojo` | `owners/gojo/inputs/pairC_edited.png` | 1920x1080 | 1,358,241 | Zenitsu close-up face with dirt marks (Gojo AMV edit) | `6e6c53d15e602fe3922a8f414e8ece0e052fe0058f9045bb5aa75e045c3a73af` |
| `gojo` | `owners/gojo/inputs/pairC_original_matched.png` | 1364x768 | 895,896 | Zenitsu close-up face with dirt marks (matched clean original frame) | `6e1332e3eb47fe0ec9bc0c82259776f9ee6d1fc24ef1c4305ab95b156a0e97a6` |
| `gojo` | `owners/gojo/inputs/pairD_edited.png` | 1920x1080 | 1,271,194 | Daki close-up face with Upper Moon eyes (Gojo AMV edit) | `c24ef40a8ccd4f561bc3672f3aa45c80284b0b1b445211d853a166dfe0840ce7` |
| `gojo` | `owners/gojo/inputs/pairD_original_matched.png` | 1364x768 | 738,332 | Daki close-up face with Upper Moon eyes (matched clean original frame) | `faf1e655b301620ddbd2341b744e1d052b19583865f575e8308b8a2d1c9e5f21` |
| `xenoz` | `owners/xenoz/inputs/pairA_edited.png` | 1280x720 | 2,766,492 | Wide shot of purple-haired character pierced by energy burst under cyan sky (Xenoz AMV edit) | `8a6faeb86b1ea82bab146d0ee6991c065bfb9a7295272ee389bb99e310c7ad52` |
| `xenoz` | `owners/xenoz/inputs/pairA_original_matched.png` | 1376x768 | 3,172,196 | Wide shot of purple-haired character pierced by energy burst (matched clean original frame) | `5da973e4011b0beacca4978d32ae43deee23d5c16cf8fa132770413ae5eae0e7` |
| `xenoz` | `owners/xenoz/inputs/pairB_edited.png` | 1280x720 | 2,766,492 | Extreme close-up of anime eyes with subtitle "IS THIS..." (Xenoz AMV edit) | `318ffa618f3664cd92dac5ac689588af0cbbb72fdba29b3df9f5f5feb6eee6f5` |
| `xenoz` | `owners/xenoz/inputs/pairB_original_matched.png` | 1359x768 | 3,132,966 | Extreme close-up of anime eyes (matched clean original frame) | `a61e1ec91681498b882eec54009accb57e1f6d0add928cef65f735fb80edf19d` |

- **Total input frames:** 16 (8 matched pairs)
- **Total payload size:** 23,285,149 bytes (~22.21 MB)
- **Modifications:** 0 (all images preserved bit-identical)

---

## 3. Retained Files
The following repository files and structures are explicitly retained:
- `owners/*/inputs/*`: All 16 ground-truth image pairs listed above.
- `SKILL.md`: The Keyflaw effect-builder skill specification in repository root.
- `prompts/`: Contains `LOOK_FIT_BRIEF.md` (unmodified).
- `.gitignore`: Standard git ignore configurations.
- `docs/RESET_NOTES.md`: This reset documentation and inventory record.

---

## 4. Deleted Files and Directories
All previous generated outputs, analysis pipelines, intermediate masks, fitted parameters, specifications, and old documentation have been removed:

1. **Analysis and Fitting Pipelines:**
   - `owners/floby/analysis/` (all scripts, numpy arrays, intermediate crops, alignment data, heatmaps)
   - `owners/gojo/analysis/` (all scripts, numpy arrays, intermediate crops, alignment data)
   - `owners/xenoz/analysis/` (all scripts, numpy arrays, intermediate crops, alignment data)
   - `tools/release_pack.py` (legacy pack release script)
2. **Masks and Overlays:**
   - `owners/floby/masks/` (all bar, caption, flat interior, edge masks, and overlay previews)
   - `owners/gojo/masks/` (all bar, caption, flat interior, edge masks, and overlay previews)
   - `owners/xenoz/masks/` (all bar, caption, flat interior, edge masks, and overlay previews)
3. **Specifications and LUTs:**
   - `owners/floby/spec/` (`LOOK_SPEC.md`, `look_params.json`, `look_apply.py`, `look.cube`)
   - `owners/gojo/spec/` (`look.cube`)
   - `owners/xenoz/spec/` (`LOOK_SPEC.md`, `look_params.json`, `look_apply.py`, `look.cube`)
4. **Reports and Residual Visualizations:**
   - `owners/floby/reports/` (`REPORT.md`, `look.cube`, `look_params.json`, etc.)
   - `owners/xenoz/reports/` (`REPORT.md`, `BURN_SAFETY_v1.1.1.md`, `side_by_side_comparison.png`, etc.)
5. **Pack Sources and Releases:**
   - `pack/` (root suite and effect directories: `MS_floby_cc`, `MS_xenoz_cc`, `suite.json`)
   - `owners/floby/pack/`
   - `owners/xenoz/pack/`
   - `releases/` (`MotionSalt_CC.kfpack`, `MotionSalt_CC_v1.1.0.kfpack`, `MotionSalt_CC_v1.1.1.kfpack`, and sha256 files)
6. **Old Build States and Documentation:**
   - Root `BUILD_STATE.json` (replaced with fresh reset state)
   - `owners/BUILD_STATE.json`, `owners/floby/BUILD_STATE.json`, `owners/gojo/BUILD_STATE.json`, `owners/xenoz/BUILD_STATE.json`
   - `owners/floby/README.md`, `owners/xenoz/README.md`
   - `owners/gojo/docs/`, `owners/xenoz/docs/`
   - `docs/BUILD_PROMPT.md`, `docs/TIDY_NOTES.md`, `docs/manifest.md`
   - `roadmap.md`

---

## 5. Quarantined Files
- **Status:** Empty (`0` items in `quarantine/`).
- **Explanation:** Every file in the repository was unambiguously identified as either a ground-truth input (retained in `owners/*/inputs/`), core scaffolding (`SKILL.md`, `prompts/`, `.gitignore`), or decommissioned output/analysis/pack artifact. No ambiguous files required isolation.

---

## 6. GitHub Releases and Tags Purged
All GitHub Releases, release assets, and git tags have been permanently deleted via the GitHub REST API:

| Release ID | Tag Name | Release Title | Assets Deleted |
|---|---|---|---|
| `431170295` | `motionsalt-cc-v1.1.1` | Motion Salt CC v1.1.1 — Xenoz burn-safety | `MotionSalt_CC_v1.1.1.kfpack`, `MotionSalt_CC_v1.1.1.kfpack.sha256` |
| `431170259` | `motionsalt-cc-v1.1.0` | Motion Salt CC v1.1.0 — archived rollback | `MotionSalt_CC_v1.1.0.kfpack`, `MotionSalt_CC_v1.1.0.kfpack.sha256` |
| `431079262` | `floby-cc-v1.0` | Floby's CC v1.0 | `look.cube`, `look_apply.py`, `look_params.json`, `LOOK_SPEC.md`, `REPORT.md` |

- Git tags deleted from remote: `motionsalt-cc-v1.1.1`, `motionsalt-cc-v1.1.0`, `floby-cc-v1.0`.
- GitHub Actions runs and artifacts: verified 0 existing runs and 0 existing artifacts.
- Target verification: 0 releases and 0 tags remaining.

---

## 7. Next Steps for Plugin-Based Look-Fit System
1. Implement standalone plugin modules for:
   - **Unsharp Mask:** Gaussian blur subtracted from original, scaled by `amount`, gated by `threshold` (testing `sigma = radius`).
   - **Sharpen:** Fixed small-neighbourhood high-pass filtering with single strength parameter.
   - **Haze Flare (Bloom):** Multi-scale blur of thresholded bright areas composited via Screen blend.
2. Measure and fit each plugin independently on held-out error over the 16 ground-truth frame pairs.
