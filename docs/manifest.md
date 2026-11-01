# Input & Mask Manifest (`Q1`)

## 1. Input Images (`inputs/`)

All four attached PNGs were verified visually rather than trusting attachment order, confirmed to be opaque 8-bit RGB (`mode=RGB`, no alpha channel), and copied byte-for-byte losslessly without re-encoding.

| Canonical Repo Path | Dimensions (`W x H`) | Colour Mode | SHA-256 (prefix) | Attachment Filename & Visual Verification |
|---|---:|---|---|---|
| `inputs/pairA_edited.png` | `1278 x 720` | 8-bit RGB | `067714ec4bea` | Attachment #2 (`Screenshot_20261101-160638_NewPipe_067714ec.png`). Luffy close-up, edited look, top/bottom black letterbox bars (rows `0..34` and `686..719`, soft transitions `35..36` and `684..685`, stray codec values on rows `0` and `719`), centre caption `"When It's time to do a special edit..."`, top-right warm/hazy glow. |
| `inputs/pairA_original_matched.png` | `1278 x 720` | 8-bit RGB | `2f14811d8a97` | Attachment #3 (`original_matched_to_edit_1278x720_2f14811d.png`). Ungraded AI-reconstructed frame pre-aligned to `pairA_edited.png`, matching top/bottom black bars, no caption. |
| `inputs/pairB_edited.png` | `1291 x 720` | 8-bit RGB | `bd4d3ea2133f` | Attachment #4 (`Screenshot_20261101-162355_NewPipe_bd4d3ea2.png`). Group shot (Nami, Luffy, Sanji, Chopper, foreground green cloak). Note: unlike older prose describing a `720x409` subtitled capture, the actual attached edited frame is a `1291x720` NewPipe screenshot from the same letterboxed 720p AMV export as Pair A (top/bottom bars at rows `0..34` and `686..719`, left/right NewPipe pillarbox strips at cols `0..6` and `1287..1290`, and **no** burned-in subtitle). |
| `inputs/pairB_original_matched.png` | `720 x 409` | 8-bit RGB | `1c647de78a06` | Attachment #1 (`pairB_original_matched_720x409_1c647de7.png`). Ungraded AI-reconstructed clean frame spanning the full un-letterboxed 16:9 composition (`~0.558x` scale relative to `pairB_edited.png`), no bars, no subtitle, edge-replicated borders (~1 px top, ~4 px bottom, ~3 px right). Note: AI reconstruction hallucinated yellow foliage (`RGB ~ [224, 201, 100]`) for the green bush (`RGB ~ [157, 201, 115]`) and smooth cloth folds instead of the flat cel highlight on the right cloak. |

---

## 2. Masks (`masks/`)

Convention: single-channel 8-bit PNG where **`255` = active / inside mask**, **`0` = inactive / outside mask**.

### Pair A (`1278 x 720`, total `920,160` px)
| Mask File | Active Pixels | % of Frame | Definition |
|---|---:|---:|---|
| `masks/pairA_bars.png` | `98,406` | `10.69%` | Top rows `0..38` and bottom rows `682..719` (covers black bars, stray codec rows `0` & `719`, soft bar transitions `35..36` & `684..685`, and 2 px bar-edge ringing buffer). |
| `masks/pairA_caption.png` | `28,210` | `3.07%` | Detected strokes + soft drop-shadow/glow of `"When It's time to do a special edit..."` (`y ~ 336..380, x ~ 345..935`), closed and dilated by ~10 px (`>= 8 px` margin beyond strokes). |
| `masks/pairA_invalid_border.png` | `2,880` | `0.31%` | 2 px left/right border (`cols 0..1` and `1276..1277`) where resampling edge dropoff occurs. |
| `masks/pairA_line_edges.png` | `249,084` | `27.07%` | Union of high gradient (`max_RGB |grad| > 4.5` after Gaussian `sigma = 1.0`) in original or edit (excluding bars and caption), dilated by `3 px` radius (`7x7` ellipse). |
| `masks/pairA_flat_interior.png` | `470,112` | `51.09%` | Low gradient in **both** original (`< 2.5`) and edit (`< 2.8`) after Gaussian `sigma = 1.0`, excluding `bars`, `caption` (+4 px glow guard), `invalid_border`, and `line_edges`, eroded by `3 px` radius (`7x7` ellipse). |
| `masks/pairA_overlay_preview.png` | — | — | Colour-coded visual inspection overlay on `pairA_edited.png` (verified visually). |

### Pair B — Primary Edit Grid (`1291 x 720`, total `929,520` px)
*(Constructed after aligning `pairB_original_matched.png` onto the `1291x720` grid; refined to sub-pixel precision via ECC in `Q2`.)*

| Mask File | Active Pixels | % of Frame | Definition |
|---|---:|---:|---|
| `masks/pairB_bars.png` | `109,052` | `11.73%` | Top/bottom letterbox rows `0..38` & `682..719` plus NewPipe left/right pillarbox strips `cols 0..8` & `1285..1290`. |
| `masks/pairB_caption.png` | `0` | `0.00%` | Empty (`0`), as `pairB_edited.png` (`1291x720` AMV screenshot) contains no burned-in subtitle. |
| `masks/pairB_invalid_border.png` | `9,645` | `1.04%` | `6 px` border of `pairB_original_matched.png` (`720x409`) projected into `1291x720` (`~11 px` inset from active content borders), excluding `bars`. |
| `masks/pairB_line_edges.png` | `406,199` | `43.70%` | Union of high gradient after Gaussian `sigma = 1.0` in edit or aligned original, dilated by `3 px` radius (`7x7` ellipse). |
| `masks/pairB_flat_interior.png` | `316,015` | `34.00%` | Low gradient in **both** edit and aligned original, excluding `bars`, `caption`, `invalid_border`, and `line_edges`, eroded by `3 px` radius (`7x7` ellipse). |
| `masks/pairB_overlay_preview.png` | — | — | Colour-coded visual inspection overlay on `pairB_edited.png` (verified visually). |

### Pair B — Native Matched-Original Grid (`720 x 409`, total `294,480` px)
Saved as `masks/pairB_409p_{bars,invalid_border,line_edges,flat_interior,overlay_preview}.png` (with exact `6 px` invalid border = `13,404` px and `flat_interior` = `65,472` px) for direct evaluation when running `look_apply.py` on `inputs/pairB_original_matched.png`.
