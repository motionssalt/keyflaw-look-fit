"""Exact CIEDE2000, channel MAE, masked SSIM, line-art edge-profile RMSE, and noise stats."""
from __future__ import annotations

from typing import Dict, Optional

import cv2
import numpy as np
from scipy.ndimage import map_coordinates
from skimage.metrics import structural_similarity

from .colour_spaces import luma_rec709, srgb_to_lab


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """Vectorized exact Sharma-Wu-Dalal (2005) CIEDE2000 colour difference."""
    L1 = lab1[..., 0].astype(np.float64)
    a1 = lab1[..., 1].astype(np.float64)
    b1 = lab1[..., 2].astype(np.float64)
    L2 = lab2[..., 0].astype(np.float64)
    a2 = lab2[..., 1].astype(np.float64)
    b2 = lab2[..., 2].astype(np.float64)

    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    C_bar = 0.5 * (C1 + C2)
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - np.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))

    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = np.hypot(a1p, b1)
    C2p = np.hypot(a2p, b2)

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    h1p = np.where(C1p < 1e-12, 0.0, h1p)
    h2p = np.where(C2p < 1e-12, 0.0, h2p)

    dLp = L2 - L1
    dCp = C2p - C1p

    prod_C = C1p * C2p
    dh_raw = h2p - h1p
    dhp = np.where(
        prod_C < 1e-12,
        0.0,
        np.where(
            np.abs(dh_raw) <= 180.0,
            dh_raw,
            np.where(dh_raw > 180.0, dh_raw - 360.0, dh_raw + 360.0),
        ),
    )
    dHp = 2.0 * np.sqrt(np.maximum(prod_C, 0.0)) * np.sin(np.radians(0.5 * dhp))

    Lp_bar = 0.5 * (L1 + L2)
    Cp_bar = 0.5 * (C1p + C2p)

    h_sum = h1p + h2p
    hp_bar = np.where(
        prod_C < 1e-12,
        h_sum,
        np.where(
            np.abs(h1p - h2p) <= 180.0,
            0.5 * h_sum,
            np.where(h_sum < 360.0, 0.5 * (h_sum + 360.0), 0.5 * (h_sum - 360.0)),
        ),
    )

    T = (
        1.0
        - 0.17 * np.cos(np.radians(hp_bar - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * hp_bar))
        + 0.32 * np.cos(np.radians(3.0 * hp_bar + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * hp_bar - 63.0))
    )

    d_theta = 30.0 * np.exp(-(((hp_bar - 275.0) / 25.0) ** 2))
    Cp_bar7 = Cp_bar ** 7
    RC = 2.0 * np.sqrt(Cp_bar7 / (Cp_bar7 + 25.0 ** 7))
    Lm50_sq = (Lp_bar - 50.0) ** 2
    SL = 1.0 + (0.015 * Lm50_sq) / np.sqrt(20.0 + Lm50_sq)
    SC = 1.0 + 0.045 * Cp_bar
    SH = 1.0 + 0.015 * Cp_bar * T
    RT = -np.sin(np.radians(2.0 * d_theta)) * RC

    term_L = dLp / SL
    term_C = dCp / SC
    term_H = dHp / SH
    dE = np.sqrt(np.maximum(term_L ** 2 + term_C ** 2 + term_H ** 2 + RT * term_C * term_H, 0.0))
    return dE.astype(np.float32)


def ciede2000_rgb(
    pred_rgb: np.ndarray,
    tgt_rgb: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    if mask is not None:
        p = pred_rgb[mask]
        t = tgt_rgb[mask]
    else:
        p = pred_rgb.reshape(-1, 3)
        t = tgt_rgb.reshape(-1, 3)
    if p.shape[0] == 0:
        return {"median": 0.0, "mean": 0.0, "p90": 0.0, "p95": 0.0}
    de = ciede2000(srgb_to_lab(p), srgb_to_lab(t))
    return {
        "median": float(np.median(de)),
        "mean": float(np.mean(de)),
        "p90": float(np.percentile(de, 90)),
        "p95": float(np.percentile(de, 95)),
    }


def channel_mae(
    pred_rgb: np.ndarray,
    tgt_rgb: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    diff = np.abs(pred_rgb - tgt_rgb) * 255.0
    if mask is not None:
        vals = diff[mask]
    else:
        vals = diff.reshape(-1, 3)
    if vals.shape[0] == 0:
        return {"r_255": 0.0, "g_255": 0.0, "b_255": 0.0, "mean_255": 0.0, "mean_01": 0.0}
    ch = vals.mean(axis=0)
    mean_255 = float(vals.mean())
    return {
        "r_255": float(ch[0]),
        "g_255": float(ch[1]),
        "b_255": float(ch[2]),
        "mean_255": mean_255,
        "mean_01": mean_255 / 255.0,
    }


def compute_ssim(
    pred_rgb: np.ndarray,
    tgt_rgb: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> float:
    p = np.clip(pred_rgb, 0.0, 1.0).astype(np.float32)
    t = np.clip(tgt_rgb, 0.0, 1.0).astype(np.float32)
    score, ssim_map = structural_similarity(
        p, t, data_range=1.0, channel_axis=-1, full=True
    )
    if mask is not None and int(mask.sum()) > 100:
        if ssim_map.ndim == 3:
            ssim_pix = ssim_map.mean(axis=-1)
        else:
            ssim_pix = ssim_map
        return float(ssim_pix[mask].mean())
    return float(score)


def extract_edge_profiles(
    img_luma: np.ndarray,
    anchors_yx: np.ndarray,
    normals_yx: np.ndarray,
    half_width: int = 8,
) -> np.ndarray:
    """Sample 1D perpendicular luma cross-sections of length (2*half_width+1) at edge anchors."""
    offsets = np.arange(-half_width, half_width + 1, dtype=np.float32)[None, :]  # (1, L)
    ys = anchors_yx[:, 0:1] + normals_yx[:, 0:1] * offsets  # (N, L)
    xs = anchors_yx[:, 1:2] + normals_yx[:, 1:2] * offsets  # (N, L)
    coords = np.stack([ys.ravel(), xs.ravel()], axis=0)
    sampled = map_coordinates(img_luma, coords, order=1, mode="nearest")
    return sampled.reshape(anchors_yx.shape[0], -1)


def find_edge_anchors(
    ref_luma: np.ndarray,
    active_mask: np.ndarray,
    max_anchors: int = 1200,
    half_width: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministically select clean gradient-maximum edge anchor points and unit normals."""
    h, w = ref_luma.shape
    blur = cv2.GaussianBlur(ref_luma, (0, 0), 1.0)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)

    pad = half_width + 3
    inner = np.zeros_like(active_mask)
    if h > 2 * pad and w > 2 * pad:
        inner[pad : h - pad, pad : w - pad] = True
    cand_mask = active_mask & inner
    if int(cand_mask.sum()) < 50:
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32)

    thr = max(0.08, float(np.percentile(mag[cand_mask], 88)))
    # Local 3x3 non-max suppression on gradient magnitude
    dil = cv2.dilate(mag, np.ones((3, 3), np.uint8))
    peaks = cand_mask & (mag >= thr) & (mag >= dil - 1e-6)
    ys, xs = np.nonzero(peaks)
    if ys.size == 0:
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32)

    if ys.size > max_anchors:
        # Uniform deterministic stride across sorted coordinates for full spatial coverage
        idx = np.linspace(0, ys.size - 1, max_anchors, dtype=np.int64)
        ys, xs = ys[idx], xs[idx]

    g_x = gx[ys, xs]
    g_y = gy[ys, xs]
    nrm = np.maximum(np.hypot(g_x, g_y), 1e-6)
    normals_yx = np.stack([g_y / nrm, g_x / nrm], axis=-1).astype(np.float32)
    anchors_yx = np.stack([ys.astype(np.float32), xs.astype(np.float32)], axis=-1)
    return anchors_yx, normals_yx


def edge_profile_metrics(
    pred_rgb: np.ndarray,
    tgt_rgb: np.ndarray,
    ref_rgb: np.ndarray,
    active_mask: np.ndarray,
    half_width: int = 8,
) -> Dict[str, object]:
    """Compute perpendicular edge-profile RMSE (both raw and DC-removed halo/slope RMSE in /255)."""
    ref_l = luma_rec709(ref_rgb)
    pred_l = luma_rec709(pred_rgb)
    tgt_l = luma_rec709(tgt_rgb)

    anchors, normals = find_edge_anchors(ref_l, active_mask, max_anchors=1200, half_width=half_width)
    if anchors.shape[0] == 0:
        return {
            "raw_rmse_255": 0.0,
            "halo_rmse_255": 0.0,
            "n_profiles": 0,
            "mean_pred_profile": [0.0] * (2 * half_width + 1),
            "mean_tgt_profile": [0.0] * (2 * half_width + 1),
            "mean_ref_profile": [0.0] * (2 * half_width + 1),
        }

    prof_ref = extract_edge_profiles(ref_l, anchors, normals, half_width=half_width)
    prof_pred = extract_edge_profiles(pred_l, anchors, normals, half_width=half_width)
    prof_tgt = extract_edge_profiles(tgt_l, anchors, normals, half_width=half_width)

    raw_diff = (prof_pred - prof_tgt) * 255.0
    raw_rmse = float(np.sqrt(np.mean(raw_diff ** 2)))

    # Remove per-profile mean so local colour offset doesn't mask overshoot/halo shape
    pred_zero = prof_pred - prof_pred.mean(axis=1, keepdims=True)
    tgt_zero = prof_tgt - prof_tgt.mean(axis=1, keepdims=True)
    ref_zero = prof_ref - prof_ref.mean(axis=1, keepdims=True)
    halo_diff = (pred_zero - tgt_zero) * 255.0
    halo_rmse = float(np.sqrt(np.mean(halo_diff ** 2)))

    return {
        "raw_rmse_255": raw_rmse,
        "halo_rmse_255": halo_rmse,
        "n_profiles": int(anchors.shape[0]),
        "mean_pred_profile": (pred_zero.mean(axis=0) * 255.0).tolist(),
        "mean_tgt_profile": (tgt_zero.mean(axis=0) * 255.0).tolist(),
        "mean_ref_profile": (ref_zero.mean(axis=0) * 255.0).tolist(),
    }


def noise_statistics(
    img_rgb: np.ndarray,
    ref_rgb: np.ndarray,
    flat_mask: np.ndarray,
) -> Dict[str, object]:
    """Measure flat-area high-frequency noise std, luma dependence, grain size, and 8x8 blockiness."""
    img_l = luma_rec709(img_rgb)
    ref_l = luma_rec709(ref_rgb)

    # Exact impulse gain of (I - GaussianBlur(sigma=1.4)) so white noise std is unbiased
    imp = np.zeros((15, 15), dtype=np.float32)
    imp[7, 7] = 1.0
    hp_imp = imp - cv2.GaussianBlur(imp, (0, 0), 1.4)
    hp_gain = float(np.sqrt(np.sum(hp_imp * hp_imp)))

    hp_img = (img_l - cv2.GaussianBlur(img_l, (0, 0), 1.4)) / hp_gain
    hp_ref = (ref_l - cv2.GaussianBlur(ref_l, (0, 0), 1.4)) / hp_gain

    if int(flat_mask.sum()) < 200:
        return {
            "tgt_std_255": 0.0,
            "ref_std_255": 0.0,
            "excess_std_255": 0.0,
            "blockiness_ratio": 1.0,
            "corr_lag1": 0.0,
            "luma_bin_excess_std_255": [0.0] * 5,
        }

    # Robust MAD-based std in /255 units so residual micro-textures don't inflate std
    def _mad_std(arr: np.ndarray) -> float:
        if arr.size < 20:
            return 0.0
        med = float(np.median(arr))
        return float(1.4826 * np.median(np.abs(arr - med)) * 255.0)

    tgt_std = _mad_std(hp_img[flat_mask])
    ref_std = _mad_std(hp_ref[flat_mask])
    excess_var = max(0.0, tgt_std ** 2 - ref_std ** 2)
    excess_std = float(np.sqrt(excess_var))

    # Luma-binned excess std across 5 tonal bands [0..0.2..0.4..0.6..0.8..1.0]
    bins = np.linspace(0.0, 1.0, 6)
    bin_excess = []
    for i in range(5):
        bm = flat_mask & (img_l >= bins[i]) & (img_l < (bins[i + 1] + (1e-4 if i == 4 else 0.0)))
        if int(bm.sum()) >= 80:
            s_t = _mad_std(hp_img[bm])
            s_r = _mad_std(hp_ref[bm])
            bin_excess.append(float(np.sqrt(max(0.0, s_t ** 2 - s_r ** 2))))
        else:
            bin_excess.append(excess_std)

    # Spatial lag-1 autocorrelation inside flat_mask (estimates grain size > 1 px)
    m_h = flat_mask[:, :-1] & flat_mask[:, 1:]
    if int(m_h.sum()) > 200:
        a = hp_img[:, :-1][m_h]
        b = hp_img[:, 1:][m_h]
        sa, sb = float(a.std()), float(b.std())
        corr_lag1 = float(np.corrcoef(a, b)[0, 1]) if (sa > 1e-6 and sb > 1e-6) else 0.0
    else:
        corr_lag1 = 0.0

    # 8x8 DCT block-boundary ratio to separate MPEG/H.264 blockiness from genuine film grain
    h, w = img_l.shape
    dx = np.abs(img_l[:, 1:] - img_l[:, :-1])
    m_dx = flat_mask[:, 1:] & flat_mask[:, :-1]
    xs = np.arange(1, w)[None, :]
    is_b8 = np.broadcast_to((xs % 8) == 0, dx.shape)
    b_vals = dx[m_dx & is_b8]
    nb_vals = dx[m_dx & (~is_b8)]
    if b_vals.size > 50 and nb_vals.size > 50 and float(nb_vals.mean()) > 1e-6:
        blockiness_ratio = float(b_vals.mean() / nb_vals.mean())
    else:
        blockiness_ratio = 1.0

    return {
        "tgt_std_255": tgt_std,
        "ref_std_255": ref_std,
        "excess_std_255": excess_std,
        "blockiness_ratio": blockiness_ratio,
        "corr_lag1": corr_lag1,
        "luma_bin_excess_std_255": bin_excess,
    }
