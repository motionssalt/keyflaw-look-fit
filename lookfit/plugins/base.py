"""Base plugin interface, parameter specifications, evidence records, and context helpers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from lookfit.core.masks import PairMasks, build_pair_masks


@dataclass
class ParamSpec:
    name: str
    default: Any
    min_val: Optional[float]
    max_val: Optional[float]
    unit: str
    scale_law: str  # e.g. "dimensionless", "fraction_of_height", "0_255_gate", "rgb_0_1", "categorical"
    description: str = ""


@dataclass
class Evidence:
    plugin_name: str
    status: str  # "present", "weak", "absent", "not_provable"
    score: float  # 0.0+ strength of evidence
    notes: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    mask_of_interest: Optional[np.ndarray] = None


@dataclass
class PairContext:
    pair_id: str
    masks: PairMasks
    orig_ref_rgb: Optional[np.ndarray] = None  # clean aligned reference before any plugin layers
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FitReport:
    plugin_name: str
    accepted_hint: bool
    train_loss_before: float
    train_loss_after: float
    held_out_loss_before: float
    held_out_loss_after: float
    held_out_rel_gain: float
    fold_losses_before: List[float] = field(default_factory=list)
    fold_losses_after: List[float] = field(default_factory=list)
    notes: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)


ImageOrList = Union[np.ndarray, Sequence[np.ndarray]]
ContextOrList = Union[PairContext, Sequence[PairContext], None]


def normalize_pair_inputs(
    ref_in: ImageOrList,
    tgt: ImageOrList,
    ctx: ContextOrList = None,
) -> List[Tuple[np.ndarray, np.ndarray, PairContext]]:
    """Normalize single-image or multi-pair inputs into a uniform list of (ref_in, tgt, PairContext)."""
    if isinstance(ref_in, np.ndarray) and ref_in.ndim == 3:
        assert isinstance(tgt, np.ndarray) and tgt.ndim == 3
        if ctx is None:
            vmask = np.ones(tgt.shape[:2], dtype=bool)
            pm = build_pair_masks(ref_in, tgt, vmask)
            pctx = PairContext(pair_id="pair0", masks=pm, orig_ref_rgb=ref_in)
        elif isinstance(ctx, PairContext):
            pctx = ctx
        else:
            raise TypeError(f"Unexpected ctx for single pair: {type(ctx)}")
        return [(ref_in.astype(np.float32), tgt.astype(np.float32), pctx)]

    refs = list(ref_in)
    tgts = list(tgt)
    assert len(refs) == len(tgts) and len(refs) > 0
    if ctx is None:
        ctxs = [
            PairContext(
                pair_id=f"pair{i}",
                masks=build_pair_masks(r, t, np.ones(t.shape[:2], dtype=bool)),
                orig_ref_rgb=r,
            )
            for i, (r, t) in enumerate(zip(refs, tgts))
        ]
    else:
        ctxs = list(ctx)  # type: ignore[arg-type]
        assert len(ctxs) == len(refs)
    return [
        (r.astype(np.float32), t.astype(np.float32), c)
        for r, t, c in zip(refs, tgts, ctxs)
    ]


class Plugin(ABC):
    """Abstract base class for every look-fit effect plugin."""

    name: str = "base"
    param_spec: List[ParamSpec] = []

    @abstractmethod
    def detect(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Evidence:
        """Measure whether target exhibits this effect beyond reference."""

    @abstractmethod
    def initial_guess(self, ref: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Dict[str, Any]:
        """Return initial parameter dictionary prior to optimisation."""

    @abstractmethod
    def render(self, img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply plugin forward model to a float32 [0, 1] RGB image (resolution independent)."""

    @abstractmethod
    def loss(self, pred: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None, fold: Optional[int] = None, train: bool = False) -> float:
        """Evaluate plugin-specific loss on its target pixel mask (optionally restricted to CV fold)."""

    @abstractmethod
    def fit(self, ref_in: ImageOrList, tgt: ImageOrList, ctx: ContextOrList = None) -> Tuple[Dict[str, Any], FitReport]:
        """Fit plugin parameters using spatial 96px block cross-validation."""

    @abstractmethod
    def to_glsl(self, params: Dict[str, Any]) -> str:
        """Export strict GLSL ES 1.00 helper snippet (no extra textures)."""

    def glsl_taps(self, params: Dict[str, Any]) -> int:
        """Return number of extra texture2D fetches required by this plugin in single-pass GLSL."""
        return 0

    @abstractmethod
    def describe(self, params: Dict[str, Any]) -> str:
        """Describe fitted parameters in plain words."""
