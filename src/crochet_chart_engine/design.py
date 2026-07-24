"""Render ASCII-art design files into crochet chart PNGs.

Design file format (see examples in designs/):
    # comment
    palette: G=#4CAF50, D=#2E7D32, .=#FFFFFF
    title: Baby Dragon
    technique: graph
    ---
    <rows of palette chars, one char per stitch>

Rows are right-padded with the "." (background) palette entry to the width
of the longest row.
"""
from __future__ import annotations

import io
from collections import Counter
from pathlib import Path

from PIL import Image

from .engine import DEFAULT_TECHNIQUE, TECHNIQUES, render_chart


def parse_design(path: str | Path) -> tuple[dict, dict[str, tuple[int, int, int]], list[str]]:
    """Parse a design file. Returns (meta, palette, rows)."""
    path = Path(path)
    meta: dict = {"technique": DEFAULT_TECHNIQUE, "title": path.stem.title()}
    palette: dict[str, tuple[int, int, int]] = {}
    rows: list[str] = []
    section = "meta"
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line == "---":
            section = "grid"
            continue
        if section == "meta":
            if line.startswith("palette:"):
                for item in line.split(":", 1)[1].split(","):
                    ch, hexv = item.strip().split("=")
                    palette[ch] = tuple(int(hexv.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            elif ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        else:
            rows.append(line)
    if not rows:
        raise ValueError(f"no grid rows in {path}")
    width = max(len(r) for r in rows)
    rows = [r.ljust(width, ".") for r in rows]
    return meta, palette, rows


def render_design(path: str | Path, *, cell_px: int = 18) -> tuple[bytes, dict]:
    """Render an ASCII design file to a chart. Returns (png_bytes, meta).

    meta: title, grid_w, grid_h, colors ([{hex, count}] sorted desc),
    total_stitches, technique.
    """
    meta, palette, rows = parse_design(path)
    technique = meta["technique"] if meta["technique"] in TECHNIQUES else DEFAULT_TECHNIQUE
    bg = palette.get(".", (255, 255, 255))
    h, w = len(rows), len(rows[0])

    img = Image.new("RGB", (w, h), bg)
    counts: Counter = Counter()
    pal_list: list[tuple[int, int, int]] = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            rgb = palette.get(ch, bg)
            img.putpixel((x, y), rgb)
            counts[ch] += 1
            if rgb not in pal_list:
                pal_list.append(rgb)

    # render_chart expects palette indices in `counts`; map chars -> index
    pal_index = {ch: pal_list.index(palette.get(ch, bg)) for ch in palette}
    idx_counts = Counter({pal_index[ch]: n for ch, n in counts.items()})

    chart = render_chart(img, idx_counts, pal_list, meta["title"], technique, cell_px=cell_px)

    buf = io.BytesIO()
    chart.save(buf, format="PNG")
    out_meta = {
        "title": meta["title"],
        "grid_w": w,
        "grid_h": h,
        "colors": [
            {"hex": f"#{pal_list[i][0]:02X}{pal_list[i][1]:02X}{pal_list[i][2]:02X}",
             "count": int(c)}
            for i, c in idx_counts.most_common()
        ],
        "total_stitches": w * h,
        "technique": technique,
    }
    return buf.getvalue(), out_meta
