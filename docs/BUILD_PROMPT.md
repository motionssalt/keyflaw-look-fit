# LOOK-FIT: Recover an edit's colour grade and "quality" look from frame pairs

An analysis job for MOTIONSALT. Read this whole file first. It is self-contained: assume nothing from any earlier conversation.

## STEP 0: CREDENTIALS (read first)
```
GITHUB_PAT = <REDACTED_IN_REPO>
CLOUDFLARE_API_TOKEN  = <REDACTED_IN_REPO>
CLOUDFLARE_ACCOUNT_ID = <REDACTED_IN_REPO>
```
- Use `GITHUB_PAT` to create the repo and push to it. Nothing in this job deploys, so the Cloudflare values are not needed: leave them as placeholders and do not stall on them.
- Never commit credentials, and never write their values into `BUILD_STATE.json` (names only).
- If `GITHUB_PAT` is still a placeholder, do the entire analysis anyway, keep every output in your working directory, and ask Victor for the PAT in one short message at the very end.

---

## 1. Role and autonomy
You have full autonomy. This file describes the outcome and the constraints, not step-by-step instructions. You choose the implementation, the libraries and the order of work inside each queue item. Do not stop to ask Victor anything (clarifications, confirmations, choices) unless the work genuinely cannot continue. When something is ambiguous, pick the most sensible default, proceed, and record the assumption in `BUILD_STATE.json` under `decisions`.

## 2. Project background
Victor is a solo developer and motion designer working under the brand **MOTIONSALT**. He is an AMV (anime music video) editor who works entirely from an Android phone.

He has an edited anime clip with a look he likes. He wants to reproduce that look as a reusable effect inside **Keyflaw**, a video editing app that loads custom shader effects as `.kfpack` packs (a ZIP of `suite.json` + `effects/<id>/effect.json` + `shader.glsl`). People using the effect should get the same colour correction and the same "quality" processing.

**This job is the measuring step.** You analyse frame pairs and produce a precise, machine-checkable description of the look (a "look spec"). A different AI will later turn that spec into the Keyflaw effect. Building the Keyflaw pack is explicitly NOT part of this job.

Victor's own description of the look (his words, not verified):
1. Colour correction.
2. Unsharp mask.
3. Gradient remap: "the lower part of the image is a bit darker".
4. Haze flare.

He first suggested fitting per-channel levels until the result matches. That is a good first model (see Q3), but levels alone are probably not enough.

## 3. Relevant facts and evidence

### The four images (attach order = this order; verify by looking, not by filename)
Save them losslessly (no re-encoding) in the repo as:

| # | Save as | What it is |
|---|---------|-----------|
| 1 | `inputs/pairA_edited.png` | **Pair A, edited frame**, 1278x720. Close-up of Luffy (straw hat, scowling). Black letterbox bars top and bottom. A caption "When it's time to do a special edit..." sits across the middle. |
| 2 | `inputs/pairA_original_matched.png` | **Pair A, original colours, matched geometry**, 1278x720. Same frame with the original's ungraded colours, scaled and positioned to match image 1, with matching bars drawn on. No caption. |
| 3 | `inputs/pairB_edited.png` | **Pair B, edited frame**, 720x409. Group shot: Nami (left), Luffy (centre), Sanji (right), Chopper (bottom centre), a dark-green figure in the right foreground. A burned-in subtitle "All we can do is make a fuss, so just let us!" near the bottom centre. No bars. |
| 4 | `inputs/pairB_original_matched.png` | **Pair B, original colours, matched geometry**, 720x409. Same frame, ungraded, matched to image 3. No subtitle. |

Convert all to RGB and confirm any alpha channel is fully opaque.

### How the "matched originals" were made (important for trusting the data)
The true source frames could not be found, so each "original" is an AI-reconstructed clean frame, then geometrically aligned to its edit by a script. They are NOT real source frames. Consequences:
- **Pair A:** scaled to the edit's width (1278), placed at the top, bars drawn on the same rows as the edit's bars, with soft edges estimated from the edit. Measured alignment: residual shift about 0.1 px; edge-map correlation with the edit 0.97 (0.974 with the caption masked). The only line-art difference left is the caption. Bars: rows 0-34 (top) and 686-719 (bottom) are black; rows 35-36 and 684-685 are soft transitions. Rows 0 and 719 of the edit carry faint stray codec values (about 23 and 19 mean) that are NOT part of the look.
- **Pair B:** fitted with a similarity + small affine transform (scale about 0.524, about 0.5% anisotropy). Edge-map correlation is only about 0.78: the edit is softer and recompressed, and the reconstruction redrew some details (notably Luffy's face and hat). Treat alignment as good to roughly 1 px with local redraw mismatch. Rows/columns the reconstruction did not cover were filled by edge replication: about 1 row at the top, 4 at the bottom, 3 on the right. **Exclude a 6 px border of pair B from every fit.**
- **Colour fidelity of the reconstruction (noise floor):** for pair A, a real ungraded frame of the same shot (a nearby moment, not the exact instant) was compared with the reconstruction over flat colour regions. Average difference was 2.9 out of 255, worst channel 7 (blue channel of skin). The reconstruction tends to be a few levels lower in the lights (about 3-7) and 2-3 levels higher in the darks. **So any fitted colour correction smaller than about 3 levels is within the noise floor and is unreliable unless it is consistent across both pairs.**

### What the edits are
They are screenshots of exports from a mobile editor, so they are recompressed (softness, blockiness). Pair A is sharper (720p); pair B is soft (409p). Victor believes both edits carry the same look but has not confirmed it. Pair A's edit appears to show a hazy bright glow near the top right (verify yourself).

### Goal and honesty
Perfect pixel parity is impossible (recompression, resampling, AI redraw, the roughly 3-level reconstruction drift). The target is the lowest residual achievable, reported honestly with error maps. Do not overfit: validate across pairs.

## 4. Environment and constraints
- Victor has only an Android phone (Termux). Never ask him to run anything on his device. You work in your own environment, push to GitHub; he reads results from there.
- Free tools only. Python with numpy / OpenCV / scikit-image / scipy is expected; install what you need. No GPU, no paid APIs.
- **The spec must be implementable later in a Keyflaw shader.** Assume (and state in the spec that this is an assumption the later builder must confirm): a single-pass GLSL fragment shader; only the input frame plus uniform controls; no extra textures or LUT images; no multi-pass; the unsharp blur done with at most about 25 texture taps; everything in closed form. So the colour correction must be expressible as levels + matrix + (optionally) a small smooth curve held as constant arrays, not as a 3D lookup texture.
- **Resolution independence:** positions are normalised (0..1 of width / height); sizes are fractions of frame height; also give pixel values at each pair's resolution.
- Do not edit the input images. Work on copies. Never regenerate or retouch an image.
- Non-goals: do not build the Keyflaw pack or any shader, do not do any UI or polish work, do not inspect any repository other than your own.

## 5. Secrets handling
Credentials live only in your environment or GitHub / Cloudflare secrets. They never appear in commits, logs, reports or `BUILD_STATE.json`.

## 6. Repo name
Create a **private** repo (the inputs are copyrighted anime frames): `motionssalt/keyflaw-look-fit`. If it already exists, continue in it.

## 7. State and resume protocol
Create `BUILD_STATE.json` in the **first commit** and update it after every meaningful step. Also save this prompt in the repo as `docs/BUILD_PROMPT.md` so a fresh AI can reread the full brief.

**On start: read `BUILD_STATE.json` first (if it exists), then continue from `current_phase` and the first queue item not marked `done`. Never redo finished work.**

## 8. Commit and push discipline
- Commit and push **very frequently**: after every file or small unit of work, never only at the end of a phase.
- First commit: repo scaffold + `BUILD_STATE.json` + `docs/BUILD_PROMPT.md` + the four input images. Push immediately.
- Meaningful commit messages. Never leave work uncommitted while starting something new.
- Every push must leave the repo understandable from `BUILD_STATE.json` alone.

## 9. Task queue
1. **Q1. Setup, inputs, masks**
2. **Q2. Alignment audit**
3. **Q3. Colour correction fit**
4. **Q4. Gradient / lower-area darkening**
5. **Q5. Unsharp mask**
6. **Q6. Haze flare**
7. **Q7. Order of operations and the full composite**
8. **Q8. Deliverables** (`LOOK_SPEC.md`, `look_params.json`, `look_apply.py`, `look.cube`, `REPORT.md`)

## 10. Definition of done and final report
Done means every queue item is `done` (or `blocked` with the reason recorded), `LOOK_SPEC.md` is verified against `look_apply.py`, and everything is pushed.
