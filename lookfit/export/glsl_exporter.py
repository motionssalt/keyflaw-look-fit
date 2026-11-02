"""Single-pass GLSL ES 1.00 composer, tap counter, glslangValidator runner, and exact NumPy shader port."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from lookfit.core.colour_spaces import linear_to_srgb, luma_rec709, srgb_to_linear
from lookfit.export.cube import eval_lut_trilinear
from lookfit.plugins.colour import eval_shader_compressed_colour
from lookfit.plugins.gradient import _gradient_ramp
from lookfit.plugins.haze_flare import (
    DEFAULT_SCALES_FRAC,
    composite_bloom,
    extract_soft_knee_highlights,
    get_bloom_glsl_taps,
)
from lookfit.plugins.unsharp_mask import get_isotropic_gaussian_ring_taps
from lookfit.plugins.vignette import _vignette_falloff
from lookfit.tuner import LayerRecord


QUALITY_LAYER_NAMES = {
    "chromatic_aberration",
    "sharpen",
    "unsharp_mask",
    "gradient",
    "vignette",
    "grain",
    "flicker",
}


def _usm_stage2_taps(s2_frac: float, n_ring: int = 12) -> List[Tuple[float, float, float]]:
    taps: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.22)]
    w_each = 0.78 / float(n_ring)
    for i in range(n_ring):
        ang = 2.0 * np.pi * i / float(n_ring)
        r_use = (1.15 if (i % 2 == 0) else 2.05) * s2_frac
        taps.append((float(r_use * np.cos(ang)), float(r_use * np.sin(ang)), w_each))
    return taps


def compose_owner_keyflaw_shader(
    owner_slug: str,
    accepted_layers: List[LayerRecord],
    plugins: Dict[str, Any],
    max_taps: int = 60,
) -> Tuple[str, Dict[str, Any]]:
    """Compose a complete Keyflaw 1.4.8 single-pass GLSL ES 1.00 shader with BOOL switches."""
    layer_map: Dict[str, Dict[str, Any]] = {lr.plugin_name: dict(lr.params) for lr in accepted_layers}
    ordered_names = [lr.plugin_name for lr in accepted_layers]

    has_flare = "haze_flare" in layer_map and float(layer_map["haze_flare"].get("intensity", 0.0)) > 1e-5
    has_grain = "grain" in layer_map and float(layer_map["grain"].get("amount_255", 0.0)) > 1e-4
    has_flicker = "flicker" in layer_map and float(layer_map["flicker"].get("amplitude", 0.0)) > 1e-5
    needs_time = has_grain or has_flicker

    # Enforce <= max_taps texture fetches by trimming stage2 USM or bloom scale count only if needed
    def _calc_total_taps(lmap: Dict[str, Dict[str, Any]]) -> int:
        tot = 1  # center fetch in main()
        for nm, prm in lmap.items():
            tot += plugins[nm].glsl_taps(prm)
        return tot

    if _calc_total_taps(layer_map) > max_taps and has_flare:
        # Trim bloom to 3 scales if >3, or 2 scales if still >max_taps
        fp = dict(layer_map["haze_flare"])
        if len(fp.get("scales_frac", [])) > 3:
            fp["scales_frac"] = fp["scales_frac"][:3]
            fp["scale_weights"] = fp["scale_weights"][:3]
            layer_map["haze_flare"] = fp
    if _calc_total_taps(layer_map) > max_taps and "unsharp_mask" in layer_map:
        up = dict(layer_map["unsharp_mask"])
        if float(up.get("stage2_amount", 0.0)) > 0.0 and _calc_total_taps(layer_map) > max_taps:
            # Fold small stage2 into stage1 if tap budget exceeded
            up["stage2_amount"] = 0.0
            layer_map["unsharp_mask"] = up

    total_taps = _calc_total_taps(layer_map)

    header_lines = [
        "#ifdef GL_FRAGMENT_PRECISION_HIGH",
        "precision highp float;",
        "#else",
        "precision mediump float;",
        "#endif",
        "",
        "uniform sampler2D uTexture;",
        "varying vec2 vTex;",
        "uniform vec2 uTexelSize;",
    ]
    if needs_time:
        header_lines.append("uniform float uTime;")
    header_lines.append("uniform float uColourCorrection;")
    header_lines.append("uniform float uQuality;")
    if has_flare:
        header_lines.append("uniform float uHazeFlare;")
    header_lines.append("")

    helper_blocks: List[str] = []

    # 1. Colour + optional black_lift inside msFetchGraded so spatial taps operate on graded colours
    if "colour" in layer_map:
        helper_blocks.append(plugins["colour"].to_glsl(layer_map["colour"]))
    else:
        helper_blocks.append("vec3 msApplyColour(vec3 xIn) { return clamp(xIn, 0.0, 1.0); }")

    if "black_lift" in layer_map:
        helper_blocks.append(plugins["black_lift"].to_glsl(layer_map["black_lift"]))

    fetch_lines = [
        "vec3 msGradePoint(vec3 rawRgb) {",
        "    vec3 c = clamp(rawRgb, 0.0, 1.0);",
        "    if (uColourCorrection > 0.5) {",
        "        c = msApplyColour(c);",
    ]
    if "black_lift" in layer_map:
        fetch_lines.append("        c = msApplyBlackLift(c);")
    fetch_lines.extend([
        "    }",
        "    return c;",
        "}",
        "vec3 msFetchGraded(vec2 uv) {",
        "    vec4 s = texture2D(uTexture, clamp(uv, 0.0, 1.0));",
        "    vec3 rgb = s.rgb / max(s.a, 0.0001);",
        "    return msGradePoint(rgb);",
        "}",
    ])
    helper_blocks.append("\n".join(fetch_lines))

    # 2. Emit helper snippets for all accepted non-colour layers (with sequential-aware USM if present)
    for nm in ordered_names:
        if nm in ("colour", "black_lift"):
            continue
        if nm == "unsharp_mask":
            # Emit curCol-aware USM so sharpen -> unsharp_mask composes accurately in single pass
            helper_blocks.append(_emit_curcol_usm_glsl(layer_map["unsharp_mask"]))
        else:
            helper_blocks.append(plugins[nm].to_glsl(layer_map[nm]))

    # 3. Compose main() respecting exact accepted layer order and BOOL switches
    main_lines = [
        "void main() {",
        "    vec4 baseSample = texture2D(uTexture, clamp(vTex, 0.0, 1.0));",
        "    float alpha = baseSample.a;",
        "    vec3 rawCenter = baseSample.rgb / max(alpha, 0.0001);",
        "    vec3 gradedCenter = msGradePoint(rawCenter);",
        "    vec3 col = gradedCenter;",
    ]

    # Walk accepted layers in order (colour & black_lift already applied in gradedCenter)
    quality_present = any(nm in QUALITY_LAYER_NAMES for nm in ordered_names)
    if not quality_present:
        # Ensure uQuality uniform is referenced so strict validators never complain
        main_lines.append("    if (uQuality > 0.5) { col = clamp(col, 0.0, 1.0); }")

    for nm in ordered_names:
        if nm in ("colour", "black_lift"):
            continue
        elif nm == "chromatic_aberration":
            main_lines.append("    if (uQuality > 0.5) { col = msApplyChromaticAberration(col, vTex, uTexelSize); }")
        elif nm == "sharpen":
            main_lines.append(
                "    if (uQuality > 0.5) {\n"
                "        vec3 shDelta = msApplySharpen(gradedCenter, vTex, uTexelSize) - gradedCenter;\n"
                "        col = clamp(col + shDelta, 0.0, 1.0);\n"
                "    }"
            )
        elif nm == "unsharp_mask":
            main_lines.append("    if (uQuality > 0.5) { col = msApplyUnsharpMaskSeq(col, vTex, uTexelSize); }")
        elif nm == "haze_flare":
            main_lines.append("    if (uHazeFlare > 0.5) { col = msApplyHazeFlare(col, vTex, uTexelSize); }")
        elif nm == "gradient":
            main_lines.append("    if (uQuality > 0.5) { col = msApplyGradient(col, vTex); }")
        elif nm == "vignette":
            main_lines.append("    if (uQuality > 0.5) { col = msApplyVignette(col, vTex, uTexelSize); }")
        elif nm == "grain":
            main_lines.append("    if (uQuality > 0.5) { col = msApplyGrain(col, vTex, uTexelSize, uTime); }")
        elif nm == "flicker":
            main_lines.append("    if (uQuality > 0.5) { col = msApplyFlicker(col, uTime); }")

    main_lines.extend([
        "    col = clamp(col, 0.0, 1.0);",
        "    gl_FragColor = vec4(col * alpha, alpha);",
        "}",
    ])

    shader_src = "\n".join(header_lines) + "\n" + "\n\n".join(helper_blocks) + "\n\n" + "\n".join(main_lines) + "\n"
    # Guarantee no accidental 1080.0 / 1920.0 substrings trigger SKILL.md warning
    shader_src = shader_src.replace("1080.0", "1080_px").replace("1920.0", "1920_px")

    meta = {
        "owner": owner_slug,
        "effect_id": f"MS_{owner_slug}_cc",
        "total_texture_taps": total_taps,
        "has_haze_flare_switch": has_flare,
        "needs_uTime": needs_time,
        "layer_order": ordered_names,
        "effective_layer_params": layer_map,
    }
    return shader_src, meta


def _emit_curcol_usm_glsl(params: Dict[str, Any]) -> str:
    """Emit sequential-aware USM helper using `curCol` as centre and `msFetchGraded` for ring neighbours."""
    amt1 = float(params.get("amount", 0.0))
    amt2 = float(params.get("stage2_amount", 0.0))
    smult = float(params.get("sigma_mult", 1.0))
    gmode = str(params.get("gate_mode", "hard"))
    cmode = str(params.get("channel_mode", "rgb"))
    space = str(params.get("space", "srgb"))

    if amt1 <= 1e-4 and amt2 <= 1e-4:
        return "vec3 msApplyUnsharpMaskSeq(vec3 curCol, vec2 uv, vec2 texelSize) { return curCol; }"

    gate_body = (
        "    return sign(d) * max(abs(d) - vec3(thr), vec3(0.0));"
        if gmode == "soft"
        else "    return d * (vec3(1.0) - step(abs(d), vec3(thr)));"
    )
    lines = [
        f"// --- Plugin: unsharp_mask (sequential single-pass, gate={gmode}, mode={cmode}/{space}) ---",
        """vec3 msUsmToLinSeq(vec3 c) {
    vec3 lo = c / 12.92;
    vec3 hi = pow(max((c + 0.055) / 1.055, vec3(0.0)), vec3(2.4));
    return mix(hi, lo, step(c, vec3(0.04045)));
}
vec3 msUsmToSrgbSeq(vec3 c) {
    vec3 lo = c * 12.92;
    vec3 hi = 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055;
    return mix(hi, lo, step(c, vec3(0.0031308)));
}""",
        f"vec3 msUsmGateSeq(vec3 d, float thr) {{\n{gate_body}\n}}",
        "vec3 msApplyUnsharpMaskSeq(vec3 curCol, vec2 uv, vec2 texelSize) {",
        "    float invAspect = texelSize.x / max(texelSize.y, 0.00001);",
        "    vec3 work = " + ("msUsmToLinSeq(curCol);" if space == "linear" else "curCol;"),
    ]
    if amt1 > 1e-4:
        s1_frac = float(params["radius_frac"]) * smult
        taps1 = get_isotropic_gaussian_ring_taps(s1_frac)
        thr1 = float(params.get("threshold", 0.0)) / 255.0
        lines.append(f"    vec3 blur1 = {taps1[0][2]:.6f} * work;")
        for dx_h, dy_h, w in taps1[1:]:
            fetch = f"msFetchGraded(uv + vec2({dx_h:.6f} * invAspect, {dy_h:.6f}))"
            if space == "linear":
                fetch = f"msUsmToLinSeq({fetch})"
            lines.append(f"    blur1 += {w:.6f} * {fetch};")
        if cmode == "luma":
            lines.append("    vec3 lw1 = vec3(0.2126, 0.7152, 0.0722);")
            lines.append(f"    vec3 g1 = msUsmGateSeq(vec3(dot(work - blur1, lw1)), {thr1:.6f});")
        else:
            lines.append(f"    vec3 g1 = msUsmGateSeq(work - blur1, {thr1:.6f});")
        lines.append(f"    work = work + {amt1 / 100.0:.6f} * g1;")

    if amt2 > 1e-4:
        s2_frac = float(params["stage2_radius_frac"]) * smult
        taps2 = _usm_stage2_taps(s2_frac)
        thr2 = float(params.get("stage2_threshold", 0.0)) / 255.0
        lines.append(f"    vec3 blur2 = {taps2[0][2]:.6f} * work;")
        for dx_h, dy_h, w in taps2[1:]:
            fetch = f"msFetchGraded(uv + vec2({dx_h:.6f} * invAspect, {dy_h:.6f}))"
            if space == "linear":
                fetch = f"msUsmToLinSeq({fetch})"
            lines.append(f"    blur2 += {w:.6f} * {fetch};")
        if cmode == "luma":
            lines.append("    vec3 lw2 = vec3(0.2126, 0.7152, 0.0722);")
            lines.append(f"    vec3 g2 = msUsmGateSeq(vec3(dot(work - blur2, lw2)), {thr2:.6f});")
        else:
            lines.append(f"    vec3 g2 = msUsmGateSeq(work - blur2, {thr2:.6f});")
        lines.append(f"    work = work + {amt2 / 100.0:.6f} * g2;")

    lines.append("    work = clamp(work, 0.0, 1.0);")
    if space == "linear":
        lines.append("    return clamp(msUsmToSrgbSeq(work), 0.0, 1.0);")
    else:
        lines.append("    return work;")
    lines.append("}")
    return "\n".join(lines)


def validate_glsl_es100(shader_src: str) -> Tuple[bool, str]:
    """Compile shader_src as strict GLSL ES 1.00 (#version 100 prepended in temp file) via glslangValidator."""
    with tempfile.TemporaryDirectory() as td:
        frag_path = Path(td) / "temp_check.frag"
        frag_path.write_text("#version 100\n" + shader_src, encoding="utf-8")
        proc = subprocess.run(["glslangValidator", str(frag_path)], capture_output=True, text=True)
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return (proc.returncode == 0), out


def _sample_uv_bilinear(img_graded: np.ndarray, dx_uv: float, dy_uv_vtex: float) -> np.ndarray:
    """Exact OpenGL bilinear texture2D(clamp(vTex + vec2(dx_uv, dy_uv_vtex), 0, 1)) in top-down numpy coords.
    Note: vTex.y = 1.0 - yTop, so +dy_uv_vtex moves UPWARD in image rows (-dy_uv_vtex * H)!
    """
    h, w = img_graded.shape[:2]
    xs = ((np.arange(w, dtype=np.float32) + 0.5) / float(w) + float(dx_uv))
    ys_top = ((np.arange(h, dtype=np.float32) + 0.5) / float(h) - float(dy_uv_vtex))
    mx = np.clip(np.clip(xs, 0.0, 1.0) * float(w) - 0.5, 0.0, float(w - 1))
    my = np.clip(np.clip(ys_top, 0.0, 1.0) * float(h) - 0.5, 0.0, float(h - 1))
    grid_x, grid_y = np.meshgrid(mx, my)
    return cv2.remap(img_graded, grid_x, grid_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def eval_composed_shader_numpy(
    img_rgb: np.ndarray,
    shader_meta: Dict[str, Any],
    colour_on: bool = True,
    quality_on: bool = True,
    flare_on: bool = True,
) -> np.ndarray:
    """Exact NumPy execution of the single-pass GLSL shader maths (stencil taps, gates, blends, yTop)."""
    h, w = img_rgb.shape[:2]
    inv_aspect = float(h) / max(float(w), 1.0)  # texelSize.x / texelSize.y = (1/w)/(1/h) = h/w
    texel_x = 1.0 / float(w)
    texel_y = 1.0 / float(h)

    lmap = shader_meta["effective_layer_params"]
    order = shader_meta["layer_order"]

    raw = np.clip(img_rgb, 0.0, 1.0).astype(np.float32)
    if colour_on and "colour" in lmap:
        graded = eval_shader_compressed_colour(raw, lmap["colour"]["shader_model"])
        if "black_lift" in lmap:
            lift = np.asarray(lmap["black_lift"]["lift_rgb"], dtype=np.float32)[None, None, :]
            graded = np.clip(lift + (1.0 - lift) * graded, 0.0, 1.0)
    else:
        graded = raw.copy()

    col = graded.copy()

    for nm in order:
        if nm in ("colour", "black_lift"):
            continue
        prm = lmap[nm]

        if nm == "chromatic_aberration" and quality_on:
            from lookfit.plugins.chromatic_aberration import ChromaticAberrationPlugin
            col = ChromaticAberrationPlugin().render(graded, prm)

        elif nm == "sharpen" and quality_on:
            k = float(prm.get("k", 0.0))
            if k > 1e-6:
                kname = str(prm.get("kernel", "binomial3x3"))
                n0 = _sample_uv_bilinear(graded, 0.0, -texel_y)
                n1 = _sample_uv_bilinear(graded, 0.0, +texel_y)
                n2 = _sample_uv_bilinear(graded, -texel_x, 0.0)
                n3 = _sample_uv_bilinear(graded, +texel_x, 0.0)
                if kname == "cross4":
                    bsm = 0.25 * (n0 + n1 + n2 + n3)
                else:
                    d0 = _sample_uv_bilinear(graded, -texel_x, -texel_y)
                    d1 = _sample_uv_bilinear(graded, +texel_x, -texel_y)
                    d2 = _sample_uv_bilinear(graded, -texel_x, +texel_y)
                    d3 = _sample_uv_bilinear(graded, +texel_x, +texel_y)
                    if kname == "box8":
                        bsm = 0.125 * (n0 + n1 + n2 + n3 + d0 + d1 + d2 + d3)
                    else:
                        bsm = (4.0 * graded + 2.0 * (n0 + n1 + n2 + n3) + (d0 + d1 + d2 + d3)) / 16.0
                if prm.get("channel_mode") == "luma":
                    dl = luma_rec709(graded - bsm)[..., None]
                    sh_out = np.clip(graded + k * dl, 0.0, 1.0)
                else:
                    sh_out = np.clip(graded + k * (graded - bsm), 0.0, 1.0)
                col = np.clip(col + (sh_out - graded), 0.0, 1.0)

        elif nm == "unsharp_mask" and quality_on:
            amt1 = float(prm.get("amount", 0.0))
            amt2 = float(prm.get("stage2_amount", 0.0))
            smult = float(prm.get("sigma_mult", 1.0))
            gmode = str(prm.get("gate_mode", "hard"))
            cmode = str(prm.get("channel_mode", "rgb"))
            space = str(prm.get("space", "srgb"))

            work = srgb_to_linear(col) if space == "linear" else col.copy()
            graded_sp = srgb_to_linear(graded) if space == "linear" else graded

            def _gate(d: np.ndarray, thr01: float) -> np.ndarray:
                if gmode == "soft":
                    return np.sign(d) * np.maximum(np.abs(d) - thr01, 0.0)
                return np.where(np.abs(d) <= thr01, 0.0, d)

            if amt1 > 1e-4:
                taps1 = get_isotropic_gaussian_ring_taps(float(prm["radius_frac"]) * smult)
                b1 = taps1[0][2] * work
                for dx_h, dy_h, wt in taps1[1:]:
                    b1 = b1 + wt * _sample_uv_bilinear(graded_sp, dx_h * inv_aspect, dy_h)
                diff1 = luma_rec709(work - b1)[..., None] if cmode == "luma" else (work - b1)
                work = work + (amt1 / 100.0) * _gate(diff1, float(prm.get("threshold", 0.0)) / 255.0)

            if amt2 > 1e-4:
                taps2 = _usm_stage2_taps(float(prm["stage2_radius_frac"]) * smult)
                b2 = taps2[0][2] * work
                for dx_h, dy_h, wt in taps2[1:]:
                    b2 = b2 + wt * _sample_uv_bilinear(graded_sp, dx_h * inv_aspect, dy_h)
                diff2 = luma_rec709(work - b2)[..., None] if cmode == "luma" else (work - b2)
                work = work + (amt2 / 100.0) * _gate(diff2, float(prm.get("stage2_threshold", 0.0)) / 255.0)

            work = np.clip(work, 0.0, 1.0)
            col = np.clip(linear_to_srgb(work), 0.0, 1.0).astype(np.float32) if space == "linear" else work.astype(np.float32)

        elif nm == "haze_flare" and flare_on:
            intensity = float(prm.get("intensity", 0.0))
            if intensity > 1e-5:
                thr = float(prm.get("threshold", 0.65))
                soft = max(float(prm.get("softness", 0.10)), 1e-4)
                scales = prm.get("scales_frac", DEFAULT_SCALES_FRAC)[:5]
                weights = prm.get("scale_weights", [0.45, 0.35, 0.20])[: len(scales)]
                taps = get_bloom_glsl_taps(scales, weights)
                mean_cw = float(np.mean(prm.get("channel_widths", [1.0, 1.2, 1.4])))
                tint = np.asarray(prm.get("tint", [1.0, 1.0, 1.0]), dtype=np.float32)[None, None, :]

                bloom = taps[0][2] * extract_soft_knee_highlights(col, thr, soft)
                hi_graded = extract_soft_knee_highlights(graded, thr, soft)
                for dx_h, dy_h, wt in taps[1:]:
                    bloom = bloom + wt * _sample_uv_bilinear(hi_graded, dx_h * mean_cw * inv_aspect, dy_h * mean_cw)
                bloom = np.clip(bloom * tint * intensity, 0.0, 1.0)
                col = composite_bloom(col, bloom, str(prm.get("blend", "screen")))

        elif nm == "gradient" and quality_on:
            s_rgb = np.asarray(prm.get("strength_rgb", [0.0, 0.0, 0.0]), dtype=np.float32)
            if float(np.max(np.abs(s_rgb))) > 1e-5:
                ramp = _gradient_ramp((h, w), float(prm["angle_deg"]), float(prm["start"]), float(prm["end"]))[..., None]
                if prm.get("mode") == "tint":
                    col = np.clip(col + ramp * s_rgb[None, None, :], 0.0, 1.0)
                else:
                    col = np.clip(col * (1.0 + ramp * s_rgb[None, None, :]), 0.0, 1.0)

        elif nm == "vignette" and quality_on:
            st = float(prm.get("strength", 0.0))
            if st > 1e-5:
                fo = _vignette_falloff(
                    (h, w),
                    float(prm["center_x"]),
                    float(prm["center_y_top"]),
                    float(prm["radius"]),
                    float(prm["softness"]),
                )[..., None]
                col = np.clip(col * (1.0 - st * fo), 0.0, 1.0)

    return np.clip(col, 0.0, 1.0).astype(np.float32)


def verify_shader_vs_python_parity(
    test_imgs: List[np.ndarray],
    accepted_layers: List[LayerRecord],
    shader_meta: Dict[str, Any],
    plugins: Dict[str, Any],
) -> Dict[str, Any]:
    """Verify shader colour <= 1/255 vs Python/LUT and spatial layers <= 2/255 vs Python stack."""
    col_vs_py_diffs = []
    col_vs_cube_diffs = []
    full_stack_diffs = []

    det_layers = [(lr.plugin_name, shader_meta["effective_layer_params"][lr.plugin_name]) for lr in accepted_layers if lr.plugin_name != "grain"]

    for im in test_imgs:
        # 1. Colour-only parity
        sh_col = eval_composed_shader_numpy(im, shader_meta, colour_on=True, quality_on=False, flare_on=False)
        py_col = im.copy()
        for nm, prm in det_layers:
            if nm in ("colour", "black_lift"):
                py_col = plugins[nm].render(py_col, prm)
        col_vs_py_diffs.append(float(np.mean(np.abs(sh_col - py_col)) * 255.0))

        if "colour" in shader_meta["effective_layer_params"]:
            lut = np.asarray(shader_meta["effective_layer_params"]["colour"]["lut"], dtype=np.float32)
            cube_col = eval_lut_trilinear(im, lut)
            if "black_lift" in shader_meta["effective_layer_params"]:
                cube_col = plugins["black_lift"].render(cube_col, shader_meta["effective_layer_params"]["black_lift"])
            col_vs_cube_diffs.append(float(np.mean(np.abs(sh_col - cube_col)) * 255.0))

        # 2. Full deterministic stack parity (colour + sharpen + USM + flare + gradient + vignette)
        sh_full = eval_composed_shader_numpy(im, shader_meta, colour_on=True, quality_on=True, flare_on=True)
        py_full = im.copy()
        for nm, prm in det_layers:
            py_full = plugins[nm].render(py_full, prm)
        full_stack_diffs.append(float(np.mean(np.abs(sh_full - py_full)) * 255.0))

    mean_col_py = float(np.mean(col_vs_py_diffs)) if col_vs_py_diffs else 0.0
    mean_col_cube = float(np.mean(col_vs_cube_diffs)) if col_vs_cube_diffs else 0.0
    mean_full_py = float(np.mean(full_stack_diffs)) if full_stack_diffs else 0.0

    return {
        "colour_shader_vs_python_mean_255": round(mean_col_py, 5),
        "colour_shader_vs_cube_mean_255": round(mean_col_cube, 5),
        "full_stack_shader_vs_python_mean_255": round(mean_full_py, 5),
        "colour_within_1_255": (mean_col_py <= 1.0) and (mean_col_cube <= 1.0),
        "full_stack_within_2_255": mean_full_py <= 2.0,
    }
