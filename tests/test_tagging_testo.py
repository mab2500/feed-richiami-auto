"""TestoTagger: i tag vengono dalle parole di Matteo, non da un modello.

Il valore: gira senza GPU, senza API e senza foto; e ciò che dice è verificabile, perché
l'ha scritto un umano guardando quell'immagine.
"""

from PIL import Image

from inkscout.cli import main
from inkscout.store.db import Store
from inkscout.tagging.testo import TestoTagger
from inkscout.web.app import App

ASSI = {
    "form": {"round": ["rotondo", "tondo"], "linear": ["lineare"]},
    "color_mode": {"black-only": ["nero", "bianco e nero"], "color": ["colorato"]},
    "placement": {"wrist": ["polso"], "forearm": ["avambraccio"]},
}
STILI = {"fine-line": ["fineline", "single-needle"], "blackwork": [], "dotwork": []}


def _tagger():
    return TestoTagger(assi=ASSI, stili=STILI)


def test_riconosce_gli_assi_in_italiano():
    tags = {(t.axis, t.value) for t in _tagger().tag_testo(
        "questo serpente rotondo tutto nero sul polso")}
    assert ("form", "round") in tags
    assert ("color_mode", "black-only") in tags
    assert ("placement", "wrist") in tags


def test_confini_di_parola_niente_falsi_positivi():
    """`nero` non deve scattare dentro «nerofumo», né `polso` dentro «impolso»."""
    tags = {(t.axis, t.value) for t in _tagger().tag_testo("un pigmento nerofumo impolso")}
    assert ("color_mode", "black-only") not in tags
    assert ("placement", "wrist") not in tags


def test_stili_anche_dagli_alias():
    t = _tagger()
    assert t.stili_nel_testo("mi piace il fineline") == ["fine-line"]
    assert t.stili_nel_testo("blackwork e dotwork insieme") == ["blackwork", "dotwork"]
    assert t.stili_nel_testo("niente di riconoscibile") == []


def test_soggetto_e_testo_libero_senza_handle_e_stopword():
    s = _tagger().soggetto("guarda questo serpente di @dario.ink https://x.com bellissimo")
    assert "serpente" in s
    assert "@dario.ink" not in s and "http" not in s
    assert "guarda" not in s and "questo" not in s


def test_testo_vuoto_non_inventa_tag():
    """Se la chat non dice niente, il tagger tace: tocca a CLIP o al Vision LLM."""
    assert _tagger().tag_testo("") == []
    assert _tagger().tag_testo("   ") == []


def test_accenti_e_maiuscole():
    tags = {(t.axis, t.value) for t in _tagger().tag_testo("ROTONDO sull'avambraccio")}
    assert ("form", "round") in tags and ("placement", "forearm") in tags


CHAT = (
    "[06/09/24, 21:14:02] Matteo: questo serpente blackwork rotondo\n"
    "[06/09/24, 21:14:20] Matteo: ‎<allegato: FOTO-1.jpg>\n"
    "[06/09/24, 21:15:01] Matteo: è di @dario.ink, lo voglio sul polso\n"
)


def test_ingest_whatsapp_tagga_e_la_galleria_diventa_cercabile(tmp_path, monkeypatch, capsys):
    """End-to-end: dalla frase in chat alla ricerca per tema nella galleria."""
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    d = tmp_path / "Tatuaggi mab"
    d.mkdir(parents=True)
    (d / "_chat.txt").write_text(CHAT, encoding="utf-8")
    Image.new("RGB", (32, 32), (12, 12, 12)).save(d / "FOTO-1.jpg")

    main(["sync-styles"])
    main(["ingest", "--kind", "whatsapp", "--ref", str(d), "--chat", "Tatuaggi mab"])
    assert "1 taggate dal testo" in capsys.readouterr().out

    store = Store(tmp_path / "data" / "inkscout.db")
    img_id = store.list_images()[0]["id"]
    tags = {(t["axis"], t["value"]) for t in store.image_tags(img_id)}
    assert ("form", "round") in tags
    assert ("placement", "wrist") in tags
    assert any(a == "subject" and "serpente" in v for a, v in tags)
    # lo stile nominato in chat è collegato davvero
    stili = [r["name"] for r in store.conn.execute(
        "SELECT s.name FROM style s JOIN image_style i ON i.style_id=s.id WHERE i.image_id=?",
        (img_id,))]
    assert "blackwork" in stili

    # e la galleria lo trova cercando la parola che ha usato lui
    app = App(store, tmp_path / "data" / "images")
    assert f"/image/{img_id}" in app.handle("GET", "/", {"theme": "serpente"}).body
    assert f"/image/{img_id}" not in app.handle("GET", "/", {"theme": "balena"}).body
