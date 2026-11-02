---
name: keyflaw-effect-builder
description: Build custom shader effects for the Keyflaw video editing app as importable .kfpack files (a ZIP of suite.json + effects/ID/effect.json + shader.glsl). Use whenever the user describes a visual effect (distortion, glitch, shake, blur, color, simulation, generator) and wants it as a Keyflaw pack. Covers the exact file format, GLSL rules, parameter conventions (incl. Keyflaw 1.4.9 multi-pass, expandBounds, native motion trails, COLOR params), tested effect patterns, a validator/packer script, and delivery fallbacks.
---

# Keyflaw Effect Builder

You turn an effect description into a working `.kfpack` for the Keyflaw editor.
Everything below was reverse-engineered from 49 real, working effects in seven packs (Distortion & Optics,
Shaky Wakie, AE Optical Flare, Blur MoCurve, CC Plastic, GM Magic Circle 3D, and the 33-effect Amethyst pack).
Keyflaw 1.4.9 (section 0.1, from the official guide) added multi-pass shaders, `expandBounds`, native motion trails and COLOR params; it overrides older rules where they conflict.
There are TWO observed pack dialects (plus the 1.4.9 additions): the original slider-only one and the newer typed one (Amethyst,
`minAppVersion` 1.2.4) with BOOL/CHOICE parameters and groups. Section 3 explains when to use which. Rules marked **OBSERVED** were
seen in those working files. Rules marked **SAFE DEFAULT** are standard GLSL ES 1.00
practice that no sample contradicts. If the user supplies a newer working sample that
contradicts this file, trust the sample.


## 0.1 KEYFLAW 1.4.9+ UPDATE (from the official PLUGIN_MAKER_GUIDE + PROMPT_TEMPLATE_FOR_AI) - read first

Source: the Keyflaw team's own guide for app version **1.4.9** (release notes: Multi-Pass Pipeline, Expand Bounds, Native
Shutter Motion Trails, crash-proof startup). **Where this section contradicts older sections below, THIS section wins for
apps on 1.4.9+.** For older apps, ignore the new fields. Rules marked **OFFICIAL** come from that guide; **UNVERIFIED** means
the guide does not say, so do not invent behaviour: build conservatively and tell the user.

**New `effect.json` fields (all OFFICIAL, all optional):**

| field | meaning |
|---|---|
| `"passes": ["p1.glsl", "p2.glsl", ...]` | Ordered list of fragment-shader files in the effect folder, run in sequence. Replaces `shader.glsl` (omit `passes` for a normal single-pass effect). Official example: downsample -> blur H -> blur V -> composite (16 taps instead of 64). Each file is a complete shader with the section 4 skeleton. |
| `"expandBounds": 0.3` | Padding as a fraction (0.3 = 30%, 0.5 = 50%). The render mesh grows beyond the clip quad so glows, light rays, drop shadows and particles bleed outward instead of being cut in a square. Use for any effect that draws OUTSIDE the layer. |
| `"usesNativeMotionBlur": true` | Tells the engine the effect integrates over the shutter itself. Use for time-driven motion (shake, twitch, oscillate) together with a `motionBlur` BOOL and a `trailLength` slider (pattern in section 7). |
| `"author"`, `"version"` | Optional metadata, same as in suite.json. |

**New parameter type `COLOR` (OFFICIAL):** `{ "key": "color", "label": "Glow Color", "type": "COLOR", "default": "#FF6020" }`.
`default` is a `#RRGGBB` string; `min/max/step` are not needed. The shader receives **`uniform vec3 uColor;`** (not float).
On 1.4.9+ prefer COLOR over the old three-slider `R/G/B` trick. Colours are 0..1 RGB, treat them as unpremultiplied.
BOOL is read as `uToggle > 0.5` as before (official example default `1.0`).

**Categories (OFFICIAL, 11 names):** `Gerak` (motion/shake/zoom), `Warna` (grading/glow/invert), `Distorsi` (warp/glitch/chromatic/ripple),
`Stilisasi` (halftone/CRT/pixelate/edge/vignette), `Blur`, `Simulasi` (rain/snow/grain/light leaks), `Generator`,
`Transisi` (wipes/dissolves), `Keying` (green screen/luma key), `Perspective` (3D tilt/cylinder/sphere), `Custom`.
Section 0.5 (suite `category` equal to every effect `category`, reverse-domain suite id) still applies to pack listing.

**Official-guide traps:** (1) its example effect.json contains `/* ... */` comments, which are NOT valid JSON: never
write comments in JSON. (2) Its shake snippet calls `getTransformedUV()` and `mirrorCoords()` without defining them: write
your own helpers. (3) Its suite example uses `minAppVersion "1.2.4"`; when you use `passes`, `expandBounds` or
`usesNativeMotionBlur`, set `minAppVersion` to `"1.4.9"` so older apps refuse the pack instead of misrendering it.

**Multi-pass: what the guide does NOT say (UNVERIFIED), and the safe defaults:**
- What `uTexture` is in pass 2+. SAFE DEFAULT: assume it is the previous pass's output. Do NOT declare any extra sampler
  (`uOriginal`, `uPrev`...) or any uniform name that is not in section 4. The guide says the last pass "composites the
  blurred bloom over the original clip" but names no way to read the original: if a composite needs the untouched clip,
  tell the user, and ask for a working multi-pass sample before relying on it. A bloom whose last pass only adds the
  blurred result to what it receives is the safe shape.
- Whether parameter uniforms reach every pass. SAFE DEFAULT: declare in each pass only the uniforms it uses (the validator
  accepts any subset per pass, but every parameter must be used in at least one pass).
- Resolution of intermediate buffers (a "downsample" pass may or may not shrink the buffer), so never assume
  `uTexelSize` changed between passes; keep per-pass taps small (8 per blur pass is the official figure).
- Always say in the delivery message that multi-pass behaviour is untested and which of these assumptions the pack makes.

**Expanded bounds, safe habit (UNVERIFIED how `vTex` behaves in the padding):** with `expandBounds`, `vTex` may leave 0..1
inside the padding. Fetch the source with a range check so the padding stays transparent instead of smearing edge pixels:
`float inside = step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);` then fetch `clamp(uv, 0.0, 1.0)`
and multiply the fetched colour AND alpha by `inside`. Build glows/shadows from that, additively, and output premultiplied.

## 0.5 FIELD REPORT: a pack that imported but did NOT show in "My effects" (read first)

A pack built from this skill (suite id `motionsalt_distort`, plain effect ids, category `Distorsi`, no suite
`category`) was added to the app but never appeared in the user's effects list. The working Amethyst pack
(v0.1.0) differs in exactly these ways, so copy ALL of them every time:
1. suite.json `id` is reverse-domain (`com.amethyst.effects`), not a bare word.
2. suite.json has `"category": "<Custom>"` AND every effect.json has the SAME `"category": "<Custom>"`
   (a custom word like `Amethyst`). The seven built-in names (`Distorsi`, `Gerak`...) did not get the pack listed.
3. Effect ids carry a short uppercase prefix + underscore (`A_fisheye`); folder name == id == `name` in the pack.
4. suite.json has `minAppVersion` and the ordered `effects` list.
5. Every param has `"type"` (SCALAR/BOOL/CHOICE) and most have `"group"`.
Second working sample (Phone 3D, `com.keyflaw.phone3d`) used the BUILT-IN category `Generator` on suite and effect alike, so
built-in names are fine too. What every working pack shares: reverse-domain suite id, suite `category` present and equal to
the effects' category, `minAppVersion`, `effects` list. Suite-level `category` is now the prime suspect, not the custom word.
Default now: use rule 1-5. Only fall back to built-in categories if the user shows a working sample that does.
Which of these was the decisive one is not proven (all were changed together); category is the prime suspect.
If a pack still does not show, ask for a working sample again and diff suite.json/effect.json field by field.

## 0. Workflow (follow in order)

1. **Clarify only if essential.** If the description is workable, just build it. If
   ambiguous in a way that changes the look a lot (e.g. "glitch" = block displace vs.
   RGB split vs. scanlines), pick the most common reading, build it, and say which you chose.
2. **Decide** the suite (new or user-named), the effect id(s), the category, the dialect (section 3.2: typed with
   BOOL/CHOICE/groups if the user's app supports it, otherwise legacy sliders), and the 2-12 parameters the user will want.
3. **Write** `suite.json`, then each `effect.json` and `shader.glsl` into a folder tree.
4. **Run the validator/packer** (section 8) if you have a code sandbox. Fix every ERROR.
5. **Deliver** per section 9. Always also show the shader source so the user can read/fix it.
6. **Tell the user honestly** that you cannot test inside Keyflaw, and give 1-2 specific
   things to try if it looks wrong (section 10).

## 1. Pack layout (OBSERVED)

```
<suite_id>.kfpack                (a normal ZIP, renamed)
├── suite.json                   <- at ROOT, not inside a wrapper folder
└── effects/
    └── <effect_id>/
        ├── effect.json
        └── shader.glsl              (single pass)  OR  the files named in effect.json "passes" (1.4.9+)
```

- Multi-pass effect (1.4.9+): no `shader.glsl`; the folder holds `pass1_xxx.glsl`, `pass2_xxx.glsl`... exactly as listed in
  `"passes"`, in order. Pass files must be zipped too (the packer in section 8 does this).
- Several effects can live in one pack (the samples have 5 and 7). One effect is fine too.
- `<effect_id>` folder name, `"id"` in effect.json: identical, lowercase, `snake_case`
  (e.g. `block_glitch`, `s_shake`, `cclens`).
- File names are exactly `suite.json`, `effect.json`, `shader.glsl`. Paths inside the ZIP use `/`.
- Name the output `<suite_id>.kfpack`. If the pack has one effect, `<effect_id>.kfpack` is fine,
  but the suite id inside suite.json still needs to exist.

## 2. suite.json (OBSERVED)

**Basic form (all older packs):**
```json
{
  "id": "shaky_wakie",
  "name": "Shaky Wakie Suite",
  "author": "Keyflaw Studio",
  "version": "1.0.0",
  "description": "Essential camera shake, fluid jelly wobble, sensor jitter, and elastic physics dynamics for Keyflaw."
}
```

**Extended form (Amethyst pack, for the typed dialect):**
```json
{
  "id": "com.amethyst.effects",
  "name": "Amethyst",
  "category": "Amethyst",
  "author": "ryn",
  "version": "1.0.0",
  "minAppVersion": "1.2.4",
  "description": "Amethyst Visual Effects Suite ...",
  "effects": ["A_bokeh_blur", "A_s_shake", "A_fisheye"]
}
```
- `effects` is an ordered list of the effect folder names (it controls their order). Keep it identical to the
  folders actually present; the validator checks this.
- `minAppVersion` ("1.2.4" in the reference pack) is a hint that typed params need a newer app. Include it
  when you use typed params.
- `category` on the suite and on every effect was the same custom word (`"Amethyst"`) in that pack, so a custom
  category does work in at least that app version. It is unknown whether it works everywhere; a pack using the built-in
  `Distorsi` category did NOT show up. DEFAULT: custom category on suite and every effect (see 0.5).
- Suite `id` can be a plain snake_case word, a hyphenated word (`gm-magiccircle3d`) or reverse-domain style.
  Effect ids are letters/digits/underscore (the Amethyst ones start with an uppercase letter, e.g. `A_vhs`).
- All fields are strings (and the `effects` list of strings). Use the user's name/brand as `author`.

## 3. effect.json (OBSERVED, exact shape)

```json
{
  "id": "micro_jitter",
  "name": "Micro Jitter",
  "category": "Gerak",
  "parameters": [
    { "key": "power",    "label": "Jitter Power",  "default": 0.5, "min": 0.0, "max": 1.0,  "step": 0.01 },
    { "key": "jitterPx", "label": "Jitter Pixels", "default": 8.0, "min": 0.0, "max": 30.0, "step": 0.5 }
  ]
}
```

- `category`: DEFAULT is the pack's custom category word (same as suite.json). Built-in names, if you must: `Distorsi`, `Stilisasi`, `Blur`, `Warna`, `Gerak`, `Simulasi`, `Generator` (Indonesian
  spellings; "Distortion" would be wrong). Samples used `Distorsi` for lens/warp/glitch/wobble and `Gerak` for
  shake/bounce/jitter; Amethyst used one custom word for everything (see section 2).
- `id` equals the folder name; `name` is the display name.
- `parameters`: 2-11 for ordinary effects, 22-29 for rich ones, 94-126 for the big generators (magiccircle3d,
  A_mystic_seal_3d). Long lists are accepted. Keep ordinary effects focused (3-12 controls) and group big ones.

### 3.1 Parameter fields

All dialects: `key, label, default, min, max, step` (numbers as numbers, decimals preferred). Rules:
`min < max`, `min <= default <= max`, `step > 0`. `key` is camelCase starting lowercase (`blockSize`).
**Key to uniform name:** `"u"` + key with ONLY its first letter uppercased (`blockSize` -> `uBlockSize`,
`colorAR` -> `uColorAR`). Every parameter is exposed to the shader as `uniform float`, whatever its type.
Slider resolution: `step` ~ range/100 to range/1000 for smooth values, whole numbers for counts, seeds and modes.
Keep each `label` **at most 40 characters** (the Amethyst pack's longest labels are cut at exactly 40).
No key may collide with a built-in (`texture`, `time`, `texelSize`).

### 3.2 Typed dialect (Amethyst, app 1.2.4+): add these fields

| field | meaning |
|---|---|
| `"type": "SCALAR"` | an ordinary numeric slider (401 of 431 params) |
| `"type": "BOOL"` | an on/off switch: `default` 0 or 1, `min` 0, `max` 1, `step` 1 (10 params) |
| `"type": "CHOICE"` | a dropdown: add `"options": ["Sine", "Cosine", "Triangle"]`, `default` = the selected index, `min` 0, `max` = options-1, `step` 1.0 (20 params) |
| `"group": "Wave Dynamics"` | optional section title; params with the same `group` appear together in the UI |

Example:
```json
{ "key": "waveType", "label": "Wave Type", "default": 0.0, "min": 0.0, "max": 2.0, "step": 1.0,
  "type": "CHOICE", "options": ["Sine", "Cosine", "Triangle"], "group": "Wave Dynamics" }
```
In GLSL a BOOL is read as `uToggle > 0.5`; a CHOICE as `uMode < 0.5`, `< 1.5` ... (compare with thresholds, never `==`).
Order of params in the array is the order shown in the UI; put the most-used controls first within each group.

**Which dialect to write:**
- If the user's app supports it (they run Amethyst or see native dropdowns/toggles), or says so, use the **typed dialect**
  for every toggle and dropdown, group related params, and add `minAppVersion` plus the `effects` list to suite.json.
- If you do not know the app version, write the typed dialect only when the user confirmed it; otherwise use
  the **legacy way**: toggles as 0..1 step-1 sliders with the legend in the label ("Auto Intro (0 Off, 1 On)"),
  dropdowns as 0..N step-1 sliders with the legend in the label. The shader code is identical either way.
- Never invent other `type` values. The types known are SCALAR, BOOL, CHOICE and (official 1.4.9 docs) **COLOR**
  (section 0.1: `#RRGGBB` default, `uniform vec3` in the shader). No vector/point, int or text type has been seen. On apps
  older than 1.4.9, or when unsure of the version, colours are three SCALAR sliders named `<name>R`, `<name>G`, `<name>B`
  (0..1), and hue is a plain 0..360 SCALAR. If the user shows a sample with a new type, copy its format exactly and update this section.
- Large effects: animate with a `0..1` progress slider (labels like "Reveal (Keyframe Me)" show that sliders are
  meant to be keyframed), and optionally an auto-timed alternative driven by `uTime` (`introAuto` + `introTime`).
- Stacked/repeated parts: define the maximum number of parts up front (e.g. `layerCount` 1..5) and make every
  per-part setting its own parameter; unused parts' controls still appear.
- Reuse common names: `centerX`/`centerY` (0..1, default 0.5), `speed`, `frequency`, `strength`/`amplitude`,
  `seed` (0..50 step 1), `edgeMode`, `blendWithImage` (0..1, default 1.0), `flipY`.
- Default values should show the effect clearly on first drop; all-zero defaults that look like "nothing happened"
  only make sense for a correction tool.

## 4. shader.glsl: mandatory skeleton (OBSERVED in all 49)

```glsl
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform sampler2D uTexture;   // the clip frame
varying vec2 vTex;            // 0..1 UV, (0,0) and (1,1) are opposite frame corners
// only declare these if you use them:
uniform float uTime;          // seconds, increasing
uniform vec2  uTexelSize;     // (1/width, 1/height) of the frame

// one 'uniform float uKey;' per parameter in effect.json, nothing extra

void main() {
    // ...
    gl_FragColor = texture2D(uTexture, clamp(uv, 0.0, 1.0));
}
```

Hard rules:
- **One fragment shader per pass; single pass unless `"passes"` is used (1.4.9+, section 0.1).** No `#version`, no vertex
  shader, no feedback/previous frame, no extra textures. Entry point is `void main()`; output is `gl_FragColor`.
- **GLSL ES 1.00 syntax:** `texture2D(...)`, `varying`, `gl_FragColor`. Never `texture(`, `in`/`out`, `layout`.
- **Uniform set is exactly:** `uTexture`, `vTex` (varying), optional `uTime`, optional `uTexelSize`,
  plus one `uniform float u<Key>;` per parameter (`uniform vec3 u<Key>;` for a COLOR parameter). Do not declare any other uniforms (SAFE DEFAULT: the app only feeds these); a parameter with no matching uniform is an error (in a multi-pass effect, each parameter must be declared in at least one pass).
- **Every texture fetch gets in-range coordinates** (`clamp(uv, 0.0, 1.0)`, or a mirror/fract wrapper
  that already guarantees 0..1). Samples that skip the clamp always use a mirror wrapper.
- **No unsafe division.** `x / max(y, 0.0001)`. Same for `normalize()` of a possibly-zero vector
  (use `(d > 0.0001) ? v / d : vec2(0.0)`), `atan(0,0)`, `sqrt(max(0.0, x))`, `pow(max(x,0.0), p)`.
  The app's rule is that a NaN can black-screen the GPU.
- **Float literals everywhere:** `1.0` not `1`, `2.0 * x` not `2 * x`. Integers only as loop counters.
- **Loops:** the bound must be a literal or a `const int` (OBSERVED: `for (int i = 0; i < 7; i++)` in
  `s_shake`, `for (int i = 0; i < 12; i++)` in `magiccircle3d`, and `const int SAMPLES = 64;` +
  `for (int i = 0; i < SAMPLES; i++)` in `blur_mo_curve`). Never a uniform. Higher tap counts work but cost
  performance on phones: 5-16 taps is comfortable, 64 is the largest seen (a long motion blur). If a slider
  must control quality, keep the loop at a constant max and `break`/weight-zero beyond the wanted count.
- No arrays of non-constant size, no recursion, no `discard` needed (output alpha 0 instead).
- Put helper functions above `main()`. Prefix helpers with an effect-specific word
  (`dHash`, `jHash`, `hash1`) so they never collide with names the app injects.
- **Write only fields the effect needs, but always initialize every `vec`/`float` you read.**

## 5. Alpha and color handling (OBSERVED)

The frame arrives **premultiplied** (RGB already multiplied by alpha; inferred from the samples' unpremultiply/premultiply code and the app's alpha rule).

- **Pure coordinate warps** (distort, shake, glitch-displace, wobble): just return the
  fetched pixel: `gl_FragColor = texture2D(uTexture, uv);` This preserves alpha automatically.
  Nine of the twelve samples do exactly this.
- **Anything that changes or mixes colors** (blend with original, per-channel splits, tint, grade):
  unpremultiply, do the math, premultiply back:

```glsl
vec4 c = texture2D(uTexture, uv);
vec3 rgb = c.rgb / max(c.a, 0.0001);      // unpremultiply
// ... change rgb ...
gl_FragColor = vec4(rgb * c.a, c.a);      // premultiply, keep alpha
```

  When mixing two fetches with a blend slider, mix rgb (unpremultiplied) and mix the vec4 for
  alpha, then output `vec4(rgb * base.a, base.a)` (see `lens_distortion`).
- When an effect deliberately erases pixels (dissolve), multiply both color and alpha by the
  mask: `gl_FragColor = vec4(col * cut * a, a * cut);`
- Never output color with alpha 1.0 unless the effect is a Generator that fills the frame.

## 6. Conventions that make effects behave correctly

**Time.** `uTime` is a running clock, most likely in seconds (inferred from how the samples scale it). Always scale it with a user-facing `speed` or `frequency` param
(`uTime * uSpeed`) so the user can slow it down or freeze it (0). Stepped/"stutter" motion:
`floor(uTime * rate)`. Use `fract(t)` for repeating cycles.

**Frame size in pixels.** `1.0 / max(uTexelSize, vec2(0.0001))` gives width/height in pixels (used by `magiccircle3d`).

**Aspect ratio.** `uTexelSize = (1/w, 1/h)`, so `w/h = uTexelSize.y / max(uTexelSize.x, 0.0001)`.
For round shapes (lens, circles, ripples) multiply the x offset by that aspect before taking length.
**Never hard-code 1080/1920** (two of the samples do; it is a bug on any other resolution).
Pixel-sized params: `vec2 pix = uTexelSize;` then `offset = pixels * pix`.

**Centers/origins.** `centerX`/`centerY` params in 0..1 UV space, default 0.5.

**Edges.** Samples that move the image pick one of: `clamp` (smears edge pixels), mirror
(`1.0 - abs(mod(uv, 2.0) - 1.0)`), tile (`fract(uv)`), or a small zoom-in "guard" so no
edge shows (`(uv - 0.5) / zoom + 0.5`, zoom 1.03). Shake-type effects should use mirror or
guard zoom, never leave black borders.

**Randomness.** No random built-in. Use a hash, scaled by a `seed` param:
`fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123)`. Keep the `sin` argument modest
(multiply seeds by ~17-20 not 100000) so `mediump` devices do not show banding.

**Amplitude units.** Displacement in UV units: 0.01-0.05 is a visible-but-tasteful ripple;
0.2 is extreme. Express strengths as small UV factors under the hood and keep the slider range
human-friendly (`uAmplitude * 0.06`, as the shake samples do).

**Interpolation.** Smooth value noise: `f = f*f*(3.0-2.0*f)` then `mix()`.

## 7. Pattern library (all taken from the working samples)

Copy and adapt. Each is complete enough to compile as the body of `main()` once uniforms are declared.

**Mirror wrapper (no black edges)**
```glsl
vec2 mirrorEdge(vec2 uv) { return 1.0 - abs(mod(uv, 2.0) - 1.0); }
```

**Selectable edge mode (param edgeMode 0/1/2)**
```glsl
vec2 applyEdgeMode(vec2 uv, float mode) {
    if (mode < 0.5)      return clamp(uv, 0.0, 1.0);
    else if (mode < 1.5) { vec2 m = mod(uv, 2.0); m = mod(m + 2.0, 2.0); return clamp(1.0 - abs(m - 1.0), 0.0, 1.0); }
    else                 return clamp(fract(uv), 0.0, 1.0);
}
```

**Barrel/pincushion lens** (`lens_distortion`)
```glsl
vec2 center = vec2(uCenterX, uCenterY);
vec2 p = vTex - center;
float aspect = uTexelSize.y / max(uTexelSize.x, 0.0001);
vec2 pa = vec2(p.x * aspect, p.y);
float r2 = dot(pa, pa);
float k = uDistortionStrength * 1.6;
vec2 uv = center + p * (1.0 + k * r2);          // k<0 zooms/pincushion, k>0 barrel
```

**Lens / optics compensation rule (user-verified against After Effects):** the view centre must keep scale 1 and only the
edges may move. Never normalise so the frame edge is pinned (that zooms the centre and looks like the inside moving
backwards). Use focal length `f = S / tan(h)` (S = half frame size on the FOV axis, h = FOV/2) and radial factors
`tan(a)/a` (edges inward, Reverse OFF) and `atan(a)/a` (edges outward, Reverse ON), a = R/f. They are exact inverses of each other.

**Chromatic aberration** (`chromatic_lens`): sample R, G, B at slightly different radial scales
(`baseFactor - spread`, `baseFactor`, `baseFactor + spread`, with `spread = uAberration*0.12*r2`),
then unpremultiply each channel by its own alpha, recombine, premultiply with G's alpha.

**Radial ripple / shockwave** (`circular_shockwave`)
```glsl
float dist = length(vTex - center);
float wave = sin(dist * uFrequency - uTime * uSpeed) * exp(-uDecay * dist);
float mask = smoothstep(uRadius, 0.0, dist);
vec2 dir = (dist > 0.0001) ? (vTex - center) / dist : vec2(0.0);
vec2 uv = vTex + dir * wave * uStrength * mask;
```

**Horizontal scanline wobble / rolling shutter**
`uv.x += sin(uv.y * uFrequency + uTime * uSpeed) * uIntensity;`

**Blocky glitch displacement** (`block_glitch`): `grid = floor(uv * blockSize)`,
`t = floor(uTime * speed)`, `n = hash(grid + t*0.13)`; where `n > threshold`, shift x by
`(hash(grid + t*0.57) - 0.5) * 2.0 * strength`.

**Jelly wobble** (`jelly_wobble`): breathe-scale around 0.5, then
`wx = sin(p.y * freq * 6.283 + t*2.2) * 0.015 * wobbleX`, `wy = sin(p.x * freq * 6.283 * 0.8 + t*1.8) * 0.015 * wobbleY`.

**Elastic spring bounce** (`elastic_bounce`)
```glsl
float f = fract(uTime * uSpeed * uCycles);
float springWave = sin(f * uSpring) * exp(-f * uDecay) * uPower;   // damped oscillation per cycle
```

**Camera shake with 1-D fractal noise** (`s_shake`): smooth `noise1(x)` summed over 3 octaves
(`fbm1`), drive move-x, move-y, rotation and zoom from different offsets of the same
time coordinate (`n`, `n+31.7`, `n+73.4`, `n+113.8`), rotate with `mat2(c,-s,s,c)`.

**Motion blur by temporal sampling** (`s_shake`): sample the whole shake function 7 times at
slightly different times and cosine-weight-average them. Use this idea for any motion-based
effect's blur; no neighbor-pixel blur is needed. (Older apps. On 1.4.9+ use the next pattern.)

**Native shutter motion trails, 1.4.9+ (OFFICIAL pattern, "Sapphire S_Shake" look).** Needs `"usesNativeMotionBlur": true`,
a `motionBlur` BOOL (default 1), a `trailLength` SCALAR (official suggestion 0..2.5, default 0.65; it is the shutter length
in 60 fps frames) and `frequency`. Wrap your whole motion in ONE function `vec2 getTransformedUV(vec2 uv, float t, float aspect)`
(offset + roll, no fetch) and integrate it over the shutter with 20 stratified, dithered taps:
```glsl
float dither(vec2 c) { return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453); }
vec2 mirrorCoords(vec2 uv) { return 1.0 - abs(mod(uv, 2.0) - 1.0); }   // you must define these helpers yourself

void main() {
    float aspect = uTexelSize.y / max(uTexelSize.x, 0.0001);
    float baseTime = max(uTime, 0.0);
    if (uMotionBlur < 0.5 || uTrailLength <= 0.001) {                    // fast path: blur off
        gl_FragColor = texture2D(uTexture, mirrorCoords(getTransformedUV(vTex, baseTime * uFrequency, aspect)));
        return;
    }
    float shutter = uTrailLength / 60.0;
    float jitter = dither(gl_FragCoord.xy) - 0.5;
    vec4 acc = vec4(0.0);
    const int TAPS = 20;
    for (int i = 0; i < TAPS; i++) {
        float fr = (float(i) + jitter) / float(TAPS) - 0.5;              // [-0.5, +0.5] with dithered phase
        float subTime = (baseTime + fr * shutter) * uFrequency;
        acc += texture2D(uTexture, mirrorCoords(getTransformedUV(vTex, subTime, aspect)));
    }
    gl_FragColor = acc / float(TAPS);
}
```
Why: it follows the true curve of the motion, and the per-pixel dither interleaves taps so there are no discrete ghost
echoes. Do NOT use a static Gaussian blur for motion (looks like fog). The loop bound is a `const int`, as section 4 requires.
For a still-image-only warp that has no time motion, none of this applies.

**Multi-pass bloom / glow recipe, 1.4.9+ (UNVERIFIED data flow, see 0.1).** `passes`: bright-pass/downsample -> blur H
(8 taps along x with `uTexelSize.x * uRadius`) -> blur V (8 taps along y) -> add to what the last pass receives, tinted by a
COLOR param and scaled by `brightness`. Add `"expandBounds": 0.3`. Weight taps with a Gaussian and normalise by the weight sum.

**Random per-frame stutter** (`micro_jitter`): `tick = floor(t * rate)`;
`vec2 step = vec2(hash(vec2(tick,13.7)), hash(vec2(29.3,tick))) - 0.5`; mix with a smooth sin/cos drift via a `driftMix` param; add a guard zoom.

**Noise dissolve** (`dissolve_shake`): value-noise mask animated over time;
`cut = step(uDissolve, noise)`; multiply color and alpha by `cut`.

**Curved/directional motion blur** (`blur_mo_curve`, Blur category): `const int SAMPLES = 64;` taps along an arc
(length in px via `uTexelSize`, angle, curvature, bias, taper sliders), clamped fetches, weights normalized by their sum.

**Generator over the source** (`ae_optical_flare`, `magiccircle3d`): compute the generated light/shape as a color,
then add or mix it onto the source: `vec3 rgb = base.rgb + flare * uBrightness; gl_FragColor = vec4(rgb * base.a, base.a);`.
Add an `Effect Strength` (`mixAmt`) slider that mixes between source and result.

**Emboss / plastic highlight** (`cc_plastic`, Stilisasi): sample 4 neighbours at `uTexelSize`, take luminance
gradients `gx, gy` as a fake surface normal, then light it with a `lightAngle` direction plus a specular term.

**Pseudo-3D** (`magiccircle3d`; true SDF ray marching is in 7b): rotate a point with sliders `rotX/rotY/rotZ`, divide by `(camDist - z)` for perspective,
stack several planes with `layerGap`/`layerScaleStep`/`layerTwist`, and fade by depth. No real 3D engine is needed.

**Reference effects worth asking the user to send (all in the Amethyst pack, typed dialect):**
`A_bevel_light_sweep` (edge bevel from the alpha gradient plus a sweeping light beam), `A_bevel`, `A_cc_plastic`,
`A_dimoo_light` (light beams, 25 params), `A_bokeh_blur` (19 params, aperture blades), `A_shatter` / `A_shatter3d_v7`,
`A_broken_glass`, `A_stained_glass`, `A_vhs`, `A_smear`, `A_omino_diffusion`, `A_depth_map_pro`, `A_hue`, `A_blend_hue`.
When a new request resembles one of these, ask for that pack (or its shader) as a reference instead of guessing.

**Edge normal from alpha (`A_bevel_light_sweep`):**
```glsl
vec2 texel = uTexelSize * max(uEdgeThickness, 1.0);
float a_t = texture2D(uTexture, vTex + vec2(0.0,  texel.y)).a;
float a_b = texture2D(uTexture, vTex + vec2(0.0, -texel.y)).a;
float a_r = texture2D(uTexture, vTex + vec2( texel.x, 0.0)).a;
float a_l = texture2D(uTexture, vTex + vec2(-texel.x, 0.0)).a;
vec2 grad = vec2(a_r - a_l, a_t - a_b);          // points toward more opaque pixels
float edgeStrength = length(grad);
float lighting = dot(normalize(grad + 1e-5), lightDir);   // lightDir = vec2(cos, sin) of the light angle
```
Use `lighting` for rim light / bevel highlight (positive) and shadow (negative), weighted by `edgeStrength`.


## 7a. Warp effects after Motion Tile / full-frame layers (user-reported)

The effect texture is the whole canvas, not the layer: a small layer sits inside transparent padding, so normalise warps
to the layer bounds (scan alpha in from the border along the centre row/column) or the warp looks like plain scaling.
A shader can only read the texture Keyflaw hands it, and that texture does not contain image/tile pixels beyond the canvas
edge (verified: an image larger than the frame is not available past the edge). Mirror-wrapping the lookup fills gaps with
FAKE mirrored content; the user rejected that (wants the real pixels). Do not mirror-fill unless asked. Return transparent
instead, or offer an optional zoom-to-fill that uses only real pixels. Real fix would need the app to give a larger texture.

## 7b. 3D effects ARE possible (OBSERVED: `kf_phone3d`, 563-line shader, 63 params, Generator category)

Still one fragment shader, one pass, only the standard uniforms. 3D is done by ray marching signed distance fields in `main`:
- Rotate with `mat3` (`rotX/rotY/rotZ`; model->world `M = rotZ*rotX*rotY`, world->model is the transposed product), build a
  perspective ray per pixel (a `persp` slider blends orthographic and perspective), march `for (int i = 0; i < 96; i++)`
  (literal bound; drop to ~56 taps inside motion-blur loops), normals by central differences of the SDF.
- Shape from SDF helpers: rounded box `sdRR`, extrusion `ext`, rings/holes by `min/max` of distances.
- Shading: metalness/roughness/fresnel, studio-style soft highlights, sanded grain from `hash21`/value noise, fake env reflections.
- The clip frame (`uTexture`) is used as a texture mapped onto a surface (screen content), with fit/scale/offset/rotation/tiling params.
- Output is premultiplied: render the object with its coverage as alpha, then composite over the original frame scaled by a
  `Show Background` slider (`outRGB = acc.rgb + bg*(1-cov)`).
- Animation: `uTime` drives auto spin (deg/s), float bob, and a timed tween (start, duration, easing, loop/ping-pong).
- Motion blur: accumulate N renders at jittered times inside the shutter window: `for (int k = 0; k < 12; k++) { if (float(k) >= n) break; ... }`
  with a constant max and a runtime `break`. Skip blur (single render) when nothing moves. Hash-jitter per pixel.
- Keep heavy effects usable on phones: expose a quality/sample slider, cheaper march steps when blurred, early-out on rays that miss.
- Many params are plain SCALAR sliders with the legend in the label ("Body Color: 0 Custom 1 Silver ..."), plus BOOL for on/off.

## 8. Validator + packer script

Save as `kfpack_build.py`. It validates against every rule above and only writes the pack
when there are zero ERRORs. The original single-pass checks were tested on all 49 reference effects from seven packs (all pass; it warns on
the two that hard-code resolution). The 1.4.9 additions (passes, expandBounds, usesNativeMotionBlur, COLOR, new categories,
per-pass uniform checks, minAppVersion warning) were tested on a small synthetic pack (passes) and a broken one (catches
bad COLOR default, missing pass file, old minAppVersion). It has NOT been run against a real 1.4.9 multi-pass pack.

Folder it expects:
```
build/
  suite.json
  effects/<id>/effect.json
  effects/<id>/shader.glsl            (or the pass files listed in effect.json "passes")
```
Run: `python3 kfpack_build.py build /path/to/<suite_id>.kfpack`

```python
#!/usr/bin/env python3
"""Validate a Keyflaw suite folder and zip it into a .kfpack (Keyflaw 1.4.9+ aware).

Usage:  python3 kfpack_build.py <suite_folder> [output.kfpack]

<suite_folder> must contain suite.json and effects/<id>/effect.json plus either
shader.glsl (single pass) or the files listed in effect.json "passes" (multi-pass).
Exit code 1 if any ERROR is found (no file is written). WARN lines never block.
"""
import json, re, sys, zipfile
from pathlib import Path

PARAM_TYPES = {"SCALAR", "BOOL", "CHOICE", "COLOR"}
CATEGORIES = {"Distorsi", "Stilisasi", "Blur", "Warna", "Gerak", "Simulasi", "Generator",
              "Transisi", "Keying", "Perspective", "Custom"}
BUILTIN = {"uTexture", "uTime", "uTexelSize"}
NEW_FEATURES = ("passes", "expandBounds", "usesNativeMotionBlur")
errors, warns = [], []
E = lambda m: errors.append(m)
W = lambda m: warns.append(m)


def ver(s):
    try:
        return tuple(int(x) for x in str(s).split("."))
    except ValueError:
        return (0,)


def uname(k):
    return "u" + k[0].upper() + k[1:]


def check_shader(fid, fname, src):
    tag = f"{fid}/{fname}"
    if "GL_FRAGMENT_PRECISION_HIGH" not in src or "precision mediump float" not in src:
        E(f"{tag}: missing the 5-line precision header")
    if "#version" in src:
        E(f"{tag}: remove #version (app uses GLSL ES 1.00 style)")
    if re.search(r"\btexture\s*\(", src):
        E(f"{tag}: use texture2D(), not texture()")
    if "gl_FragColor" not in src:
        E(f"{tag}: never writes gl_FragColor")
    if "texture2D" not in src:
        W(f"{tag}: no texture2D call (fine only for Generator effects)")
    if not re.search(r"uniform\s+sampler2D\s+uTexture\s*;", src):
        E(f"{tag}: missing 'uniform sampler2D uTexture;'")
    if not re.search(r"varying\s+vec2\s+vTex\s*;", src):
        E(f"{tag}: missing 'varying vec2 vTex;'")
    consts = set(re.findall(r"const\s+int\s+(\w+)\s*=\s*\d+\s*;", src))
    for m in re.finditer(r"\bfor\s*\(([^;]*);([^;]*);", src):
        cond = m.group(2).strip()
        ok = re.search(r"[<>]=?\s*\d+\s*$", cond) or any(re.search(r"[<>]=?\s*" + c + r"\s*$", cond) for c in consts)
        if not ok:
            E(f"{tag}: for-loop bound must be a literal or a 'const int' constant: for(...;{cond};...)")
    if re.search(r"1080\.0|1920\.0", src):
        W(f"{tag}: hard-coded 1080/1920 resolution; use uTexelSize instead")
    decl_all = set(re.findall(r"uniform\s+(?:float|vec2|vec3)\s+(u\w+)\s*;", src))
    if "uTexelSize" in src and "uTexelSize" not in decl_all:
        E(f"{tag}: uses uTexelSize without declaring 'uniform vec2 uTexelSize;'")
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
    if code.count("{") != code.count("}") or code.count("(") != code.count(")"):
        E(f"{tag}: unbalanced braces/parentheses")
    if re.search(r"/\s*(?:u[A-Z]\w*|dot\([^)]*\)|length\([^)]*\))(?!\s*[\w(])", src) and "max(" not in src:
        W(f"{tag}: division by a uniform/length with no max(...,0.0001) anywhere")
    return {n: t for t, n in re.findall(r"uniform\s+(float|vec2|vec3)\s+(u\w+)\s*;", src)}


def check_effect(folder: Path, suite_min):
    fid = folder.name
    try:
        meta = json.loads((folder / "effect.json").read_text(encoding="utf-8"))
    except Exception as ex:
        return E(f"{fid}: effect.json missing/invalid JSON ({ex}) (comments are NOT allowed in JSON)")

    for k in ("id", "name", "category", "parameters"):
        if k not in meta:
            E(f"{fid}: effect.json missing '{k}'")
    if meta.get("id") != fid:
        E(f"{fid}: effect.json id '{meta.get('id')}' must equal folder name")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", fid):
        E(f"{fid}: id must be letters/digits/underscore, starting with a letter")
    if meta.get("category") not in CATEGORIES:
        W(f"{fid}: category '{meta.get('category')}' is not one of {sorted(CATEGORIES)} "
          "(a custom category worked in the Amethyst pack, but is untested elsewhere)")

    # ---- 1.4.9 fields ----
    files = ["shader.glsl"]
    if "passes" in meta:
        ps = meta["passes"]
        if not (isinstance(ps, list) and len(ps) >= 2 and all(isinstance(x, str) and x.endswith(".glsl") for x in ps)):
            E(f"{fid}: 'passes' must be a list of 2+ .glsl file names")
        else:
            files = ps
            if len(set(ps)) != len(ps):
                E(f"{fid}: 'passes' lists the same file twice")
            if (folder / "shader.glsl").exists():
                W(f"{fid}: shader.glsl exists but 'passes' is set; shader.glsl is ignored (and not packed)")
    if "expandBounds" in meta:
        eb = meta["expandBounds"]
        if isinstance(eb, bool) or not isinstance(eb, (int, float)) or eb < 0:
            E(f"{fid}: expandBounds must be a number >= 0 (0.3 = 30% padding)")
        elif eb > 1:
            W(f"{fid}: expandBounds {eb} is over 1.0 (100% padding); expensive and rarely needed")
    if "usesNativeMotionBlur" in meta and not isinstance(meta["usesNativeMotionBlur"], bool):
        E(f"{fid}: usesNativeMotionBlur must be true or false")
    if any(f in meta for f in NEW_FEATURES) and suite_min is not None and ver(suite_min) < (1, 4, 9):
        W(f"{fid}: uses 1.4.9 fields but suite minAppVersion is {suite_min}; set it to '1.4.9'")

    # ---- parameters ----
    keys, ptypes = [], {}
    for p in meta.get("parameters", []):
        k = p.get("key", "")
        keys.append(k)
        ptype = p.get("type", "SCALAR")
        ptypes[k] = ptype
        need = ("key", "label", "default") if ptype == "COLOR" else ("key", "label", "default", "min", "max", "step")
        for f in need:
            if f not in p:
                E(f"{fid}: param '{k}' missing '{f}'")
        if not re.fullmatch(r"[a-z][A-Za-z0-9]*", k):
            E(f"{fid}: param key '{k}' must be camelCase starting lowercase")
        if ptype not in PARAM_TYPES:
            W(f"{fid}: param '{k}' has unseen type '{ptype}' (seen types: {sorted(PARAM_TYPES)})")
        if len(str(p.get("label", ""))) > 40:
            W(f"{fid}: label of '{k}' is over 40 chars; the app may cut it off")
        if "group" in p and not isinstance(p["group"], str):
            E(f"{fid}: param '{k}' group must be a string")
        if ptype == "COLOR":
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(p.get("default", ""))):
                E(f"{fid}: COLOR '{k}' default must be a '#RRGGBB' string")
            continue
        if ptype == "CHOICE":
            opts = p.get("options")
            if not (isinstance(opts, list) and len(opts) >= 2 and all(isinstance(o, str) for o in opts)):
                E(f"{fid}: CHOICE param '{k}' needs an 'options' list of 2+ strings")
            elif not (p.get("min") == 0 and p.get("max") == len(opts) - 1 and p.get("step") == 1
                      and p.get("default") == int(p.get("default", 0))):
                E(f"{fid}: CHOICE '{k}' needs min 0, max {len(opts) - 1}, step 1, whole-number default")
        elif "options" in p:
            E(f"{fid}: only CHOICE params take 'options'")
        if ptype == "BOOL":
            if not (p.get("min") == 0 and p.get("max") == 1 and p.get("default") in (0, 1)):
                E(f"{fid}: BOOL '{k}' needs min 0, max 1, default 0 or 1")
            elif p.get("step") != 1:
                W(f"{fid}: BOOL '{k}' step should be 1 (one reference pack used 0.01)")
        try:
            if not (p["min"] < p["max"]):
                E(f"{fid}: param '{k}' min must be < max")
            if not (p["min"] <= p["default"] <= p["max"]):
                E(f"{fid}: param '{k}' default outside min..max")
            if p["step"] <= 0:
                E(f"{fid}: param '{k}' step must be > 0")
            if any(isinstance(p[f], bool) or not isinstance(p[f], (int, float))
                   for f in ("default", "min", "max", "step")):
                E(f"{fid}: param '{k}' default/min/max/step must be plain numbers")
        except KeyError:
            pass
    if len(keys) != len(set(keys)):
        E(f"{fid}: duplicate parameter keys")

    if meta.get("usesNativeMotionBlur") is True and not {"motionBlur", "trailLength"} <= set(keys):
        W(f"{fid}: usesNativeMotionBlur is true; the official pattern also has 'motionBlur' (BOOL) and 'trailLength' sliders")

    # ---- shaders ----
    declared_union = {}
    for fn in files:
        path = folder / fn
        if not path.exists():
            E(f"{fid}: {fn} missing")
            continue
        decl = check_shader(fid, fn, path.read_text(encoding="utf-8"))
        wanted = {uname(k): ("vec3" if ptypes.get(k) == "COLOR" else "float") for k in keys if k}
        for u, t in sorted(decl.items()):
            if u in BUILTIN:
                continue
            if u not in wanted:
                E(f"{fid}/{fn}: shader declares {u} but no matching parameter key")
            elif wanted[u] != t:
                E(f"{fid}/{fn}: {u} must be 'uniform {wanted[u]}', found {t}")
        declared_union.update(decl)
    if all((folder / fn).exists() for fn in files):
        for k in keys:
            if k and uname(k) not in declared_union:
                E(f"{fid}: parameter '{k}' needs 'uniform {'vec3' if ptypes.get(k) == 'COLOR' else 'float'} {uname(k)};' "
                  f"in {'at least one pass' if len(files) > 1 else 'the shader'}")
    return files


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1]).resolve()
    suite_path = root / "suite.json"
    if not suite_path.exists():
        sys.exit(f"ERROR: {suite_path} missing (suite.json must be at the ROOT of the pack)")
    try:
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
    except Exception as ex:
        sys.exit(f"ERROR: suite.json invalid JSON: {ex}")
    for k in ("id", "name", "author", "version", "description"):
        if k not in suite:
            E(f"suite.json missing '{k}'")

    eff_dirs = sorted(p for p in (root / "effects").glob("*") if p.is_dir())
    if not eff_dirs:
        E("no effects/<id>/ folders found")
    if "effects" in suite:
        listed, found = list(suite["effects"]), [d.name for d in eff_dirs]
        for n in sorted(set(listed) - set(found)):
            E(f"suite.json effects lists '{n}' but effects/{n}/ does not exist")
        for n in sorted(set(found) - set(listed)):
            E(f"effects/{n}/ exists but is missing from suite.json 'effects' list")
    typed = False
    for d in eff_dirs:
        if (d / "effect.json").exists():
            try:
                typed |= any("type" in p for p in json.loads((d / "effect.json").read_text(encoding="utf-8")).get("parameters", []))
            except Exception:
                pass
    if typed and "minAppVersion" not in suite:
        W("typed params (BOOL/CHOICE/COLOR/group) are used; set suite.json minAppVersion (1.2.4 for typed, 1.4.9 for passes/expandBounds/usesNativeMotionBlur)")

    packed = {}
    for d in eff_dirs:
        packed[d.name] = check_effect(d, suite.get("minAppVersion")) or ["shader.glsl"]

    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(f"\n{len(errors)} error(s). Pack NOT written. Fix and re-run.")

    out = Path(sys.argv[2]) if len(sys.argv) > 2 else root.parent / f"{suite['id']}.kfpack"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(suite_path, "suite.json")
        order = suite.get("effects") or [d.name for d in eff_dirs]
        for d in sorted(eff_dirs, key=lambda x: order.index(x.name) if x.name in order else 999):
            for name in ["effect.json"] + packed[d.name]:
                z.write(d / name, f"effects/{d.name}/{name}")  # forward slashes always
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        print("\nOK. Wrote", out)
        for n in z.namelist():
            print("  ", n)


if __name__ == "__main__":
    main()
```

## 9. Delivering the file (pick the first that works)

1. **You have a code sandbox + file download/link ability:** write the folder, run the script,
   hand over the actual `.kfpack` file or its real link. Never invent a link. If you cannot
   produce a real downloadable file, do not claim you did.
2. **You can run code but not share files:** run the script anyway to validate, then print every
   file's full contents in separate labeled code blocks (section 9.3).
3. **No code execution at all (plain chat):** print each file in its own code block with its exact
   path as the label, and give the user these steps for an Android phone:
   - Create the folders exactly as shown, paste each file's text in.
   - In Termux: `cd build && zip -r ../<suite_id>.kfpack suite.json effects` (`pkg install zip` first),
     or select `suite.json` and the `effects` folder in a file manager, compress to ZIP, rename
     `.zip` to `.kfpack`.
   - Common mistake: zipping the parent folder, which puts `build/suite.json` one level too deep.
     `suite.json` must be at the ZIP's top level.

Always show the final `shader.glsl` in the reply too.

## 10. Honest limits and fast debugging

You cannot run the shader inside Keyflaw. Say so. If the user reports a problem:

| Symptom | Likely cause | Fix |
|---|---|---|
| Multi-pass effect shows black/unchanged, or a later pass looks wrong | assumed data flow between passes (0.1) is wrong, or a pass reads something it was not given | simplify to the safe shape (each pass uses only `uTexture`), send the user's working multi-pass sample, diff |
| Glow/shadow still cut off in a square | missing `expandBounds`, or effect is clamped to 0..1 | add `"expandBounds": 0.3`, do not clamp the output to the clip rect |
| Shake blur looks like fog or ghost echoes | static blur or too few discrete taps | use the 20-tap dithered shutter pattern (section 7) |
| Pack will not import | suite.json not at ZIP root, bad JSON, wrong category spelling, id != folder | run the validator; re-zip from inside the folder |
| Effect imports, shows black/blank | NaN from a division/normalize/pow, or alpha written wrong | add `max(x,0.0001)`; check final line writes `vec4(rgb*a, a)` |
| Shader error / effect missing | uniform name mismatch (`blockSize` needs `uBlockSize`), int/float mix (`2 * x`), non-constant loop bound, `texture(` | fix per section 4 |
| Sliders do nothing | uniform not declared, or declared but never used | declare and use every parameter |
| Looks stretched/oval | forgot aspect correction | use `uTexelSize` aspect (section 6) |
| Wrong size on other resolutions | hard-coded pixel size | use `uTexelSize` |
| Black/smeared borders | no edge handling | mirror wrapper or guard zoom |
| Motion too fast/slow | `uTime` not scaled | multiply by a speed param |
| Dropdown/toggle shows as a plain slider, or the pack will not import after adding `type` fields | the app is older than the typed dialect | rebuild in the legacy dialect (section 3.2), legend in the label |
| Strange flicker on some phones | `mediump` precision with huge `sin()` arguments | keep hash inputs small |

## 11. Output checklist (run before delivering)

- [ ] suite.json has all 5 string fields
- [ ] folder name == `"id"` == snake_case
- [ ] suite id reverse-domain; suite `category` == every effect `category` (custom word); effect ids prefixed (`X_name`); see 0.5
- [ ] every param has key/label/default/min/max/step, default within range, camelCase key, label <= 40 chars
- [ ] 1.4.9 features only if the user's app is 1.4.9+: `passes` files all exist and are zipped, `expandBounds` for anything drawn outside the layer, COLOR params as `uniform vec3`, `minAppVersion "1.4.9"`, no `/* */` comments in JSON
- [ ] typed dialect only if the app supports it: BOOL 0/1, CHOICE with `options` and max = options-1, groups, suite `effects` list + `minAppVersion`
- [ ] every param has `uniform float u<Key>;` and the shader actually uses it
- [ ] precision header present, no `#version`, `texture2D` only
- [ ] all fetches clamped or mirror-wrapped; all divisions via `max(...,0.0001)`
- [ ] loops have literal bounds; float literals everywhere
- [ ] colors un/premultiplied correctly; alpha preserved
- [ ] no hard-coded resolution; aspect from `uTexelSize` where shape matters
- [ ] `uTime` scaled by a speed/frequency param
- [ ] validator run with zero ERRORs (or code shown as in 9.3)
- [ ] user told what was assumed and that it is untested inside Keyflaw
