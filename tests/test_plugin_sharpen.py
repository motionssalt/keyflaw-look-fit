"""Unit tests for SharpenPlugin (parameter & kernel recovery + GLSL compile check)."""
from __future__ import annotations

import subprocess
from pathlib import Path
import cv2
import numpy as np

from lookfit.plugins.sharpen import SharpenPlugin


def _make_anime_test_frame(h: int = 320, w: int = 480) -> np.ndarray:
    img = np.full((h, w, 3), 0.42, dtype=np.float32)
    cv2.circle(img, (160, 160), 85, (0.82, 0.65, 0.52), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (160, 160), 85, (0.09, 0.08, 0.10), 3, lineType=cv2.LINE_AA)
    cv2.rectangle(img, (290, 65), (430, 255), (0.24, 0.58, 0.78), -1)
    cv2.rectangle(img, (290, 65), (430, 255), (0.07, 0.07, 0.09), 2)
    for k in range(8):
        cv2.line(img, (40 + k * 50, 30), (80 + k * 45, 290), (0.14, 0.14, 0.18), 2, lineType=cv2.LINE_AA)
    return cv2.GaussianBlur(img, (0, 0), 0.7).astype(np.float32)


def test_sharpen_recovers_known_params_and_labels_fitted(tmp_path: Path):
    ref = _make_anime_test_frame()
    plugin = SharpenPlugin()
    true_params = {"k": 0.85, "kernel": "binomial3x3", "channel_mode": "rgb"}
    tgt = plugin.render(ref, true_params)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"
    assert "fitted, not known" in ev.notes

    fitted, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    assert "fitted, not known" in plugin.describe(fitted)
    assert "fitted, not known" in report.notes
    assert fitted["kernel"] == "binomial3x3"
    assert abs(fitted["k"] - 0.85) < 0.08
    assert report.held_out_loss_after < 0.15 * report.held_out_loss_before

    glsl = plugin.to_glsl(fitted)
    assert "fitted, not known" in glsl
    frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nuniform vec2 uTexelSize;\nvarying vec2 vTex;\n"
        "vec3 msFetchGraded(vec2 uv) { vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0)); return c.rgb / max(c.a, 0.0001); }\n"
        + glsl
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = msApplySharpen(c.rgb / max(c.a, 0.0001), vTex, uTexelSize);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    f_path = tmp_path / "sharpen.frag"
    f_path.write_text(frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(f_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"
