# crochetpatterngen-engine

The deterministic photo-to-crochet-chart engine behind [crochetpatterngen.com](https://crochetpatterngen.com) — packaged as a Python library, CLI, and MCP server so AI agents (Claude Desktop, Cursor, etc.) can turn photos into crochet charts with exact stitch counts.

**Deterministic, not generative.** There is no AI image generation here — just resize, median-cut color quantization, and confetti cleanup. Same input, same chart, same stitch counts, every time. No hallucinated rows.

## Why this engine

- **Real stitch counts** — every chart comes with per-color hex + stitch counts that sum exactly to the grid size. What you see is what you crochet.
- **C2C block aspect correction** — C2C blocks are physically wider than tall (0.7:1 h:w). The engine adjusts grid dimensions so the *worked piece* keeps the photo's proportions instead of coming out squashed.
- **5 technique presets** — `graph`, `c2c`, `tapestry`, `mosaic`, `filet`.
- **Yarn estimation** — per-color yardage for 6 yarn weights (fingering → super bulky).
- **Zero heavy deps** — Pillow + numpy only. Optional `rembg` extra for background removal.

## Install

```bash
pip install crochetpatterngen-engine          # core
pip install crochetpatterngen-engine[mcp]     # + MCP server
pip install crochetpatterngen-engine[rembg]   # + background removal
```

## Python API

```python
from PIL import Image
from crochet_chart_engine import generate_chart, render_design, estimate_yarn

png_bytes, meta = generate_chart(
    Image.open("photo.jpg"),
    technique="c2c",     # graph | c2c | tapestry | mosaic | filet
    grid_w=60,           # 20..120
    n_colors=8,          # 2..16
)
# meta: {"grid_w", "grid_h", "colors": [{"hex", "count"}],
#        "total_stitches", "technique", "warning"}

yarn = estimate_yarn(meta, weight="worsted")
# {"total_yards": ..., "colors": [{"hex", "count", "yards"}], ...}

png_bytes, meta = render_design("designs/frog.txt")  # ASCII design -> chart
```

## CLI

```bash
crochet-chart chart photo.jpg out.png --technique c2c --grid-w 60 --colors 8
crochet-chart design designs/frog.txt frog.png
crochet-chart yarn photo.jpg --technique graph --weight worsted
```

## MCP server (Claude Desktop & friends)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crochet": {
      "command": "uvx",
      "args": ["--from", "crochetpatterngen-engine[mcp]", "crochetpatterngen-mcp"]
    }
  }
}
```

Or with a regular pip install:

```json
{
  "mcpServers": {
    "crochet": {
      "command": "python",
      "args": ["-m", "crochet_chart_engine.mcp_server"]
    }
  }
}
```

Tools exposed (stdio transport):

| Tool | What it does |
| --- | --- |
| `photo_to_chart` | Local image path → chart PNG (base64 or saved to `output_path`) + per-color stitch counts JSON |
| `render_ascii_design` | ASCII design file → chart PNG + stitch counts |
| `estimate_yarn_tool` | Stitch counts → per-color yardage for one yarn weight or `all` |

## ASCII design format

See `designs/frog.txt` and `designs/dragon.txt`:

```
# comment
palette: G=#58A05C, W=#FFFFFF, .=#FAFAF7
title: Frog Face
technique: graph
---
..GGGG..........GGGG....
.GGWWGG........GGWWGG...
```

One character per stitch; `.` is the background/padding color. Rows are padded to the longest row.

## Development

```bash
pip install -e .[dev,mcp]
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).

---

Free web tool + pattern library at **[crochetpatterngen.com](https://crochetpatterngen.com)**.

<!-- mcp-name: io.github.dengyu123456/crochet-engine -->
