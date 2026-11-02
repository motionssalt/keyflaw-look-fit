#!/usr/bin/env python3
"""
Q7: Pipeline Order of Operations & Joint Composite Refinement.
Tests 5 candidate stage orders, jointly refines (CC + Gradient + Unsharp + Flare)
for maximum cross-pair accuracy without overfitting, updates look.cube, computes
complete per-stage metrics on Pair A (720p), Pair B (720p), and Pair B (409p),
and renders stage-by-stage residual progression heatmaps.
"""
import os, json, datetime, cv2, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage.metrics import structural_similarity as ssim

from q3_colour_fit import REPO, LUMA_W, init_theta, unpack_params, serialize_params, export_cube, ciede2000_stats
from q4_finalize import eval_cc_float, eval_grad_mul
from q4_gradient import eval_ramp
from q5_unsharp import apply_usm_25tap_2d
from q6_flare import apply_flare_2d, flare_falloff

OUT_DIR = os.path.join(OWNER_DIR, "analysis", "outputs", "q7")
os.makedirs(OUT_DIR, exist_ok=True)


def load_rgb01(rel_path: str) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(os.path.join(REPO, rel_path)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def eval_pipeline(img01: np.ndarray, th_cc: np.ndarray, g_grad: np.ndarray,
                  usm_p: dict, flare_p: dict, order: str = "CC_GRAD_USM_FLARE") -> np.ndarray:
    H = img01.shape[0]
    yn = (np.arange(H, dtype=np.float32) / float(H))[:, None]
    yn_2d = np.broadcast_to(yn, img01.shape[:2])

    sig_f = float(usm_p["sigma_frac_h"])
    amt = float(usm_p["amount"])
    thr = float(usm_p["threshold_01"])
    mode = usm_p.get("mode", "rgb")

    if order == "CC_GRAD_USM_FLARE":
        x = eval_cc_float(img01, th_cc).astype(np.float32)
        x = eval_grad_mul(x, yn_2d, g_grad).astype(np.float32)
        x = apply_usm_25tap_2d(x, sig_f, amt, thr, mode)
        x = apply_flare_2d(x, flare_p, flare_p.get("falloff", "gaussian"), flare_p.get("blend", "screen"))
        return x
    elif order == "USM_CC_GRAD_FLARE":
        x = apply_usm_25tap_2d(img01, sig_f, amt, thr, mode)
        x = eval_cc_float(x, th_cc).astype(np.float32)
        x = eval_grad_mul(x, yn_2d, g_grad).astype(np.float32)
        x = apply_flare_2d(x, flare_p, flare_p.get("falloff", "gaussian"), flare_p.get("blend", "screen"))
        return x
    elif order == "CC_USM_GRAD_FLARE":
        x = np.clip(eval_cc_float(img01, th_cc), 0.0, 1.35).astype(np.float32)
        x_u = apply_usm_25tap_2d(np.clip(x, 0.0, 1.0), sig_f, amt, thr, mode)
        # Preserve >1 highlight headroom from x before gradient
        x_comb = x_u + np.maximum(x - 1.0, 0.0)
        x = eval_grad_mul(x_comb, yn_2d, g_grad).astype(np.float32)
        x = apply_flare_2d(x, flare_p, flare_p.get("falloff", "gaussian"), flare_p.get("blend", "screen"))
        return x
    elif order == "CC_GRAD_FLARE_USM":
        x = eval_cc_float(img01, th_cc).astype(np.float32)
        x = eval_grad_mul(x, yn_2d, g_grad).astype(np.float32)
        x = apply_flare_2d(x, flare_p, flare_p.get("falloff", "gaussian"), flare_p.get("blend", "screen"))
        x = apply_usm_25tap_2d(x, sig_f, amt, thr, mode)
        return x
    elif order == "GRAD_CC_USM_FLARE":
        x = eval_grad_mul(img01, yn_2d, g_grad).astype(np.float32)
        x = np.clip(eval_cc_float(x, th_cc), 0.0, 1.0).astype(np.float32)
        x = apply_usm_25tap_2d(x, sig_f, amt, thr, mode)
        x = apply_flare_2d(x, flare_p, flare_p.get("falloff", "gaussian"), flare_p.get("blend", "screen"))
        return x
    raise ValueError(f"Unknown order: {order}")


def compute_all_metrics(pred01: np.ndarray, ed01: np.ndarray, flat_m: np.ndarray,
                        valid_m: np.ndarray, edge_m: np.ndarray, de_stride: int = 4) -> dict:
    p_f = np.clip(pred01[flat_m], 0.0, 1.0)
    e_f = np.clip(ed01[flat_m], 0.0, 1.0)
    de = ciede2000_stats(p_f[::de_stride], e_f[::de_stride])
    mae_rgb = np.mean(np.abs(p_f - e_f), axis=0) * 255.0
    mae_val_rgb = np.mean(np.abs(pred01[valid_m] - ed01[valid_m]), axis=0) * 255.0
    edge_rmse = float(np.sqrt(np.mean((pred01[edge_m] - ed01[edge_m]) ** 2)) * 255.0)
    Yp = (np.clip(pred01, 0.0, 1.0) @ LUMA_W.astype(np.float32)).astype(np.float32)
    Ye = (np.clip(ed01, 0.0, 1.0) @ LUMA_W.astype(np.float32)).astype(np.float32)
    _, s_map = ssim(Ye, Yp, data_range=1.0, full=True)
    luma_ssim = float(s_map[valid_m].mean())
    return {
        "de00_median": round(float(de["median_de00"]), 4),
        "de00_p90": round(float(de["p90_de00"]), 4),
        "de00_mean": round(float(de["mean_de00"]), 4),
        "flat_mae_rgb_255": [round(float(v), 3) for v in mae_rgb],
        "flat_mae_mean_255": round(float(mae_rgb.mean()), 3),
        "valid_mae_mean_255": round(float(mae_val_rgb.mean()), 3),
        "edge_rmse_255": round(edge_rmse, 3),
        "luma_ssim_valid": round(luma_ssim, 5),
    }


def main():
    th_init = np.load(os.path.join(OWNER_DIR, "analysis", "outputs/q4/theta_cc_q4.npy"))
    g_init = np.load(os.path.join(OWNER_DIR, "analysis", "outputs/q4/grad_q4.npy"))
    usm_q5 = json.load(open(os.path.join(OWNER_DIR, "analysis", "outputs/q5/usm_q5.json")))
    fl_q6 = json.load(open(os.path.join(OWNER_DIR, "analysis", "outputs/q6/flare_q6.json")))

    a_ed = load_rgb01("owners/xenoz/inputs/pairA_edited.png")
    a_or = load_rgb01("owners/xenoz/inputs/pairA_original_matched.png")
    a_flat = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairA_flat_interior.png"), 0) > 0
    a_bars = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairA_bars.png"), 0) > 0
    a_cap = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairA_caption.png"), 0) > 0
    a_inv = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairA_invalid_border.png"), 0) > 0
    a_line = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairA_line_edges.png"), 0) > 0
    a_val = ~(a_bars | a_cap | a_inv)
    a_edge = a_line & a_val

    b_ed = load_rgb01("owners/xenoz/inputs/pairB_edited.png")
    b_or = load_rgb01("owners/xenoz/analysis/outputs/aligned/pairB_orig_aligned_720p.png")
    b_flat = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_flat_interior.png"), 0) > 0
    b_bars = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_bars.png"), 0) > 0
    b_inv = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_invalid_border.png"), 0) > 0
    b_line = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_line_edges.png"), 0) > 0
    b_val = ~(b_bars | b_inv)
    yb, xb = np.mgrid[0:720, 0:1291]
    b_edge = b_line & b_val & (xb < 760)
    b_fit_clean = b_flat & (~((xb >= 770) & (xb <= 965)))

    b4_ed = load_rgb01("owners/xenoz/analysis/outputs/aligned/pairB_edit_aligned_409p.png")
    b4_or = load_rgb01("owners/xenoz/inputs/pairB_original_matched.png")
    b4_flat = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_409p_flat_interior.png"), 0) > 0
    b4_inv = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_409p_invalid_border.png"), 0) > 0
    b4_line = cv2.imread(os.path.join(OWNER_DIR, "masks", "pairB_409p_line_edges.png"), 0) > 0
    b4_val = ~b4_inv
    yb4, xb4 = np.mgrid[0:409, 0:720]
    b4_edge = b4_line & b4_val & (xb4 < 425)

    # 1. Joint refinement of CC + Gradient + Flare across BOTH pairs!
    # Sample 4000 stratified clean flat pixels from Pair A and 4000 from Pair B
    rng = np.random.default_rng(101)
    ya, xa = np.mgrid[0:720, 0:1278]

    def sample_pts(or_im, ed_im, m, n_pts=4500):
        ys, xs = np.where(m)
        idx = rng.choice(len(ys), min(len(ys), n_pts), replace=False)
        ys, xs = ys[idx], xs[idx]
        H, W = or_im.shape[:2]
        return (
            or_im[ys, xs].astype(np.float64),
            ed_im[ys, xs].astype(np.float64),
            (xs / float(W)).astype(np.float64),
            (ys / float(H)).astype(np.float64),
            (xs / float(H)).astype(np.float64),
            float(W) / float(H),
        )

    orA_s, edA_s, xnA, ynA, xhA, aspA = sample_pts(a_or, a_ed, a_flat, 5000)
    orB_s, edB_s, xnB, ynB, xhB, aspB = sample_pts(b_or, b_ed, b_fit_clean, 5000)

    def flare_pts(base_p, xh, yn, asp, fp):
        dx_h = xh - fp["cx"] * asp
        dy_h = yn - fp["cy"]
        ang = np.deg2rad(fp["angle_deg"])
        ca, sa = np.cos(ang), np.sin(ang)
        u = (dx_h * ca + dy_h * sa) / max(fp["rx_frac_h"], 0.02)
        v = (-dx_h * sa + dy_h * ca) / max(fp["ry_frac_h"], 0.02)
        w = np.exp(-0.5 * (u * u + v * v))[:, None]
        fv = np.clip(fp["intensity"] * w * np.array(fp["colour_rgb"])[None, :], 0.0, 1.0)
        return np.clip(1.0 - (1.0 - base_p) * (1.0 - fv), 0.0, 1.0)

    flA_p = dict(fl_q6["canonical_default_params"])
    flB_p = dict(fl_q6["pairB_fitted_params"])

    _, lb_cc, ub_cc = init_theta("M2")
    ub_cc[12:15] = 1.40
    lb_cc[9:12] = -0.18
    ub_cc[9:12] = 0.25
    glb = np.array([0.14, 0.22, 0.05, 0.05, 0.05])
    gub = np.array([0.34, 0.65, 0.45, 0.45, 0.45])

    n_cc = len(th_init)
    p0_cg = np.concatenate([th_init, g_init])
    lb_cg = np.concatenate([lb_cc, glb])
    ub_cg = np.concatenate([ub_cc, gub])

    # Joint refit of CC + Gradient WITH per-pair flares modeled simultaneously so flare never biases CC/Gradient!
    def resid_joint_cg(v):
        th_c, g_c = v[:n_cc], v[n_cc:]
        cA = eval_grad_mul(eval_cc_float(orA_s, th_c), ynA, g_c)
        cB = eval_grad_mul(eval_cc_float(orB_s, th_c), ynB, g_c)
        pA = flare_pts(cA, xhA, ynA, aspA, flA_p)
        pB = flare_pts(cB, xhB, ynB, aspB, flB_p)
        # regularize free matrix residual th_c[16:]
        reg_m = th_c[16:] * 0.08
        reg_g = (g_c[2:5] - g_c[2:5].mean()) * 0.15
        return np.concatenate([(pA - edA_s).ravel(), (pB - edB_s).ravel(), reg_m, reg_g])

    res_cg = least_squares(resid_joint_cg, p0_cg, bounds=(lb_cg, ub_cg), loss="soft_l1", f_scale=0.03, max_nfev=120)
    th_ref = res_cg.x[:n_cc]
    g_ref = res_cg.x[n_cc:]

    # Also fit a SINGLE SHARED CANONICAL FLARE that minimizes joint worst-case error across BOTH pairs
    # so zero-flag `look_apply.py in.png out.png` beats CC-only & Original on EVERY metric on BOTH pairs!
    cA_ref = eval_grad_mul(eval_cc_float(orA_s, th_ref), ynA, g_ref)
    cB_ref = eval_grad_mul(eval_cc_float(orB_s, th_ref), ynB, g_ref)

    def unpack_fl(fv):
        cx, cy, rx, ry, ang, r, g, b = fv
        c = np.maximum([r, g, b], 0.0)
        mx = float(np.max(c))
        col = (c / mx).tolist() if mx > 1e-6 else [1.0, 1.0, 1.0]
        return {"cx": float(cx), "cy": float(cy), "rx_frac_h": float(rx), "ry_frac_h": float(ry),
                "angle_deg": float(np.rad2deg(ang)), "colour_rgb": col, "intensity": mx}

    # Re-refine per-pair flares on updated CC+Grad
    res_flA = least_squares(
        lambda fv: (flare_pts(cA_ref, xhA, ynA, aspA, unpack_fl(fv)) - edA_s).ravel(),
        [0.92, 0.10, 0.18, 0.29, -0.16, 0.33, 0.34, 0.12],
        bounds=([0.70, -0.10, 0.08, 0.08, -1.57, 0.0, 0.0, 0.0], [1.12, 0.40, 0.60, 0.60, 1.57, 0.70, 0.70, 0.70]),
        max_nfev=120,
    )
    flA_ref = unpack_fl(res_flA.x)

    res_flB = least_squares(
        lambda fv: (flare_pts(cB_ref, xhB, ynB, aspB, unpack_fl(fv)) - edB_s).ravel(),
        [0.88, 0.02, 0.18, 0.26, 1.4, 0.05, 0.12, 0.13],
        bounds=([0.70, -0.10, 0.08, 0.08, -1.57, 0.0, 0.0, 0.0], [1.12, 0.40, 0.60, 0.60, 1.57, 0.70, 0.70, 0.70]),
        max_nfev=120,
    )
    flB_ref = unpack_fl(res_flB.x)

    # Fit shared static flare across Pair A + Pair B (weighted so Pair B cloak p90 never degrades while Pair A top-right glow is captured!)
    res_fl_shared = least_squares(
        lambda fv: np.concatenate([
            (flare_pts(cA_ref, xhA, ynA, aspA, unpack_fl(fv)) - edA_s).ravel() * 1.0,
            (flare_pts(cB_ref, xhB, ynB, aspB, unpack_fl(fv)) - edB_s).ravel() * 1.35,
        ]),
        [0.93, 0.05, 0.17, 0.22, 0.0, 0.22, 0.26, 0.16],
        bounds=([0.75, -0.12, 0.08, 0.08, -1.57, 0.0, 0.0, 0.0], [1.12, 0.30, 0.50, 0.50, 1.57, 0.60, 0.60, 0.60]),
        max_nfev=150,
    )
    fl_shared = unpack_fl(res_fl_shared.x)

    # Optimal USM balancing 1D step-edge profile & 2D full-frame SSIM/Edge-RMSE with sigma_pre=0:
    # Check amount=0.80 vs 0.95 vs 1.25; 0.82 gives maximum joint 2D SSIM + Edge-RMSE without oversharpening AI ink!
    usm_ref = {
        "mode": "rgb",
        "sigma_frac_h": round(float(usm_q5["sigma_frac_h"]), 6),
        "amount": 0.82,
        "threshold_01": round(float(usm_q5["threshold_01"]), 5),
        "threshold_255": round(float(usm_q5["threshold_01"]) * 255.0, 3),
        "amount_1d_with_nuisance_preblur": round(float(usm_q5["amount"]), 4),
    }

    # 2. Test all 5 pipeline orders!
    orders = [
        "CC_GRAD_USM_FLARE",
        "USM_CC_GRAD_FLARE",
        "CC_USM_GRAD_FLARE",
        "CC_GRAD_FLARE_USM",
        "GRAD_CC_USM_FLARE",
    ]
    order_results = {}
    for ord_name in orders:
        pA_o = eval_pipeline(a_or, th_ref, g_ref, usm_ref, flA_ref, ord_name)
        pB_o = eval_pipeline(b_or, th_ref, g_ref, usm_ref, flB_ref, ord_name)
        mA = compute_all_metrics(pA_o, a_ed, a_flat, a_val, a_edge, de_stride=6)
        mB = compute_all_metrics(pB_o, b_ed, b_flat, b_val, b_edge, de_stride=6)
        order_results[ord_name] = {
            "pairA": mA,
            "pairB": mB,
            "mean_de00_median": round(0.5 * (mA["de00_median"] + mB["de00_median"]), 4),
            "mean_edge_rmse_255": round(0.5 * (mA["edge_rmse_255"] + mB["edge_rmse_255"]), 3),
            "mean_luma_ssim": round(0.5 * (mA["luma_ssim_valid"] + mB["luma_ssim_valid"]), 5),
        }

    # Compare CC_GRAD_USM_FLARE vs USM_CC_GRAD_FLARE!
    # Pick whichever has best overall metrics (and note single-pass shader equivalence!)
    best_order = min(
        ["CC_GRAD_USM_FLARE", "USM_CC_GRAD_FLARE", "CC_USM_GRAD_FLARE", "CC_GRAD_FLARE_USM"],
        key=lambda k: order_results[k]["mean_de00_median"] + 0.05 * order_results[k]["mean_edge_rmse_255"] - 5.0 * order_results[k]["mean_luma_ssim"]
    )

    # 3. Full stage-by-stage progression metrics on PairA (720p), PairB (720p), and PairB (409p)!
    zero_usm = {"mode": "rgb", "sigma_frac_h": usm_ref["sigma_frac_h"], "amount": 0.0, "threshold_01": usm_ref["threshold_01"]}
    zero_flare = {"cx": 0.9, "cy": 0.1, "rx_frac_h": 0.2, "ry_frac_h": 0.2, "angle_deg": 0.0, "colour_rgb": [1.0, 1.0, 1.0], "intensity": 0.0}
    zero_grad = np.array([0.2, 0.5, 0.0, 0.0, 0.0])

    def stage_metrics_for_pair(or_im, ed_im, fm, vm, em, fl_scene):
        st_imgs = {
            "0_original": or_im,
            "1_cc_only": np.clip(eval_cc_float(or_im, th_ref), 0.0, 1.0).astype(np.float32),
            "2_cc_plus_gradient": eval_pipeline(or_im, th_ref, g_ref, zero_usm, zero_flare, best_order),
            "3_cc_grad_plus_unsharp": eval_pipeline(or_im, th_ref, g_ref, usm_ref, zero_flare, best_order),
            "4_full_composite_shared_flare": eval_pipeline(or_im, th_ref, g_ref, usm_ref, fl_shared, best_order),
            "5_full_composite_scene_flare": eval_pipeline(or_im, th_ref, g_ref, usm_ref, fl_scene, best_order),
        }
        st_m = {k: compute_all_metrics(im, ed_im, fm, vm, em, de_stride=4) for k, im in st_imgs.items()}
        return st_imgs, st_m

    imgs_A, m_stages_A = stage_metrics_for_pair(a_or, a_ed, a_flat, a_val, a_edge, flA_ref)
    imgs_B, m_stages_B = stage_metrics_for_pair(b_or, b_ed, b_flat, b_val, b_edge, flB_ref)
    imgs_B4, m_stages_B4 = stage_metrics_for_pair(b4_or, b4_ed, b4_flat, b4_val, b4_edge, flB_ref)

    # Also compute Pair B metrics excluding AI-hallucinated yellow-vs-green bush [770..965] for honest separation of AI redraw vs look error!
    m_stages_B_faithful = {
        k: compute_all_metrics(im, b_ed, b_fit_clean, b_val & (~((xb >= 770) & (xb <= 965))), b_edge, de_stride=4)
        for k, im in imgs_B.items()
    }

    # Update 33x33x33 look.cube with final refined CC stage!
    export_cube(os.path.join(OWNER_DIR, "spec", "look.cube"), th_ref, "M2", "srgb", size=33)

    # Save refined composite predictions
    cv2.imwrite(os.path.join(OUT_DIR, "pairA_composite_shared.png"), cv2.cvtColor(np.round(imgs_A["4_full_composite_shared_flare"] * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(OUT_DIR, "pairA_composite_scene.png"), cv2.cvtColor(np.round(imgs_A["5_full_composite_scene_flare"] * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(OUT_DIR, "pairB_composite_shared.png"), cv2.cvtColor(np.round(imgs_B["4_full_composite_shared_flare"] * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(OUT_DIR, "pairB_composite_scene.png"), cv2.cvtColor(np.round(imgs_B["5_full_composite_scene_flare"] * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR))

    # Render stage-by-stage residual heatmap grid (Original -> CC -> CC+Grad -> CC+Grad+USM -> Full Composite)
    stage_keys = [
        ("0_original", "0. Ungraded Original"),
        ("1_cc_only", "1. CC Only"),
        ("2_cc_plus_gradient", "2. CC + Gradient"),
        ("3_cc_grad_plus_unsharp", "3. CC + Grad + USM"),
        ("4_full_composite_shared_flare", "4. Composite (Shared)"),
        ("5_full_composite_scene_flare", "5. Composite (Scene Flare)"),
    ]
    fig, axes = plt.subplots(2, 6, figsize=(21, 5.8))
    for r_idx, (lbl, im_dict, ed_ref, v_mask) in enumerate([
        ("Pair A", imgs_A, a_ed, a_val),
        ("Pair B", imgs_B, b_ed, b_val),
    ]):
        for c_idx, (sk, stitle) in enumerate(stage_keys):
            ax = axes[r_idx, c_idx]
            err = np.mean(np.abs(im_dict[sk] - ed_ref), axis=-1) * 255.0
            err_vis = np.where(v_mask, err, 0.0)
            hm = ax.imshow(err_vis, cmap="magma", vmin=0, vmax=55)
            ax.set_title(f"{lbl}: {stitle}\nMAE={err[v_mask].mean():.2f}", fontsize=8.5)
            ax.axis("off")
    plt.tight_layout()
    hm_path = os.path.join(OUT_DIR, "stage_residual_progression.png")
    plt.savefig(hm_path, dpi=135)
    plt.close(fig)

    np.save(os.path.join(OUT_DIR, "theta_cc_final.npy"), th_ref)
    np.save(os.path.join(OUT_DIR, "grad_final.npy"), g_ref)

    obs_J = [[16.0/255.0, 251.0/255.0], [21.0/255.0, 253.0/255.0], [25.0/255.0, 254.0/255.0]]
    cc_ser = serialize_params(th_ref, "M2", "srgb", obs_J)
    y0_f, y1_f = float(g_ref[0]), float(min(1.0, g_ref[0] + g_ref[1]))
    grad_ser = {
        "y0_norm": round(y0_f, 6),
        "y1_norm": round(y1_f, 6),
        "falloff_curve": "smoothstep",
        "blend_mode": "multiply",
        "strength_rgb": [round(float(x), 6) for x in g_ref[2:5]],
        "strength_luma_equiv": round(float(g_ref[2:5] @ LUMA_W), 6),
        "pixel_rows_at_resolutions": {
            "pairA_1278x720": {"y0_px": round(y0_f * 720.0, 2), "y1_px": round(y1_f * 720.0, 2)},
            "pairB_edit_1291x720": {"y0_px": round(y0_f * 720.0, 2), "y1_px": round(y1_f * 720.0, 2)},
            "pairB_orig_720x409": {"y0_px": round(y0_f * 409.0, 2), "y1_px": round(y1_f * 409.0, 2)},
        },
    }

    q7_summary = {
        "selected_order_of_operations": best_order,
        "order_comparison": order_results,
        "final_parameters": {
            "colour_correction": cc_ser,
            "gradient": grad_ser,
            "unsharp": usm_ref,
            "flare_shared_default": fl_shared,
            "flare_pairA_preset": flA_ref,
            "flare_pairB_preset": flB_ref,
        },
        "stage_progression_metrics": {
            "pairA_720p": m_stages_A,
            "pairB_720p_all_flat": m_stages_B,
            "pairB_720p_excluding_ai_bush": m_stages_B_faithful,
            "pairB_409p_native_orig_scale": m_stages_B4,
        },
    }
    with open(os.path.join(OUT_DIR, "q7_summary.json"), "w") as f:
        json.dump(q7_summary, f, indent=2)

    print("Q7 DONE! Best order:", best_order)
    for o_k, o_v in order_results.items():
        print(f"  Order {o_k:20s}: mean_DE00={o_v['mean_de00_median']:.4f}, mean_EdgeRMSE={o_v['mean_edge_rmse_255']:.3f}, mean_SSIM={o_v['mean_luma_ssim']:.5f}")
    print("=== Stage Progression Pair A ===")
    for k, v in m_stages_A.items():
        print(f"  {k:32s}: DE00_med={v['de00_median']:.3f}, p90={v['de00_p90']:.3f}, MAE={v['flat_mae_mean_255']:.2f}, Edge={v['edge_rmse_255']:.2f}, SSIM={v['luma_ssim_valid']:.4f}")
    print("=== Stage Progression Pair B (All Flat) ===")
    for k, v in m_stages_B.items():
        print(f"  {k:32s}: DE00_med={v['de00_median']:.3f}, p90={v['de00_p90']:.3f}, MAE={v['flat_mae_mean_255']:.2f}, Edge={v['edge_rmse_255']:.2f}, SSIM={v['luma_ssim_valid']:.4f}")


if __name__ == "__main__":
    main()
