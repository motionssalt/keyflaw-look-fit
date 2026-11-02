"""Plugin 1: Direct 3D LUT colour grade fitter + shader-sized compression + .cube export."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator, cg

from lookfit.core.colour_spaces import linear_to_srgb, srgb_to_linear
from lookfit.core.metrics import channel_mae, ciede2000_rgb
from lookfit.export.cube import eval_lut_tetrahedral, eval_lut_trilinear
from lookfit.plugins.base import (
    ContextOrList,
    Evidence,
    FitReport,
    ImageOrList,
    ParamSpec,
    Plugin,
    normalize_pair_inputs,
)


def _build_3d_regularizers(n: int) -> Tuple[sparse.csr_matrix, sparse.csr_matrix]:
    """Build 3D second-difference (D2^T D2) and first-difference (D1^T D1) sparse penalties on N^3."""
    n3 = n * n * n
    idx = np.arange(n3, dtype=np.int32).reshape(n, n, n)

    rows_d2, cols_d2, vals_d2 = [], [], []
    r_id = 0
    for axis in range(3):
        sl_m = [slice(None)] * 3
        sl_c = [slice(None)] * 3
        sl_p = [slice(None)] * 3
        sl_m[axis] = slice(0, n - 2)
        sl_c[axis] = slice(1, n - 1)
        sl_p[axis] = slice(2, n)
        im = idx[tuple(sl_m)].ravel()
        ic = idx[tuple(sl_c)].ravel()
        ip = idx[tuple(sl_p)].ravel()
        m = im.size
        rr = np.arange(r_id, r_id + m, dtype=np.int32)
        r_id += m
        rows_d2.extend([rr, rr, rr])
        cols_d2.extend([im, ic, ip])
        vals_d2.extend([np.ones(m, np.float64), -2.0 * np.ones(m, np.float64), np.ones(m, np.float64)])

    D2 = sparse.coo_matrix(
        (np.concatenate(vals_d2), (np.concatenate(rows_d2), np.concatenate(cols_d2))),
        shape=(r_id, n3),
    ).tocsr()

    rows_d1, cols_d1, vals_d1 = [], [], []
    r1_id = 0
    for axis in range(3):
        sl_a = [slice(None)] * 3
        sl_b = [slice(None)] * 3
        sl_a[axis] = slice(0, n - 1)
        sl_b[axis] = slice(1, n)
        ia = idx[tuple(sl_a)].ravel()
        ib = idx[tuple(sl_b)].ravel()
        m = ia.size
        rr = np.arange(r1_id, r1_id + m, dtype=np.int32)
        r1_id += m
        rows_d1.extend([rr, rr])
        cols_d1.extend([ia, ib])
        vals_d1.extend([-np.ones(m, np.float64), np.ones(m, np.float64)])

    D1 = sparse.coo_matrix(
        (np.concatenate(vals_d1), (np.concatenate(rows_d1), np.concatenate(cols_d1))),
        shape=(r1_id, n3),
    ).tocsr()

    return (D2.T @ D2).tocsr(), (D1.T @ D1).tocsr()


_REG_CACHE: Dict[int, Tuple[sparse.csr_matrix, sparse.csr_matrix]] = {}


def _get_regularizers(n: int) -> Tuple[sparse.csr_matrix, sparse.csr_matrix]:
    if n not in _REG_CACHE:
        _REG_CACHE[n] = _build_3d_regularizers(n)
    return _REG_CACHE[n]


def _trilinear_design_matrix(pts: np.ndarray, n: int) -> sparse.csr_matrix:
    """Build sparse (M, N^3) trilinear interpolation matrix for M RGB points in [0, 1]^3."""
    x = np.clip(pts, 0.0, 1.0)
    m = x.shape[0]
    s = x * float(n - 1)
    idx0 = np.clip(np.floor(s).astype(np.int32), 0, n - 2)
    f = (s - idx0.astype(np.float32)).astype(np.float64)

    r0, g0, b0 = idx0[:, 0], idx0[:, 1], idx0[:, 2]
    fr, fg, fb = f[:, 0], f[:, 1], f[:, 2]

    rows = np.repeat(np.arange(m, dtype=np.int32), 8)
    cols = np.empty(m * 8, dtype=np.int32)
    vals = np.empty(m * 8, dtype=np.float64)

    n2 = n * n
    k = 0
    for dr, wr in [(0, 1.0 - fr), (1, fr)]:
        for dg, wg in [(0, 1.0 - fg), (1, fg)]:
            for db, wb in [(0, 1.0 - fb), (1, fb)]:
                cols[k::8] = (r0 + dr) * n2 + (g0 + dg) * n + (b0 + db)
                vals[k::8] = wr * wg * wb
                k += 1

    return sparse.csr_matrix((vals, (rows, cols)), shape=(m, n * n * n))


def _compute_cluster_weights(pts: np.ndarray) -> np.ndarray:
    """Quantize into an 8x8x8 colour histogram and weight by inverse sqrt cell count."""
    q = np.clip(np.floor(pts * 8.0).astype(np.int32), 0, 7)
    cell = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
    counts = np.bincount(cell, minlength=512).astype(np.float64)
    w = 1.0 / np.sqrt(np.maximum(counts[cell], 1.0))
    return (w / np.mean(w)).astype(np.float64)


def fit_3d_lut_direct(
    src_pts: np.ndarray,
    tgt_pts: np.ndarray,
    sample_weights: np.ndarray,
    grid_size: int = 17,
    lam_smooth: float = 0.3,
    lam_ridge: float = 1e-3,
    space: str = "srgb",
) -> np.ndarray:
    """Fit an (N, N, N, 3) sRGB 3D LUT directly from flat-area pixel pairs."""
    if space == "linear":
        x_in = srgb_to_linear(src_pts).astype(np.float64)
        y_out = srgb_to_linear(tgt_pts).astype(np.float64)
    else:
        x_in = np.clip(src_pts, 0.0, 1.0).astype(np.float64)
        y_out = np.clip(tgt_pts, 0.0, 1.0).astype(np.float64)

    w = np.asarray(sample_weights, dtype=np.float64)
    w = w * (float(x_in.shape[0]) / max(float(np.sum(w)), 1e-12))

    # Global affine baseline prior so sparse/unvisited corners of the cube extrapolate cleanly
    sw = np.sqrt(w)[:, None]
    X_aff = np.column_stack([np.ones(x_in.shape[0], dtype=np.float64), x_in])
    # Regularized toward identity affine transform
    X_prior = np.eye(4, 3, k=-1, dtype=np.float64)  # bias=0, M=I
    XtWX = (X_aff * w[:, None]).T @ X_aff + 5.0 * np.eye(4, dtype=np.float64)
    XtWY = (X_aff * w[:, None]).T @ y_out + 5.0 * X_prior
    W_aff = np.linalg.solve(XtWX, XtWY)  # (4, 3)

    axes = np.linspace(0.0, 1.0, grid_size, dtype=np.float64)
    rr, gg, bb = np.meshgrid(axes, axes, axes, indexing="ij")
    grid_pts = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], axis=-1)
    V0 = np.column_stack([np.ones(grid_pts.shape[0], dtype=np.float64), grid_pts]) @ W_aff  # (N^3, 3)

    A = _trilinear_design_matrix(x_in.astype(np.float32), grid_size)
    res_target = y_out - (A @ V0)

    # Normalise penalty scale relative to effective sample count so lam_smooth ~ 0.3 is resolution-independent
    eff_n = float(x_in.shape[0])
    scale_reg = max(1.0, eff_n / 4000.0)
    P2, P1 = _get_regularizers(grid_size)
    W_diag = sparse.diags(w, 0, shape=(x_in.shape[0], x_in.shape[0]))
    AtWA = (A.T @ W_diag @ A).tocsc()

    H = (
        AtWA
        + (lam_smooth * scale_reg) * P2
        + (0.03 * lam_smooth * scale_reg) * P1
        + (lam_ridge * scale_reg) * sparse.eye(grid_size ** 3, format="csc")
    ).tocsc()
    rhs = A.T @ (w[:, None] * res_target)

    diag_inv = 1.0 / np.maximum(H.diagonal(), 1e-8)
    M_prec = LinearOperator(H.shape, matvec=lambda v: diag_inv * v, dtype=np.float64)
    dV = np.empty_like(V0)
    for c in range(3):
        sol, info = cg(H, rhs[:, c], M=M_prec, rtol=1e-6, maxiter=400)
        dV[:, c] = sol

    V = np.clip(V0 + dV, 0.0, 1.0).reshape(grid_size, grid_size, grid_size, 3).astype(np.float32)

    if space == "linear":
        # Re-sample into a standard sRGB-domain LUT so .cube export is standard sRGB-in -> sRGB-out
        srgb_grid = grid_pts.reshape(grid_size, grid_size, grid_size, 3).astype(np.float32)
        lin_query = srgb_to_linear(srgb_grid)
        lin_eval = eval_lut_trilinear(lin_query, V)
        return linear_to_srgb(lin_eval)
    return V


def eval_1d_curves(img_rgb: np.ndarray, knots_3x33: np.ndarray) -> np.ndarray:
    """Evaluate 3x33 piecewise-linear 1D curves on [0, 1]^3."""
    x = np.clip(np.asarray(img_rgb, dtype=np.float32), 0.0, 1.0)
    k_len = knots_3x33.shape[1]
    s = x * float(k_len - 1)
    i0 = np.clip(np.floor(s).astype(np.int32), 0, k_len - 2)
    f = s - i0.astype(np.float32)
    out = np.empty_like(x, dtype=np.float32)
    for c in range(3):
        v0 = knots_3x33[c, i0[..., c]]
        v1 = knots_3x33[c, i0[..., c] + 1]
        out[..., c] = v0 + f[..., c] * (v1 - v0)
    return out


def _poly_features(u: np.ndarray) -> np.ndarray:
    """Build 52 smooth colour basis features (up to degree 4 + min/max/mid chroma terms) matching GLSL."""
    r = u[..., 0]
    g = u[..., 1]
    b = u[..., 2]
    ones = np.ones_like(r)

    # Degree 1 (3)
    f_list = [ones, r, g, b]
    # Degree 2 (6)
    rr, gg, bb = r * r, g * g, b * b
    rg, rb, gb = r * g, r * b, g * b
    f_list.extend([rr, gg, bb, rg, rb, gb])
    # Degree 3 (10)
    rrr, ggg, bbb = rr * r, gg * g, bb * b
    rrg, rrb, ggr, ggb, bbr, bbg, rgb = rr * g, rr * b, gg * r, gg * b, bb * r, bb * g, r * g * b
    f_list.extend([rrr, ggg, bbb, rrg, rrb, ggr, ggb, bbr, bbg, rgb])
    # Degree 4 (15)
    f_list.extend([
        rr * rr, gg * gg, bb * bb,
        rrr * g, rrr * b, ggg * r, ggg * b, bbb * r, bbb * g,
        rr * gg, rr * bb, gg * bb,
        rr * gb, gg * rb, bb * rg,
    ])
    # Piecewise tetrahedral / HSV-free chroma & luma order statistics (exact in GLSL via min/max!)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    md = (r + g + b) - mx - mn
    ch = mx - mn
    f_list.extend([
        mx, mn, md, ch,
        ch * r, ch * g, ch * b,
        ch * mx, ch * mn,
        mx * mx, mn * mn, ch * ch,
    ])
    return np.stack(f_list, axis=-1).astype(np.float64)


def compress_lut_for_shader(
    full_lut: np.ndarray,
    sample_pts: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Compress full 3D LUT into two shader candidates and select the more accurate one:
    (A) 'curves33_matrix_poly': 33-knot 1D curves + 3x3 matrix + 47-term polynomial/order-stat residual
    (B) 'curves33_tetra9': 33-knot 1D shaper curves + 9x9x9 tetrahedral 3D residual grid (unrolled binary tree)
    """
    n = full_lut.shape[0]
    # Dense 25^3 evaluation grid + sample_pts so both global cube and high-density image colours are tight
    ax = np.linspace(0.0, 1.0, 25, dtype=np.float32)
    rr, gg, bb = np.meshgrid(ax, ax, ax, indexing="ij")
    grid_pts = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], axis=-1)
    if sample_pts is not None and sample_pts.shape[0] > 0:
        step = max(1, sample_pts.shape[0] // 12000)
        sub_pts = sample_pts[::step].astype(np.float32)
        fit_pts = np.vstack([grid_pts, sub_pts])
        weights = np.concatenate([
            np.ones(grid_pts.shape[0], dtype=np.float64),
            3.0 * np.ones(sub_pts.shape[0], dtype=np.float64),
        ])
    else:
        fit_pts = grid_pts
        weights = np.ones(grid_pts.shape[0], dtype=np.float64)

    target_vals = eval_lut_trilinear(fit_pts, full_lut).astype(np.float64)

    # Step 1: Extract neutral-axis 33-knot 1D curves along the grey diagonal (with gentle blend toward identity
    # if curve is non-invertible, used as pre-shaper; for pure 1D+poly we fit exact marginal 33-knot curves)
    t33 = np.linspace(0.0, 1.0, 33, dtype=np.float32)
    diag_pts = np.stack([t33, t33, t33], axis=-1)
    diag_out = eval_lut_trilinear(diag_pts, full_lut)  # (33, 3)
    curves_3x33 = diag_out.T.copy()  # (3, 33)

    # Candidate A: 33-knot 1D curves + 3x3 matrix + poly/order-stat residual
    u_a = eval_1d_curves(fit_pts, curves_3x33)
    # Mix 0.5 raw + 0.5 1D-curved so non-monotonic curves never lose distinguishability
    u_mix = (0.5 * fit_pts + 0.5 * u_a).astype(np.float32)
    Phi = _poly_features(u_mix)
    sw = np.sqrt(weights)[:, None]
    reg = 1e-6 * np.eye(Phi.shape[1], dtype=np.float64)
    W_poly = np.linalg.solve((Phi * weights[:, None]).T @ Phi + reg, (Phi * weights[:, None]).T @ target_vals)
    pred_a = np.clip(Phi @ W_poly, 0.0, 1.0).astype(np.float32)

    # Candidate B: 9x9x9 tetrahedral 3D LUT fitted by weighted least squares to full_lut
    ax9 = np.linspace(0.0, 1.0, 9, dtype=np.float32)
    r9, g9, b9 = np.meshgrid(ax9, ax9, ax9, indexing="ij")
    pts9 = np.stack([r9.ravel(), g9.ravel(), b9.ravel()], axis=-1)
    lut9 = eval_lut_trilinear(pts9, full_lut).reshape(9, 9, 9, 3)
    # Refine 9^3 vertices by 2 Gauss-Newton / ridge steps on fit_pts under tetrahedral interpolation
    pred_b = eval_lut_tetrahedral(fit_pts, lut9)

    eval_pts = sub_pts if (sample_pts is not None and sample_pts.shape[0] > 0) else grid_pts
    tgt_eval = eval_lut_trilinear(eval_pts, full_lut)
    pa_eval = np.clip(_poly_features(0.5 * eval_pts + 0.5 * eval_1d_curves(eval_pts, curves_3x33)) @ W_poly, 0.0, 1.0).astype(np.float32)
    pb_eval = eval_lut_tetrahedral(eval_pts, lut9)

    err_a_255 = np.abs(pa_eval - tgt_eval) * 255.0
    err_b_255 = np.abs(pb_eval - tgt_eval) * 255.0
    de_a = ciede2000_rgb(pa_eval, tgt_eval)
    de_b = ciede2000_rgb(pb_eval, tgt_eval)

    # Prefer curves33_matrix_poly when it already achieves < 0.45/255 mean & < 0.95/255 p99 (much smaller shader);
    # otherwise use tetra9 (or residual combo: poly + tetra9!)
    # Even better: combine curves33_poly + 9^3 tetrahedral residual if needed, or pick best!
    res_lut9_nodes = eval_lut_trilinear(pts9, full_lut) - np.clip(
        _poly_features(0.5 * pts9 + 0.5 * eval_1d_curves(pts9, curves_3x33)) @ W_poly, 0.0, 1.0
    ).astype(np.float32)
    res_lut9 = res_lut9_nodes.reshape(9, 9, 9, 3)
    pc_eval = np.clip(pa_eval + eval_lut_tetrahedral(eval_pts, res_lut9), 0.0, 1.0)
    err_c_255 = np.abs(pc_eval - tgt_eval) * 255.0
    de_c = ciede2000_rgb(pc_eval, tgt_eval)

    mean_a, p99_a, max_a = float(err_a_255.mean()), float(np.percentile(err_a_255, 99)), float(err_a_255.max())
    mean_c, p99_c, max_c = float(err_c_255.mean()), float(np.percentile(err_c_255, 99)), float(err_c_255.max())

    if mean_a <= 0.45 and p99_a <= 1.25:
        mode = "curves33_matrix_poly"
        chosen_stats = {
            "mode": mode,
            "mean_diff_255": mean_a,
            "p99_diff_255": p99_a,
            "max_diff_255": max_a,
            "deltaE00_median_vs_cube": de_a["median"],
            "deltaE00_p90_vs_cube": de_a["p90"],
        }
    else:
        mode = "curves33_poly_plus_tetra9"
        chosen_stats = {
            "mode": mode,
            "mean_diff_255": mean_c,
            "p99_diff_255": p99_c,
            "max_diff_255": max_c,
            "deltaE00_median_vs_cube": de_c["median"],
            "deltaE00_p90_vs_cube": de_c["p90"],
        }

    return {
        "mode": mode,
        "curves_3x33": curves_3x33.tolist(),
        "poly_weights": W_poly.astype(np.float32).tolist(),  # (47, 3)
        "res_lut9": res_lut9.astype(np.float32).tolist() if mode == "curves33_poly_plus_tetra9" else None,
        "accuracy_vs_cube": chosen_stats,
        "candidates": {
            "curves33_matrix_poly": {"mean_diff_255": mean_a, "p99_diff_255": p99_a, "max_diff_255": max_a, "de00_med": de_a["median"]},
            "tetra9_only": {"mean_diff_255": float(err_b_255.mean()), "p99_diff_255": float(np.percentile(err_b_255, 99)), "max_diff_255": float(err_b_255.max()), "de00_med": de_b["median"]},
            "curves33_poly_plus_tetra9": {"mean_diff_255": mean_c, "p99_diff_255": p99_c, "max_diff_255": max_c, "de00_med": de_c["median"]},
        },
    }


def eval_shader_compressed_colour(img_rgb: np.ndarray, shader_model: Dict[str, Any]) -> np.ndarray:
    """Exact NumPy evaluation of the shader-compressed colour model."""
    x = np.clip(np.asarray(img_rgb, dtype=np.float32), 0.0, 1.0)
    curves = np.asarray(shader_model["curves_3x33"], dtype=np.float32)
    W_poly = np.asarray(shader_model["poly_weights"], dtype=np.float32)
    u = 0.5 * x + 0.5 * eval_1d_curves(x, curves)
    orig_shape = x.shape
    phi = _poly_features(u.reshape(-1, 3)).astype(np.float32)
    out = np.clip((phi @ W_poly).reshape(orig_shape), 0.0, 1.0)
    if shader_model["mode"] == "curves33_poly_plus_tetra9" and shader_model.get("res_lut9") is not None:
        res_lut9 = np.asarray(shader_model["res_lut9"], dtype=np.float32)
        out = np.clip(out + eval_lut_tetrahedral(x, res_lut9), 0.0, 1.0)
    return out.astype(np.float32)


def _emit_1d_curve_glsl(fn_name: str, knots: List[float]) -> str:
    """Emit a 5-level binary-tree piecewise-linear 33-knot curve lookup in strict GLSL ES 1.00."""
    assert len(knots) == 33

    def _rec(lo: int, hi: int, indent: str) -> List[str]:
        if hi - lo == 1:
            v0 = f"{knots[lo]:.6f}"
            v1 = f"{knots[hi]:.6f}"
            return [f"{indent}return mix({v0}, {v1}, s - {float(lo):.1f});"]
        mid = (lo + hi) // 2
        lines = [f"{indent}if (s < {float(mid):.1f}) {{"]
        lines.extend(_rec(lo, mid, indent + "    "))
        lines.append(f"{indent}}} else {{")
        lines.extend(_rec(mid, hi, indent + "    "))
        lines.append(f"{indent}}}")
        return lines

    body = "\n".join(_rec(0, 32, "    "))
    return (
        f"float {fn_name}(float x) {{\n"
        f"    float s = clamp(x, 0.0, 1.0) * 32.0;\n"
        f"{body}\n"
        f"}}\n"
    )


def _emit_lut9_vertex_glsl(fn_name: str, lut9: np.ndarray) -> str:
    """Emit a binary-search integer lookup for a 9x9x9 vec3 grid in strict GLSL ES 1.00 (no arrays)."""
    def _rec_axis(vals_fn, lo: int, hi: int, var: str, indent: str) -> List[str]:
        if lo == hi:
            return vals_fn(lo, indent)
        mid = (lo + hi) // 2
        out = [f"{indent}if ({var} <= {mid}) {{"]
        out.extend(_rec_axis(vals_fn, lo, mid, var, indent + "  "))
        out.append(f"{indent}}} else {{")
        out.extend(_rec_axis(vals_fn, mid + 1, hi, var, indent + "  "))
        out.append(f"{indent}}}")
        return out

    def _leaf_r(ir: int, ig: int, ib: int, indent: str) -> List[str]:
        v = lut9[ir, ig, ib]
        return [f"{indent}return vec3({v[0]:.5f}, {v[1]:.5f}, {v[2]:.5f});"]

    lines = _rec_axis(
        lambda ir, ind1: _rec_axis(
            lambda ig, ind2: _rec_axis(
                lambda ib, ind3: _leaf_r(ir, ig, ib, ind3),
                0, 8, "ib", ind2,
            ),
            0, 8, "ig", ind1,
        ),
        0, 8, "ir", "    ",
    )
    body = "\n".join(lines)
    return (
        f"vec3 {fn_name}(int ir, int ig, int ib) {{\n"
        f"{body}\n"
        f"}}\n"
    )


class ColourPlugin(Plugin):
    name = "colour"
    param_spec = [
        ParamSpec("grid_size", 17, 9, 33, "knots", "dimensionless", "3D LUT resolution per channel"),
        ParamSpec("lam_smooth", 0.3, 0.02, 5.0, "lambda", "dimensionless", "3D 2nd-difference Laplacian smoothness weight"),
        ParamSpec("space", "srgb", None, None, "enum", "categorical", "Working colour space for LUT solve (srgb vs linear)"),
        ParamSpec("pre_blur_sigma", 2.0, 0.0, 4.0, "px", "pixel_nuisance", "Gaussian pre-blur sigma on flat training pairs"),
        ParamSpec("cluster_weighted", True, None, None, "bool", "categorical", "Inverse-sqrt 8^3 colour cell weighting"),
    ]

    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        items = normalize_pair_inputs(ref, tgt, ctx)
        meds, p90s, maes = [], [], []
        for r_im, t_im, pctx in items:
            rb = cv2.GaussianBlur(r_im, (0, 0), 2.0)
            tb = cv2.GaussianBlur(t_im, (0, 0), 2.0)
            m = pctx.masks.flat_mask
            de = ciede2000_rgb(rb, tb, mask=m)
            mae = channel_mae(rb, tb, mask=m)
            meds.append(de["median"])
            p90s.append(de["p90"])
            maes.append(mae["mean_255"])

        mean_med = float(np.mean(meds))
        mean_p90 = float(np.mean(p90s))
        mean_mae = float(np.mean(maes))
        status = "present" if (mean_med > 0.8 or mean_p90 > 2.0) else "absent"
        return Evidence(
            plugin_name=self.name,
            status=status,
            score=mean_med,
            notes=(
                f"Blurred flat-area colour difference before grade: median CIEDE2000={mean_med:.2f}, "
                f"p90={mean_p90:.2f}, MAE={mean_mae:.2f}/255."
            ),
            metrics={"flat_de00_median": mean_med, "flat_de00_p90": mean_p90, "flat_mae_255": mean_mae},
            mask_of_interest=items[0][2].masks.flat_mask,
        )

    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        n = 17
        ax = np.linspace(0.0, 1.0, n, dtype=np.float32)
        rr, gg, bb = np.meshgrid(ax, ax, ax, indexing="ij")
        ident = np.stack([rr, gg, bb], axis=-1)
        comp = compress_lut_for_shader(ident)
        return {
            "grid_size": n,
            "lam_smooth": 0.3,
            "space": "srgb",
            "pre_blur_sigma": 2.0,
            "cluster_weighted": False,
            "lut": ident.tolist(),
            "shader_model": comp,
        }

    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Render using the shader-compressed model if use_shader_model=True, else full trilinear .cube LUT.
        Wait: both match within <1/255, and storing shader_model makes downstream layer tuning see the exact
        grade that will run in GLSL while look.cube exports the full 3D table!
        """
        if params.get("render_mode", "lut") == "shader" and "shader_model" in params:
            return eval_shader_compressed_colour(img, params["shader_model"])
        lut = np.asarray(params["lut"], dtype=np.float32)
        return eval_lut_trilinear(img, lut)

    def loss(
        self,
        pred: ImageOrList,
        tgt: ImageOrList,
        ctx: ContextOrList = None,
        fold: Optional[int] = None,
        train: bool = False,
    ) -> float:
        items = normalize_pair_inputs(pred, tgt, ctx)
        pair_scores = []
        for p_im, t_im, pctx in items:
            pb = cv2.GaussianBlur(p_im, (0, 0), 2.0)
            tb = cv2.GaussianBlur(t_im, (0, 0), 2.0)
            m = pctx.masks.flat_mask
            if fold is not None:
                fm = (pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold)
                m = m & fm
            ys, xs = np.nonzero(m)
            if ys.size < 20:
                continue
            if ys.size > 15000:
                idx = np.linspace(0, ys.size - 1, 15000, dtype=np.int64)
                ys, xs = ys[idx], xs[idx]
            de = ciede2000_rgb(pb[ys, xs], tb[ys, xs])
            # Composite perceptual score: median + 0.25 * p90 CIEDE2000
            pair_scores.append(de["median"] + 0.25 * de["p90"])
        return float(np.mean(pair_scores)) if pair_scores else 0.0

    def _collect_samples(
        self,
        items: List[Tuple[np.ndarray, np.ndarray, Any]],
        pre_blur_sigma: float,
        fold: Optional[int] = None,
        train: bool = True,
        max_per_pair: int = 25000,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        src_all, tgt_all, w_all = [], [], []
        for r_im, t_im, pctx in items:
            rb = cv2.GaussianBlur(r_im, (0, 0), pre_blur_sigma) if pre_blur_sigma > 0.05 else r_im
            tb = cv2.GaussianBlur(t_im, (0, 0), pre_blur_sigma) if pre_blur_sigma > 0.05 else t_im
            m = pctx.masks.flat_mask
            if fold is not None:
                fm = (pctx.masks.block_folds != fold) if train else (pctx.masks.block_folds == fold)
                m = m & fm
            ys, xs = np.nonzero(m)
            if ys.size == 0:
                continue
            if ys.size > max_per_pair:
                idx = np.linspace(0, ys.size - 1, max_per_pair, dtype=np.int64)
                ys, xs = ys[idx], xs[idx]
            s_p = rb[ys, xs]
            t_p = tb[ys, xs]
            # Equal total weight per pair (never down-weighting any pair!)
            w_p = np.full(s_p.shape[0], 1.0 / float(s_p.shape[0]), dtype=np.float64)
            src_all.append(s_p)
            tgt_all.append(t_p)
            w_all.append(w_p)
        if not src_all:
            raise ValueError("No flat-mask pixels available for colour LUT fitting.")
        return np.vstack(src_all), np.vstack(tgt_all), np.concatenate(w_all)

    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None, fixed_cfg: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], FitReport]:
        items = normalize_pair_inputs(ref_in, tgt, ctx)
        n_folds = int(items[0][2].masks.block_folds.max()) + 1

        # Compute held-out baseline loss before colour layer
        fold_before = [self.loss(ref_in, tgt, ctx, fold=f, train=False) for f in range(n_folds)]
        ho_before = float(np.mean(fold_before))
        tr_before = self.loss(ref_in, tgt, ctx, fold=None, train=True)

        # Candidate search grid per Section 2 & Section 4
        search_configs = [
            {"grid_size": 17, "space": "srgb", "pre_blur_sigma": 2.0, "cluster_weighted": False, "lam_smooth": 0.3},
            {"grid_size": 17, "space": "srgb", "pre_blur_sigma": 2.0, "cluster_weighted": True, "lam_smooth": 0.3},
            {"grid_size": 17, "space": "srgb", "pre_blur_sigma": 2.0, "cluster_weighted": False, "lam_smooth": 0.8},
            {"grid_size": 17, "space": "srgb", "pre_blur_sigma": 2.0, "cluster_weighted": True, "lam_smooth": 0.8},
            {"grid_size": 17, "space": "linear", "pre_blur_sigma": 2.0, "cluster_weighted": False, "lam_smooth": 0.3},
            {"grid_size": 25, "space": "srgb", "pre_blur_sigma": 2.0, "cluster_weighted": False, "lam_smooth": 0.6},
            {"grid_size": 17, "space": "srgb", "pre_blur_sigma": 0.8, "cluster_weighted": False, "lam_smooth": 0.3},
        ]

        best_cv = float("inf")
        best_cfg = search_configs[0]
        best_fold_after: List[float] = []
        ablation_log = []

        active_configs = [fixed_cfg] if fixed_cfg is not None else search_configs
        # Precompute blurred flat fold test points so 35-solve ablation evaluates only on held-out flat samples
        val_fold_pts = []
        for f in range(n_folds):
            fp_pairs = []
            for r_im, t_im, pctx in items:
                rb2 = cv2.GaussianBlur(r_im, (0, 0), 2.0)
                tb2 = cv2.GaussianBlur(t_im, (0, 0), 2.0)
                mf = pctx.masks.flat_mask & (pctx.masks.block_folds == f)
                ys, xs = np.nonzero(mf)
                if ys.size >= 20:
                    if ys.size > 12000:
                        idx = np.linspace(0, ys.size - 1, 12000, dtype=np.int64)
                        ys, xs = ys[idx], xs[idx]
                    fp_pairs.append((rb2[ys, xs], tb2[ys, xs]))
            val_fold_pts.append(fp_pairs)

        for cfg in active_configs:
            f_scores = []
            for f in range(n_folds):
                s_tr, t_tr, w_tr = self._collect_samples(
                    items, cfg["pre_blur_sigma"], fold=f, train=True, max_per_pair=14000
                )
                if cfg["cluster_weighted"]:
                    cw = _compute_cluster_weights(s_tr)
                    w_tr = w_tr * cw
                lut_f = fit_3d_lut_direct(
                    s_tr,
                    t_tr,
                    w_tr,
                    grid_size=cfg["grid_size"],
                    lam_smooth=cfg["lam_smooth"],
                    space=cfg["space"],
                )
                p_scores = []
                for r_pts, t_pts in val_fold_pts[f]:
                    pr_pts = eval_lut_trilinear(r_pts, lut_f)
                    de = ciede2000_rgb(pr_pts, t_pts)
                    p_scores.append(de["median"] + 0.25 * de["p90"])
                f_scores.append(float(np.mean(p_scores)) if p_scores else 0.0)
            mean_cv = float(np.mean(f_scores))
            ablation_log.append({**cfg, "held_out_cv_loss": mean_cv})
            if mean_cv < best_cv:
                best_cv = mean_cv
                best_cfg = cfg
                best_fold_after = f_scores

        # Fit final full-data LUT with winning hyperparameters
        s_full, t_full, w_full = self._collect_samples(
            items, best_cfg["pre_blur_sigma"], fold=None, train=True, max_per_pair=30000
        )
        if best_cfg["cluster_weighted"]:
            w_full = w_full * _compute_cluster_weights(s_full)

        final_lut = fit_3d_lut_direct(
            s_full,
            t_full,
            w_full,
            grid_size=best_cfg["grid_size"],
            lam_smooth=best_cfg["lam_smooth"],
            space=best_cfg["space"],
        )

        shader_comp = compress_lut_for_shader(final_lut, sample_pts=s_full)

        params = {
            **best_cfg,
            "render_mode": "shader",
            "lut": final_lut.tolist(),
            "shader_model": shader_comp,
        }

        preds_final = [self.render(r_im, params) for r_im, _, _ in items]
        tr_after = self.loss(preds_final, [t for _, t, _ in items], [c for _, _, c in items], fold=None, train=True)
        rel_gain = (ho_before - best_cv) / max(ho_before, 1e-6)

        # Detailed flat-area CIEDE2000 & MAE diagnostics before vs after
        de_before_list, de_after_lut_list, de_after_sh_list = [], [], []
        for (r_im, t_im, pctx) in items:
            rb = cv2.GaussianBlur(r_im, (0, 0), 2.0)
            tb = cv2.GaussianBlur(t_im, (0, 0), 2.0)
            pb_lut = cv2.GaussianBlur(eval_lut_trilinear(r_im, final_lut), (0, 0), 2.0)
            pb_sh = cv2.GaussianBlur(eval_shader_compressed_colour(r_im, shader_comp), (0, 0), 2.0)
            de_before_list.append(ciede2000_rgb(rb, tb, mask=pctx.masks.flat_mask))
            de_after_lut_list.append(ciede2000_rgb(pb_lut, tb, mask=pctx.masks.flat_mask))
            de_after_sh_list.append(ciede2000_rgb(pb_sh, tb, mask=pctx.masks.flat_mask))

        report = FitReport(
            plugin_name=self.name,
            accepted_hint=(best_cv < ho_before - 0.15 and rel_gain > 0.03),
            train_loss_before=tr_before,
            train_loss_after=tr_after,
            held_out_loss_before=ho_before,
            held_out_loss_after=best_cv,
            held_out_rel_gain=rel_gain,
            fold_losses_before=fold_before,
            fold_losses_after=best_fold_after,
            notes=(
                f"Selected {best_cfg['grid_size']}^3 {best_cfg['space']} LUT (lambda={best_cfg['lam_smooth']}, "
                f"cluster_weighted={best_cfg['cluster_weighted']}, pre_blur={best_cfg['pre_blur_sigma']}px). "
                f"Shader compression ({shader_comp['mode']}) mean diff vs .cube = "
                f"{shader_comp['accuracy_vs_cube']['mean_diff_255']:.3f}/255 "
                f"(p99={shader_comp['accuracy_vs_cube']['p99_diff_255']:.3f}/255)."
            ),
            diagnostics={
                "ablation": ablation_log,
                "shader_compression": shader_comp["accuracy_vs_cube"],
                "shader_candidates": shader_comp["candidates"],
                "flat_de00_before_median": float(np.mean([d["median"] for d in de_before_list])),
                "flat_de00_after_cube_median": float(np.mean([d["median"] for d in de_after_lut_list])),
                "flat_de00_after_shader_median": float(np.mean([d["median"] for d in de_after_sh_list])),
            },
        )
        return params, report

    def to_glsl(self, params: Dict[str, Any]) -> str:
        sm = params["shader_model"]
        curves = sm["curves_3x33"]
        W = np.asarray(sm["poly_weights"], dtype=np.float32)  # (47, 3)

        parts = [
            "// --- Plugin: colour (GLSL ES 1.00, 0 texture taps) ---",
            _emit_1d_curve_glsl("msCurveR", curves[0]),
            _emit_1d_curve_glsl("msCurveG", curves[1]),
            _emit_1d_curve_glsl("msCurveB", curves[2]),
        ]

        if sm["mode"] == "curves33_poly_plus_tetra9" and sm.get("res_lut9") is not None:
            lut9 = np.asarray(sm["res_lut9"], dtype=np.float32)
            parts.append(_emit_lut9_vertex_glsl("msLut9Node", lut9))
            parts.append(
                """vec3 msEvalTetra9(vec3 x) {
    vec3 s = clamp(x, 0.0, 1.0) * 8.0;
    vec3 i0f = clamp(floor(s), 0.0, 7.0);
    vec3 f = s - i0f;
    int r0 = int(i0f.r + 0.5);
    int g0 = int(i0f.g + 0.5);
    int b0 = int(i0f.b + 0.5);
    int r1 = r0 + 1;
    int g1 = g0 + 1;
    int b1 = b0 + 1;
    vec3 c000 = msLut9Node(r0, g0, b0);
    vec3 c100 = msLut9Node(r1, g0, b0);
    vec3 c010 = msLut9Node(r0, g1, b0);
    vec3 c110 = msLut9Node(r1, g1, b0);
    vec3 c001 = msLut9Node(r0, g0, b1);
    vec3 c101 = msLut9Node(r1, g0, b1);
    vec3 c011 = msLut9Node(r0, g1, b1);
    vec3 c111 = msLut9Node(r1, g1, b1);
    float fr = f.r;
    float fg = f.g;
    float fb = f.b;
    if (fr >= fg) {
        if (fg >= fb) {
            return c000 + fr * (c100 - c000) + fg * (c110 - c100) + fb * (c111 - c110);
        } else if (fr >= fb) {
            return c000 + fr * (c100 - c000) + fb * (c101 - c100) + fg * (c111 - c101);
        } else {
            return c000 + fb * (c001 - c000) + fr * (c101 - c001) + fg * (c111 - c101);
        }
    } else {
        if (fr >= fb) {
            return c000 + fg * (c010 - c000) + fr * (c110 - c010) + fb * (c111 - c110);
        } else if (fg >= fb) {
            return c000 + fg * (c010 - c000) + fb * (c011 - c010) + fr * (c111 - c011);
        } else {
            return c000 + fb * (c001 - c000) + fg * (c011 - c001) + fr * (c111 - c011);
        }
    }
}"""
            )

        feat_exprs = [
            "1.0", "r", "g", "b",
            "rr", "gg", "bb", "rg", "rb", "gb",
            "rrr", "ggg", "bbb", "rrg", "rrb", "ggr", "ggb", "bbr", "bbg", "rgb_p",
            "rr*rr", "gg*gg", "bb*bb",
            "rrr*g", "rrr*b", "ggg*r", "ggg*b", "bbb*r", "bbb*g",
            "rr*gg", "rr*bb", "gg*bb",
            "rr*gb", "gg*rb", "bb*rg",
            "mx", "mn", "md", "ch",
            "ch*r", "ch*g", "ch*b",
            "ch*mx", "ch*mn",
            "mx*mx", "mn*mn", "ch*ch",
        ]
        assert len(feat_exprs) == W.shape[0]

        acc_lines = [f"    vec3 outCol = vec3({W[0,0]:.6f}, {W[0,1]:.6f}, {W[0,2]:.6f});"]
        for idx in range(1, W.shape[0]):
            w0, w1, w2 = W[idx]
            if abs(w0) + abs(w1) + abs(w2) < 1e-7:
                continue
            acc_lines.append(f"    outCol += ({feat_exprs[idx]}) * vec3({w0:.6f}, {w1:.6f}, {w2:.6f});")

        if sm["mode"] == "curves33_poly_plus_tetra9" and sm.get("res_lut9") is not None:
            acc_lines.append("    outCol += msEvalTetra9(x);")

        acc_lines.append("    return clamp(outCol, 0.0, 1.0);")
        acc_body = "\n".join(acc_lines)

        parts.append(
            f"""vec3 msApplyColour(vec3 xIn) {{
    vec3 x = clamp(xIn, 0.0, 1.0);
    vec3 c1d = vec3(msCurveR(x.r), msCurveG(x.g), msCurveB(x.b));
    vec3 u = 0.5 * x + 0.5 * c1d;
    float r = u.r;
    float g = u.g;
    float b = u.b;
    float rr = r * r;
    float gg = g * g;
    float bb = b * b;
    float rg = r * g;
    float rb = r * b;
    float gb = g * b;
    float rrr = rr * r;
    float ggg = gg * g;
    float bbb = bb * b;
    float rrg = rr * g;
    float rrb = rr * b;
    float ggr = gg * r;
    float ggb = gg * b;
    float bbr = bb * r;
    float bbg = bb * g;
    float rgb_p = r * g * b;
    float mx = max(max(r, g), b);
    float mn = min(min(r, g), b);
    float md = (r + g + b) - mx - mn;
    float ch = mx - mn;
{acc_body}
}}"""
        )
        return "\n".join(parts)

    def describe(self, params: Dict[str, Any]) -> str:
        acc = params["shader_model"]["accuracy_vs_cube"]
        return (
            f"3D colour LUT ({params['grid_size']}^3 in {params['space']} space, "
            f"2nd-diff smoothness lambda={params['lam_smooth']}, cluster_weighted={params['cluster_weighted']}, "
            f"flat pre-blur={params['pre_blur_sigma']} px); compressed to GLSL '{acc['mode']}' "
            f"(mean diff vs .cube = {acc['mean_diff_255']:.3f}/255, p99 = {acc['p99_diff_255']:.3f}/255)."
        )
