from PIL import Image

from inkscout.store.db import Store
from inkscout.web.app import App


def _app(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"
    Image.new("RGB", (8, 8)).save(p)
    src = store.add_source("upload", "local")
    img = store.add_image(str(p), 1, 8, 8, None, src, "u://a", "ref", "t")
    store.add_image_tag(img, "subject", "owl", 1.0, "test")
    return App(store, tmp_path / "images"), store, img


def test_favorite_toggles(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("POST", "/favorite", {"id": str(img)})
    assert r.status in (200, 303)
    assert store.get_image(img)["favorite"] == 1


def test_studio_form_lists_mode_E(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("GET", "/studio", {})
    assert r.status == 200 and "value='E'" in r.body


def test_generate_mode_E_returns_prompt_and_label(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("POST", "/generate", {"mode": "E", "theme": "owl", "styles": "blackwork"})
    assert r.status == 200
    assert "blackwork" in r.body
    assert "AI-generated / reference only" in r.body  # label §11
    assert f"/image/{img}" in r.body  # moodboard dalla libreria
