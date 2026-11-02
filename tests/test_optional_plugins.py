"""Unit tests for optional plugins: black_lift, chromatic_aberration, and flicker."""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np

from lookfit.plugins.black_lift import BlackLiftPlugin
from lookfit.plugins.chromatic_aberration import ChromaticAberrationPlugin
from lookfit.plugins.flicker import FlickerPlugin


def test_black_lift_recovery_and_glsl(tmp_path: Path):
    h, w = 288, 384
    ref = np.zeros((h, w, 3), dtype=np.float32)
    ref[:, : w // 3] = 0.02
    ref[:, w // 3 : 2 * w // 3] = 0.35
    ref[:, 2 * w // 3 :] = 0.75
    ref = cv2.GaussianBlur(ref, (0, 0), 1.5)

    plugin = BlackLiftPlugin()
    tgt = plugin.render(ref, {"lift_rgb": [0.035, 0.040, 0.055]})

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"
    fitted, rep = plugin.fit(ref, tgt)
    assert rep.accepted_hint is True
    assert np.max(np.abs(np.array(fitted["lift_rgb"]) - np.array([0.035, 0.040, 0.055]))) < 0.004

    assert plugin.detect(ref, ref).status == "absent"

    frag = (
        "#version 100\nprecision highp float;\nuniform sampler2D uTexture;\nvarying vec2 vTex;\n"
        + plugin.to_glsl(fitted)
        + "\nvoid main() { vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0)); "
        "vec3 rgb = msApplyBlackLift(c.rgb / max(c.a, 0.0001)); gl_FragColor = vec4(rgb * c.a, c.a); }\n"
    )
    fp = tmp_path / "bl.frag"
    fp.write_text(frag, encoding="utf-8")
    assert subprocess.run(["glslangValidator", str(fp)], capture_output=True).returncode == 0


def test_chromatic_aberration_recovery_and_glsl(tmp_path: Path):
    h, w = 320, 480
    ref = np.full((h, w, 3), 0.25, dtype=np.float32)
    for r in (45, 95, 145, 195):
        cv2.circle(ref, (w // 2, h // 2), r, (0.88, 0.86, 0.84), 4, lineType=cv2.LINE_AA)
    for x in range(40, w - 30, 55):
        cv2.line(ref, (x, 20), (x, h - 20), (0.85, 0.82, 0.80), 3, lineType=cv2.LINE_AA)
    ref = cv2.GaussianBlur(ref, (0, 0), 1.0)

    plugin = ChromaticAberrationPlugin()
    true_p = {"k_red": 0.0085, "k_blue": -0.0095, "center_x": 0.50, "center_y_top": 0.50}
    tgt = plugin.render(ref, true_p)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"
    fitted, rep = plugin.fit(ref, tgt)
    assert rep.accepted_hint is True
    assert abs(fitted["k_red"] - 0.0085) < 0.0025
    assert abs(fitted["k_blue"] - (-0.0095)) < 0.0025
    assert plugin.detect(ref, ref).status == "absent"

    frag = (
        "#version 100\nprecision highp float;\nuniform sampler2D uTexture;\nuniform vec2 uTexelSize;\nvarying vec2 vTex;\n"
        "vec3 msFetchGraded(vec2 uv) { vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0)); return c.rgb / max(c.a, 0.0001); }\n"
        + plugin.to_glsl(fitted)
        + "\nvoid main() { vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0)); "
        "vec3 rgb = msApplyChromaticAberration(c.rgb / max(c.a, 0.0001), vTex, uTexelSize); gl_FragColor = vec4(rgb * c.a, c.a); }\n"
    )
    fp = tmp_path / "ca.frag"
    fp.write_text(frag, encoding="utf-8")
    assert subprocess.run(["glslangValidator", str(fp)], capture_output=True).returncode == 0


def test_flicker_recovery_and_rejection(tmp_path: Path):
    rng = np.random.default_rng(55)
    refs = []
    tgts = []
    gains = [0.91, 1.08, 0.93, 1.07]
    for g in gains:
        tiles = rng.uniform(0.2, 0.7, size=(6, 8, 3)).astype(np.float32)
        im = cv2.GaussianBlur(np.repeat(np.repeat(tiles, 48, axis=0), 48, axis=1), (0, 0), 2.0)
        refs.append(im)
        tgts.append(np.clip(im * g, 0.0, 1.0).astype(np.float32))

    plugin = FlickerPlugin()
    ev = plugin.detect(refs, tgts)
    assert ev.status == "present"
    fitted, rep = plugin.fit(refs, tgts)
    assert rep.accepted_hint is True
    assert fitted["amplitude"] > 0.06
    assert plugin.detect(refs[:2], tgts[:2]).status == "absent"

    frag = (
        "#version 100\nprecision highp float;\nuniform sampler2D uTexture;\nuniform float uTime;\nvarying vec2 vTex;\n"
        + plugin.to_glsl(fitted)
        + "\nvoid main() { vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0)); "
        "vec3 rgb = msApplyFlicker(c.rgb / max(c.a, 0.0001), uTime); gl_FragColor = vec4(rgb * c.a, c.a); }\n"
    )
    fp = tmp_path / "flicker.frag"
    fp.write_text(frag, encoding="utf-8")
    assert subprocess.run(["glslangValidator", str(fp)], capture_output=True).returncode == 0
