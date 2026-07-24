"""Tests for the deterministic chart engine and design renderer."""
from __future__ import annotations

import io
from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

from crochet_chart_engine import (
    estimate_yarn,
    generate_chart,
    grid_dims,
    render_design,
)

DESIGNS = Path(__file__).resolve().parent.parent / "designs"


def _is_png(data: bytes) -> bool:
    return data[:8] == b"\x89PNG\r\n\x1a\n"


def _openable(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


# --- design rendering ---------------------------------------------------------

def test_frog_design_png_and_stitches():
    png, meta = render_design(DESIGNS / "frog.txt")
    assert _is_png(png)
    _openable(png)
    assert meta["grid_w"] == 24
    assert meta["grid_h"] == 16
    assert meta["total_stitches"] == 24 * 16 == 384
    # stitch conservation: per-color counts sum to the grid size
    assert sum(c["count"] for c in meta["colors"]) == 384
    # every reported color is a valid hex
    for c in meta["colors"]:
        assert c["hex"].startswith("#") and len(c["hex"]) == 7


def test_dragon_design_renders():
    png, meta = render_design(DESIGNS / "dragon.txt")
    assert _is_png(png)
    assert meta["total_stitches"] == meta["grid_w"] * meta["grid_h"]
    assert sum(c["count"] for c in meta["colors"]) == meta["total_stitches"]


# --- photo -> chart -----------------------------------------------------------

def test_generate_chart_solid_color():
    img = Image.new("RGB", (100, 100), (200, 30, 30))
    png, meta = generate_chart(img, technique="graph", grid_w=30, n_colors=4)
    assert _is_png(png)
    _openable(png)
    assert meta["grid_w"] == 30
    assert meta["grid_h"] == 30  # square source, square-cell technique
    assert meta["total_stitches"] == 900
    # stitch conservation
    assert sum(c["count"] for c in meta["colors"]) == meta["total_stitches"]
    # a solid color image collapses to a single color
    assert len(meta["colors"]) == 1
    assert meta["colors"][0]["count"] == 900


def test_generate_chart_rectangular_c2c_ratio():
    # 2:1 wide source; C2C blocks are 0.7:1 (h:w) so the grid needs more rows
    img = Image.new("RGB", (200, 100), (30, 30, 200))
    _, meta = generate_chart(img, technique="c2c", grid_w=40, n_colors=2)
    assert meta["grid_w"] == 40
    expected_h = round(40 * (100 / 200) / 0.7)  # grid_dims formula
    assert meta["grid_h"] == expected_h
    assert sum(c["count"] for c in meta["colors"]) == meta["total_stitches"]


def test_grid_dims_c2c_correction():
    assert grid_dims(100, 100, 30, 1.0) == (30, 30)
    assert grid_dims(100, 100, 30, 0.7) == (30, round(30 / 0.7))


def test_generate_chart_deterministic():
    img = Image.new("RGB", (80, 60), (10, 200, 90))
    png1, meta1 = generate_chart(img, technique="tapestry", grid_w=25, n_colors=3)
    png2, meta2 = generate_chart(img, technique="tapestry", grid_w=25, n_colors=3)
    assert png1 == png2
    assert meta1 == meta2


# --- yarn estimation ----------------------------------------------------------

def test_estimate_yarn_worsted_graph():
    meta = {
        "technique": "graph",
        "total_stitches": 1000,
        "colors": [{"hex": "#FF0000", "count": 600}, {"hex": "#00FF00", "count": 400}],
    }
    est = estimate_yarn(meta, "worsted")
    assert est["unit"] == "stitch"
    assert est["total_yards"] == pytest.approx(60.0)
    assert est["colors"][0]["yards"] == pytest.approx(36.0)
    assert sum(c["yards"] for c in est["colors"]) == pytest.approx(est["total_yards"])


def test_estimate_yarn_c2c_uses_block_rate():
    meta = {
        "technique": "c2c",
        "total_stitches": 100,
        "colors": [{"hex": "#0000FF", "count": 100}],
    }
    assert estimate_yarn(meta, "worsted")["total_yards"] == pytest.approx(65.0)
    assert estimate_yarn(meta, "fingering")["total_yards"] == pytest.approx(40.0)


def test_estimate_yarn_unknown_weight():
    meta = {"technique": "graph", "total_stitches": 10,
            "colors": [{"hex": "#FFFFFF", "count": 10}]}
    with pytest.raises(ValueError):
        estimate_yarn(meta, "lace")
