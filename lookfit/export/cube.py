"""Iridas .cube 3D LUT writer, reader, and trilinear/tetrahedral evaluators."""
from __future__ import annotations

from pathlib import Path
import numpy as np


def eval_lut_trilinear(img_rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Evaluate an (N, N, N, 3) 3D LUT (indexed [r, g, b, c]) via trilinear interpolation."""
    x = np.clip(np.asarray(img_rgb, dtype=np.float32), 0.0, 1.0)
    orig_shape = x.shape
    pts = x.reshape(-1, 3)
    n = lut.shape[0]
    s = pts * float(n - 1)
    idx0 = np.clip(np.floor(s).astype(np.int32), 0, n - 2)
    f = s - idx0.astype(np.float32)

    r0, g0, b0 = idx0[:, 0], idx0[:, 1], idx0[:, 2]
    r1, g1, b1 = r0 + 1, g0 + 1, b0 + 1
    fr, fg, fb = f[:, 0:1], f[:, 1:2], f[:, 2:3]

    c000 = lut[r0, g0, b0]
    c100 = lut[r1, g0, b0]
    c010 = lut[r0, g1, b0]
    c110 = lut[r1, g1, b0]
    c001 = lut[r0, g0, b1]
    c101 = lut[r1, g0, b1]
    c011 = lut[r0, g1, b1]
    c111 = lut[r1, g1, b1]

    c00 = c000 + fr * (c100 - c000)
    c10 = c010 + fr * (c110 - c010)
    c01 = c001 + fr * (c101 - c001)
    c11 = c011 + fr * (c111 - c011)

    c0 = c00 + fg * (c10 - c00)
    c1 = c01 + fg * (c11 - c01)
    out = c0 + fb * (c1 - c0)
    return out.reshape(orig_shape).astype(np.float32)


def eval_lut_tetrahedral(img_rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Evaluate an (N, N, N, 3) 3D LUT (indexed [r, g, b, c]) via exact tetrahedral interpolation."""
    x = np.clip(np.asarray(img_rgb, dtype=np.float32), 0.0, 1.0)
    orig_shape = x.shape
    pts = x.reshape(-1, 3)
    n = lut.shape[0]
    s = pts * float(n - 1)
    idx0 = np.clip(np.floor(s).astype(np.int32), 0, n - 2)
    f = s - idx0.astype(np.float32)

    r0, g0, b0 = idx0[:, 0], idx0[:, 1], idx0[:, 2]
    r1, g1, b1 = r0 + 1, g0 + 1, b0 + 1
    fr, fg, fb = f[:, 0:1], f[:, 1:2], f[:, 2:3]

    c000 = lut[r0, g0, b0]
    c100 = lut[r1, g0, b0]
    c010 = lut[r0, g1, b0]
    c110 = lut[r1, g1, b0]
    c001 = lut[r0, g0, b1]
    c101 = lut[r1, g0, b1]
    c011 = lut[r0, g1, b1]
    c111 = lut[r1, g1, b1]

    # 6 sub-tetrahedra ordered by relative magnitude of (fr, fg, fb)
    out = np.empty_like(pts, dtype=np.float32)

    m1 = (fr >= fg) & (fg >= fb)
    m2 = (fr >= fb) & (fb > fg)
    m3 = (fb > fr) & (fr >= fg)
    m4 = (fg > fr) & (fr >= fb)
    m5 = (fg >= fb) & (fb > fr)
    m6 = ~(m1 | m2 | m3 | m4 | m5)

    for mask, expr in [
        (m1[:, 0], lambda: c000 + fr * (c100 - c000) + fg * (c110 - c100) + fb * (c111 - c110)),
        (m2[:, 0], lambda: c000 + fr * (c100 - c000) + fb * (c101 - c100) + fg * (c111 - c101)),
        (m3[:, 0], lambda: c000 + fb * (c001 - c000) + fr * (c101 - c001) + fg * (c111 - c101)),
        (m4[:, 0], lambda: c000 + fg * (c010 - c000) + fr * (c110 - c010) + fb * (c111 - c110)),
        (m5[:, 0], lambda: c000 + fg * (c010 - c000) + fb * (c011 - c010) + fr * (c111 - c011)),
        (m6[:, 0], lambda: c000 + fb * (c001 - c000) + fg * (c011 - c001) + fr * (c111 - c011)),
    ]:
        if np.any(mask):
            val = expr()
            out[mask] = val[mask]

    return out.reshape(orig_shape).astype(np.float32)


def write_cube_file(path: str | Path, lut: np.ndarray, title: str = "Keyflaw_LookFit_LUT") -> None:
    """Write an (N, N, N, 3) LUT (indexed [r, g, b, c]) in standard Iridas .cube order (R fastest)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = int(lut.shape[0])
    assert lut.shape == (n, n, n, 3), f"Expected (N,N,N,3), got {lut.shape}"
    clipped = np.clip(lut, 0.0, 1.0)
    lines = [
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {n}",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
    ]
    # Standard .cube ordering: R changes fastest, then G, then B
    for ib in range(n):
        for ig in range(n):
            for ir in range(n):
                r, g, b = clipped[ir, ig, ib]
                lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_cube_file(path: str | Path) -> np.ndarray:
    """Read a standard Iridas .cube 3D LUT into an (N, N, N, 3) float32 array [r, g, b, c]."""
    text = Path(path).read_text(encoding="utf-8")
    size = None
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("TITLE") or line.startswith("DOMAIN_"):
            continue
        if line.startswith("LUT_3D_SIZE"):
            size = int(line.split()[1])
            continue
        parts = line.split()
        if len(parts) == 3:
            rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
    if size is None or len(rows) != size ** 3:
        raise ValueError(f"Invalid .cube LUT: size={size}, rows={len(rows)}")
    arr = np.array(rows, dtype=np.float32).reshape(size, size, size, 3)  # [ib, ig, ir, c]
    return np.transpose(arr, (2, 1, 0, 3)).copy()
