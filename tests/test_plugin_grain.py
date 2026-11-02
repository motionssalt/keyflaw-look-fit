"""Unit tests for GrainPlugin: statistics-matching parameter recovery, blockiness rejection, and GLSL compile."""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np

from lookfit.plugins.grain import GrainPlugin


def _make_smooth_tonal_scene(h: int = 384, w: int = 512) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.float32)
    # Large flat tonal bands (dark, midtone, bright) + a few clean geometric edges
    img[:, : w // 3] = np.array([0.14, 0.16, 0.20], dtype=np.float32)
    img[:, w // 3 : 2 * w // 3] = np.array([0.48, 0.46, 0.44], dtype=np.float32)
    img[:, 2 * w // 3 :] = np.array([0.82, 0.80, 0.76], dtype=np.float32)
    cv2.circle(img, (w // 2, h // 2), 65, (0.30, 0.55, 0.70), -1, lineType=cv2.LINE_AA)
    return cv2.GaussianBlur(img, (0, 0), 1.0).astype(np.float32)


def test_grain_recovers_statistics_from_independent_seed_and_rejects_blocks(tmp_path: Path):
    ref = _make_smooth_tonal_scene()
    plugin = GrainPlugin()

    true_params = {
        "amount_255": 4.8,
        "size_frac": 0.0015,
        "shadow_weight": 0.70,
        "midtone_weight": 1.00,
        "highlight_weight": 0.50,
        "chroma_mix": 0.0,
        "seed": 99991,  # Completely independent random realization from fitter!
    }
    tgt = plugin.render(ref, true_params)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"

    fitted, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    assert abs(fitted["amount_255"] - 4.8) < 1.2
    assert abs(fitted["size_frac"] - 0.0015) < 0.0012
    assert fitted["chroma_mix"] < 0.25
    assert report.held_out_loss_after < 0.50 * report.held_out_loss_before

    # Clean pair -> must report 'not provable' and NOT add grain
    ev_clean = plugin.detect(ref, ref)
    assert ev_clean.status == "not_provable"
    assert "not provable" in ev_clean.notes
    p_clean, rep_clean = plugin.fit(ref, ref)
    assert rep_clean.accepted_hint is False
    assert float(p_clean["amount_255"]) == 0.0
    assert "not provable" in plugin.describe(p_clean)

    # 8x8 DCT blocky artifacts -> must distinguish from film grain and report 'not provable'
    rng = np.random.default_rng(77)
    block_grid = rng.normal(0.0, 4.5 / 255.0, size=(ref.shape[0] // 8, ref.shape[1] // 8, 1)).astype(np.float32)
    block_noise = np.repeat(np.repeat(block_grid, 8, axis=0), 8, axis=1)
    tgt_blocky = np.clip(ref + block_noise, 0.0, 1.0).astype(np.float32)
    ev_blk = plugin.detect(ref, tgt_blocky)
    assert ev_blk.status == "not_provable"
    assert "not provable" in ev_blk.notes

    # Compile strict GLSL ES 1.00
    glsl = plugin.to_glsl(fitted)
    frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nuniform vec2 uTexelSize;\nuniform float uTime;\nvarying vec2 vTex;\n"
        + glsl
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = msApplyGrain(c.rgb / max(c.a, 0.0001), vTex, uTexelSize, uTime);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    f_path = tmp_path / "grain.frag"
    f_path.write_text(frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(f_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"
