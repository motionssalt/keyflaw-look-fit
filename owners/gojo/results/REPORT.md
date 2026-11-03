# Look-Fit Report: `gojo`

## 1. Summary
- **Accepted Effect Stack:** `colour (17x17x17 3D LUT)`
- **Median CIEDE2000:** `9.50` -> **`1.88`** (p90: `21.25` -> **`5.11`**)
- **RGB MAE (/255):** `23.28` -> **`5.35`**
- **Edge RMSE (/255):** `48.33` -> **`46.92`**
- **SSIM:** `0.6501` -> **`0.7242`**

## 2. Visual Comparison
- Side-by-side comparison images saved in `results/visuals/`:
  - `pairA_ref_pred_tgt_res.jpg`
  - `pairB_ref_pred_tgt_res.jpg`
  - `pairC_ref_pred_tgt_res.jpg`
  - `pairD_ref_pred_tgt_res.jpg`
  - `lineart_comparison.png`

## 3. Effects Identified & Absent
- **colour (PRESENT):** Direct 17x17x17 3D colour table fitted on flat blurred areas with Laplacian smoothness (`lambda_smooth = 0.10`). Reconstructs the vivid electric-cyan haori shift, crushed deep blacks, and heightened skin contrast. Brings median colour error down from 9.50 to 1.88 (p90: 21.25 -> 5.11).
- **unsharp_mask (ABSENT):** Visual inspection of zoomed line-art crops confirms target outlines are smooth without artificial unsharp halos. Applying USM created noticeable white halo fringes on dark lines that do not exist in the target.
- **sharpen (ABSENT):** No 3x3 high-pass sharpening.
- **haze_flare (ABSENT):** Sparks and ground fire in pairB are scene elements, not post-process bloom.
- **gradient (ABSENT):** No directional gradient.
- **grain (ABSENT):** No film grain added.
- **vignette (ABSENT):** No radial darkening.

## 4. Honest Limits
- **Scale difference:** Reference frames are 1364x768 while targets are 1920x1080, introducing slight interpolation softness at 1080p.
- **PairD:** Dynamic battle sequence with slight motion crop differences.
