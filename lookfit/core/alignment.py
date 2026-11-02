"""Multi-candidate geometric & sub-pixel ECC alignment for frame pairs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .colour_spaces import luma_rec709


@dataclass
class AlignmentResult:
    ref_aligned: np.ndarray        # float32 (H_tgt, W_tgt, 3) in [0, 1]
    valid_warp_mask: np.ndarray    # bool (H_tgt, W_tgt)
    warp_matrix_2x3: np.ndarray    # float64 (2, 3) mapping ref coords -> tgt coords
    tx_px: float                   # residual shift relative to uniform scale-to-target (px)
    ty_px: float                   # residual shift relative to uniform scale-to-target (px)
    scale_x: float
    scale_y: float
    rotation_deg: float
    edge_corr_before: float
    edge_corr_after: float
    method: str


def _grad_mag(gray_f32: np.ndarray, blur_sigma: float = 1.0) -> np.ndarray:
    g = cv2.GaussianBlur(gray_f32, (0, 0), blur_sigma)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    p99 = float(np.percentile(mag, 99.0))
    if p99 > 1e-6:
        mag = np.clip(mag / p99, 0.0, 1.5)
    return mag.astype(np.float32)


def _warp_and_score(
    ref_rgb: np.ndarray,
    tgt_grad: np.ndarray,
    tgt_gray: np.ndarray,
    M_ref_to_tgt: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, float]:
    th, tw = tgt_gray.shape[:2]
    rh, rw = ref_rgb.shape[:2]
    warped = cv2.warpAffine(
        ref_rgb,
        M_ref_to_tgt.astype(np.float32),
        (tw, th),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT101,
    )
    warped = np.clip(warped, 0.0, 1.0).astype(np.float32)
    ones = np.ones((rh, rw), dtype=np.float32)
    vmask_f = cv2.warpAffine(
        ones,
        M_ref_to_tgt.astype(np.float32),
        (tw, th),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    vmask = vmask_f >= 0.999
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    vmask = cv2.erode(vmask.astype(np.uint8), kernel) > 0

    coverage = float(vmask.mean())
    if coverage < 0.35:
        return warped, vmask, -1.0

    w_gray = luma_rec709(warped)
    w_grad = _grad_mag(w_gray, blur_sigma=1.0)

    # Interior non-bar region for clean edge correlation
    margin_y = max(8, int(0.04 * th))
    margin_x = max(8, int(0.04 * tw))
    interior = np.zeros_like(vmask)
    interior[margin_y : th - margin_y, margin_x : tw - margin_x] = True
    non_black = (tgt_gray > (8.0 / 255.0)) | (w_gray > (8.0 / 255.0))
    eval_mask = vmask & interior & non_black
    if int(eval_mask.sum()) < 1000:
        eval_mask = vmask
    a = w_grad[eval_mask]
    b = tgt_grad[eval_mask]
    if a.size < 100 or float(a.std()) < 1e-6 or float(b.std()) < 1e-6:
        return warped, vmask, -1.0
    corr = float(np.corrcoef(a, b)[0, 1])
    if not np.isfinite(corr):
        corr = -1.0
    return warped, vmask, corr


def _refine_ecc_on_grad(
    ref_rgb: np.ndarray,
    tgt_grad: np.ndarray,
    M_init: np.ndarray,
    motion_type: int = cv2.MOTION_AFFINE,
) -> Optional[np.ndarray]:
    """Refine a 2x3 ref->tgt matrix via gradient-magnitude ECC (at <=960px working width)."""
    th, tw = tgt_grad.shape[:2]
    rh, rw = ref_rgb.shape[:2]
    ds = min(1.0, 960.0 / float(max(tw, th)))
    ew = max(64, int(round(tw * ds)))
    eh = max(64, int(round(th * ds)))
    S_down = np.array([[ew / float(tw), 0.0, 0.0], [0.0, eh / float(th), 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    S_up = np.linalg.inv(S_down)
    M_work = (S_down @ np.vstack([M_init.astype(np.float64), [0.0, 0.0, 1.0]]))[:2, :]

    warped = cv2.warpAffine(
        ref_rgb,
        M_work.astype(np.float32),
        (ew, eh),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT101,
    )
    ones = np.ones((rh, rw), dtype=np.float32)
    vmask = (
        cv2.warpAffine(ones, M_work.astype(np.float32), (ew, eh), flags=cv2.INTER_NEAREST) > 0.5
    ).astype(np.uint8)
    vmask = cv2.erode(vmask, np.ones((7, 7), np.uint8))
    if int(vmask.sum()) < 1000:
        return None

    w_grad = _grad_mag(luma_rec709(np.clip(warped, 0.0, 1.0)), blur_sigma=1.0)
    t_grad_full = cv2.GaussianBlur(tgt_grad.copy(), (0, 0), 0.8)
    t_grad = cv2.resize(t_grad_full, (ew, eh), interpolation=cv2.INTER_AREA) if ds < 1.0 else t_grad_full

    warp_ecc_work = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 70, 1e-5)
    try:
        _, warp_ecc_work = cv2.findTransformECC(
            t_grad,
            w_grad,
            warp_ecc_work,
            motion_type,
            criteria,
            inputMask=vmask,
            gaussFiltSize=5,
        )
    except cv2.error:
        return None
    A_ecc_work = np.vstack([warp_ecc_work.astype(np.float64), [0.0, 0.0, 1.0]])
    warp_ecc = (S_up @ A_ecc_work @ S_down)[:2, :]

    # warp_ecc maps target coords (dst) -> warped_ref coords (src).
    # Since warped_ref(u) = ref(M_init^-1 u), forward ref->tgt is M_new = (M_init^-1_inv) @ warp_ecc^-1 = warp_ecc^-1 @ M_init!
    A_ecc = np.vstack([warp_ecc.astype(np.float64), [0.0, 0.0, 1.0]])
    A_init = np.vstack([M_init.astype(np.float64), [0.0, 0.0, 1.0]])
    try:
        A_ecc_inv = np.linalg.inv(A_ecc)
    except np.linalg.LinAlgError:
        return None
    # Sanity check: ECC refinement should only make small adjustments (< 25 px, < 5% scale)
    if abs(A_ecc[0, 2]) > 25.0 or abs(A_ecc[1, 2]) > 25.0:
        return None
    if abs(A_ecc[0, 0] - 1.0) > 0.06 or abs(A_ecc[1, 1] - 1.0) > 0.06:
        return None
    A_total = A_ecc_inv @ A_init
    return A_total[:2, :]


def _sift_candidates(ref_gray_u8: np.ndarray, tgt_gray_u8: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    out: List[Tuple[str, np.ndarray]] = []
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    r_eq = clahe.apply(ref_gray_u8)
    t_eq = clahe.apply(tgt_gray_u8)

    sift = cv2.SIFT_create(nfeatures=5000)
    kp1, des1 = sift.detectAndCompute(r_eq, None)
    kp2, des2 = sift.detectAndCompute(t_eq, None)
    if des1 is None or des2 is None or len(kp1) < 6 or len(kp2) < 6:
        return out

    bf = cv2.BFMatcher(cv2.NORM_L2)
    raw_matches = bf.knnMatch(des1, des2, k=2)
    good = [pair[0] for pair in raw_matches if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
    if len(good) < 6:
        return out

    pts1 = np.float32([kp1[m.queryIdx].pt for m in good])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in good])

    m_sim, inl_sim = cv2.estimateAffinePartial2D(
        pts1, pts2, method=cv2.RANSAC, ransacReprojThreshold=3.5, maxIters=3000, confidence=0.995
    )
    if m_sim is not None and inl_sim is not None and int(inl_sim.sum()) >= 6:
        out.append(("sift_similarity", m_sim.astype(np.float64)))

    m_aff, inl_aff = cv2.estimateAffine2D(
        pts1, pts2, method=cv2.RANSAC, ransacReprojThreshold=3.5, maxIters=3000, confidence=0.995
    )
    if m_aff is not None and inl_aff is not None and int(inl_aff.sum()) >= 8:
        out.append(("sift_affine", m_aff.astype(np.float64)))

    return out


def align_pair(ref_rgb: np.ndarray, tgt_rgb: np.ndarray) -> AlignmentResult:
    """Align ref_rgb onto tgt_rgb pixel grid with sub-pixel accuracy."""
    rh, rw = ref_rgb.shape[:2]
    th, tw = tgt_rgb.shape[:2]

    tgt_gray = luma_rec709(tgt_rgb)
    ref_gray = luma_rec709(ref_rgb)
    tgt_grad = _grad_mag(tgt_gray, blur_sigma=1.0)

    # Baseline direct resize matrix: x_tgt = (tw/rw)*x_ref + 0.5*(tw/rw - 1)
    sx0 = float(tw) / float(rw)
    sy0 = float(th) / float(rh)
    M_base = np.array(
        [[sx0, 0.0, 0.5 * (sx0 - 1.0)], [0.0, sy0, 0.5 * (sy0 - 1.0)]],
        dtype=np.float64,
    )
    _, _, corr_before = _warp_and_score(ref_rgb, tgt_grad, tgt_gray, M_base)

    candidates: List[Tuple[str, np.ndarray]] = [("direct_resize", M_base)]

    # Phase correlation on resized gradient magnitude
    w_base, _, _ = _warp_and_score(ref_rgb, tgt_grad, tgt_gray, M_base)
    wb_grad = _grad_mag(luma_rec709(w_base), blur_sigma=1.0)
    hann = cv2.createHanningWindow((tw, th), cv2.CV_32F)
    (dx_pc, dy_pc), resp = cv2.phaseCorrelate(wb_grad.copy(), tgt_grad.copy(), hann)
    if resp > 0.02 and np.hypot(dx_pc, dy_pc) < 0.25 * min(tw, th):
        M_pc = M_base.copy()
        M_pc[0, 2] += dx_pc
        M_pc[1, 2] += dy_pc
        candidates.append(("phase_correlate", M_pc))

    # SIFT candidates (handles crops, zooms, pan, letterbox differences)
    ref_u8 = np.clip(np.rint(ref_gray * 255.0), 0, 255).astype(np.uint8)
    tgt_u8 = np.clip(np.rint(tgt_gray * 255.0), 0, 255).astype(np.uint8)
    candidates.extend(_sift_candidates(ref_u8, tgt_u8))

    # Evaluate coarse candidates and refine top candidates with sub-pixel ECC
    scored: List[Tuple[float, str, np.ndarray]] = []
    for name, M in candidates:
        _, _, c = _warp_and_score(ref_rgb, tgt_grad, tgt_gray, M)
        scored.append((c, name, M))

    scored.sort(key=lambda x: x[0], reverse=True)
    refined_candidates: List[Tuple[float, str, np.ndarray]] = list(scored)

    for _, name, M in scored[:3]:
        for mtype, mtag in [(cv2.MOTION_TRANSLATION, "ecc_trans"), (cv2.MOTION_AFFINE, "ecc_affine")]:
            M_ref = _refine_ecc_on_grad(ref_rgb, tgt_grad, M, motion_type=mtype)
            if M_ref is not None:
                _, _, c_ref = _warp_and_score(ref_rgb, tgt_grad, tgt_gray, M_ref)
                refined_candidates.append((c_ref, f"{name}+{mtag}", M_ref))

    refined_candidates.sort(key=lambda x: x[0], reverse=True)
    best_corr, best_name, best_M = refined_candidates[0]
    warped_best, vmask_best, _ = _warp_and_score(ref_rgb, tgt_grad, tgt_gray, best_M)

    # Extract readable geometric stats
    scale_x = float(np.hypot(best_M[0, 0], best_M[1, 0]))
    scale_y = float(np.hypot(best_M[0, 1], best_M[1, 1]))
    rot_rad = float(np.arctan2(best_M[1, 0], best_M[0, 0]))
    rot_deg = float(np.degrees(rot_rad))

    # Shift of image center relative to direct resize
    cx_ref, cy_ref = 0.5 * (rw - 1.0), 0.5 * (rh - 1.0)
    cx_tgt_pred = best_M[0, 0] * cx_ref + best_M[0, 1] * cy_ref + best_M[0, 2]
    cy_tgt_pred = best_M[1, 0] * cx_ref + best_M[1, 1] * cy_ref + best_M[1, 2]
    tx_px = float(cx_tgt_pred - 0.5 * (tw - 1.0))
    ty_px = float(cy_tgt_pred - 0.5 * (th - 1.0))

    return AlignmentResult(
        ref_aligned=warped_best,
        valid_warp_mask=vmask_best,
        warp_matrix_2x3=best_M,
        tx_px=tx_px,
        ty_px=ty_px,
        scale_x=scale_x,
        scale_y=scale_y,
        rotation_deg=rot_deg,
        edge_corr_before=float(corr_before),
        edge_corr_after=float(best_corr),
        method=best_name,
    )
