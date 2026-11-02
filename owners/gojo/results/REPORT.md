# Look-Fit Report: `gojo` (`MS_gojo_cc`)

## 1. Summary
- **Accepted Layer Stack (1):** `colour`
- **Median CIEDE2000:** `9.69` -> **`4.66`** (p90: `21.03` -> **`13.69`**)
- **Active RGB MAE (/255):** `27.12` -> **`13.02`** (R `15.83`, G `12.90`, B `10.32`)
- **Edge-Profile Halo RMSE (/255):** `23.58` -> **`23.44`** (raw edge RMSE: `38.81` -> `32.28`)
- **Active SSIM:** `0.6540` -> **`0.7531`**
- **Keyflaw 1.4.8 Shader:** `1` texture taps, `glslangValidator` (`#version 100`) = `PASS`, `Haze Flare` switch = `absent (omitted)`.

## 2. P0 Alignment & Mask Summary (All Pairs Treated Equally)
| Pair | Ref Res | Target Res | Method | Shift (dx, dy px) | Scale (sx, sy) | Edge Corr (before -> after) | Active / Flat / Edge / Caption % |
|---|---|---|---|---|---|---|---|
| `pairA` | `1364x768` | `1920x1080` | `phase_correlate` | `(+0.19, -0.06)` | `(1.4076, 1.4062)` | `0.926 -> 0.928` | `80.1% / 40.3% / 29.0% / 0.4%` |
| `pairB` | `1364x768` | `1920x1080` | `sift_affine` | `(-2.61, +0.10)` | `(1.4061, 1.4065)` | `0.587 -> 0.871` | `83.0% / 32.1% / 34.8% / 0.1%` |
| `pairC` | `1364x768` | `1920x1080` | `phase_correlate` | `(-0.00, -0.20)` | `(1.4076, 1.4062)` | `0.867 -> 0.868` | `94.7% / 49.8% / 32.4% / 1.5%` |
| `pairD` | `1364x768` | `1920x1080` | `sift_affine+ecc_affine` | `(-23.75, -33.06)` | `(1.7351, 1.6431)` | `0.053 -> 0.481` | `84.0% / 49.1% / 20.2% / 13.2%` |

## 3. P1 Detector Evidence
- [colour] PRESENT: Blurred flat-area colour difference before grade: median CIEDE2000=8.82, p90=20.92, MAE=24.98/255.
- [sharpen] WEAK: 3x3 fine-edge high-pass ratio tgt/ref=0.744, edge-halo RMSE=23.62/255 (kernel model fitted, not known).
- [unsharp_mask] PRESENT: Multi-scale edge band ratio=1.087, perpendicular edge-halo RMSE=23.62/255.
- [haze_flare] PRESENT: Low-frequency smooth residual MAE=6.89/255 (halo-ring MAE=8.95/255); excess positive glow in highlight-halo rings vs background=+1.27/255 -> present.
- [grain] NOT_PROVABLE: not provable: flat-area noise shows 8x8 recompression blockiness (blockiness_ratio=1.38 > 1.22, excess_std=0.06/255); skipping grain.
- [gradient] PRESENT: Low-frequency directional gradient check: peak-to-peak amp=8.97/255, linear plane R^2=0.213 -> present.
- [vignette] ABSENT: Radial corner darkening check: centre-to-outer drop=0.97/255, quadrant consistency=0.50 -> absent.
- [black_lift] ABSENT: Shadow black-point veil check on 1772138 dark pixels: median lift=-1.46/255 -> absent.
- [chromatic_aberration] ABSENT: Outer-frame radial R/B chromatic fringe check: corner shift=0.19 px -> absent.
- [flicker] ABSENT: Multi-pair global exposure flicker check: est_amp=0.010, scalar-gain R^2=0.009, pair_gains=[0.997, 1.015, 1.007, 1.0] -> absent.

## 4. P3 & P4 Layer-by-Layer Progression
| Stage | Median DE00 | p90 DE00 | RGB MAE (/255) | Edge Halo RMSE (/255) | SSIM | Layer Notes |
|---|---|---|---|---|---|---|
| `0. Aligned Ref` | 9.69 | 21.03 | 27.12 | 23.58 | 0.6540 | Unmodified aligned reference |
| `1. +colour` | 4.66 | 13.69 | 13.02 | 23.44 | 0.7531 | 3D colour LUT (17^3 in srgb space, 2nd-diff smoothness lambda=0.3, cluster_weighted=True, flat pre-blur=2.0 px); compressed to GLSL 'curves33_poly_plus_tetra9' (mean diff vs .cube = 5.564/255, p99 = 31.543/255). |

### Absent or Rejected Plugins
- **`grain`**: Dropped at P2 Plan (not_provable): not provable: flat-area noise shows 8x8 recompression blockiness (blockiness_ratio=1.38 > 1.22, excess_std=0.06/255); skipping grain.
- **`vignette`**: Dropped at P2 Plan (absent): Radial corner darkening check: centre-to-outer drop=0.97/255, quadrant consistency=0.50 -> absent.
- **`black_lift`**: Optional plugin not triggered (absent): Shadow black-point veil check on 1772138 dark pixels: median lift=-1.46/255 -> absent.
- **`chromatic_aberration`**: Optional plugin not triggered (absent): Outer-frame radial R/B chromatic fringe check: corner shift=0.19 px -> absent.
- **`flicker`**: Optional plugin not triggered (absent): Multi-pair global exposure flicker check: est_amp=0.010, scalar-gain R^2=0.009, pair_gains=[0.997, 1.015, 1.007, 1.0] -> absent.
- **`sharpen`**: Rejected at P3 fit: 3x3 Sharpen (fitted, not known): kernel=binomial3x3, channel_mode=luma, k=0.0003 (~AE amount 0.0). Edge SSIM 0.6072 -> 0.6071.
- **`unsharp_mask`**: Rejected at P3 fit: USM amount=0.0%, radius=0.500% H (5.40 px @1080p vs hand 22.1 px), sigma_mult=1.0x, threshold=2.0/255 (hard), mode=rgb/srgb. Edge SSIM 0.6072 -> 0.6072.
- **`haze_flare`**: Rejected at P3 fit: haze_flare: absent (Low-frequency smooth residual MAE=8.90/255 (halo-ring MAE=10.65/255); excess positive glow in highlight-halo rings vs background=+0.28/255 -> absent.)
- **`gradient`**: Rejected at P3 fit: Gradient rejected on held-out blocks (13.01 -> 12.77, max_strength=0.108).

## 5. Per-Pair Before vs After Metrics
| Pair | Med DE00 (Before -> After) | p90 DE00 (Before -> After) | R / G / B MAE After (/255) | Mean MAE (Before -> After) | Edge Halo RMSE (Before -> After) | SSIM (Before -> After) |
|---|---|---|---|---|---|---|
| `pairA` | `8.31 -> 5.26` | `18.45 -> 11.29` | `12.12 / 10.17 / 8.36` | `19.98 -> 10.22` | `15.38 -> 15.05` | `0.7714 -> 0.8206` |
| `pairB` | `6.08 -> 2.94` | `19.46 -> 12.26` | `10.25 / 10.72 / 10.82` | `22.28 -> 10.60` | `25.13 -> 24.35` | `0.5675 -> 0.7388` |
| `pairC` | `12.21 -> 6.78` | `22.85 -> 16.17` | `23.81 / 17.24 / 9.67` | `35.22 -> 16.92` | `18.36 -> 20.13` | `0.6674 -> 0.7488` |
| `pairD` | `12.16 -> 3.67` | `23.35 -> 15.05` | `17.12 / 13.45 / 12.46` | `31.01 -> 14.36` | `35.46 -> 34.24` | `0.6096 -> 0.7044` |

## 6. Shader Compression & Parity Verification
- **Colour Shader vs Python Colour Plugin:** `0.0000 / 255` (limit `<= 1.0 / 255`)
- **Colour Shader vs Full 3D `.cube` LUT:** `5.5352 / 255` (limit `<= 1.0 / 255`)
- **Full Single-Pass Shader vs Sequential Python Stack:** `0.0000 / 255` (limit `<= 2.0 / 255`)
- **Texture Fetch Count:** `1` taps (`<= 60` mobile budget).

## 7. Visuals
- Per-pair strips (`Reference | Prediction | Target | Signed Residual x3`): `visuals/*_ref_pred_tgt_res.jpg`
- Perpendicular edge-halo cross-sections: `visuals/edge_profiles_final.png` and `visuals/p1_edge_halo_profiles.png`
- Low-frequency & flat-noise diagnostic maps: `visuals/*_p1_lowfreq_map.jpg`, `visuals/*_p1_noise_map.jpg`

## 8. Honest Limits
- **Dominant remaining error source:** edge/line-art resampling & source-replica geometry differences.
- Edge/resampling & source-replica micro-geometry difference: edge MAE is 20.32/255 vs flat-interior MAE 8.64/255 (mean post-alignment gradient correlation = 0.787). Different source resolution/cropping or redrawn line-art widths cannot be collapsed by a global filter.
- Spatially local / scene-dependent differences across 96x96 blocks (std = 13.26/255): local relighting, motion blur, or per-shot adjustments vary across frame regions.
- High-frequency recompression & quantization texture in flat areas: target flat noise std = 0.17/255 vs prediction 0.22/255 (8x8 blockiness ratio = 1.18).
- GLSL ES 1.00 single-pass shader compression vs full 3D .cube LUT: mean difference = 5.564/255.
- **After Effects Sharpen note:** Any `sharpen` kernel (`cross4`, `box8`, `binomial3x3`) and slider mapping is **fitted, not known**, because Adobe does not publish the exact kernel.
- **Keyflaw runtime verification:** Validated with `SKILL.md` pack checker, `glslangValidator` (`#version 100`), and NumPy shader parity; **not tested inside the live Keyflaw Android app**.
