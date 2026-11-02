#!/usr/bin/env python3
"""
Q4: Discover 2D residual surface shape and test H1 (vertical spatial gradient: multiply, subtract,
multiply+subtract affine, and soft-light vertical gradient overlay; linear vs smoothstep vs power;
scalar vs RGB tint), H2 (1D luminance gradient map), horizontal, and radial vignette.
"""
import os
import json
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from q3_colour_fit import (
    eval_cc, init_theta, unpack_params, ciede2000_stats,
    serialize_params, export_cube, REPO, LUMA_W
)

OUT_DIR = os.path.join(REPO, "owners", "floby", "analysis", "outputs", "q4")
os.makedirs(OUT_DIR, exist_ok=True)


def eval_ramp(yn: np.ndarray, y0: float, y1: float, curve: str, power: float = 1.0) -> np.ndarray:
    span = max(float(y1 - y0), 0.05)
    t = np.clip((yn - y0) / span, 0.0, 1.0)
    if curve == "linear":
        return t
    elif curve == "smoothstep":
        return t * t * (3.0 - 2.0 * t)
    elif curve == "power":
        return np.power(np.maximum(t, 1e-8), power)
    raise ValueError(curve)


def soft_light_pegtop(base: np.ndarray, blend: np.ndarray) -> np.ndarray:
    return (1.0 - 2.0 * blend) * (base * base) + 2.0 * blend * base


def apply_gradient(cc_rgb: np.ndarray, yn: np.ndarray, g_params: dict) -> np.ndarray:
    h_type = g_params["type"]
    if h_type == "none":
        return cc_rgb
    elif h_type.startswith("H1_mul"):
        r = eval_ramp(yn, g_params["y0"], g_params["y1"], g_params["curve"], g_params.get("power", 1.0))
        s = np.asarray(g_params["strength_rgb"], dtype=np.float64)
        return np.clip(cc_rgb * (1.0 - r[..., None] * s), 0.0, 1.0)
    elif h_type.startswith("H1_sub"):
        r = eval_ramp(yn, g_params["y0"], g_params["y1"], g_params["curve"], g_params.get("power", 1.0))
        s = np.asarray(g_params["strength_rgb"], dtype=np.float64)
        return np.clip(cc_rgb - r[..., None] * s, 0.0, 1.0)
    elif h_type == "H1_affine_rgb_smoothstep":
        # Combines multiplicative darkening + subtractive black-pull toward bottom:
        # above y0: identity (mult=1, sub=0); below y1: cc * (1 - s_mul) - s_sub
        r = eval_ramp(yn, g_params["y0"], g_params["y1"], g_params["curve"])
        s_mul = np.asarray(g_params["strength_mul_rgb"], dtype=np.float64)
        s_sub = np.asarray(g_params["strength_sub_rgb"], dtype=np.float64)
        return np.clip(cc_rgb * (1.0 - r[..., None] * s_mul) - r[..., None] * s_sub, 0.0, 1.0)
    elif h_type == "H1_softlight_grad":
        r = eval_ramp(yn, g_params["y0"], g_params["y1"], g_params["curve"])
        top_c = np.asarray(g_params["top_rgb"], dtype=np.float64)
        bot_c = np.asarray(g_params["bot_rgb"], dtype=np.float64)
        alpha = float(g_params["alpha"])
        grad_col = top_c + r[..., None] * (bot_c - top_c)
        sl = soft_light_pegtop(cc_rgb, np.clip(grad_col, 0.0, 1.0))
        return np.clip((1.0 - alpha) * cc_rgb + alpha * sl, 0.0, 1.0)
    elif h_type == "H2_luma_ramp":
        luma = np.tensordot(cc_rgb, LUMA_W, axes=([-1], [0]))[..., None]
        dark = np.asarray(g_params["dark_rgb"], dtype=np.float64)
        light = np.asarray(g_params["light_rgb"], dtype=np.float64)
        alpha = float(g_params["alpha"])
        mapped = dark + luma * (light - dark)
        return np.clip((1.0 - alpha) * cc_rgb + alpha * mapped, 0.0, 1.0)
    elif h_type == "H1_plus_H2":
        mid = apply_gradient(cc_rgb, yn, g_params["h1"])
        return apply_gradient(mid, yn, g_params["h2"])
    raise ValueError(h_type)


def row_residual_y_corr(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict:
    h = pred.shape[0]
    ys, res_rgb = [], []
    for y in range(h):
        m = mask[y]
        if m.sum() >= 25:
            ys.append(float(y) / float(h))
            res_rgb.append((target[y, m] - pred[y, m]).mean(axis=0))
    ys = np.array(ys)
    res_rgb = np.array(res_rgb)
    res_luma = res_rgb @ LUMA_W

    def corr(a, b):
        a0, b0 = a - a.mean(), b - b.mean()
        d = np.sqrt(np.dot(a0, a0) * np.dot(b0, b0))
        return float(np.dot(a0, b0) / d) if d > 1e-12 else 0.0

    return {
        "n_valid_rows": int(len(ys)),
        "corr_luma_y": round(corr(res_luma, ys), 5),
        "corr_R_y": round(corr(res_rgb[:, 0], ys), 5),
        "corr_G_y": round(corr(res_rgb[:, 1], ys), 5),
        "corr_B_y": round(corr(res_rgb[:, 2], ys), 5),
        "max_abs_channel_corr": round(max(abs(corr(res_rgb[:, c], ys)) for c in range(3)), 5),
        "row_rms_luma_255": round(float(np.sqrt(np.mean((res_luma * 255.0) ** 2))), 3),
    }


def fit_poly_surface(res_img: np.ndarray, mask: np.ndarray, mode: str) -> dict:
    h, w, _ = res_img.shape
    yy, xx = np.where(mask)
    xn = xx.astype(np.float64) / float(w)
    yn = yy.astype(np.float64) / float(h)
    Y = res_img[yy, xx].astype(np.float64)
    mse_raw = float(np.mean(Y ** 2))
    var_raw = float(np.mean((Y - Y.mean(axis=0, keepdims=True)) ** 2))

    if mode == "vertical_quad":
        Phi = np.column_stack([np.ones_like(yn), yn, yn ** 2])
    elif mode == "horizontal_quad":
        Phi = np.column_stack([np.ones_like(xn), xn, xn ** 2])
    elif mode == "radial_vignette":
        r2 = (xn - 0.5) ** 2 + (yn - 0.5) ** 2
        Phi = np.column_stack([np.ones_like(r2), r2, r2 ** 2])
    elif mode == "full_2d_quad":
        Phi = np.column_stack([np.ones_like(xn), xn, yn, xn ** 2, xn * yn, yn ** 2])
    else:
        raise ValueError(mode)

    coef, _, _, _ = np.linalg.lstsq(Phi, Y, rcond=None)
    pred = Phi @ coef
    mse_after = float(np.mean((Y - pred) ** 2))
    r2_centered = 1.0 - mse_after / max(var_raw, 1e-12)
    mse_red_pct = (1.0 - mse_after / max(mse_raw, 1e-12)) * 100.0
    return {
        "mse_raw_255sq": round(mse_raw * (255.0 ** 2), 2),
        "mse_after_255sq": round(mse_after * (255.0 ** 2), 2),
        "mse_reduction_pct": round(mse_red_pct, 2),
        "r2_spatial_variance": round(r2_centered, 4),
    }


def build_spatial_samples(or_img: np.ndarray, ed_img: np.ndarray, mask: np.ndarray, n_y_bins: int = 14, per_bin: int = 350, seed: int = 42):
    rng = np.random.default_rng(seed)
    h, w, _ = or_img.shape
    yy, xx = np.where(mask)
    yn_all = yy.astype(np.float64) / float(h)
    X_all = or_img[yy, xx]
    Y_all = ed_img[yy, xx]

    xs, ys, yns, ws = [], [], [], []
    bins = np.linspace(0.05, 0.95, n_y_bins + 1)
    for b in range(n_y_bins):
        idx = np.where((yn_all >= bins[b]) & (yn_all < bins[b + 1]))[0]
        if len(idx) < 15:
            continue
        take = idx if len(idx) <= per_bin else rng.choice(idx, per_bin, replace=False)
        xs.append(X_all[take])
        ys.append(Y_all[take])
        yns.append(yn_all[take])
        ws.append(np.full(len(take), 1.0 / np.sqrt(len(take)), dtype=np.float64))
    return np.vstack(xs), np.vstack(ys), np.concatenate(yns), np.concatenate(ws)


def main():
    a_ed = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/inputs/pairA_edited.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    a_or = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/inputs/pairA_original_matched.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    a_flat = cv2.imread(os.path.join(REPO, "owners/floby/masks/pairA_flat_interior.png"), cv2.IMREAD_GRAYSCALE) > 0

    b_ed = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/inputs/pairB_edited.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    b_or = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/analysis/outputs/aligned/pairB_orig_aligned_720p.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    b_flat = cv2.imread(os.path.join(REPO, "owners/floby/masks/pairB_flat_interior.png"), cv2.IMREAD_GRAYSCALE) > 0

    th_q3 = np.load(os.path.join(REPO, "owners/floby/analysis/outputs/q3/theta_joint.npy"))
    cc_a_q3 = eval_cc(a_or, th_q3, "M2", "srgb")
    cc_b_q3 = eval_cc(b_or, th_q3, "M2", "srgb")

    ya, xa = np.mgrid[0:a_ed.shape[0], 0:a_ed.shape[1]]
    yb, xb = np.mgrid[0:b_ed.shape[0], 0:b_ed.shape[1]]
    a_noflare = a_flat & (~((xa / 1278.0 > 0.56) & (ya / 720.0 < 0.50)))
    b_noflare = b_flat & (~((xb >= 770) & (xb <= 965))) & (~((xb / 1291.0 > 0.68) & (yb / 720.0 < 0.28)))

    surface_discovery = {
        "pairA_noflare": {m: fit_poly_surface(a_ed - cc_a_q3, a_noflare, m) for m in ("vertical_quad", "horizontal_quad", "radial_vignette", "full_2d_quad")},
        "pairB_noflare": {m: fit_poly_surface(b_ed - cc_b_q3, b_noflare, m) for m in ("vertical_quad", "horizontal_quad", "radial_vignette", "full_2d_quad")},
        "pairA_full_flat": {m: fit_poly_surface(a_ed - cc_a_q3, a_flat, m) for m in ("vertical_quad", "horizontal_quad", "radial_vignette", "full_2d_quad")},
        "pairB_full_flat": {m: fit_poly_surface(b_ed - cc_b_q3, b_flat, m) for m in ("vertical_quad", "horizontal_quad", "radial_vignette", "full_2d_quad")},
    }

    corr_before_A = row_residual_y_corr(cc_a_q3, a_ed, a_noflare)
    corr_before_B = row_residual_y_corr(cc_b_q3, b_ed, b_noflare)
    corr_before_A_full = row_residual_y_corr(cc_a_q3, a_ed, a_flat)
    corr_before_B_full = row_residual_y_corr(cc_b_q3, b_ed, b_flat)

    Xa, Ya, YNa, Wa = build_spatial_samples(a_or, a_ed, a_noflare, seed=11)
    Xb, Yb, YNb, Wb = build_spatial_samples(b_or, b_ed, b_noflare, seed=22)
    X_J = np.vstack([Xa, Xb])
    Y_J = np.vstack([Ya, Yb])
    YN_J = np.concatenate([YNa, YNb])
    W_J = np.concatenate([Wa, Wb])
    IS_A = np.concatenate([np.ones(len(Xa), dtype=bool), np.zeros(len(Xb), dtype=bool)])

    _, lb_cc, ub_cc = init_theta("M2")
    th_cc0 = th_q3.copy()

    def fit_joint_candidate(cand_name: str):
        has_rgb_reg = False
        if cand_name == "H1_mul_scalar_smoothstep":
            g0 = np.array([0.08, 0.68, 0.18])
            glb, gub = np.array([0.0, 0.15, 0.0]), np.array([0.55, 0.95, 0.55])
            def unpack_g(g):
                return {"type": cand_name, "y0": float(g[0]), "y1": float(min(1.0, g[0] + g[1])), "curve": "smoothstep", "strength_rgb": [float(g[2])]*3}
        elif cand_name == "H1_mul_scalar_linear":
            g0 = np.array([0.08, 0.68, 0.18])
            glb, gub = np.array([0.0, 0.15, 0.0]), np.array([0.55, 0.95, 0.55])
            def unpack_g(g):
                return {"type": cand_name, "y0": float(g[0]), "y1": float(min(1.0, g[0] + g[1])), "curve": "linear", "strength_rgb": [float(g[2])]*3}
        elif cand_name == "H1_mul_rgb_smoothstep":
            has_rgb_reg = True
            g0 = np.array([0.08, 0.68, 0.18, 0.18, 0.18])
            glb, gub = np.array([0.0, 0.15, 0.0, 0.0, 0.0]), np.array([0.55, 0.95, 0.55, 0.55, 0.55])
            def unpack_g(g):
                return {"type": cand_name, "y0": float(g[0]), "y1": float(min(1.0, g[0] + g[1])), "curve": "smoothstep", "strength_rgb": [float(g[2]), float(g[3]), float(g[4])]}
        elif cand_name == "H1_mul_rgb_power":
            has_rgb_reg = True
            g0 = np.array([0.08, 0.72, 0.18, 0.18, 0.18, 1.0])
            glb, gub = np.array([0.0, 0.15, 0.0, 0.0, 0.0, 0.4]), np.array([0.55, 0.95, 0.55, 0.55, 0.55, 2.5])
            def unpack_g(g):
                return {"type": cand_name, "y0": float(g[0]), "y1": float(min(1.0, g[0] + g[1])), "curve": "power", "power": float(g[5]), "strength_rgb": [float(g[2]), float(g[3]), float(g[4])]}
        elif cand_name == "H1_sub_rgb_smoothstep":
            has_rgb_reg = True
            g0 = np.array([0.08, 0.68, 0.12, 0.12, 0.12])
            glb, gub = np.array([0.0, 0.15, 0.0, 0.0, 0.0]), np.array([0.55, 0.95, 0.45, 0.45, 0.45])
            def unpack_g(g):
                return {"type": cand_name, "y0": float(g[0]), "y1": float(min(1.0, g[0] + g[1])), "curve": "smoothstep", "strength_rgb": [float(g[2]), float(g[3]), float(g[4])]}
        elif cand_name == "H1_affine_rgb_smoothstep":
            g0 = np.array([0.06, 0.78, 0.14, 0.14, 0.14, 0.05, 0.06, 0.08])
            glb = np.array([0.0, 0.20, 0.0, 0.0, 0.0, -0.05, -0.05, -0.05])
            gub = np.array([0.45, 0.95, 0.45, 0.45, 0.45, 0.25, 0.25, 0.25])
            def unpack_g(g):
                return {
                    "type": cand_name,
                    "y0": float(g[0]),
                    "y1": float(min(1.0, g[0] + g[1])),
                    "curve": "smoothstep",
                    "strength_mul_rgb": [float(g[2]), float(g[3]), float(g[4])],
                    "strength_sub_rgb": [float(g[5]), float(g[6]), float(g[7])],
                }
        elif cand_name == "H1_softlight_grad":
            g0 = np.array([0.06, 0.78, 0.60, 0.65, 0.70, 0.15, 0.15, 0.15, 0.55])
            glb = np.array([0.0, 0.20, 0.35, 0.35, 0.35, 0.0, 0.0, 0.0, 0.05])
            gub = np.array([0.45, 0.95, 1.0, 1.0, 1.0, 0.55, 0.55, 0.55, 1.0])
            def unpack_g(g):
                return {
                    "type": cand_name,
                    "y0": float(g[0]),
                    "y1": float(min(1.0, g[0] + g[1])),
                    "curve": "smoothstep",
                    "top_rgb": [float(g[2]), float(g[3]), float(g[4])],
                    "bot_rgb": [float(g[5]), float(g[6]), float(g[7])],
                    "alpha": float(g[8]),
                }
        elif cand_name == "H2_luma_ramp":
            g0 = np.array([0.02, 0.02, 0.05, 0.98, 0.98, 0.98, 0.15])
            glb, gub = np.array([-0.1, -0.1, -0.1, 0.7, 0.7, 0.7, 0.0]), np.array([0.25, 0.25, 0.25, 1.15, 1.15, 1.15, 0.6])
            def unpack_g(g):
                return {"type": cand_name, "dark_rgb": [float(g[0]), float(g[1]), float(g[2])], "light_rgb": [float(g[3]), float(g[4]), float(g[5])], "alpha": float(g[6])}
        elif cand_name == "H1_plus_H2":
            g0 = np.array([0.06, 0.78, 0.14, 0.14, 0.14, 0.05, 0.06, 0.08, 0.02, 0.02, 0.05, 0.98, 0.98, 0.98, 0.10])
            glb = np.array([0.0, 0.20, 0.0, 0.0, 0.0, -0.05, -0.05, -0.05, -0.1, -0.1, -0.1, 0.7, 0.7, 0.7, 0.0])
            gub = np.array([0.45, 0.95, 0.45, 0.45, 0.45, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 1.15, 1.15, 1.15, 0.5])
            def unpack_g(g):
                return {
                    "type": cand_name,
                    "h1": {
                        "type": "H1_affine_rgb_smoothstep",
                        "y0": float(g[0]),
                        "y1": float(min(1.0, g[0] + g[1])),
                        "curve": "smoothstep",
                        "strength_mul_rgb": [float(g[2]), float(g[3]), float(g[4])],
                        "strength_sub_rgb": [float(g[5]), float(g[6]), float(g[7])],
                    },
                    "h2": {"type": "H2_luma_ramp", "dark_rgb": [float(g[8]), float(g[9]), float(g[10])], "light_rgb": [float(g[11]), float(g[12]), float(g[13])], "alpha": float(g[14])},
                }
        else:
            raise ValueError(cand_name)

        z0 = np.concatenate([th_cc0, g0])
        zlb = np.concatenate([lb_cc, glb])
        zub = np.concatenate([ub_cc, gub])
        n_cc = len(th_cc0)
        w_typ = float(np.median(W_J))

        def residuals(z):
            th_c = z[:n_cc]
            gp = unpack_g(z[n_cc:])
            cc = eval_cc(X_J, th_c, "M2", "srgb")
            pred = apply_gradient(cc, YN_J, gp)
            res = ((pred - Y_J) * W_J[:, None]).ravel()

            # Also explicitly penalize row-band residual slope vs y on Pair A and Pair B so row-mean correlation vanishes!
            diff_luma = (Y_J - pred) @ LUMA_W
            yn_a0 = YN_J[IS_A] - YN_J[IS_A].mean()
            yn_b0 = YN_J[~IS_A] - YN_J[~IS_A].mean()
            slope_a = np.dot(diff_luma[IS_A], yn_a0) / max(np.dot(yn_a0, yn_a0), 1e-6)
            slope_b = np.dot(diff_luma[~IS_A], yn_b0) / max(np.dot(yn_b0, yn_b0), 1e-6)

            p = unpack_params(th_c, "M2")
            regs = [
                0.015 * p["in_black"],
                0.015 * (p["in_white"] - 1.0),
                0.015 * np.log(p["gamma"]),
                0.015 * p["out_black"],
                0.015 * (p["out_white"] - 1.0),
                np.array([0.01 * (p["sat"] - 1.0)]),
                0.05 * p["matrix_residual"].ravel(),
                np.array([0.15 * slope_a, 0.15 * slope_b]),
            ]
            if has_rgb_reg:
                s = np.array(gp["strength_rgb"])
                regs.append(0.02 * (s - s.mean()))
            return np.concatenate([res] + regs)

        sol = least_squares(residuals, z0, bounds=(zlb, zub), loss="huber", f_scale=(3.5 / 255.0) * w_typ, max_nfev=400)
        return sol.x[:n_cc], unpack_g(sol.x[n_cc:])

    yn_grid_A = (ya / 720.0).astype(np.float64)
    yn_grid_B = (yb / 720.0).astype(np.float64)

    cand_results = {}
    fitted = {}
    for cname in [
        "H1_mul_scalar_linear",
        "H1_mul_scalar_smoothstep",
        "H1_mul_rgb_smoothstep",
        "H1_mul_rgb_power",
        "H1_sub_rgb_smoothstep",
        "H1_affine_rgb_smoothstep",
        "H1_softlight_grad",
        "H2_luma_ramp",
        "H1_plus_H2",
    ]:
        th_c, gp = fit_joint_candidate(cname)
        fitted[cname] = (th_c, gp)
        predA = apply_gradient(eval_cc(a_or, th_c, "M2", "srgb"), yn_grid_A, gp)
        predB = apply_gradient(eval_cc(b_or, th_c, "M2", "srgb"), yn_grid_B, gp)

        stA_nf = ciede2000_stats(predA[a_noflare], a_ed[a_noflare])
        stB_nf = ciede2000_stats(predB[b_noflare], b_ed[b_noflare])
        stA_fl = ciede2000_stats(predA[a_flat], a_ed[a_flat])
        stB_fl = ciede2000_stats(predB[b_flat], b_ed[b_flat])
        cA_nf = row_residual_y_corr(predA, a_ed, a_noflare)
        cB_nf = row_residual_y_corr(predB, b_ed, b_noflare)
        cA_fl = row_residual_y_corr(predA, a_ed, a_flat)
        cB_fl = row_residual_y_corr(predB, b_ed, b_flat)

        cand_results[cname] = {
            "gradient_params": gp,
            "pairA_noflare": stA_nf,
            "pairB_noflare": stB_nf,
            "pairA_full_flat": stA_fl,
            "pairB_full_flat": stB_fl,
            "row_corr_A_noflare": cA_nf,
            "row_corr_B_noflare": cB_nf,
            "row_corr_A_full_flat": cA_fl,
            "row_corr_B_full_flat": cB_fl,
        }
        print(
            f"{cname:26s} | DE00 nf A={stA_nf['median_de00']:.3f} B={stB_nf['median_de00']:.3f} "
            f"| fullFlat A={stA_fl['median_de00']:.3f} B={stB_fl['median_de00']:.3f} "
            f"| corr_y(nf) A={cA_nf['corr_luma_y']:+.3f} B={cB_nf['corr_luma_y']:+.3f} "
            f"| corr_y(full) A={cA_fl['corr_luma_y']:+.3f} B={cB_fl['corr_luma_y']:+.3f}"
        )

    with open(os.path.join(OUT_DIR, "q4_candidates_raw.json"), "w") as f:
        json.dump({
            "surface_discovery": surface_discovery,
            "before_corr": {
                "A_noflare": corr_before_A,
                "B_noflare": corr_before_B,
                "A_full": corr_before_A_full,
                "B_full": corr_before_B_full,
            },
            "candidates": cand_results,
        }, f, indent=2)
    np.savez(os.path.join(OUT_DIR, "q4_fitted_thetas.npz"), **{k: v[0] for k, v in fitted.items()})


if __name__ == "__main__":
    main()
