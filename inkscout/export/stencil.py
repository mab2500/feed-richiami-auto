"""Export stencil: binarizza → upscala a 300 DPI → label → PNG (+ SVG via vtracer lazy).

La label "AI-generated / reference only" è una guardia §11 non opzionale: la pipeline
completa (`to_stencil_png`) la applica sempre, non esiste un percorso per saltarla.
vtracer (extra `[export]`) è importato lazy dentro `to_svg`, mai a livello di modulo,
così il resto del modulo resta importabile e utilizzabile senza quell'extra.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def binarize(image, threshold: int = 128):
    gray = image.convert("L")
    return gray.point(lambda p: 255 if p > threshold else 0).convert("1")


def add_label(image, text: str):
    from PIL import Image, ImageDraw

    band = max(24, image.size[0] // 20)
    out = Image.new("RGB", (image.size[0], image.size[1] + band), "white")
    out.paste(image.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(out)
    draw.rectangle([0, image.size[1], out.size[0], out.size[1]], fill=(20, 20, 20))
    draw.text((6, image.size[1] + max(2, (band - 12) // 2)), text, fill="white")
    return out


def to_stencil_png(
    src,
    out_path,
    *,
    dpi: int = 300,
    target_long_side: int = 2000,
    label: str = "AI-generated / reference only",
) -> Path:
    from PIL import Image

    img = Image.open(BytesIO(src)) if isinstance(src, (bytes, bytearray)) else Image.open(src)
    bw = binarize(img)
    scale = max(1.0, target_long_side / max(bw.size))
    if scale > 1.0:
        bw = bw.resize((round(bw.size[0] * scale), round(bw.size[1] * scale)), Image.NEAREST)
    labeled = add_label(bw, label)
    out_path = Path(out_path)
    labeled.save(out_path, format="PNG", dpi=(dpi, dpi))
    return out_path


def to_svg(png_path, out_path) -> Path:
    import vtracer  # lazy, extra [export]

    out_path = Path(out_path)
    vtracer.convert_image_to_svg_py(str(png_path), str(out_path))
    return out_path
