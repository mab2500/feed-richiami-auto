"""Test per la rotta web di export stencil (Task 21).

Guardia §11: `to_stencil_png` (Task 18) ha un default non opzionale per `label`
("AI-generated / reference only"). La rotta /export NON deve esporre un campo per
personalizzarlo né inoltrare un eventuale "label" letto dai params — il chiamante
non può mai svuotare o sostituire la label, nemmeno manomettendo il form.
"""

from PIL import Image

from inkscout.export import stencil as stencil_mod
from inkscout.store.db import Store
from inkscout.web import templates
from inkscout.web.app import App


def _app(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"
    Image.new("RGB", (40, 30), (120, 120, 120)).save(p)
    src = store.add_source("upload", "local")
    img = store.add_image(str(p), 1, 40, 30, None, src, "u://a", "ref", "t")
    return App(store, tmp_path / "images"), store, img


def test_export_returns_png(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"
    Image.new("RGB", (40, 30), (120, 120, 120)).save(p)
    src = store.add_source("upload", "local")
    img = store.add_image(str(p), 1, 40, 30, None, src, "u://a", "ref", "t")
    app = App(store, tmp_path / "images")
    r = app.handle("POST", "/export", {"id": str(img)})
    assert r.status == 200 and r.content_type == "image/png"
    assert isinstance(r.body, (bytes, bytearray)) and r.body[:8] == b"\x89PNG\r\n\x1a\n"
    assert "attachment" in r.headers.get("Content-Disposition", "")


def test_export_missing_image_returns_404(tmp_path):
    app, _store, _img = _app(tmp_path)
    r = app.handle("POST", "/export", {"id": "999999"})
    assert r.status == 404


def test_export_ignores_label_param(tmp_path, monkeypatch):
    """Guardia §11: anche se un chiamante manomette il form e aggiunge un campo
    "label", la rotta non deve MAI inoltrarlo a to_stencil_png — deve sempre
    affidarsi al default della pipeline (label non svuotabile/sostituibile)."""
    app, _store, img = _app(tmp_path)
    calls = []
    real = stencil_mod.to_stencil_png

    def spy(src, out_path, **kwargs):
        calls.append(kwargs)
        return real(src, out_path, **kwargs)

    monkeypatch.setattr(stencil_mod, "to_stencil_png", spy)

    r = app.handle("POST", "/export", {"id": str(img), "label": "qualcosa d'altro"})

    assert r.status == 200
    assert len(calls) == 1
    assert "label" not in calls[0]  # mai inoltrato: la pipeline usa sempre il default


def test_gallery_export_button_has_no_label_field(tmp_path):
    """Guardia §11 lato UI: il bottone export nella galleria non offre un campo
    per personalizzare la label."""
    app, _store, img = _app(tmp_path)
    r = app.handle("GET", "/", {})
    assert "action='/export'" in r.body
    assert f"value='{img}'" in r.body
    assert "name='label'" not in r.body


def test_image_card_export_button_no_label_field():
    card = templates.image_card({"id": 7})
    assert "action='/export'" in card
    assert "value='7'" in card
    assert "name='label'" not in card
