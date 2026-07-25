"""Il flusso completo WhatsApp → libreria → attribuzione visibile nel web.

Copre il difetto trovato il 24/07: la CLI ingeriva senza creare l'artista, quindi
`artist_handle` si perdeva e la CTA «Commissiona questo artista» (guardia §11.4) non si
attivava mai nel flusso reale, pur essendo verde nei test dei template.
"""

from PIL import Image

from inkscout.cli import main
from inkscout.store.db import Store
from inkscout.web.app import App

CHAT = (
    "[06/09/24, 21:14:02] Matteo: guarda questo blackwork\n"
    "[06/09/24, 21:14:20] Matteo: ‎<allegato: FOTO-1.jpg>\n"
    "[06/09/24, 21:15:01] Matteo: è di @dario.ink\n"
    "[07/09/24, 09:00:00] Giulia: e questo?\n"
    "[07/09/24, 09:00:10] Giulia: ‎<allegato: FOTO-2.jpg>\n"
    "[07/09/24, 09:01:00] Giulia: sempre @dario.ink\n"
)


def _export(tmp_path):
    d = tmp_path / "Tatuaggi mab"
    d.mkdir(parents=True)
    (d / "_chat.txt").write_text(CHAT, encoding="utf-8")
    Image.new("RGB", (32, 32), (10, 10, 10)).save(d / "FOTO-1.jpg")
    # seconda immagine DIVERSA, altrimenti il dedup pHash la collassa
    grad = Image.new("L", (32, 32))
    for x in range(32):
        for y in range(32):
            grad.putpixel((x, y), (x * 8) % 256)
    grad.convert("RGB").save(d / "FOTO-2.jpg")
    return d


def test_ingest_whatsapp_attribuisce_e_non_duplica_artista(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    d = _export(tmp_path)
    assert main(["ingest", "--kind", "whatsapp", "--ref", str(d), "--chat", "Tatuaggi mab"]) == 0
    out = capsys.readouterr().out
    assert "2 nuove" in out and "2 con artista attribuito" in out

    store = Store(tmp_path / "data" / "inkscout.db")
    artisti = list(store.conn.execute("SELECT id, handle, provenance_url FROM artist"))
    assert len(artisti) == 1, "lo stesso handle non deve creare due artisti"
    assert artisti[0]["handle"] == "@dario.ink"
    assert artisti[0]["provenance_url"] == "https://instagram.com/dario.ink"

    # provenance completa: ogni immagine ha artista E sorgente
    for r in store.conn.execute("SELECT artist_id, source_id, license_note FROM image"):
        assert r["artist_id"] == artisti[0]["id"]
        assert r["source_id"] is not None
        assert r["license_note"] == "whatsapp-personal"


def test_la_cta_compare_davvero_nella_galleria(tmp_path, monkeypatch):
    """La guardia §11 non basta averla nel template: deve accendersi col dato reale."""
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    d = _export(tmp_path)
    main(["ingest", "--kind", "whatsapp", "--ref", str(d), "--chat", "Tatuaggi mab"])
    store = Store(tmp_path / "data" / "inkscout.db")
    html = App(store, tmp_path / "data" / "images").handle("GET", "/", {}).body
    assert "dario.ink" in html
    assert "Commissiona questo artista" in html


def test_upload_senza_handle_non_crea_artisti_fantasma(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    src = tmp_path / "in"
    src.mkdir()
    Image.new("RGB", (16, 16), (5, 5, 5)).save(src / "a.png")
    main(["ingest", "--kind", "upload", "--ref", str(src)])
    assert "0 con artista attribuito" in capsys.readouterr().out
    store = Store(tmp_path / "data" / "inkscout.db")
    assert store.conn.execute("SELECT COUNT(*) c FROM artist").fetchone()["c"] == 0
