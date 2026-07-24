"""Core photo -> crochet chart pipeline (Pillow + numpy only).

Deterministic image processing — no AI image generation. Given the same
input image and parameters, the output chart and stitch counts are always
identical.

Steps: optional background removal (rembg extra) -> resize to grid ->
median-cut color quantization -> confetti cleanup -> aspect correction ->
render chart (grid/numbers/legend/title).
"""
from __future__ import annotations

import io
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- technique presets -------------------------------------------------------
# cell_yx_ratio = physical height/width of one worked cell. C2C blocks are
# wider than tall (ch3 + 3 dc), conventionally "0.7:1" (h:w). The chart
# itself is drawn with square cells (schematic); the ratio only changes the
# grid dimensions so the *worked piece* keeps photo proportions:
# wider-than-tall cells need MORE rows to reproduce the image's proportions.
TECHNIQUES = {
    "graph": {"cell_yx_ratio": 1.0, "unit_note": "Each square = 1 stitch"},
    "tapestry": {"cell_yx_ratio": 1.0, "unit_note": "Each square = 1 sc (tapestry)"},
    "mosaic": {"cell_yx_ratio": 1.0, "unit_note": "Each square = 1 mosaic stitch"},
    "filet": {"cell_yx_ratio": 1.0, "unit_note": "Each square = 1 filet mesh"},
    "c2c": {"cell_yx_ratio": 0.7, "unit_note": "Each square = 1 block (C2C)"},
}
DEFAULT_TECHNIQUE = "graph"

GRID_MIN, GRID_MAX = 20, 120
COLORS_MIN, COLORS_MAX = 2, 16

# --- optional background removal (rembg extra) --------------------------------
_rembg_session = None
_rembg_checked = None


def bg_removal_available() -> bool:
    global _rembg_checked
    if _rembg_checked is None:
        try:
            import rembg  # noqa: F401
            _rembg_checked = True
        except BaseException:  # rembg without onnxruntime can raise SystemExit
            _rembg_checked = False
    return _rembg_checked


def remove_background(img: Image.Image) -> Image.Image:
    """Remove background with rembg (optional extra); transparent -> white."""
    global _rembg_session
    if not bg_removal_available():
        raise RuntimeError(
            "background removal requires the 'rembg' extra: "
            "pip install crochetpatterngen-engine[rembg]"
        )
    import rembg
    if _rembg_session is None:
        import os
        _rembg_session = rembg.new_session(os.environ.get("REMBG_MODEL", "u2net"))
    cut = rembg.remove(img.convert("RGB"), session=_rembg_session)
    bg = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    bg.alpha_composite(cut.convert("RGBA"))
    return bg.convert("RGB")


# --- pipeline ----------------------------------------------------------------

def grid_dims(img_w: int, img_h: int, grid_w: int, cell_yx_ratio: float) -> tuple[int, int]:
    # piece: W = grid_w * cell_w, H = grid_h * cell_h; want W:H = img_w:img_h
    # => grid_h = grid_w * (cell_w/cell_h) * (img_h/img_w) = grid_w * (img_h/img_w) / cell_yx_ratio
    grid_h = max(1, round(grid_w * (img_h / img_w) / cell_yx_ratio))
    return grid_w, grid_h


def quantize_to_grid(img: Image.Image, grid_w: int, grid_h: int, n_colors: int):
    """Resize to grid and quantize. Returns (P-mode image, palette_rgb list, counts)."""
    small = img.resize((grid_w, grid_h), Image.Resampling.LANCZOS).convert("RGB")
    q = small.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    raw_palette = q.getpalette()[: n_colors * 3]
    palette = [tuple(raw_palette[i * 3: i * 3 + 3]) for i in range(n_colors)]
    counts = Counter(np.array(q, dtype=np.uint8).flatten().tolist())
    return q, palette, counts


def clean_confetti(q: Image.Image, max_passes: int = 3) -> Image.Image:
    """Replace a cell whose 4 orthogonal neighbors all differ from it by the
    most common neighbor color. Iterates until stable (max `max_passes`)."""
    a = np.array(q, dtype=np.uint8)
    h, w = a.shape
    for _ in range(max_passes):
        changed = 0
        out = a.copy()
        for y in range(h):
            for x in range(w):
                c = a[y, x]
                neighbors = []
                if y > 0: neighbors.append(a[y - 1, x])
                if y < h - 1: neighbors.append(a[y + 1, x])
                if x > 0: neighbors.append(a[y, x - 1])
                if x < w - 1: neighbors.append(a[y, x + 1])
                if len(neighbors) >= 3 and all(n != c for n in neighbors):
                    out[y, x] = Counter(neighbors).most_common(1)[0][0]
                    changed += 1
        a = out
        if changed == 0:
            break
    cleaned = Image.fromarray(a, mode="P")
    cleaned.putpalette(q.getpalette())
    return cleaned


# --- rendering ----------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_chart(grid_img_rgb: Image.Image, counts: Counter, palette: list,
                 title: str, technique: str, cell_px: int = 22) -> Image.Image:
    grid_w, grid_h = grid_img_rgb.size
    major = 5 if max(grid_w, grid_h) <= 40 else 10
    note = TECHNIQUES.get(technique, TECHNIQUES[DEFAULT_TECHNIQUE])["unit_note"]

    font_small = _load_font(max(14, cell_px - 4))
    font_title = _load_font(22)

    left_margin = 14 + font_small.getlength(str(grid_h)) + 10
    top_margin = 34 + 24  # title + column numbers
    legend_w = 270
    w = int(left_margin + grid_w * cell_px + 1 + legend_w)
    h = int(top_margin + grid_h * cell_px + 1 + 12)

    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    ox, oy = left_margin, top_margin  # grid origin

    # title
    d.text((8, 6), f"{title} - {technique.upper()} Chart ({grid_w} x {grid_h})",
           fill=(20, 20, 20), font=font_title)

    # cells
    px = grid_img_rgb.load()
    for gy in range(grid_h):
        for gx in range(grid_w):
            x0, y0 = ox + gx * cell_px, oy + gy * cell_px
            d.rectangle([x0, y0, x0 + cell_px, y0 + cell_px], fill=px[gx, gy])

    # grid lines
    thin, thick = (200, 200, 200), (60, 60, 60)
    for i in range(grid_w + 1):
        x = ox + i * cell_px
        d.line([x, oy, x, oy + grid_h * cell_px],
               fill=thick if i % major == 0 else thin,
               width=2 if i % major == 0 else 1)
    for j in range(grid_h + 1):
        y = oy + j * cell_px
        d.line([ox, y, ox + grid_w * cell_px, y],
               fill=thick if j % major == 0 else thin,
               width=2 if j % major == 0 else 1)

    # numbers at major lines (1-based)
    for i in range(0, grid_w, major):
        x = ox + i * cell_px + 2
        d.text((x, oy - 20), str(i + 1), fill=(80, 80, 80), font=font_small)
    for j in range(0, grid_h, major):
        y = oy + j * cell_px + 2
        d.text((8, y), str(j + 1), fill=(80, 80, 80), font=font_small)

    # legend (colors sorted by stitch count desc)
    lx = ox + grid_w * cell_px + 24
    ly = oy + 4
    swatch = 22
    for idx, cnt in counts.most_common():
        r, g, b = palette[idx]
        d.rectangle([lx, ly, lx + swatch, ly + swatch], fill=(r, g, b),
                    outline=(120, 120, 120))
        d.text((lx + swatch + 8, ly + 3), f"#{r:02X}{g:02X}{b:02X}: {cnt} sts",
               fill=(40, 40, 40), font=font_small)
        ly += swatch + 8
    ly += 10
    d.text((lx, ly), note, fill=(90, 90, 90), font=font_small)
    return img


def generate_chart(image: Image.Image, *, title: str = "My Pattern",
                   technique: str = DEFAULT_TECHNIQUE, grid_w: int = 60,
                   n_colors: int = 8, remove_bg: bool = False,
                   cell_px: int = 22) -> tuple[bytes, dict]:
    """Full pipeline. Returns (png_bytes, meta).

    meta: grid_w, grid_h, colors ([{hex, count}] sorted desc),
    total_stitches, technique, warning.
    """
    technique = technique if technique in TECHNIQUES else DEFAULT_TECHNIQUE
    grid_w = int(min(GRID_MAX, max(GRID_MIN, grid_w)))
    n_colors = int(min(COLORS_MAX, max(COLORS_MIN, n_colors)))

    img = image.convert("RGB")
    warning = None
    if remove_bg:
        img = remove_background(img)
        # rembg can misjudge the subject (or find none) and erase most of the
        # photo — an empty chart is a worse surprise than a busy one, so warn.
        lum = np.asarray(img.convert("L"), dtype=np.uint8)
        if float((lum < 245).mean()) < 0.15:
            warning = ("Background removal left very little subject. "
                       "Try again without background removal, or use a photo "
                       "with a clearer subject.")

    ratio = TECHNIQUES[technique]["cell_yx_ratio"]
    gw, gh = grid_dims(*img.size, grid_w, ratio)

    q, palette, counts = quantize_to_grid(img, gw, gh, n_colors)
    q = clean_confetti(q)
    counts = Counter(np.array(q, dtype=np.uint8).flatten().tolist())

    grid_rgb = q.convert("RGB")
    chart = render_chart(grid_rgb, counts, palette, title, technique, cell_px)

    buf = io.BytesIO()
    chart.save(buf, format="PNG")
    meta = {
        "grid_w": gw,
        "grid_h": gh,
        "colors": [
            {"hex": f"#{palette[i][0]:02X}{palette[i][1]:02X}{palette[i][2]:02X}",
             "count": int(c)}
            for i, c in counts.most_common()
        ],
        "total_stitches": gw * gh,
        "technique": technique,
        "warning": warning,
    }
    return buf.getvalue(), meta
