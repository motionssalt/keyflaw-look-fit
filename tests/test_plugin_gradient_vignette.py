"""Unit tests for GradientPlugin and VignettePlugin (parameter recovery, yTop GLSL parity, glslangValidator)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np

from lookfit.plugins.gradient import GradientPlugin
from lookfit.plugins.vignette import VignettePlugin


def _make_base_scene(h: int = 360, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(123)
    tiles = rng.uniform(0.25, 0.78, size=(h // 40, w // 40, 3)).astype(np.float32)
    img = np.repeat(np.repeat(tiles, 40, axis=0), 40, axis=1)
    return cv2.GaussianBlur(img, (0, 0), 3.0).astype(np.float32)


def test_gradient_recovers_known_params_and_glsl_parity(tmp_path: Path):
    ref = _make_base_scene()
    plugin = GradientPlugin()
    true_params = {
        "angle_deg": 90.0,
        "start": 0.18,
        "end": 0.84,
        "mode": "multiply",
        "strength_rgb": [-0.28, -0.22, -0.10],
    }
    tgt = plugin.render(ref, true_params)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"

    fitted, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    assert report.held_out_loss_after < 0.20 * report.held_out_loss_before
    pred = plugin.render(ref, fitted)
    assert float(np.mean(np.abs(pred - tgt)) * 255.0) < 0.8

    glsl = plugin.to_glsl(fitted)
    assert "yTop = 1.0 - uv.y" in glsl
    frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nvarying vec2 vTex;\n"
        + glsl
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = msApplyGradient(c.rgb / max(c.a, 0.0001), vTex);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    f_path = tmp_path / "gradient.frag"
    f_path.write_text(frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(f_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"


def test_vignette_recovers_known_params_and_glsl_parity(tmp_path: Path):
    ref = _make_base_scene()
    plugin = VignettePlugin()
    true_params = {
        "center_x": 0.50,
        "center_y_top": 0.50,
        "radius": 0.42,
        "softness": 0.55,
        "strength": 0.36,
    }
    tgt = plugin.render(ref, true_params)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"

    fitted, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    assert report.held_out_loss_after < 0.20 * report.held_out_loss_before
    pred = plugin.render(ref, fitted)
    assert float(np.mean(np.abs(pred - tgt)) * 255.0) < 0.8

    glsl = plugin.to_glsl(fitted)
    assert "yTop = 1.0 - uv.y" in glsl
    frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nuniform vec2 uTexelSize;\nvarying vec2 vTex;\n"
        + glsl
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = msApplyVignette(c.rgb / max(c.a, 0.0001), vTex, uTexelSize);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    f_path = tmp_path / "vignette.frag"
    f_path.write_text(frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(f_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"
