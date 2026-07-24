"""crochet-chart-engine: deterministic photo-to-crochet-chart conversion.

This is the open-sourced core engine behind https://crochetpatterngen.com.
All chart generation is deterministic image processing (resize, median-cut
quantization, confetti cleanup) — there is no AI image generation involved,
so stitch counts are exact and reproducible.

Public API:
    generate_chart(image, technique=..., grid_w=..., n_colors=...) -> (png_bytes, meta)
    render_design(path) -> (png_bytes, meta)
    estimate_yarn(meta, weight="worsted") -> dict
"""

from .design import parse_design, render_design
from .engine import (
    COLORS_MAX,
    COLORS_MIN,
    DEFAULT_TECHNIQUE,
    GRID_MAX,
    GRID_MIN,
    TECHNIQUES,
    clean_confetti,
    generate_chart,
    grid_dims,
    quantize_to_grid,
    render_chart,
)
from .yarn import YARN_WEIGHTS, estimate_yarn

__version__ = "0.1.0"

__all__ = [
    "COLORS_MAX",
    "COLORS_MIN",
    "DEFAULT_TECHNIQUE",
    "GRID_MAX",
    "GRID_MIN",
    "TECHNIQUES",
    "YARN_WEIGHTS",
    "clean_confetti",
    "estimate_yarn",
    "generate_chart",
    "grid_dims",
    "parse_design",
    "quantize_to_grid",
    "render_chart",
    "render_design",
]
