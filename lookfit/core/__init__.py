"""Core I/O, alignment, masking, colour-space, and metric utilities."""
from .io import FramePair, load_owner_pairs, read_rgb_float, verify_inputs_untouched, write_rgb_jpg, write_rgb_png
from .colour_spaces import lab_to_srgb, linear_to_srgb, luma_rec709, srgb_to_lab, srgb_to_linear
from .alignment import AlignmentResult, align_pair
from .masks import PairMasks, build_pair_masks, make_block_folds
from .metrics import channel_mae, ciede2000, ciede2000_rgb, compute_ssim, edge_profile_metrics, noise_statistics

__all__ = [
    "FramePair",
    "load_owner_pairs",
    "read_rgb_float",
    "verify_inputs_untouched",
    "write_rgb_jpg",
    "write_rgb_png",
    "srgb_to_linear",
    "linear_to_srgb",
    "luma_rec709",
    "srgb_to_lab",
    "lab_to_srgb",
    "AlignmentResult",
    "align_pair",
    "PairMasks",
    "build_pair_masks",
    "make_block_folds",
    "ciede2000",
    "ciede2000_rgb",
    "channel_mae",
    "compute_ssim",
    "edge_profile_metrics",
    "noise_statistics",
]
