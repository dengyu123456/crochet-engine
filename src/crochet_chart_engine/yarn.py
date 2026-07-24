"""Yarn yardage estimation from stitch counts.

Baseline: worsted-weight yarn uses ~0.06 yards per stitch (graph / single
crochet and other square-cell techniques) and ~0.65 yards per C2C block.
Other yarn weights scale per the table below. These are planning estimates,
not exact measurements — gauge and tension vary by crocheter.
"""
from __future__ import annotations

# yards per unit: "stitch" for square-cell techniques, "block" for C2C
YARN_WEIGHTS: dict[str, dict[str, float]] = {
    "fingering": {"stitch": 0.035, "block": 0.4},
    "sport": {"stitch": 0.045, "block": 0.45},
    "dk": {"stitch": 0.05, "block": 0.55},
    "worsted": {"stitch": 0.06, "block": 0.65},
    "bulky": {"stitch": 0.085, "block": 0.9},
    "super bulky": {"stitch": 0.12, "block": 1.2},
}
DEFAULT_WEIGHT = "worsted"


def estimate_yarn(meta: dict, weight: str = DEFAULT_WEIGHT) -> dict:
    """Estimate yarn yardage per color from a chart meta dict.

    `meta` is the dict returned by generate_chart() or render_design()
    (must contain technique, colors, total_stitches).
    Returns {weight, technique, unit, yards_per_unit, colors, total_yards}.
    """
    key = weight.strip().lower()
    if key not in YARN_WEIGHTS:
        raise ValueError(
            f"unknown yarn weight {weight!r}; choose from: {', '.join(YARN_WEIGHTS)}"
        )
    unit = "block" if meta.get("technique") == "c2c" else "stitch"
    rate = YARN_WEIGHTS[key][unit]
    colors = [
        {"hex": c["hex"], "count": int(c["count"]), "yards": round(int(c["count"]) * rate, 1)}
        for c in meta["colors"]
    ]
    return {
        "weight": key,
        "technique": meta.get("technique", "graph"),
        "unit": unit,
        "yards_per_unit": rate,
        "colors": colors,
        "total_yards": round(int(meta["total_stitches"]) * rate, 1),
    }
