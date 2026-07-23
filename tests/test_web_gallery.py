from PIL import Image

from inkscout.store.db import Store
from inkscout.web.app import App


def _app(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"
    Image.new("RGB", (8, 8)).save(p)
    src = store.add_source("site", "https://artist.ex")
    art = store.add_artist(
        "Jane", handle="@jane", source_id=src, provenance_url="https://artist.ex"
    )
    img = store.add_image(str(p), 1, 8, 8, art, src, "https://artist.ex/a", "personal-site", "t")
    return App(store, tmp_path / "images"), store, img


def test_gallery_shows_attribution_and_cta(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("GET", "/", {})
    assert r.status == 200 and "text/html" in r.content_type
    assert "@jane" in r.body  # attribuzione
    assert "Commissiona questo artista" in r.body  # CTA guardia §11


def test_image_route_serves_bytes(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("GET", f"/image/{img}", {})
    assert r.status == 200 and r.content_type.startswith("image/")
    assert isinstance(r.body, (bytes, bytearray)) and len(r.body) > 0


def test_do_not_mimic_excluded(tmp_path):
    app, store, img = _app(tmp_path)
    store.conn.execute("UPDATE artist SET do_not_mimic=1")
    store.conn.commit()
    r = app.handle("GET", "/", {})
    assert "@jane" not in r.body
