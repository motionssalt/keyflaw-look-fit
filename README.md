# Keyflaw Look-Fit Work

This repository holds look-fit measurement data and ground-truth still frames for several Keyflaw colour corrections (CCs). The still frames serve as reference measurement inputs to recover an editor's colour grade and "quality" enhancement pipeline.

## Status: Clean Reset for Plugin-Based Tuning
**All previous fits, monolithic shaders, analysis scripts, masks, and releases have been deliberately wiped.** 

The earlier fits combined stages into monolithic shaders that were difficult to calibrate and tune. All generated deliverables have been removed so that a clean, modular, plugin-based tuning system can be constructed from scratch. What survives in this repository is the raw material: the lossless frame pairs.

---

## Input Frame Pairs Inventory

The repository contains 16 input images (8 matched pairs) organized by creator under `owners/<owner_slug>/inputs/`:

| Owner | Input Pair Files | Resolution | File Size | Shot Description |
|---|---|---|---|---|
| **Floby** | `pairA_edited.png`<br>`pairA_original_matched.png` | 1278x720<br>1278x720 | 580 KB<br>752 KB | Luffy close-up under straw hat with burnt-in subtitle `"When It's time to do a special edit..."` |
| **Floby** | `pairB_edited.png`<br>`pairB_original_matched.png` | 1291x720<br>720x409 | 879 KB<br>429 KB | Anime characters group shot with cloaks and background foliage |
| **Gojo** | `pairA_edited.png`<br>`pairA_original_matched.png` | 1920x1080<br>1364x768 | 1.04 MB<br>629 KB | Tanjiro head tilted back, closed eyes (Demon Slayer) |
| **Gojo** | `pairB_edited.png`<br>`pairB_original_matched.png` | 1920x1080<br>1364x768 | 1.33 MB<br>931 KB | Tanjiro sword swing with sparks in dark forest (Demon Slayer) |
| **Gojo** | `pairC_edited.png`<br>`pairC_original_matched.png` | 1920x1080<br>1364x768 | 1.36 MB<br>896 KB | Zenitsu close-up face with dirt marks (Demon Slayer) |
| **Gojo** | `pairD_edited.png`<br>`pairD_original_matched.png` | 1920x1080<br>1364x768 | 1.27 MB<br>738 KB | Daki close-up face with Upper Moon eyes (Demon Slayer) |
| **Xenoz** | `pairA_edited.png`<br>`pairA_original_matched.png` | 1280x720<br>1376x768 | 2.77 MB<br>3.17 MB | Wide shot of purple-haired character pierced by energy burst under bright cyan-blue sky |
| **Xenoz** | `pairB_edited.png`<br>`pairB_original_matched.png` | 1280x720<br>1359x768 | 2.77 MB<br>3.13 MB | Extreme close-up of anime character's eyes with burnt-in subtitle `"IS THIS..."` |

---

## Repository Structure

```
keyflaw-look-fit/
├── BUILD_STATE.json             # Root state record (reset_complete, owners, checksums, decisions)
├── docs/
│   └── RESET_NOTES.md           # Full audit of wiped files, checksum verification, and release deletions
├── owners/
│   ├── floby/
│   │   └── inputs/              # Raw frame pairs (pairA, pairB)
│   ├── gojo/
│   │   └── inputs/              # Raw frame pairs (pairA, pairB, pairC, pairD)
│   └── xenoz/
│       └── inputs/              # Raw frame pairs (pairA, pairB)
├── prompts/
│   └── LOOK_FIT_BRIEF.md        # Look-fit brief for editor CC recovery
├── SKILL.md                     # Keyflaw effect-builder skill specification
└── .gitignore                   # Git ignore rules
```

---

## Plugin Architecture Guidelines for the Next AI

The new look-fit system will implement three decoupled, standalone plugins tested against real edge profiles and held-out validation error:

### 1. Unsharp Mask (After Effects)
- **Mathematical formulation:** `sharpened = original + (original - blurred) * amount`
- **Radius vs. Gaussian sigma:** Start with `sigma = radius` in pixels (test `0.5 * radius`, `1.0 * radius`, and `2.0 * radius` against target line-art edge profiles).
- **Threshold gating:** Threshold is a gate (`abs(diff) <= threshold` receives no adjustment) to prevent boosting compression artifacts, ringing, or noise in smooth cel fills. Test both hard gating and soft coring (`sign(d) * max(abs(d) - t, 0)`).
- **Search ranges:**
  - `amount`: 0% to 500%
  - `radius`: 0.3 px to 3% of frame height
  - `threshold`: 0 to 40 (/255)

### 2. Sharpen (After Effects)
- Fixed small-neighbourhood high-pass filtering: `out = x + k(amount) * (x - Blur_small(x))`.
- Test candidate kernels: 4-neighbour average, 8-neighbour average, and 3x3 binomial `[1 2 1] / 4` outer product.
- Expose independent strength control (`amount` 0 to 100).

### 3. Haze Flare (Bloom / Glow)
- **Model:** Real bloom generated from bright source areas (`bright = max(luma_or_channel - threshold, 0)` with a soft knee).
- Multi-scale blur across 3 to 5 scales with sigmas as fractions of frame height (e.g. 0.5%, 1%, 2%, 4%, 8%).
- Per-channel width multipliers (defaults `R:G:B ≈ 1.0 : 1.2 : 1.4` following optical dispersion), tint color, and **Screen** composite mode.
- Non-destructive test: on a pure black frame, flare must evaluate to zero; bloom must emanate strictly from scene highlights.

---

## Notice
Anime frame captures in `inputs/` are copyrighted by their respective animation studios and are stored strictly as measurement reference data for colorimetry analysis. If any copyright takedown request is received, the raw input frames may be removed while retaining fitted parameters and plugins.
