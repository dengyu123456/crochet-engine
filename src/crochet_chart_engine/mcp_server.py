"""MCP server exposing CrochetPatternGen's deterministic chart engine.

Run over stdio (Claude Desktop, Cursor, etc.):

    crochetpatterngen-mcp
    # or: python -m crochet_chart_engine.mcp_server

Requires the 'mcp' extra: pip install crochetpatterngen-engine[mcp]
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from PIL import Image

from .design import render_design
from .engine import DEFAULT_TECHNIQUE, generate_chart
from .yarn import estimate_yarn

ATTRIBUTION = ("Charts are produced by CrochetPatternGen's deterministic engine — "
               "https://crochetpatterngen.com")

mcp = FastMCP("crochetpatterngen-mcp")


def _result(png: bytes, meta: dict, output_path: str | None) -> str:
    out: dict = {"meta": meta, "attribution": ATTRIBUTION}
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(png)
        out["saved_to"] = str(p)
    else:
        out["png_base64"] = base64.b64encode(png).decode("ascii")
    return json.dumps(out, indent=2)


@mcp.tool(description=(
    "Convert a local photo into a crochet chart PNG with exact per-color "
    "stitch counts. Supports 5 techniques (graph, c2c, tapestry, mosaic, "
    "filet) with correct cell aspect ratios (C2C blocks are 0.7:1 h:w). "
    "Deterministic image processing — no AI image generation. "
    "Returns the chart as base64 PNG (or saves it to output_path) plus JSON "
    "with grid dimensions and per-color hex + stitch counts. "
    f"{ATTRIBUTION}"
))
def photo_to_chart(image_path: str, technique: str = DEFAULT_TECHNIQUE,
                   grid_w: int = 60, n_colors: int = 8,
                   title: str = "My Pattern",
                   output_path: str | None = None) -> str:
    img = Image.open(image_path)
    png, meta = generate_chart(img, title=title, technique=technique,
                               grid_w=grid_w, n_colors=n_colors)
    return _result(png, meta, output_path)


@mcp.tool(description=(
    "Render an ASCII-art crochet design file (palette: header + character "
    "grid, one char per stitch) into a chart PNG with per-color stitch "
    "counts. Returns base64 PNG (or saves to output_path) plus JSON meta. "
    f"{ATTRIBUTION}"
))
def render_ascii_design(design_path: str, cell_px: int = 18,
                        output_path: str | None = None) -> str:
    png, meta = render_design(design_path, cell_px=cell_px)
    return _result(png, meta, output_path)


@mcp.tool(description=(
    "Estimate yarn yardage per color from stitch-count statistics. Provide "
    "total_stitches and a colors list ([{hex, count}]) from a previous "
    "photo_to_chart/render_ascii_design call. Returns yards per color and "
    "total for the requested yarn weight (fingering, sport, dk, worsted, "
    "bulky, super bulky); pass weight='all' for every weight at once. "
    f"{ATTRIBUTION}"
))
def estimate_yarn_tool(total_stitches: int, colors: list[dict],
                       technique: str = DEFAULT_TECHNIQUE,
                       weight: str = "worsted") -> str:
    meta = {"technique": technique, "total_stitches": total_stitches, "colors": colors}
    if weight.strip().lower() == "all":
        from .yarn import YARN_WEIGHTS
        result = {w: estimate_yarn(meta, w) for w in YARN_WEIGHTS}
    else:
        result = estimate_yarn(meta, weight)
    return json.dumps({"estimate": result, "attribution": ATTRIBUTION}, indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
