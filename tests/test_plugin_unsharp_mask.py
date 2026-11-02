"""Unit tests for UnsharpMaskPlugin (parameter recovery, threshold speckle gating, and GLSL ring parity)."""
from __future__ import annotations

import subprocess
from pathlib import Path
import cv2
import numpy as np

from lookfit.plugins.unsharp_mask import UnsharpMaskPlugin, get_isotropic_gaussian_ring_taps


def _make_anime_frame_with_subtle_flat_noise(h: int = 360, w: int = 540) -> np.ndarray:
    rng = np.random.default_rng(42)
    img = np.full((h, w, 3), 0.48, dtype=np.float32)
    cv2.circle(img, (180, 180), 95, (0.85, 0.68, 0.56), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (180, 180), 95, (0.08, 0.07, 0.09), 4, lineType=cv2.LINE_AA)
    cv2.rectangle(img, (320, 70), (480, 290), (0.20, 0.55, 0.78), -1)
    cv2.rectangle(img, (320, 70), (480, 290), (0.06, 0.06, 0.08), 3)
    img = cv2.GaussianBlur(img, (0, 0), 1.1)
    # Add tiny +/- 3/255 compression texture in flats so threshold gating matters!
    noise = cv2.GaussianBlur(rng.normal(0.0, 3.0 / 255.0, img.shape).astype(np.float32), (0, 0), 0.8)
    return np.clip(img + noise, 0.0, 1.0).astype(np.float32)


def test_unsharp_mask_recovers_known_params_and_shader_parity(tmp_path: Path):
    ref = _make_anime_frame_with_subtle_flat_noise()
    plugin = UnsharpMaskPlugin()
    true_params = {
        "amount": 95.0,
        "radius_frac": 0.012,
        "sigma_mult": 1.0,
        "threshold": 8.0,
        "gate_mode": "hard",
        "channel_mode": "rgb",
        "space": "srgb",
    }
    tgt = plugin.render(ref, true_params)

    ev = plugin.detect(ref, tgt)
    assert ev.status == "present"

    fitted, report = plugin.fit(ref, tgt)
    assert report.accepted_hint is True
    eff_sigma_true = true_params["radius_frac"] * true_params["sigma_mult"]
    eff_sigma_fit = fitted["radius_frac"] * fitted["sigma_mult"]
    assert abs(eff_sigma_fit - eff_sigma_true) < 0.0035
    assert abs(fitted["amount"] - 95.0) < 18.0
    assert fitted["threshold"] >= 2.5  # Must recover non-zero threshold gate to avoid flat noise!
    assert report.held_out_loss_after < 0.25 * report.held_out_loss_before

    # Verify 21-tap isotropic Gaussian ring stencil matches Python render within < 2/255!
    h, w = ref.shape[:2]
    taps = get_isotropic_gaussian_ring_taps(eff_sigma_fit)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    blur_ring = np.zeros_like(ref)
    for dx_h, dy_h, wt in taps:
        mx = np.clip(xx + dx_h * h, 0.0, w - 1.0)
        my = np.clip(yy + dy_h * h, 0.0, h - 1.0)
        blur_ring += wt * cv2.remap(ref, mx, my, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    diff = ref - blur_ring
    thr01 = fitted["threshold"] / 255.0
    if fitted["gate_mode"] == "soft":
        gated = np.sign(diff) * np.maximum(np.abs(diff) - thr01, 0.0)
    else:
        gated = np.where(np.abs(diff) <= thr01, 0.0, diff)
    pred_ring = np.clip(ref + (fitted["amount"] / 100.0) * gated, 0.0, 1.0)
    pred_py = plugin.render(ref, fitted)
    mean_err_255 = float(np.mean(np.abs(pred_ring - pred_py)) * 255.0)
    assert mean_err_255 < 1.0, f"Ring stencil vs cv2.GaussianBlur mean diff too high: {mean_err_255}"

    # Verify strict GLSL ES 1.00 compilation
    glsl = plugin.to_glsl(fitted)
    frag = (
        "#version 100\n"
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n"
        "uniform sampler2D uTexture;\nuniform vec2 uTexelSize;\nvarying vec2 vTex;\n"
        "vec3 msFetchGraded(vec2 uv) { vec4 c = texture2D(uTexture, clamp(uv, 0.0, 1.0)); return c.rgb / max(c.a, 0.0001); }\n"
        + glsl
        + "\nvoid main() {\n    vec4 c = texture2D(uTexture, clamp(vTex, 0.0, 1.0));\n"
        "    vec3 rgb = msApplyUnsharpMask(c.rgb / max(c.a, 0.0001), vTex, uTexelSize);\n"
        "    gl_FragColor = vec4(rgb * c.a, c.a);\n}\n"
    )
    f_path = tmp_path / "usm.frag"
    f_path.write_text(frag, encoding="utf-8")
    proc = subprocess.run(["glslangValidator", str(f_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"glslangValidator failed:\n{proc.stdout}\n{proc.stderr}"
