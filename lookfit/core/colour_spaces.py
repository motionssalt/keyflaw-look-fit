"""Vectorized colour-space transforms (sRGB, linear RGB, Rec.709 luma, CIE L*a*b* D65)."""
from __future__ import annotations

import numpy as np


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """Convert gamma-encoded sRGB [0, 1] to linear light RGB."""
    x = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, np.power((x + 0.055) / 1.055, 2.4)).astype(np.float32)


def linear_to_srgb(lin: np.ndarray) -> np.ndarray:
    """Convert linear light RGB [0, 1] to gamma-encoded sRGB."""
    x = np.clip(np.asarray(lin, dtype=np.float32), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055).astype(np.float32)


def luma_rec709(rgb: np.ndarray) -> np.ndarray:
    """Compute Rec.709 luminance/luma from (..., 3) RGB."""
    return (
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    ).astype(np.float32)


_M_RGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float32,
)

_M_XYZ_TO_RGB = np.linalg.inv(_M_RGB_TO_XYZ.astype(np.float64)).astype(np.float32)
_D65_WHITE = np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert sRGB [0, 1] to CIE 1976 L*a*b* (D65 2-deg observer)."""
    lin = srgb_to_linear(rgb)
    xyz = lin @ _M_RGB_TO_XYZ.T
    xyz_n = xyz / _D65_WHITE
    delta = 6.0 / 29.0
    delta3 = delta ** 3
    f = np.where(xyz_n > delta3, np.cbrt(np.maximum(xyz_n, 0.0)), xyz_n / (3.0 * delta * delta) + 4.0 / 29.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1).astype(np.float32)


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """Convert CIE 1976 L*a*b* (D65) back to clamped sRGB [0, 1]."""
    lab_f = np.asarray(lab, dtype=np.float32)
    fy = (lab_f[..., 0] + 16.0) / 116.0
    fx = fy + lab_f[..., 1] / 500.0
    fz = fy - lab_f[..., 2] / 200.0
    delta = 6.0 / 29.0
    f = np.stack([fx, fy, fz], axis=-1)
    xyz_n = np.where(f > delta, f ** 3, 3.0 * delta * delta * (f - 4.0 / 29.0))
    xyz = np.maximum(xyz_n * _D65_WHITE, 0.0)
    lin = xyz @ _M_XYZ_TO_RGB.T
    return linear_to_srgb(lin)
