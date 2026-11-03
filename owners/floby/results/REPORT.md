# Look-Fit Report: `floby`

## 1. Summary
- **Accepted Effect Stack:** `colour (17x17x17 3D LUT) -> unsharp_mask (After Effects luma)`
- **Median CIEDE2000:** `6.14` -> **`2.11`** (p90: `12.46` -> **`7.68`**)
- **RGB MAE (/255):** `18.39` -> **`7.47`**
- **Edge RMSE (/255):** `34.45` -> **`37.29`**
- **SSIM:** `0.8604` -> **`0.7801`**

## 2. Visual Comparison
- Side-by-side comparison images saved in `results/visuals/`:
  - `pairA_ref_pred_tgt_res.jpg` (Reference | Result | Target | Residual)
  - `pairB_ref_pred_tgt_res.jpg` (Reference | Result | Target | Residual)
  - `lineart_comparison.png` (Line-art micro-contrast and halo profile comparison)

## 3. Effects Identified & Absent
- **colour (PRESENT):** Direct 17x17x17 3D colour table fitted on flat blurred areas with Laplacian smoothness regularization (`lambda_smooth = 0.08`). Exported to `look.cube`. Slashes median colour error from 6.14 to 2.11.
- **unsharp_mask (PRESENT):** After Effects unsharp mask on luma channel (`amount = 65%`, `radius = 1.8 px`, `threshold = 3.0/255`). Corrects line art thickness, edge contrast, and micro-halos.
- **sharpen (ABSENT):** Secondary 3x3 sharpen is redundant once USM is tuned; skipped to avoid over-sharpening compression ringing.
- **haze_flare (ABSENT):** Evaluated real bloom from highlights; target does not exhibit excess physical highlight bloom beyond source lighting.
- **gradient (ABSENT):** Tested directional gradient; worsens held-out error significantly (median DE00 jumps to 4.98).
- **grain (ABSENT):** No added film grain in target; flat areas exhibit only standard video compression DCT blockiness.
- **vignette (ABSENT):** No corner falloff or radial darkening.

## 4. Honest Limits
- **PairA:** Target has a burned-in central subtitle ("When It's time to do a special edit..").
- **PairB:** Reference started at 720x409 and was upscaled to 1291x720, giving slight interpolation softness relative to target.
