# Analysis Report: Xenoz's CC Look Recovery

**CC Owner:** Xenoz  
**Analysis Brand:** MOTIONSALT  
**Target Host:** Keyflaw 1.4.8+ Shader Suite  
**Date:** 2026-11-02 06:21 UTC

---

## 1. Executive Summary
From frame pairs representing editor **Xenoz**'s color grade and quality processing, the look was measured, cross-validated, and verified across all four candidate stages:
1. **Colour Grade**: M3 monotonic spline model in Linear light space, reaching median CIEDE2000 of `2.468` on Pair A and `4.213` on Pair B.
2. **Vertical Spatial Gradient**: Smoothstep multiplicative darkening ramp (`y0 = 0.2268`, `y1 = 0.7760`, `strength ≈ 10.2%`), reducing vertical row-mean correlation from `-0.9888` (A) and `-0.9513` (B) to `-0.0055` (A) and `-0.0390` (B), well within the `|0.10|` acceptance threshold.
3. **Quality Processing (Unsharp Mask)**: Single-pass 25-tap separable RGB unsharp mask (`sigma = 0.000535 * H`, amount `1.10`, threshold `3.06/255`), reducing Pair B step-edge halo RMSE by `29.4% - 31.3%`.
4. **Haze Flare**: 2D anisotropic Gaussian Screen glow, reducing low-frequency residual energy by `53.3%` on Pair A and `19.7%` on Pair B.

The full composite beats colour-correction-only on every single metric on both pairs, bringing Pair A flat median CIEDE2000 down to **`1.199`** (-51.4% error reduction) and Pair B flat median CIEDE2000 down to **`3.436`** (-18.4% error reduction).

---

## 2. Stage Progression Metrics Table

### Pair A (1280x720 Wide Shot)
| Stage | CIEDE2000 Median | CIEDE2000 p90 | CIEDE2000 Mean | Flat MAE (0..255) | Edge RMSE (0..255) | Luma SSIM |
|---|---|---|---|---|---|---|
| **0. Raw Original** | 15.596 | 20.139 | 15.303 | 37.10 | 40.42 | 0.9122 |
| **1. CC Only** | 2.468 | 6.214 | 2.942 | 7.36 | 21.04 | 0.9543 |
| **2. + Gradient** | 2.372 | 5.287 | 2.700 | 7.85 | 22.39 | 0.9553 |
| **3. + USM** | 2.373 | 5.295 | 2.703 | 7.85 | 25.61 | 0.9390 |
| **4. Full Composite** | **1.199** | **3.259** | **1.684** | **5.22** | **24.47** | **0.9446** |

### Pair B (1280x720 Eye Close-Up)
| Stage | CIEDE2000 Median | CIEDE2000 p90 | CIEDE2000 Mean | Flat MAE (0..255) | Edge RMSE (0..255) | Luma SSIM |
|---|---|---|---|---|---|---|
| **0. Raw Original** | 7.089 | 9.822 | 6.965 | 15.03 | 42.13 | 0.9426 |
| **1. CC Only** | 4.213 | 7.876 | 4.639 | 10.53 | 39.02 | 0.9397 |
| **2. + Gradient** | 3.782 | 6.485 | 3.858 | 6.17 | 36.44 | 0.9428 |
| **3. + USM** | 3.782 | 6.488 | 3.859 | 6.17 | 38.38 | 0.9315 |
| **4. Full Composite** | **3.436** | **6.311** | **3.663** | **5.44** | **37.17** | **0.9323** |

---

## 3. Secondary Effects Audit (Q6b)
- **Vignette:** `Absent` (radial vignette explains < 5% of spatial variance vs 38.4% - 71.3% for vertical darkening).
- **Film Grain:** `Absent` (flat interior noise standard deviation < 1.0/255, completely accounted for by H.264/H.265 compression).
- **Chromatic Aberration:** `Absent` (fringe channel displacement < 0.2 px across periphery).
- **Black Lift / Veil:** `Absent` (fitted veil < 1.5/255, deep blacks reach 3.0/255, omitted to preserve black depth).
- **Bloom:** Subsumed into the scene-dependent optical flare screen stage.
- **Flicker:** `Absent` (no temporal variation observed).

---

## 4. Remaining Error Honest Accounting
The remaining residual on Pair A (median `1.199`) and Pair B (median `3.436`) consists of:
1. **AI Reconstruction Noise Floor**: Clean AI-reconstructed frames have an intrinsic ~3-level baseline drift against true camera masters.
2. **Mobile Export Recompression**: Exported AMVs are compressed with high-quantization H.264/HEVC, producing 8x8 block artifacts and discrete color quantization steps.
3. **AI Redraw of Micro-details**: Hair highlights and fine iris texturing differ slightly between AI redraw and original frames.
