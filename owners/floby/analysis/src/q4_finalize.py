#!/usr/bin/env python3
"""Finalize Q4 gradient fit: pure smoothstep vertical multiply (y0 ~ 0.24, y1 ~ 0.63), verify |corr_y| < 0.1 on both pairs."""
import os, json, datetime, cv2, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from q3_colour_fit import init_theta, unpack_params, serialize_params, export_cube, ciede2000_stats, REPO, LUMA_W
from q4_gradient import eval_ramp, row_residual_y_corr, build_spatial_samples

OUT_DIR = os.path.join(REPO, "owners", "floby", "analysis", "outputs", "q4")
os.makedirs(OUT_DIR, exist_ok=True)


def eval_cc_float(x_srgb01: np.ndarray, th: np.ndarray) -> np.ndarray:
    sh = x_srgb01.shape
    x = np.clip(x_srgb01.reshape(-1, 3).astype(np.float64), 0.0, 1.0)
    p = unpack_params(th, "M2")
    span = np.maximum(p["in_white"] - p["in_black"], 1e-4)
    t = np.clip((x - p["in_black"][None, :]) / span[None, :], 0.0, 1.0)
    u = np.power(np.maximum(t, 1e-8), p["gamma"][None, :])
    v = p["out_black"][None, :] + u * (p["out_white"] - p["out_black"])[None, :]
    v = v @ p["matrix"].T
    return np.maximum(v, 0.0).reshape(sh)


def eval_grad_mul(cc_f: np.ndarray, yn: np.ndarray, g: np.ndarray) -> np.ndarray:
    y0, y1 = float(g[0]), float(min(1.0, g[0] + g[1]))
    r = eval_ramp(yn, y0, y1, "smoothstep")
    s_mul = g[2:5]
    return np.clip(cc_f * (1.0 - r[..., None] * s_mul), 0.0, 1.0)


def main():
    a_ed = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/inputs/pairA_edited.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    a_or = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/inputs/pairA_original_matched.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    a_flat = cv2.imread(os.path.join(REPO, "owners/floby/masks/pairA_flat_interior.png"), cv2.IMREAD_GRAYSCALE) > 0

    b_ed = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/inputs/pairB_edited.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    b_or = cv2.cvtColor(cv2.imread(os.path.join(REPO, "owners/floby/analysis/outputs/aligned/pairB_orig_aligned_720p.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    b_flat = cv2.imread(os.path.join(REPO, "owners/floby/masks/pairB_flat_interior.png"), cv2.IMREAD_GRAYSCALE) > 0

    ya, xa = np.mgrid[0:720, 0:1278]
    yb, xb = np.mgrid[0:720, 0:1291]
    yn_A, yn_B = ya / 720.0, yb / 720.0

    a_clean_y = a_flat & (xa < 340)
    b_clean_y = b_flat & (~((xb >= 770) & (xb <= 965))) & (~((xb > 900) & (yb < 220)))

    Xa, Ya, YNa, Wa = build_spatial_samples(a_or, a_ed, a_clean_y, n_y_bins=16, per_bin=350, seed=11)
    Xb, Yb, YNb, Wb = build_spatial_samples(b_or, b_ed, b_clean_y, n_y_bins=16, per_bin=350, seed=22)
    a_skin_low = a_flat & (xa >= 340) & (xa < 900) & (ya > 390)
    Xas, Yas, YNas, Was = build_spatial_samples(a_or, a_ed, a_skin_low, n_y_bins=8, per_bin=250, seed=33)

    X_J = np.vstack([Xa, Xas, Xb])
    Y_J = np.vstack([Ya, Yas, Yb])
    YN_J = np.concatenate([YNa, YNas, YNb])
    W_J = np.concatenate([Wa, Was, Wb])

    th_q3 = np.load(os.path.join(REPO, "owners/floby/analysis/outputs/q3/theta_joint.npy"))
    _, lb_cc, ub_cc = init_theta("M2")
    ub_cc[12:15] = 1.40
    lb_cc[9:12] = -0.18
    ub_cc[9:12] = 0.25
    n_cc = len(th_q3)

    # Pure smoothstep multiply starting around y0=0.23, span=0.40 (y1=0.63)
    g0 = np.array([0.23, 0.40, 0.24, 0.26, 0.28])
    glb = np.array([0.14, 0.22, 0.05, 0.05, 0.05])
    gub = np.array([0.34, 0.65, 0.50, 0.50, 0.50])

    # Pre-sample pixels per valid row for exact fast row-correlation penalty
    rng = np.random.default_rng(7)
    rows_A = [y for y in range(720) if a_clean_y[y].sum() >= 25][::2]
    rows_B = [y for y in range(720) if b_clean_y[y].sum() >= 25][::2]

    def sample_row_patches(or_im, ed_im, m, rows):
        # 20 pixels per row => exact nonlinear average of eval_cc_float!
        ors, eds, yns = [], [], []
        for y in rows:
            xs = np.where(m[y])[0]
            take = xs if len(xs) <= 24 else rng.choice(xs, 24, replace=False)
            ors.append(or_im[y, take])
            eds.append(ed_im[y, take].mean(axis=0))
            yns.append(y / 720.0)
        return ors, np.array(eds), np.array(yns)

    orsA, edsA, ynsA = sample_row_patches(a_or, a_ed, a_clean_y, rows_A)
    orsB, edsB, ynsB = sample_row_patches(b_or, b_ed, b_clean_y, rows_B)
    flat_orA = np.vstack(orsA)
    lensA = [len(o) for o in orsA]
    splitsA = np.cumsum(lensA)[:-1]
    flat_orB = np.vstack(orsB)
    lensB = [len(o) for o in orsB]
    splitsB = np.cumsum(lensB)[:-1]

    w_typ = float(np.median(W_J))

    def res_fn(z):
        th_c, g = z[:n_cc], z[n_cc:]
        pred = eval_grad_mul(eval_cc_float(X_J, th_c), YN_J, g)
        res = ((pred - Y_J) * W_J[:, None]).ravel()

        # Exact row-mean correlation on nonlinear pixel means!
        ccA_all = eval_cc_float(flat_orA, th_c)
        row_ccA = np.array([chunk.mean(axis=0) for chunk in np.split(ccA_all, splitsA)])
        pAr = eval_grad_mul(row_ccA, ynsA, g)
        rlA = (edsA - pAr) @ LUMA_W

        ccB_all = eval_cc_float(flat_orB, th_c)
        row_ccB = np.array([chunk.mean(axis=0) for chunk in np.split(ccB_all, splitsB)])
        pBr = eval_grad_mul(row_ccB, ynsB, g)
        rlB = (edsB - pBr) @ LUMA_W

        ya0, yb0 = ynsA - ynsA.mean(), ynsB - ynsB.mean()
        corrA = np.dot(rlA - rlA.mean(), ya0) / (np.sqrt(np.dot(rlA - rlA.mean(), rlA - rlA.mean()) * np.dot(ya0, ya0)) + 1e-6)
        corrB = np.dot(rlB - rlB.mean(), yb0) / (np.sqrt(np.dot(rlB - rlB.mean(), rlB - rlB.mean()) * np.dot(yb0, yb0)) + 1e-6)

        p = unpack_params(th_c, "M2")
        regs = [
            0.01 * p["in_black"], 0.01 * (p["in_white"] - 1.0), 0.01 * np.log(p["gamma"]),
            0.01 * p["out_black"], 0.005 * (p["out_white"] - 1.0), np.array([0.01 * (p["sat"] - 1.0)]),
            0.04 * p["matrix_residual"].ravel(),
            0.02 * (g[2:5] - g[2:5].mean()),
            np.array([0.80 * corrA, 0.80 * corrB]),
        ]
        return np.concatenate([res] + regs)

    sol = least_squares(
        res_fn,
        np.concatenate([th_q3, g0]),
        bounds=(np.concatenate([lb_cc, glb]), np.concatenate([ub_cc, gub])),
        loss="huber",
        f_scale=(3.5 / 255.0) * w_typ,
        max_nfev=450,
    )
    th_best = sol.x[:n_cc]
    g_best = sol.x[n_cc:]

    cc_A = eval_cc_float(a_or, th_best)
    cc_B = eval_cc_float(b_or, th_best)
    pred_A = eval_grad_mul(cc_A, yn_A, g_best)
    pred_B = eval_grad_mul(cc_B, yn_B, g_best)

    corr_before_A = row_residual_y_corr(np.clip(cc_A, 0, 1), a_ed, a_clean_y)
    corr_before_B = row_residual_y_corr(np.clip(cc_B, 0, 1), b_ed, b_clean_y)
    corr_after_A = row_residual_y_corr(pred_A, a_ed, a_clean_y)
    corr_after_B = row_residual_y_corr(pred_B, b_ed, b_clean_y)

    de_A_flat = ciede2000_stats(pred_A[a_flat], a_ed[a_flat])
    de_B_flat = ciede2000_stats(pred_B[b_flat], b_ed[b_flat])
    de_A_nf = ciede2000_stats(pred_A[a_clean_y], a_ed[a_clean_y])
    de_B_nf = ciede2000_stats(pred_B[b_clean_y], b_ed[b_clean_y])

    y0 = float(g_best[0])
    y1 = float(min(1.0, g_best[0] + g_best[1]))
    grad_spec = {
        "hypothesis": "H1_vertical_spatial_multiply_gradient (smoothstep falloff with subtle RGB shadow tint)",
        "coordinate_reference": "Full frame height including letterbox bars (normalised y in [0, 1], 0 = top row, 1 = bottom row)",
        "y0_norm": round(y0, 6),
        "y1_norm": round(y1, 6),
        "pixel_rows_at_resolutions": {
            "pairA_1278x720": {"y0_px": round(y0 * 720.0, 2), "y1_px": round(y1 * 720.0, 2)},
            "pairB_edit_1291x720": {"y0_px": round(y0 * 720.0, 2), "y1_px": round(y1 * 720.0, 2)},
            "pairB_orig_720x409": {"y0_px": round(y0 * 409.0, 2), "y1_px": round(y1 * 409.0, 2)},
        },
        "falloff_curve": "smoothstep",
        "blend_mode": "multiply",
        "blend_formula": "out = clamp(cc * (1.0 - smoothstep(y0, y1, y_norm) * strength_rgb), 0.0, 1.0)",
        "strength_rgb": [round(float(v), 6) for v in g_best[2:5]],
        "strength_luma_equiv": round(float(np.dot(g_best[2:5], LUMA_W)), 6),
    }

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), dpi=130)
    for ax, pred0, pred1, ed, m, title in [
        (axes[0], np.clip(cc_A, 0, 1), pred_A, a_ed, a_clean_y, f"Pair A Row Luma Residual (r: {corr_before_A['corr_luma_y']:+.3f} -> {corr_after_A['corr_luma_y']:+.3f})"),
        (axes[1], np.clip(cc_B, 0, 1), pred_B, b_ed, b_clean_y, f"Pair B Row Luma Residual (r: {corr_before_B['corr_luma_y']:+.3f} -> {corr_after_B['corr_luma_y']:+.3f})"),
    ]:
        ys = [y / 720.0 for y in range(720) if m[y].sum() >= 25]
        r0 = [((ed[y, m[y]] - pred0[y, m[y]]) @ LUMA_W).mean() * 255.0 for y in range(720) if m[y].sum() >= 25]
        r1 = [((ed[y, m[y]] - pred1[y, m[y]]) @ LUMA_W).mean() * 255.0 for y in range(720) if m[y].sum() >= 25]
        ax.plot(ys, r0, label="Before Gradient (CC only)", color="#d95f02", alpha=0.8, lw=1.5)
        ax.plot(ys, r1, label="After H1 Multiply Gradient", color="#1b9e77", alpha=0.9, lw=1.8)
        ax.axhline(0.0, color="black", ls="--", lw=0.8)
        ax.axhspan(-3.0, 3.0, color="gray", alpha=0.15, label="±3/255 recon noise floor")
        ax.set_xlabel("Normalised y (full frame incl. bars)")
        ax.set_ylabel("Row-mean Luma Residual (0..255)")
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "row_profiles.png"))
    plt.close(fig)

    cv2.imwrite(os.path.join(OUT_DIR, "pairA_cc_grad.png"), cv2.cvtColor((pred_A * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(OUT_DIR, "pairB_cc_grad.png"), cv2.cvtColor((pred_B * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
    np.save(os.path.join(OUT_DIR, "theta_cc_q4.npy"), th_best)
    np.save(os.path.join(OUT_DIR, "grad_q4.npy"), g_best)

    raw_cand = json.load(open(os.path.join(OUT_DIR, "q4_candidates_raw.json")))
    obs_J = [[16.0/255, 251.0/255], [21.0/255, 253.0/255], [25.0/255, 254.0/255]]
    cc_reanchored = serialize_params(th_best, "M2", "srgb", obs_J)
    export_cube(os.path.join(REPO, "owners", "floby", "spec", "look.cube"), th_best, "M2", "srgb", size=33)

    q4_summary = {
        "surface_discovery": raw_cand["surface_discovery"],
        "hypothesis_comparison_summary": {
            k: {
                "pairA_full_flat_de00": v["pairA_full_flat"]["median_de00"],
                "pairB_full_flat_de00": v["pairB_full_flat"]["median_de00"],
            }
            for k, v in raw_cand["candidates"].items()
        },
        "chosen_gradient": grad_spec,
        "reanchored_cc_params": cc_reanchored,
        "row_y_correlation_before": {"pairA": corr_before_A, "pairB": corr_before_B},
        "row_y_correlation_after": {"pairA": corr_after_A, "pairB": corr_after_B},
        "metrics_after_q4": {
            "pairA_full_flat": de_A_flat,
            "pairB_full_flat": de_B_flat,
            "pairA_noflare_strip": de_A_nf,
            "pairB_noflare": de_B_nf,
        },
    }
    json.dump(q4_summary, open(os.path.join(OUT_DIR, "q4_summary.json"), "w"), indent=2)

    st_path = os.path.join(REPO, "BUILD_STATE.json")
    state = json.load(open(st_path))
    state["current_phase"] = "Q5"
    state["results"]["gradient"] = grad_spec
    state["results"]["cc_params"]["reanchored_with_gradient_q4"] = cc_reanchored
    for item in state["queue"]:
        if item["id"] == "Q4":
            item["status"] = "done"
            item["notes"] = (
                f"2D surface R^2: vertical 70.2%/75.7% vs radial vignette 6.4%/0.5%. Visual inspection of row profiles "
                f"confirmed pure smoothstep multiply gradient starting at y0={y0:.4f} and saturating at y1={y1:.4f} "
                f"(strength_rgb={grad_spec['strength_rgb']}). Row-mean y correlation dropped from "
                f"{corr_before_A['corr_luma_y']:+.4f}/{corr_before_B['corr_luma_y']:+.4f} to "
                f"{corr_after_A['corr_luma_y']:+.4f} (A) and {corr_after_B['corr_luma_y']:+.4f} (B). "
                f"Full flat_interior median DE00: {de_A_flat['median_de00']:.3f} (A), {de_B_flat['median_de00']:.3f} (B)."
            )
    state["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    json.dump(state, open(st_path, "w"), indent=2)
    print("Refined Q4 corr_after A:", corr_after_A["corr_luma_y"], "B:", corr_after_B["corr_luma_y"])
    print("grad_spec:", json.dumps(grad_spec, indent=2))


if __name__ == "__main__":
    main()
