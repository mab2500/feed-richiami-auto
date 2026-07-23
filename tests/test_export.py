"""Test per la pipeline export stencil (Task 18, Fase 5).

`inkscout.export.stencil` deve restare importabile e utilizzabile SENZA l'extra
`[export]` (vtracer/opencv/numpy non installati): la parte Pillow-only (binarize,
300 DPI, watermark/label) è testata per davvero; la parte vtracer/SVG è lazy e qui
è coperta solo via `pytest.importorskip`, come previsto dal piano.
"""

import inspect
from io import BytesIO
from pathlib import Path

from PIL import Image

from inkscout.export.stencil import add_label, binarize, to_stencil_png


def _png(color=(120, 120, 120), size=(50, 40)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_binarize_is_bilevel():
    out = binarize(Image.new("RGB", (10, 10), (200, 200, 200)))
    assert out.mode == "1"


def test_binarize_thresholds_light_and_dark():
    # mode "1": getpixel torna 0 (nero) o 255 (bianco).
    light = binarize(Image.new("RGB", (4, 4), (200, 200, 200)), threshold=128)
    dark = binarize(Image.new("RGB", (4, 4), (10, 10, 10)), threshold=128)
    assert light.getpixel((0, 0)) == 255
    assert dark.getpixel((0, 0)) == 0


def test_to_stencil_png_sets_dpi_and_upscales(tmp_path):
    out = tmp_path / "s.png"
    to_stencil_png(_png(), out, dpi=300, target_long_side=500)
    assert out.exists()
    with Image.open(out) as im:
        # Il chunk pHYs del PNG salva pixel-per-metro: il round-trip dpi->pHYs->dpi
        # non torna mai esattamente 300.0 in virgola mobile (es. 299.9994...),
        # va confrontato arrotondato invece che con uguaglianza esatta.
        assert round(im.info.get("dpi", (0, 0))[0]) == 300
        assert max(im.size) >= 500  # upscalata al lato lungo richiesto
        assert im.size[1] > 40  # più alta dell'originale per via della label


def test_to_stencil_png_accepts_path_source(tmp_path):
    src = tmp_path / "in.png"
    src.write_bytes(_png())
    out = tmp_path / "s.png"
    to_stencil_png(src, out, target_long_side=100)
    assert out.exists()
    with Image.open(out) as im:
        assert max(im.size) >= 100


# --- Guardia §11: label "AI-generated / reference only" obbligatoria, non opzionale ---


def test_default_label_matches_guard_text():
    sig = inspect.signature(to_stencil_png)
    assert sig.parameters["label"].default == "AI-generated / reference only"


def test_add_label_adds_dark_band_at_bottom():
    img = Image.new("RGB", (100, 50), "white")
    out = add_label(img, "AI-generated / reference only")
    assert out.size[1] > img.size[1]
    band_pixel = out.getpixel((5, out.size[1] - 3))
    assert band_pixel != (255, 255, 255)


def test_to_stencil_png_label_band_is_present(tmp_path):
    # La pipeline completa non deve poter produrre uno stencil senza banda label:
    # verifica pixel reali, non solo la dimensione.
    out = tmp_path / "s.png"
    to_stencil_png(_png(), out, target_long_side=200)
    with Image.open(out) as im:
        rgb = im.convert("RGB")
        band_pixel = rgb.getpixel((2, rgb.size[1] - 2))
        assert band_pixel != (255, 255, 255)


def test_to_svg_optional(tmp_path):
    import pytest

    pytest.importorskip("vtracer")
    from inkscout.export.stencil import to_svg

    png = tmp_path / "s.png"
    to_stencil_png(_png(), png, target_long_side=200)
    svg = to_svg(png, tmp_path / "s.svg")
    assert Path(svg).read_text().lstrip().startswith("<svg") or Path(svg).exists()
