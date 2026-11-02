#!/usr/bin/env python3
"""
Q3: Colour correction model selection (M1, M2, M3), space comparison (sRGB vs Linear),
cluster-balanced robust fitting on pixels least affected by spatial gradient/flare,
cross-validation (A->B, B->A, Joint), and 33^3 look.cube export.
"""
import os
import json
import cv2
import numpy as np
from scipy.optimize import least_squares
from skimage.color import rgb2lab, deltaE_ciede2000

OWNER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO = os.path.abspath(os.path.join(OWNER_DIR, "..", ".."))
OUT_DIR = os.path.join(REPO, "analysis", "outputs", "q3")
os.makedirs(OUT_DIR, exist_ok=True)

N_KNOTS = 17
LUMA_W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, np.power((x + 0.055) / 1.055, 2.4))


def linear_to_srgb(y: np.ndarray) -> np.ndarray:
    y = np.clip(y, 0.0, 1.0)
    return np.where(y <= 0.0031308, y * 12.92, 1.055 * np.power(np.maximum(y, 1e-12), 1.0 / 2.4) - 0.055)


def sat_matrix(sat: float) -> np.ndarray:
    """Luminance-preserving 3x3 saturation matrix (rows sum to 1)."""
    return (1.0 - sat) * np.outer(np.ones(3), LUMA_W) + sat * np.eye(3)


def ciede2000_stats(pred_rgb01: np.ndarray, target_rgb01: np.ndarray) -> dict:
    if len(pred_rgb01) > 80000:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(pred_rgb01), 80000, replace=False)
        p = pred_rgb01[idx]
        t = target_rgb01[idx]
    else:
        p = pred_rgb01
        t = target_rgb01
    lab_p = rgb2lab(np.clip(p, 0.0, 1.0).reshape(-1, 1, 3)).reshape(-1, 3)
    lab_t = rgb2lab(np.clip(t, 0.0, 1.0).reshape(-1, 1, 3)).reshape(-1, 3)
    de = deltaE_ciede2000(lab_p, lab_t)
    mae_255 = np.abs(pred_rgb01 - target_rgb01).mean(axis=0) * 255.0
    return {
        "median_de00": round(float(np.median(de)), 4),
        "p90_de00": round(float(np.percentile(de, 90)), 4),
        "mean_de00": round(float(np.mean(de)), 4),
        "mae_rgb_255": [round(float(v), 3) for v in mae_255],
        "mae_mean_255": round(float(mae_255.mean()), 3),
    }


def load_pair_data():
    a_ed = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/xenoz/inputs/pairA_edited.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    a_or = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/xenoz/inputs/pairA_original_matched.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    a_flat = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairA_flat_interior.png"), cv2.IMREAD_GRAYSCALE) > 0

    b_ed = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/xenoz/inputs/pairB_edited.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    b_or = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/xenoz/analysis/outputs/aligned/pairB_orig_aligned_720p.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    b_flat = cv2.imread(os.path.join(REPO, "owners/xenoz/masks/pairB_flat_interior.png"), cv2.IMREAD_GRAYSCALE) > 0

    # Least-coupled flat pixels for initial uncoupled Q3 fit:
    # - Outside top-right flare in Pair A (x_norm > 0.58 & y_norm < 0.50)
    # - Outside lower darkening gradient (keep y_norm in [0.18, 0.52]) so Gradient(y) = 1.0 in upper-mid reference zone!
    # - Also include un-flared mid-band dark hair/cloak anchors
    ha, wa, _ = a_ed.shape
    yy_a, xx_a = np.mgrid[0:ha, 0:wa]
    yn_a, xn_a = yy_a / float(ha), xx_a / float(wa)
    flare_a = (xn_a > 0.58) & (yn_a < 0.50)
    a_clean = a_flat & (~flare_a) & (yn_a >= 0.18) & (yn_a <= 0.52)

    hb, wb, _ = b_ed.shape
    yy_b, xx_b = np.mgrid[0:hb, 0:wb]
    yn_b, xn_b = yy_b / float(hb), xx_b / float(wb)
    ai_bush_b = (xx_b >= 770) & (xx_b <= 965)
    top_haze_b = (yn_b < 0.24) & (xx_b > 900)
    b_clean = b_flat & (~ai_bush_b) & (~top_haze_b) & (yn_b >= 0.18) & (yn_b <= 0.52)

    return {
        "A": {"or": a_or, "ed": a_ed, "flat": a_flat, "clean": a_clean},
        "B": {"or": b_or, "ed": b_ed, "flat": b_flat, "clean": b_clean},
    }


def build_cluster_balanced_samples(or_img: np.ndarray, ed_img: np.ndarray, mask: np.ndarray, n_clusters: int = 20, samples_per_cluster: int = 200, seed: int = 42):
    rng = np.random.default_rng(seed)
    yy, xx = np.where(mask)
    X_all = or_img[yy, xx]
    Y_all = ed_img[yy, xx]

    # Spatially disjoint 24x24 tile split: 80% train, 20% held-out validation
    block_id = (yy // 24) * 64 + (xx // 24)
    is_val = (block_id % 5) == 0
    is_tr = ~is_val

    sub_idx = rng.choice(np.where(is_tr)[0], min(15000, int(is_tr.sum())), replace=False)
    Z = X_all[sub_idx].astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-3)
    k_eff = min(n_clusters, max(2, len(Z) // 20))
    _, _, centers = cv2.kmeans(Z, k_eff, None, criteria, 3, cv2.KMEANS_PP_CENTERS)

    dists = np.linalg.norm(X_all[:, None, :] - centers[None, :, :], axis=2)
    labels = np.argmin(dists, axis=1)

    def sample_equal_clusters(sel_mask):
        xs, ys, ws = [], [], []
        for k in range(k_eff):
            idx_k = np.where(sel_mask & (labels == k))[0]
            if len(idx_k) < 8:
                continue
            take = idx_k if len(idx_k) <= samples_per_cluster else rng.choice(idx_k, samples_per_cluster, replace=False)
            xs.append(X_all[take])
            ys.append(Y_all[take])
            ws.append(np.full(len(take), 1.0 / np.sqrt(len(take)), dtype=np.float64))
        for anchor_cond in [X_all.max(axis=1) < 0.18, X_all.min(axis=1) > 0.85]:
            idx_a = np.where(sel_mask & anchor_cond)[0]
            if len(idx_a) >= 8:
                take = idx_a if len(idx_a) <= samples_per_cluster else rng.choice(idx_a, samples_per_cluster, replace=False)
                xs.append(X_all[take])
                ys.append(Y_all[take])
                ws.append(np.full(len(take), 1.2 / np.sqrt(len(take)), dtype=np.float64))
        return np.vstack(xs), np.vstack(ys), np.concatenate(ws)

    return sample_equal_clusters(is_tr), sample_equal_clusters(is_val)


def unpack_params(theta: np.ndarray, model_type: str):
    """
    M1 (15 params): per-channel Levels (in_black, in_white, gamma, out_black, out_white)
    M2 (22 params): M1 (15) + sat (1) + 6 row-sum-zero off-diagonal colour matrix tweaks => 3x3 neutral-preserving matrix!
      Specifically M = sat_matrix(sat) + D, where each row of D sums to 0:
      D[i, :] has 2 free entries and the diagonal entry is -(sum of the 2 off-diagonals), so M * [1,1,1]^T = [1,1,1]^T!
      Any per-channel neutral gain/tint is cleanly carried by Levels (out_black, out_white, gamma), eliminating gauge degeneracy!
    M3 (22 + 51 = 73 params): M2 + monotonic 17-knot curve per channel.
    """
    in_black = theta[0:3]
    in_white = in_black + np.maximum(theta[3:6], 0.25)
    gamma = np.exp(np.clip(theta[6:9], -0.8, 0.8))
    out_black = theta[9:12]
    out_white = theta[12:15]
    p = {
        "in_black": in_black,
        "in_white": in_white,
        "gamma": gamma,
        "out_black": out_black,
        "out_white": out_white,
    }
    if model_type in ("M2", "M3"):
        sat = float(theta[15])
        d = theta[16:22]
        D = np.array([
            [-(d[0] + d[1]), d[0], d[1]],
            [d[2], -(d[2] + d[3]), d[3]],
            [d[4], d[5], -(d[4] + d[5])],
        ], dtype=np.float64)
        M = sat_matrix(sat) + D
        p["sat"] = sat
        p["matrix_residual"] = D
        p["matrix"] = M
    if model_type == "M3":
        knots = np.zeros((3, N_KNOTS), dtype=np.float64)
        offset = 22
        for c in range(3):
            y0 = 1.0 / (1.0 + np.exp(-theta[offset])) * 0.20
            raw_inc = theta[offset + 1 : offset + N_KNOTS]
            inc = np.log1p(np.exp(np.clip(raw_inc, -15.0, 15.0)))
            cum = np.concatenate([[0.0], np.cumsum(inc)])
            span = np.clip(cum[-1], 1e-6, None)
            yk = y0 + cum / max(1.0, (y0 + span)) * min(1.0 - y0, span)
            knots[c] = np.clip(yk, 0.0, 1.0)
            offset += N_KNOTS
        p["knots"] = knots
    return p


def init_theta(model_type: str) -> tuple:
    th_m1 = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype=np.float64)
    lb_m1 = np.array([-0.12]*3 + [0.55]*3 + [-0.6]*3 + [-0.12]*3 + [0.75]*3)
    ub_m1 = np.array([ 0.18]*3 + [1.25]*3 + [ 0.6]*3 + [ 0.18]*3 + [1.18]*3)
    if model_type == "M1":
        return th_m1, lb_m1, ub_m1

    th_m2 = np.concatenate([th_m1, [1.15], np.zeros(6)])
    lb_m2 = np.concatenate([lb_m1, [0.50], np.full(6, -0.35)])
    ub_m2 = np.concatenate([ub_m1, [2.00], np.full(6,  0.35)])
    if model_type == "M2":
        return th_m2, lb_m2, ub_m2

    raw_step = float(np.log(np.expm1(1.0 / (N_KNOTS - 1))))
    knot_init, knot_lb, knot_ub = [], [], []
    for _ in range(3):
        knot_init.extend([-6.0] + [raw_step] * (N_KNOTS - 1))
        knot_lb.extend([-10.0] + [-6.0] * (N_KNOTS - 1))
        knot_ub.extend([  1.0] + [ 1.0] * (N_KNOTS - 1))
    return (
        np.concatenate([th_m2, np.array(knot_init)]),
        np.concatenate([lb_m2, np.array(knot_lb)]),
        np.concatenate([ub_m2, np.array(knot_ub)]),
    )


def eval_cc(x_srgb01: np.ndarray, theta: np.ndarray, model_type: str, space: str) -> np.ndarray:
    orig_shape = x_srgb01.shape
    x = x_srgb01.reshape(-1, 3).astype(np.float64)
    w = srgb_to_linear(x) if space == "linear" else np.clip(x, 0.0, 1.0)

    p = unpack_params(theta, model_type)
    span = np.maximum(p["in_white"] - p["in_black"], 1e-4)
    t = np.clip((w - p["in_black"][None, :]) / span[None, :], 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), p["gamma"][None, :])
    v = p["out_black"][None, :] + u * (p["out_white"] - p["out_black"])[None, :]

    if model_type in ("M2", "M3"):
        v = v @ p["matrix"].T

    v = np.clip(v, 0.0, 1.0)

    if model_type == "M3":
        knots = p["knots"]
        xk = np.linspace(0.0, 1.0, N_KNOTS)
        out_v = np.empty_like(v)
        for c in range(3):
            out_v[:, c] = np.interp(v[:, c], xk, knots[c])
        v = np.clip(out_v, 0.0, 1.0)

    out = linear_to_srgb(v) if space == "linear" else v
    return np.clip(out, 0.0, 1.0).reshape(orig_shape)


def fit_cc_model(X_tr: np.ndarray, Y_tr: np.ndarray, W_tr: np.ndarray, model_type: str, space: str, obs_range: list):
    th0, lb, ub = init_theta(model_type)
    xk = np.linspace(0.0, 1.0, N_KNOTS)

    def residuals(th):
        pred = eval_cc(X_tr, th, model_type, space)
        res = ((pred - Y_tr) * W_tr[:, None]).ravel()
        p = unpack_params(th, model_type)
        regs = [
            0.02 * p["in_black"],
            0.02 * (p["in_white"] - 1.0),
            0.02 * np.log(p["gamma"]),
            0.02 * p["out_black"],
            0.02 * (p["out_white"] - 1.0),
        ]
        if model_type in ("M2", "M3"):
            # Regularize anisotropic matrix deviations around pure saturation so unobserved hues stay well-behaved
            regs.append(np.array([0.01 * (p["sat"] - 1.0)]))
            regs.append(0.06 * p["matrix_residual"].ravel())
        if model_type == "M3":
            knots = p["knots"]
            for c in range(3):
                regs.append(0.40 * np.diff(knots[c], n=2))
                c_min, c_max = obs_range[c]
                outside = (xk < c_min) | (xk > c_max)
                if np.any(outside):
                    regs.append(0.30 * (knots[c][outside] - xk[outside]))
                regs.append(0.06 * (knots[c] - xk))
        return np.concatenate([res] + regs)

    w_typ = float(np.median(W_tr))
    sol = least_squares(
        residuals,
        th0,
        bounds=(lb, ub),
        loss="huber",
        f_scale=(3.5 / 255.0) * w_typ,
        max_nfev=300,
    )
    return sol.x


def export_cube(path: str, theta: np.ndarray, model_type: str, space: str, size: int = 33):
    grid = np.linspace(0.0, 1.0, size)
    B, G, R = np.meshgrid(grid, grid, grid, indexing="ij")
    pts = np.stack([R.ravel(), G.ravel(), B.ravel()], axis=1)
    mapped = eval_cc(pts, theta, model_type, space)
    with open(path, "w") as f:
        f.write("TITLE \"MOTIONSALT_Keyflaw_Look_CC\"\n")
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for r, g, b in mapped:
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")


def serialize_params(theta: np.ndarray, model_type: str, space: str, obs_range: list) -> dict:
    p = unpack_params(theta, model_type)
    out = {
        "model_type": model_type,
        "colour_space": space,
        "levels": {
            "in_black": [round(float(v), 6) for v in p["in_black"]],
            "in_white": [round(float(v), 6) for v in p["in_white"]],
            "gamma": [round(float(v), 6) for v in p["gamma"]],
            "out_black": [round(float(v), 6) for v in p["out_black"]],
            "out_white": [round(float(v), 6) for v in p["out_white"]],
        },
        "observed_input_range_srgb_0_255": [
            {
                "channel": ch,
                "min_255": round(obs_range[i][0] * 255.0, 1),
                "max_255": round(obs_range[i][1] * 255.0, 1),
                "extrapolated_below_255": round(obs_range[i][0] * 255.0, 1),
                "extrapolated_above_255": round(obs_range[i][1] * 255.0, 1),
            }
            for i, ch in enumerate(["R", "G", "B"])
        ],
    }
    if "matrix" in p:
        out["saturation_equiv"] = round(float(p["sat"]), 6)
        out["matrix_3x3"] = [[round(float(v), 6) for v in row] for row in p["matrix"]]
    if "knots" in p:
        out["curve_knots_x"] = [round(float(v), 6) for v in np.linspace(0.0, 1.0, N_KNOTS)]
        out["curve_knots_rgb"] = {
            ch: [round(float(v), 6) for v in p["knots"][i]]
            for i, ch in enumerate(["R", "G", "B"])
        }
    return out


def main():
    data = load_pair_data()

    # Observed ranges across flat_interior of each pair
    obs_A = [(float(np.percentile(data["A"]["or"][data["A"]["flat"], c], 0.5)),
              float(np.percentile(data["A"]["or"][data["A"]["flat"], c], 99.5))) for c in range(3)]
    obs_B = [(float(np.percentile(data["B"]["or"][data["B"]["flat"], c], 0.5)),
              float(np.percentile(data["B"]["or"][data["B"]["flat"], c], 99.5))) for c in range(3)]
    obs_joint = [(min(obs_A[c][0], obs_B[c][0]), max(obs_A[c][1], obs_B[c][1])) for c in range(3)]

    trA, valA = build_cluster_balanced_samples(data["A"]["or"], data["A"]["ed"], data["A"]["clean"], seed=101)
    trB, valB = build_cluster_balanced_samples(data["B"]["or"], data["B"]["ed"], data["B"]["clean"], seed=202)

    X_tr_J = np.vstack([trA[0], trB[0]])
    Y_tr_J = np.vstack([trA[1], trB[1]])
    W_tr_J = np.concatenate([trA[2], trB[2]])
    X_val_J = np.vstack([valA[0], valB[0]])
    Y_val_J = np.vstack([valA[1], valB[1]])

    base_A_flat = ciede2000_stats(data["A"]["or"][data["A"]["flat"]], data["A"]["ed"][data["A"]["flat"]])
    base_B_flat = ciede2000_stats(data["B"]["or"][data["B"]["flat"]], data["B"]["ed"][data["B"]["flat"]])
    base_A_clean = ciede2000_stats(data["A"]["or"][data["A"]["clean"]], data["A"]["ed"][data["A"]["clean"]])
    base_B_clean = ciede2000_stats(data["B"]["or"][data["B"]["clean"]], data["B"]["ed"][data["B"]["clean"]])

    candidates = {}
    thetas = {}
    for space in ("srgb", "linear"):
        for mtype in ("M1", "M2", "M3"):
            key = f"{mtype}_{space}"
            th = fit_cc_model(X_tr_J, Y_tr_J, W_tr_J, mtype, space, obs_joint)
            thetas[key] = th
            ins_stats = ciede2000_stats(eval_cc(X_tr_J, th, mtype, space), Y_tr_J)
            val_stats = ciede2000_stats(eval_cc(X_val_J, th, mtype, space), Y_val_J)
            flatA_stats = ciede2000_stats(eval_cc(data["A"]["or"][data["A"]["flat"]], th, mtype, space), data["A"]["ed"][data["A"]["flat"]])
            flatB_stats = ciede2000_stats(eval_cc(data["B"]["or"][data["B"]["flat"]], th, mtype, space), data["B"]["ed"][data["B"]["flat"]])
            cleanA_stats = ciede2000_stats(eval_cc(data["A"]["or"][data["A"]["clean"]], th, mtype, space), data["A"]["ed"][data["A"]["clean"]])
            cleanB_stats = ciede2000_stats(eval_cc(data["B"]["or"][data["B"]["clean"]], th, mtype, space), data["B"]["ed"][data["B"]["clean"]])
            candidates[key] = {
                "in_sample_cluster_balanced": ins_stats,
                "held_out_cluster_balanced": val_stats,
                "pairA_flat_interior": flatA_stats,
                "pairB_flat_interior": flatB_stats,
                "pairA_clean_mid_band": cleanA_stats,
                "pairB_clean_mid_band": cleanB_stats,
            }
            print(
                f"{key:10s}: in={ins_stats['median_de00']:.3f}, val={val_stats['median_de00']:.3f} "
                f"| cleanA={cleanA_stats['median_de00']:.3f}, cleanB={cleanB_stats['median_de00']:.3f} "
                f"| fullFlatA={flatA_stats['median_de00']:.3f}, fullFlatB={flatB_stats['median_de00']:.3f}"
            )

    best_space = "srgb" if candidates["M2_srgb"]["held_out_cluster_balanced"]["median_de00"] <= candidates["M2_linear"]["held_out_cluster_balanced"]["median_de00"] else "linear"
    de_m1 = candidates[f"M1_{best_space}"]["held_out_cluster_balanced"]["median_de00"]
    de_m2 = candidates[f"M2_{best_space}"]["held_out_cluster_balanced"]["median_de00"]
    de_m3 = candidates[f"M3_{best_space}"]["held_out_cluster_balanced"]["median_de00"]

    if (de_m1 - de_m2) < 0.25 and (de_m1 - de_m3) < 0.35:
        best_model = "M1"
    elif (de_m2 - de_m3) >= 0.35:
        best_model = "M3"
    else:
        best_model = "M2"

    chosen_key = f"{best_model}_{best_space}"
    print(f"Chosen model: {chosen_key} (held-out DE00: M1={de_m1:.3f}, M2={de_m2:.3f}, M3={de_m3:.3f})")

    th_A = fit_cc_model(trA[0], trA[1], trA[2], best_model, best_space, obs_A)
    th_B = fit_cc_model(trB[0], trB[1], trB[2], best_model, best_space, obs_B)
    th_J = thetas[chosen_key]

    cross_val = {
        "fit_A_test_A_clean": ciede2000_stats(eval_cc(data["A"]["or"][data["A"]["clean"]], th_A, best_model, best_space), data["A"]["ed"][data["A"]["clean"]]),
        "fit_A_test_B_clean": ciede2000_stats(eval_cc(data["B"]["or"][data["B"]["clean"]], th_A, best_model, best_space), data["B"]["ed"][data["B"]["clean"]]),
        "fit_B_test_B_clean": ciede2000_stats(eval_cc(data["B"]["or"][data["B"]["clean"]], th_B, best_model, best_space), data["B"]["ed"][data["B"]["clean"]]),
        "fit_B_test_A_clean": ciede2000_stats(eval_cc(data["A"]["or"][data["A"]["clean"]], th_B, best_model, best_space), data["A"]["ed"][data["A"]["clean"]]),
        "fit_A_test_A_flat": ciede2000_stats(eval_cc(data["A"]["or"][data["A"]["flat"]], th_A, best_model, best_space), data["A"]["ed"][data["A"]["flat"]]),
        "fit_A_test_B_flat": ciede2000_stats(eval_cc(data["B"]["or"][data["B"]["flat"]], th_A, best_model, best_space), data["B"]["ed"][data["B"]["flat"]]),
        "fit_B_test_B_flat": ciede2000_stats(eval_cc(data["B"]["or"][data["B"]["flat"]], th_B, best_model, best_space), data["B"]["ed"][data["B"]["flat"]]),
        "fit_B_test_A_flat": ciede2000_stats(eval_cc(data["A"]["or"][data["A"]["flat"]], th_B, best_model, best_space), data["A"]["ed"][data["A"]["flat"]]),
        "fit_Joint_test_A_flat": candidates[chosen_key]["pairA_flat_interior"],
        "fit_Joint_test_B_flat": candidates[chosen_key]["pairB_flat_interior"],
        "params_A_only": serialize_params(th_A, best_model, best_space, obs_A),
        "params_B_only": serialize_params(th_B, best_model, best_space, obs_B),
        "params_Joint": serialize_params(th_J, best_model, best_space, obs_joint),
    }

    g9 = np.linspace(0.05, 0.95, 9)
    B9, G9, R9 = np.meshgrid(g9, g9, g9, indexing="ij")
    pts9 = np.stack([R9.ravel(), G9.ravel(), B9.ravel()], axis=1)
    outA_9 = eval_cc(pts9, th_A, best_model, best_space) * 255.0
    outB_9 = eval_cc(pts9, th_B, best_model, best_space) * 255.0
    diff_AB_levels = np.abs(outA_9 - outB_9)
    cross_val["A_vs_B_lut_diff_255"] = {
        "median": round(float(np.median(diff_AB_levels)), 2),
        "mean": round(float(np.mean(diff_AB_levels)), 2),
        "p90": round(float(np.percentile(diff_AB_levels, 90)), 2),
    }

    export_cube(os.path.join(REPO, "spec", "look.cube"), th_J, best_model, best_space, size=33)

    cc_A = (eval_cc(data["A"]["or"], th_J, best_model, best_space) * 255.0).round().astype(np.uint8)
    cc_B = (eval_cc(data["B"]["or"], th_J, best_model, best_space) * 255.0).round().astype(np.uint8)
    cv2.imwrite(os.path.join(OUT_DIR, "pairA_cc_only.png"), cv2.cvtColor(cc_A, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(OUT_DIR, "pairB_cc_only.png"), cv2.cvtColor(cc_B, cv2.COLOR_RGB2BGR))
    np.save(os.path.join(OUT_DIR, "theta_joint.npy"), th_J)

    report = {
        "baseline_ungraded": {
            "pairA_flat_interior": base_A_flat,
            "pairB_flat_interior": base_B_flat,
            "pairA_clean_mid_band": base_A_clean,
            "pairB_clean_mid_band": base_B_clean,
        },
        "observed_ranges_0_255": {
            "pairA": [[round(lo * 255, 1), round(hi * 255, 1)] for lo, hi in obs_A],
            "pairB": [[round(lo * 255, 1), round(hi * 255, 1)] for lo, hi in obs_B],
            "joint": [[round(lo * 255, 1), round(hi * 255, 1)] for lo, hi in obs_joint],
        },
        "candidates": candidates,
        "chosen_model": best_model,
        "chosen_space": best_space,
        "chosen_key": chosen_key,
        "chosen_params": cross_val["params_Joint"],
        "cross_validation": cross_val,
    }
    with open(os.path.join(OUT_DIR, "q3_summary.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("Cross-val clean DE00 A->B:", cross_val["fit_A_test_B_clean"]["median_de00"],
          "| B->A:", cross_val["fit_B_test_A_clean"]["median_de00"])
    print("Cross-val fullFlat DE00 A->B:", cross_val["fit_A_test_B_flat"]["median_de00"],
          "| B->A:", cross_val["fit_B_test_A_flat"]["median_de00"],
          "| Joint A/B:", cross_val["fit_Joint_test_A_flat"]["median_de00"], cross_val["fit_Joint_test_B_flat"]["median_de00"])
    print("A vs B LUT diff (0-255):", cross_val["A_vs_B_lut_diff_255"])


if __name__ == "__main__":
    main()
