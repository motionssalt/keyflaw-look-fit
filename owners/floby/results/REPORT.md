# Look-Fit Report: `floby` (`MS_floby_cc`)

## 1. Summary
- **Accepted Layer Stack (3):** `colour -> unsharp_mask -> gradient`
- **Median CIEDE2000:** `6.91` -> **`4.96`** (p90: `17.73` -> **`13.98`**)
- **Active RGB MAE (/255):** `24.08` -> **`15.91`** (R `17.39`, G `15.05`, B `15.29`)
- **Edge-Profile Halo RMSE (/255):** `19.94` -> **`20.18`** (raw edge RMSE: `32.44` -> `27.69`)
- **Active SSIM:** `0.8399` -> **`0.8288`**
- **Keyflaw 1.4.8 Shader:** `21` texture taps, `glslangValidator` (`#version 100`) = `PASS`, `Haze Flare` switch = `absent (omitted)`.

## 2. P0 Alignment & Mask Summary (All Pairs Treated Equally)
| Pair | Ref Res | Target Res | Method | Shift (dx, dy px) | Scale (sx, sy) | Edge Corr (before -> after) | Active / Flat / Edge / Caption % |
|---|---|---|---|---|---|---|---|
| `pairA` | `1278x720` | `1278x720` | `phase_correlate` | `(-0.03, +0.10)` | `(1.0000, 1.0000)` | `0.963 -> 0.963` | `87.3% / 53.2% / 31.1% / 0.6%` |
| `pairB` | `720x409` | `1291x720` | `sift_affine+ecc_trans` | `(+4.99, -0.16)` | `(1.7919, 1.7806)` | `0.427 -> 0.875` | `91.6% / 43.7% / 38.0% / 4.4%` |

## 3. P1 Detector Evidence
- [colour] PRESENT: Blurred flat-area colour difference before grade: median CIEDE2000=6.17, p90=12.18, MAE=21.01/255.
- [sharpen] WEAK: 3x3 fine-edge high-pass ratio tgt/ref=0.939, edge-halo RMSE=29.49/255 (kernel model fitted, not known).
- [unsharp_mask] PRESENT: Multi-scale edge band ratio=1.286, perpendicular edge-halo RMSE=29.49/255.
- [haze_flare] PRESENT: Low-frequency smooth residual MAE=10.72/255 (halo-ring MAE=13.76/255); excess positive glow in highlight-halo rings vs background=+6.14/255 -> present.
- [grain] NOT_PROVABLE: not provable: flat-area noise shows 8x8 recompression blockiness (blockiness_ratio=2.88 > 1.22, excess_std=0.00/255); skipping grain.
- [gradient] PRESENT: Low-frequency directional gradient check: peak-to-peak amp=10.08/255, linear plane R^2=0.197 -> present.
- [vignette] ABSENT: Radial corner darkening check: centre-to-outer drop=0.63/255, quadrant consistency=0.62 -> absent.
- [black_lift] ABSENT: Shadow black-point veil check on 0 dark pixels: median lift=0.00/255 -> absent.
- [chromatic_aberration] ABSENT: Outer-frame radial R/B chromatic fringe check: corner shift=0.04 px -> absent.
- [flicker] ABSENT: Flicker requires >=3 independent frame pairs to distinguish temporal oscillation from static look (have 2).

## 4. P3 & P4 Layer-by-Layer Progression
| Stage | Median DE00 | p90 DE00 | RGB MAE (/255) | Edge Halo RMSE (/255) | SSIM | Layer Notes |
|---|---|---|---|---|---|---|
| `0. Aligned Ref` | 6.91 | 17.73 | 24.08 | 19.94 | 0.8399 | Unmodified aligned reference |
| `1. +colour` | 6.69 | 15.33 | 21.49 | 23.48 | 0.8092 | 3D colour LUT (25^3 in srgb space, 2nd-diff smoothness lambda=0.6, cluster_weighted=False, flat pre-blur=2.0 px); compressed to GLSL 'curves33_poly_plus_tetra9' (mean diff vs .cube = 6.539/255, p99 = 23.692/255). |
| `2. +unsharp_mask` | 6.51 | 15.02 | 20.80 | 20.32 | 0.8175 | Unsharp Mask: amount=61.1%, radius=0.187% height (2.02 px @1080p; AE hand ref 22.1 px / 32%), sigma_mult=2.0x, threshold=5.0/255 (hard gate), mode=luma/srgb. |
| `3. +gradient` | 4.96 | 13.98 | 15.91 | 20.18 | 0.8288 | Smoothstep tint gradient at -88.9 deg (yTop coords), range [0.38, 0.75], RGB strength=[0.076, 0.081, 0.081]. |

### Absent or Rejected Plugins
- **`grain`**: Dropped at P2 Plan (not_provable): not provable: flat-area noise shows 8x8 recompression blockiness (blockiness_ratio=2.88 > 1.22, excess_std=0.00/255); skipping grain.
- **`vignette`**: Dropped at P2 Plan (absent): Radial corner darkening check: centre-to-outer drop=0.63/255, quadrant consistency=0.62 -> absent.
- **`black_lift`**: Optional plugin not triggered (absent): Shadow black-point veil check on 0 dark pixels: median lift=0.00/255 -> absent.
- **`chromatic_aberration`**: Optional plugin not triggered (absent): Outer-frame radial R/B chromatic fringe check: corner shift=0.04 px -> absent.
- **`flicker`**: Optional plugin not triggered (absent): Flicker requires >=3 independent frame pairs to distinguish temporal oscillation from static look (have 2).
- **`sharpen`**: Rejected at P3 fit: 3x3 Sharpen (fitted, not known): kernel=binomial3x3, channel_mode=luma, k=0.0003 (~AE amount 0.0). Edge SSIM 0.6979 -> 0.6979.
- **`haze_flare`**: Rejected at P3 fit: haze_flare: absent/rejected (held-out LF RMSE 24.05 -> 23.74, real_bloom_tests=True).

### Adjacent-Order Swap Checks
- `unsharp_mask <-> gradient`: original joint loss `12.9133` vs swapped `13.0258` -> kept `original`.

### P4 Coordinate-Descent Joint Refinement
- Round 1: joint loss `12.9133` -> `12.1059` (delta `+0.80739`, updates=2).
- Round 2: joint loss `12.1059` -> `11.7366` (delta `+0.36934`, updates=3).

## 5. Per-Pair Before vs After Metrics
| Pair | Med DE00 (Before -> After) | p90 DE00 (Before -> After) | R / G / B MAE After (/255) | Mean MAE (Before -> After) | Edge Halo RMSE (Before -> After) | SSIM (Before -> After) |
|---|---|---|---|---|---|---|
| `pairA` | `7.50 -> 4.84` | `13.25 -> 11.25` | `13.62 / 12.07 / 11.63` | `24.27 -> 12.44` | `14.94 -> 15.58` | `0.8984 -> 0.8811` |
| `pairB` | `6.32 -> 5.08` | `22.20 -> 16.71` | `21.15 / 18.03 / 18.96` | `23.90 -> 19.38` | `24.94 -> 24.79` | `0.7814 -> 0.7764` |

## 6. Shader Compression & Parity Verification
- **Colour Shader vs Python Colour Plugin:** `0.0000 / 255` (limit `<= 1.0 / 255`)
- **Colour Shader vs Full 3D `.cube` LUT:** `5.7583 / 255` (limit `<= 1.0 / 255`)
- **Full Single-Pass Shader vs Sequential Python Stack:** `0.1406 / 255` (limit `<= 2.0 / 255`)
- **Texture Fetch Count:** `21` taps (`<= 60` mobile budget).

## 7. Visuals
- Per-pair strips (`Reference | Prediction | Target | Signed Residual x3`): `visuals/*_ref_pred_tgt_res.jpg`
- Perpendicular edge-halo cross-sections: `visuals/edge_profiles_final.png` and `visuals/p1_edge_halo_profiles.png`
- Low-frequency & flat-noise diagnostic maps: `visuals/*_p1_lowfreq_map.jpg`, `visuals/*_p1_noise_map.jpg`

## 8. Honest Limits
- **Dominant remaining error source:** edge/line-art resampling & source-replica geometry differences.
- Edge/resampling & source-replica micro-geometry difference: edge MAE is 18.12/255 vs flat-interior MAE 11.49/255 (mean post-alignment gradient correlation = 0.919). Different source resolution/cropping or redrawn line-art widths cannot be collapsed by a global filter.
- Spatially local / scene-dependent differences across 96x96 blocks (std = 19.26/255): local relighting, motion blur, or per-shot adjustments vary across frame regions.
- High-frequency recompression & quantization texture in flat areas: target flat noise std = 0.22/255 vs prediction 0.36/255 (8x8 blockiness ratio = 0.84).
- GLSL ES 1.00 single-pass shader compression vs full 3D .cube LUT: mean difference = 6.539/255.
- **After Effects Sharpen note:** Any `sharpen` kernel (`cross4`, `box8`, `binomial3x3`) and slider mapping is **fitted, not known**, because Adobe does not publish the exact kernel.
- **Keyflaw runtime verification:** Validated with `SKILL.md` pack checker, `glslangValidator` (`#version 100`), and NumPy shader parity; **not tested inside the live Keyflaw Android app**.
