"""Lossless image I/O, pair loading, and input checksum immutability checks."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import numpy as np


@dataclass
class FramePair:
    owner_slug: str
    pair_id: str
    ref_path: Path
    tgt_path: Path
    ref_rgb: np.ndarray  # float32 (H_ref, W_ref, 3) in [0, 1]
    tgt_rgb: np.ndarray  # float32 (H_tgt, W_tgt, 3) in [0, 1]


def read_rgb_float(path: str | Path) -> np.ndarray:
    """Read an image file into a fresh float32 RGB array in [0, 1] without modifying disk."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Failed to decode image: {p}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return (rgb.astype(np.float32) / 255.0).copy()


def write_rgb_png(path: str | Path, img_rgb: np.ndarray) -> None:
    """Save a float32 [0, 1] RGB image to lossless 8-bit PNG."""
    p = Path(path)
    if "inputs" in p.parts:
        raise PermissionError(f"Refusing to write inside inputs/ directory: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    arr = np.clip(np.rint(img_rgb * 255.0), 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(p), bgr)
    if not ok:
        raise IOError(f"Failed to write PNG: {p}")


def write_rgb_jpg(path: str | Path, img_rgb: np.ndarray, quality: int = 88) -> None:
    """Save a float32 [0, 1] RGB image to compressed JPEG for compact repo diagnostics."""
    p = Path(path)
    if "inputs" in p.parts:
        raise PermissionError(f"Refusing to write inside inputs/ directory: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    arr = np.clip(np.rint(img_rgb * 255.0), 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(p), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise IOError(f"Failed to write JPEG: {p}")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs_untouched(repo_root: str | Path) -> bool:
    """Verify every input file listed in root BUILD_STATE.json matches its original SHA-256."""
    root = Path(repo_root)
    bs_path = root / "BUILD_STATE.json"
    if not bs_path.exists():
        raise FileNotFoundError(f"BUILD_STATE.json missing at {bs_path}")
    data = json.loads(bs_path.read_text(encoding="utf-8"))
    for owner in data.get("owners", []):
        for item in owner.get("inputs", []):
            fpath = root / item["file"]
            if not fpath.exists():
                raise FileNotFoundError(f"Missing ground-truth input: {fpath}")
            actual = sha256_file(fpath)
            expected = item["sha256"]
            if actual != expected:
                raise ValueError(
                    f"Input file checksum mismatch for {item['file']}: expected {expected}, got {actual}"
                )
    return True


def list_owners(repo_root: str | Path) -> List[str]:
    root = Path(repo_root) / "owners"
    if not root.exists():
        return []
    return sorted(
        d.name for d in root.iterdir() if d.is_dir() and (d / "inputs").is_dir()
    )


def load_owner_pairs(repo_root: str | Path, owner_slug: str) -> List[FramePair]:
    """Load all matched pairs for an owner. Never ranks, weights, or excludes pairs."""
    in_dir = Path(repo_root) / "owners" / owner_slug / "inputs"
    if not in_dir.is_dir():
        raise FileNotFoundError(f"Owner inputs directory not found: {in_dir}")
    edited_files = sorted(in_dir.glob("*_edited.png"))
    if not edited_files:
        raise ValueError(f"No *_edited.png files found in {in_dir}")
    pairs: List[FramePair] = []
    for ed_path in edited_files:
        stem = ed_path.name[: -len("_edited.png")]
        orig_path = in_dir / f"{stem}_original_matched.png"
        if not orig_path.exists():
            raise FileNotFoundError(f"Missing matched reference for {ed_path.name}: {orig_path}")
        pairs.append(
            FramePair(
                owner_slug=owner_slug,
                pair_id=stem,
                ref_path=orig_path,
                tgt_path=ed_path,
                ref_rgb=read_rgb_float(orig_path),
                tgt_rgb=read_rgb_float(ed_path),
            )
        )
    return pairs
