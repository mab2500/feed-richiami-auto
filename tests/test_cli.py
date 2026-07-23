"""Test per il CLI (inkscout/cli.py): ingest / sync-styles / serve."""

from __future__ import annotations

from PIL import Image

from inkscout.cli import main
from inkscout.store.db import Store


def test_cli_ingest_upload(tmp_path, monkeypatch):
    imgdir = tmp_path / "in"
    imgdir.mkdir()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(imgdir / "a.png")
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    rc = main(["ingest", "--kind", "upload", "--ref", str(imgdir)])
    assert rc == 0
    store = Store(tmp_path / "data" / "inkscout.db")
    assert len(store.all_phashes()) == 1


def test_cli_sync_styles(tmp_path, monkeypatch):
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    rc = main(["sync-styles"])
    assert rc == 0
    store = Store(tmp_path / "data" / "inkscout.db")
    assert store.style_id_by_name("blackwork") is not None


def test_cli_serve_wires_store_port_and_images_dir_without_real_port(tmp_path, monkeypatch):
    # Vincolo: niente rete/porte reali nei test. inkscout.web.app.serve è importato
    # lazy dentro main(), quindi monkeypatchare l'attributo sul modulo sorgente
    # basta perché il lookup a tempo di chiamata veda il doppio.
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    calls = {}

    def fake_serve(store, images_dir, port=8765):
        calls["store"] = store
        calls["images_dir"] = images_dir
        calls["port"] = port

    monkeypatch.setattr("inkscout.web.app.serve", fake_serve)
    rc = main(["serve", "--port", "9999"])
    assert rc == 0
    assert calls["port"] == 9999
    assert isinstance(calls["store"], Store)
    assert calls["images_dir"] == tmp_path / "data" / "images"
