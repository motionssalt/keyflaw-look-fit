"""Plugin registry for lookfit."""

from __future__ import annotations

from typing import Dict, List

from lookfit.plugins.base import Evidence, FitReport, PairContext, ParamSpec, Plugin
from lookfit.plugins.black_lift import BlackLiftPlugin
from lookfit.plugins.chromatic_aberration import ChromaticAberrationPlugin
from lookfit.plugins.colour import ColourPlugin
from lookfit.plugins.flicker import FlickerPlugin
from lookfit.plugins.gradient import GradientPlugin
from lookfit.plugins.grain import GrainPlugin
from lookfit.plugins.haze_flare import HazeFlarePlugin
from lookfit.plugins.sharpen import SharpenPlugin
from lookfit.plugins.unsharp_mask import UnsharpMaskPlugin
from lookfit.plugins.vignette import VignettePlugin

CORE_PLUGIN_ORDER: List[str] = [
    "colour",
    "sharpen",
    "unsharp_mask",
    "haze_flare",
    "grain",
    "gradient",
    "vignette",
]

OPTIONAL_PLUGIN_ORDER: List[str] = [
    "black_lift",
    "chromatic_aberration",
    "flicker",
]


def create_all_plugins() -> Dict[str, Plugin]:
    return {
        "colour": ColourPlugin(),
        "unsharp_mask": UnsharpMaskPlugin(),
        "sharpen": SharpenPlugin(),
        "haze_flare": HazeFlarePlugin(),
        "grain": GrainPlugin(),
        "gradient": GradientPlugin(),
        "vignette": VignettePlugin(),
        "black_lift": BlackLiftPlugin(),
        "chromatic_aberration": ChromaticAberrationPlugin(),
        "flicker": FlickerPlugin(),
    }


__all__ = [
    "Plugin",
    "ParamSpec",
    "Evidence",
    "FitReport",
    "PairContext",
    "ColourPlugin",
    "UnsharpMaskPlugin",
    "SharpenPlugin",
    "HazeFlarePlugin",
    "GrainPlugin",
    "GradientPlugin",
    "VignettePlugin",
    "BlackLiftPlugin",
    "ChromaticAberrationPlugin",
    "FlickerPlugin",
    "CORE_PLUGIN_ORDER",
    "OPTIONAL_PLUGIN_ORDER",
    "create_all_plugins",
]
