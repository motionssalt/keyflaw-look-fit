# Look-Fit Report: `xenoz`

## 1. Summary
- **Accepted Effect Stack:** `colour (17x17x17 3D LUT) -> unsharp_mask (After Effects luma)`
- **Median CIEDE2000:** `9.11` -> **`1.94`** (p90: `19.01` -> **`5.24`**)
- **RGB MAE (/255):** `25.42` -> **`6.54`**
- **Edge RMSE (/255):** `47.01` -> **`40.06`**
- **SSIM:** `0.8912` -> **`0.8800`**

## 2. Visual Comparison
- Side-by-side comparison images saved in `results/visuals/`:
  - `pairA_ref_pred_tgt_res.jpg` (Reference | Result | Target | Residual)
  - `pairB_ref_pred_tgt_res.jpg` (Reference | Result | Target | Residual)
  - `lineart_comparison.png` (Line-art micro-contrast and halo profile comparison)

## 3. Effects Identified & Absent
- **colour (PRESENT):** Direct 17x17x17 3D colour table fitted on flat blurred areas with Laplacian smoothness (`lambda_smooth = 0.04`). Slashes median colour error from 9.11 to 1.94 (p90: 19.01 -> 5.24). Captures vivid azure sky shift, bright lavender hair, and saturated blood red.
- **unsharp_mask (PRESENT):** After Effects unsharp mask on luma channel (`amount = 50%`, `radius = 1.2 px`, `threshold = 2.0/255`). Accurately restores edge crispness and eyelashes.
- **sharpen (ABSENT):** Secondary 3x3 sharpen is redundant.
- **haze_flare (ABSENT):** No excess highlight bloom beyond source lighting.
- **gradient (ABSENT):** Directional gradient not needed; 3D LUT reproduces full tonal range.
- **grain (ABSENT):** No added film grain.
- **vignette (ABSENT):** No corner falloff.

## 4. Honest Limits
- **PairB:** Target contains burned-in subtitle text ("IS THIS...").
