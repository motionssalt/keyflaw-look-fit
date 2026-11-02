"""Unit tests for ColourPlugin: synthetic hue-dependent 3D grade recovery, .cube roundtrip, and GLSL compile."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
import numpy as np

from lookfit.core.metrics import ciede2000_rgb
from lookfit.export.cube import eval_lut_trilinear, read_cube_file, write_cube_file
from lookfit.plugins.colour import ColourPlugin, eval_shader_compressed_colour


def _synthetic_hue_dependent_grade(rgb: np.ndarray) -> np.ndarray:
    """Apply a known non-trivial S-curve + cross-matrix + hue-dependent teal-orange shift."""
    x = np.clip(rgb, 0.0, 1.0)
    # S-curve
    sc = x * x * (3.0 - 2.0 * x)
    s = 0.35 * x + 0.65 * sc
    # Cross-talk matrix
    M = np.array(
        [
            [1.06, -0.04, -0.02],
            [-0.02, 1.02, 0.02],
            [-0.05, 0.03, 1.08],
        ],
        dtype=np.float32,
    )
    y = s @ M.T + np.array([0.01, -0.01, 0.03], dtype=np.float32)
    # Hue-dependent shadow teal / highlight warmth
    luma = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    shadow_w = (1.0 - luma) ** 2
    high_w = luma ** 2
    y[..., 2] += 0.08 * shadow_w
    y[..., 0] -= 0.04 * shadow_w
    y[..., 0] += 0.06 * high_w
    y[..., 2] -= 0.05 * high_w
    return np.clip(y, 0.0, 1.0).astype(np.float32)


def test_colour_plugin_recovers_known_3d_grade_and_compiles_glsl(tmp_path: Path):
    # Create smooth multi-patch colour test frame (384x512) covering diverse hues/tones
    h, w = 384, 512
    rng = np.random.default_rng(2026)
    # Build smooth 32x32 flat colour tiles across gamut
    tiles_y, tiles_x = h // 32, w // 32
    tile_cols = rng.uniform(0.02, 0.98, size=(tiles_y, tiles_x, 3)).astype(np.float32)
    ref = np.repeat(np.repeat(tile_cols, 32, axis=0), 32, axis=1)
    tgt = _synthetic_hue_dependent_grade(ref)

    plugin = ColourPlugin()
    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"
    assert ev.score > 3.0

    params, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    assert report.held_out_loss_after < 0.75
    assert report.held_out_loss_after < 0.20 * report.held_out_loss_before

    pred_shader = plugin.render(ref, params)
    de_after = ciede2000_rgb(pred_shader, tgt)
    assert de_after["median"] < 0.50

    # Verify shader compression vs full .cube LUT is within 1/255 mean
    lut = np.asarray(params["lut"], dtype=np.float32)
    pred_cube = eval_lut_trilinear(ref, lut)
    diff_255 = np.abs(pred_shader - pred_cube) * 255.0
    assert float(diff_255.mean()) < 0.60

    # Verify .cube export/import roundtrip
    cube_path = tmp_path / "test_look.cube"
    write_cube_file(cube_path, lut, title="TestLUT")
    lut_rt = read_cube_file(cube_path)
    assert np.max(np.abs(lut - lut_rt)) < 2e-5

    # Verify strict GLSL ES 1.00 compilation with glslangValidator (#version 100 prepended)
    glsl_snippet = plugin.to_glsl(params)
    full_frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nvarying vec2 vTex;\n"
        + glsl_snippet
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = c.rgb / max(c.a, 0.0001);\n"
        "    rgb = msApplyColour(rgb);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    frag_file = tmp_path / "test_colour.frag"
    frag_file.write_text(full_frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(frag_file)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"
