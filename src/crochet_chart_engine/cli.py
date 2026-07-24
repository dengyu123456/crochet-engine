"""Command-line interface for crochet-chart-engine.

    crochet-chart chart photo.jpg out.png [--technique c2c] [--grid-w 60] [--colors 8]
    crochet-chart design designs/frog.txt out.png [--cell 18]
    crochet-chart yarn photo.jpg [--technique c2c] [--weight worsted]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .design import render_design
from .engine import DEFAULT_TECHNIQUE, TECHNIQUES, generate_chart
from .yarn import YARN_WEIGHTS, estimate_yarn


def _write(png: bytes, out: str) -> None:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(png)


def _print_meta(meta: dict) -> None:
    print(f"{meta['grid_w']}x{meta['grid_h']} ({meta['total_stitches']} sts), "
          f"{len(meta['colors'])} colors, technique={meta['technique']}")
    for c in meta["colors"]:
        print(f"  {c['hex']}: {c['count']} sts")


def main() -> None:
    ap = argparse.ArgumentParser(prog="crochet-chart",
                                 description="Deterministic photo-to-crochet-chart engine "
                                             "(https://crochetpatterngen.com)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_chart = sub.add_parser("chart", help="photo -> chart PNG")
    p_chart.add_argument("image")
    p_chart.add_argument("out")
    p_chart.add_argument("--technique", default=DEFAULT_TECHNIQUE, choices=sorted(TECHNIQUES))
    p_chart.add_argument("--grid-w", type=int, default=60)
    p_chart.add_argument("--colors", type=int, default=8)
    p_chart.add_argument("--title", default="My Pattern")
    p_chart.add_argument("--remove-bg", action="store_true",
                         help="requires the rembg extra")
    p_chart.add_argument("--cell", type=int, default=22)

    p_design = sub.add_parser("design", help="ASCII design file -> chart PNG")
    p_design.add_argument("design")
    p_design.add_argument("out")
    p_design.add_argument("--cell", type=int, default=18)

    p_yarn = sub.add_parser("yarn", help="photo -> yarn yardage estimate (all weights)")
    p_yarn.add_argument("image")
    p_yarn.add_argument("--technique", default=DEFAULT_TECHNIQUE, choices=sorted(TECHNIQUES))
    p_yarn.add_argument("--grid-w", type=int, default=60)
    p_yarn.add_argument("--colors", type=int, default=8)
    p_yarn.add_argument("--weight", default=None, choices=sorted(YARN_WEIGHTS),
                        help="single weight; default prints all weights")

    args = ap.parse_args()

    if args.cmd == "design":
        png, meta = render_design(args.design, cell_px=args.cell)
        _write(png, args.out)
        _print_meta(meta)
        print(f"-> {args.out}")
        return

    img = Image.open(args.image)
    png, meta = generate_chart(img, title=getattr(args, "title", "Chart"),
                               technique=args.technique, grid_w=args.grid_w,
                               n_colors=args.colors,
                               remove_bg=getattr(args, "remove_bg", False),
                               cell_px=getattr(args, "cell", 22))

    if args.cmd == "chart":
        _write(png, args.out)
        _print_meta(meta)
        if meta.get("warning"):
            print(f"warning: {meta['warning']}")
        print(f"-> {args.out}")
    else:  # yarn
        if args.weight:
            print(json.dumps(estimate_yarn(meta, args.weight), indent=2))
        else:
            out = {w: estimate_yarn(meta, w)["total_yards"] for w in YARN_WEIGHTS}
            print(json.dumps({"total_yards_by_weight": out}, indent=2))


if __name__ == "__main__":
    main()
