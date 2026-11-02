"""Unit tests for HazeFlarePlugin: recovery of real bloom, rejection of absent/overlay, and GLSL compile."""
from __future__ import annotations

import subprocess
from pathlib import Path
import cv2
import numpy as np

from lookfit.plugins.haze_flare import HazeFlarePlugin


def _make_scene_with_bright_highlights(h: int = 320, w: int = 480) -> np.ndarray:
    img = np.full((h, w, 3), 0.16, dtype=np.float32)
    # Midtone shapes (below bloom threshold)
    cv2.rectangle(img, (40, 120), (220, 290), (0.35, 0.28, 0.32), -1)
    # Bright cyan-white energy burst & warm sun highlight in upper-right quadrant
    cv2.circle(img, (355, 95), 36, (0.96, 0.94, 0.85), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (295, 165), 22, (0.65, 0.92, 0.98), -1, lineType=cv2.LINE_AA)
    return cv2.GaussianBlur(img, (0, 0), 1.2).astype(np.float32)


def test_haze_flare_recovers_real_bloom_and_passes_three_mandatory_tests(tmp_path: Path):
    ref = _make_scene_with_bright_highlights()
    plugin = HazeFlarePlugin()

    true_params = {
        "threshold": 0.62,
        "softness": 0.10,
        "scales_frac": [0.008, 0.022, 0.055],
        "scale_weights": [0.45, 0.35, 0.20],
        "channel_widths": [1.0, 1.2, 1.4],
        "tint": [0.95, 0.98, 1.0],
        "intensity": 0.85,
        "blend": "screen",
    }
    tgt = plugin.render(ref, true_params)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"

    fitted, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    tests_info = report.diagnostics["real_bloom_tests"]
    assert tests_info["zero_on_black_passed"] is True
    assert tests_info["bright_shape_passed"] is True
    assert tests_info["mismatched_scene_passed"] is True
    assert report.held_out_loss_after < 0.30 * report.held_out_loss_before

    # Test 2: When no bloom is present (or only tiny noise), plugin must report 'absent'
    ev_clean = plugin.detect(ref, ref)
    assert ev_clean.status == "absent"
    p_abs, rep_abs = plugin.fit(ref, ref)
    assert rep_abs.accepted_hint is False
    assert float(p_abs["intensity"]) == 0.0
    assert "absent" in plugin.describe(p_abs)

    # Test 3: A painted uniform/corner overlay uncorrelated with scene highlights must be REJECTED!
    yy, xx = np.mgrid[0:ref.shape[0], 0:ref.shape[1]].astype(np.float32)
    fake_overlay = np.clip(ref + 0.14 * np.exp(-((xx - 60.0) ** 2 + (yy - 260.0) ** 2) / (2.0 * 90.0 ** 2))[..., None], 0.0, 1.0)
    p_fake, rep_fake = plugin.fit(ref, fake_overlay)
    assert rep_fake.accepted_hint is False

    # Test 4: Strict GLSL ES 1.00 compile check & tap count <= 30
    assert plugin.glsl_taps(fitted) <= 30
    glsl = plugin.to_glsl(fitted)
    frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nuniform vec2 uTexelSize;\nvarying vec2 vTex;\n"
        "vec3 msFetchGraded(vec2 uv) { vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0)); return c.rgb / max(c.a, 0.0001); }\n"
        + glsl
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = msApplyHazeFlare(c.rgb / max(c.a, 0.0001), vTex, uTexelSize);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    f_path = tmp_path / "haze_flare.frag"
    f_path.write_text(frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(f_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"
