# Look-Fit Report: `xenoz` (`MS_xenoz_cc`)

## 1. Summary
- **Accepted Layer Stack (2):** `colour -> gradient`
- **Median CIEDE2000:** `11.44` -> **`2.93`** (p90: `15.86` -> **`6.79`**)
- **Active RGB MAE (/255):** `26.55` -> **`8.50`** (R `7.90`, G `7.69`, B `9.92`)
- **Edge-Profile Halo RMSE (/255):** `14.42` -> **`14.56`** (raw edge RMSE: `30.01` -> `20.98`)
- **Active SSIM:** `0.9007` -> **`0.9302`**
- **Keyflaw 1.4.8 Shader:** `1` texture taps, `glslangValidator` (`#version 100`) = `PASS`, `Haze Flare` switch = `absent (omitted)`.

## 2. P0 Alignment & Mask Summary (All Pairs Treated Equally)
| Pair | Ref Res | Target Res | Method | Shift (dx, dy px) | Scale (sx, sy) | Edge Corr (before -> after) | Active / Flat / Edge / Caption % |
|---|---|---|---|---|---|---|---|
| `pairA` | `1376x768` | `1280x720` | `sift_affine` | `(-0.00, -0.51)` | `(0.9295, 0.9288)` | `0.861 -> 0.971` | `94.2% / 54.9% / 32.3% / 0.0%` |
| `pairB` | `1359x768` | `1280x720` | `sift_affine` | `(-9.18, +3.47)` | `(0.9474, 0.9472)` | `0.236 -> 0.901` | `92.0% / 68.9% / 19.4% / 4.2%` |

## 3. P1 Detector Evidence
- [colour] PRESENT: Blurred flat-area colour difference before grade: median CIEDE2000=11.57, p90=14.95, MAE=26.18/255.
- [sharpen] PRESENT: 3x3 fine-edge high-pass ratio tgt/ref=1.282, edge-halo RMSE=15.09/255 (kernel model fitted, not known).
- [unsharp_mask] PRESENT: Multi-scale edge band ratio=0.988, perpendicular edge-halo RMSE=15.09/255.
- [haze_flare] PRESENT: Low-frequency smooth residual MAE=6.62/255 (halo-ring MAE=6.62/255); excess positive glow in highlight-halo rings vs background=+2.32/255 -> present.
- [grain] NOT_PROVABLE: not provable: flat-area noise shows 8x8 recompression blockiness (blockiness_ratio=5.51 > 1.22, excess_std=0.04/255); skipping grain.
- [gradient] PRESENT: Low-frequency directional gradient check: peak-to-peak amp=12.29/255, linear plane R^2=0.511 -> present.
- [vignette] ABSENT: Radial corner darkening check: centre-to-outer drop=-0.31/255, quadrant consistency=0.75 -> absent.
- [black_lift] ABSENT: Shadow black-point veil check on 0 dark pixels: median lift=0.00/255 -> absent.
- [chromatic_aberration] PRESENT: Outer-frame radial R/B chromatic fringe check: corner shift=0.74 px -> present.
- [flicker] ABSENT: Flicker requires >=3 independent frame pairs to distinguish temporal oscillation from static look (have 2).

## 4. P3 & P4 Layer-by-Layer Progression
| Stage | Median DE00 | p90 DE00 | RGB MAE (/255) | Edge Halo RMSE (/255) | SSIM | Layer Notes |
|---|---|---|---|---|---|---|
| `0. Aligned Ref` | 11.44 | 15.86 | 26.55 | 14.42 | 0.9007 | Unmodified aligned reference |
| `1. +colour` | 3.16 | 7.38 | 10.41 | 14.55 | 0.9294 | 3D colour LUT (25^3 in srgb space, 2nd-diff smoothness lambda=0.6, cluster_weighted=False, flat pre-blur=2.0 px); compressed to GLSL 'curves33_poly_plus_tetra9' (mean diff vs .cube = 3.109/255, p99 = 13.993/255). |
| `2. +gradient` | 2.93 | 6.79 | 8.50 | 14.56 | 0.9302 | Smoothstep multiply gradient at -79.5 deg (yTop coords), range [0.36, 0.79], RGB strength=[0.043, 0.049, 0.045]. |

### Absent or Rejected Plugins
- **`grain`**: Dropped at P2 Plan (not_provable): not provable: flat-area noise shows 8x8 recompression blockiness (blockiness_ratio=5.51 > 1.22, excess_std=0.04/255); skipping grain.
- **`vignette`**: Dropped at P2 Plan (absent): Radial corner darkening check: centre-to-outer drop=-0.31/255, quadrant consistency=0.75 -> absent.
- **`black_lift`**: Optional plugin not triggered (absent): Shadow black-point veil check on 0 dark pixels: median lift=0.00/255 -> absent.
- **`flicker`**: Optional plugin not triggered (absent): Flicker requires >=3 independent frame pairs to distinguish temporal oscillation from static look (have 2).
- **`chromatic_aberration`**: Rejected at P3 fit: Chromatic aberration absent/rejected (14.13 -> 14.11, corner_px=0.27).
- **`sharpen`**: Rejected at P3 fit: 3x3 Sharpen (fitted, not known): kernel=binomial3x3, channel_mode=luma, k=0.0003 (~AE amount 0.0). Edge SSIM 0.8097 -> 0.8097.
- **`unsharp_mask`**: Rejected at P3 joint check: plugin held-out 19.287->19.017, but overall perceptual loss did not improve (7.4273 -> 7.4445).
- **`haze_flare`**: Rejected at P3 fit: haze_flare: absent/rejected (held-out LF RMSE 11.36 -> 11.36, real_bloom_tests=False).

### P4 Coordinate-Descent Joint Refinement
- Round 1: joint loss `7.0427` -> `6.7589` (delta `+0.28380`, updates=1).
- Round 2: joint loss `6.7589` -> `6.7589` (delta `+0.00000`, updates=0).

## 5. Per-Pair Before vs After Metrics
| Pair | Med DE00 (Before -> After) | p90 DE00 (Before -> After) | R / G / B MAE After (/255) | Mean MAE (Before -> After) | Edge Halo RMSE (Before -> After) | SSIM (Before -> After) |
|---|---|---|---|---|---|---|
| `pairA` | `15.00 -> 1.99` | `20.26 -> 6.96` | `8.11 / 7.27 / 8.08` | `35.68 -> 7.82` | `10.66 -> 11.20` | `0.8688 -> 0.9212` |
| `pairB` | `7.88 -> 3.88` | `11.45 -> 6.61` | `7.68 / 8.11 / 11.76` | `17.43 -> 9.18` | `18.18 -> 17.92` | `0.9326 -> 0.9392` |

## 6. Shader Compression & Parity Verification
- **Colour Shader vs Python Colour Plugin:** `0.0000 / 255` (limit `<= 1.0 / 255`)
- **Colour Shader vs Full 3D `.cube` LUT:** `3.1716 / 255` (limit `<= 1.0 / 255`)
- **Full Single-Pass Shader vs Sequential Python Stack:** `0.0000 / 255` (limit `<= 2.0 / 255`)
- **Texture Fetch Count:** `1` taps (`<= 60` mobile budget).

## 7. Visuals
- Per-pair strips (`Reference | Prediction | Target | Signed Residual x3`): `visuals/*_ref_pred_tgt_res.jpg`
- Perpendicular edge-halo cross-sections: `visuals/edge_profiles_final.png` and `visuals/p1_edge_halo_profiles.png`
- Low-frequency & flat-noise diagnostic maps: `visuals/*_p1_lowfreq_map.jpg`, `visuals/*_p1_noise_map.jpg`

## 8. Honest Limits
- **Dominant remaining error source:** edge/line-art resampling & source-replica geometry differences.
- Edge/resampling & source-replica micro-geometry difference: edge MAE is 14.40/255 vs flat-interior MAE 6.03/255 (mean post-alignment gradient correlation = 0.936). Different source resolution/cropping or redrawn line-art widths cannot be collapsed by a global filter.
- Spatially local / scene-dependent differences across 96x96 blocks (std = 8.03/255): local relighting, motion blur, or per-shot adjustments vary across frame regions.
- High-frequency recompression & quantization texture in flat areas: target flat noise std = 0.13/255 vs prediction 0.12/255 (8x8 blockiness ratio = 4.58).
- GLSL ES 1.00 single-pass shader compression vs full 3D .cube LUT: mean difference = 3.109/255.
- **After Effects Sharpen note:** Any `sharpen` kernel (`cross4`, `box8`, `binomial3x3`) and slider mapping is **fitted, not known**, because Adobe does not publish the exact kernel.
- **Keyflaw runtime verification:** Validated with `SKILL.md` pack checker, `glslangValidator` (`#version 100`), and NumPy shader parity; **not tested inside the live Keyflaw Android app**.
