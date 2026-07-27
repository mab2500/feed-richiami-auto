"""Gli 8 difetti «MECCANICO» del triage del 26/07, corretti: un test per ognuno.

Dalla pipeline di delega (`_meta/delega-out/L4-giudizio/TRIAGE-26-07.md`). «Meccanico» = la
correzione è locale, non che sia innocua: qui tre riguardano l'HTML della web UI (un apice in
uno stile rompe l'attributo) e due il modo A, che è l'unico che **paga** — un crash lì arriva
dopo aver speso la chiamata.

Resta fuori l'unica `SOSPETTO-CHIAMANTI` (`store/db.py`, parametro `styles`): nessuna via
d'ingresso reale lo passa.
"""

from html import escape
from pathlib import Path

import pytest
from PIL import Image

from inkscout.config import load_config
from inkscout.core.models import Brief
from inkscout.engine.hosted import HostedAPIEngine
from inkscout.store.db import Store
from inkscout.web import templates
from inkscout.web.app import App


# --------------------------------------------------------------------- engine/hosted (modo A)

def _cfg(tmp_path):
    return load_config({"INK_SCOUT_DATA_DIR": str(tmp_path),
                        "INK_SCOUT_FAL_MODEL_ID": "fal-ai/flux/schnell"})


def _brief():
    return Brief(theme_text="teschio", styles=["fineline"], form="round")


def test_risposta_senza_immagini_dice_cosa_manca(tmp_path):
    """`resp["images"][0]` su una risposta senza immagini moriva con KeyError/IndexError
    nudi — e succede DOPO aver pagato la chiamata, quindi il messaggio è tutto ciò che
    resta per capire se ritentare."""
    for risposta in ({}, {"images": []}, {"images": [{}]}):
        eng = HostedAPIEngine(_cfg(tmp_path), key_getter=lambda _a: "k",
                              poster=lambda *a: risposta, downloader=lambda _u: b"x")
        with pytest.raises(RuntimeError) as e:
            eng.generate(_brief())
        assert "immagin" in str(e.value).lower(), risposta


def test_api_key_col_newline_non_rompe_la_richiesta(tmp_path):
    """`security find-generic-password -w` restituisce la chiave con l'a capo: finiva
    dentro l'header Authorization e la richiesta HTTP falliva."""
    visti = {}

    def poster(url, payload, key):
        visti["key"] = key
        return {"images": [{"url": "https://x/y.png"}]}

    eng = HostedAPIEngine(_cfg(tmp_path), key_getter=lambda _a: "abc123\n",
                          poster=poster, downloader=lambda _u: b"\x89PNG")
    eng.generate(_brief())
    assert visti["key"] == "abc123"
    assert "\n" not in visti["key"]


# --------------------------------------------------------------------------- web/templates

def test_apice_in_uno_stile_non_rompe_l_attributo_html():
    """I valori finivano grezzi dentro attributi delimitati da apici singoli: uno stile
    come «l'ombra» chiudeva l'attributo e sfondava il markup."""
    html = templates.studio_form(["E", "A'B"], ["l'ombra", "fineline"])
    assert "A'B" not in html.replace(escape("A'B"), "")      # il modo è escapato
    assert "l'ombra" not in html.replace(escape("l'ombra"), "")  # e il placeholder pure


def test_negative_prompt_null_non_fa_crashare_il_risultato():
    """`escape(None)` è un AttributeError: il default di `.get` non copre il valore None."""

    class R:
        prompt = "p"
        meta = {"negative_prompt": None}

    assert "Negative" in templates.result_view(R(), [])


# --------------------------------------------------------------------------------- web/app

def _app(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"
    Image.new("RGB", (8, 8)).save(p)
    return App(store, tmp_path / "images"), store


def test_favorite_su_id_inesistente_risponde_404(tmp_path):
    """`get_image` ritorna None e `row["favorite"]` esplodeva: lo stesso guard c'è già
    in `_serve_image` e `_export`, mancava solo qui."""
    app, _store = _app(tmp_path)
    r = app.handle("POST", "/favorite", {"id": "99999"})
    assert r.status == 404


# ------------------------------------------------------------------------------ tagging/vocab

def test_vocabolario_letto_sempre_come_utf8():
    """`read_text()` senza encoding usa quello di sistema: su una macchina non-UTF-8 il
    vocabolario degli stili non si carica — e il tagging si spegne senza dirlo."""
    src = Path(templates.__file__).parent.parent / "tagging" / "vocab.py"
    testo = src.read_text(encoding="utf-8")
    assert "read_text()" not in testo, "un read_text senza encoding è rimasto"
    assert testo.count('read_text(encoding="utf-8")') >= 3


# ------------------------------------------------------------------------------------- cli

def test_conteggio_taggate_conta_le_scritture_non_i_candidati():
    """`con_tag += int(bool(tags))` contava i tag TROVATI, ma il ciclo salta quelli di
    asse `style`: una foto i cui tag erano tutti stili veniva contata come «taggata dal
    testo» senza che a DB finisse niente."""
    src = (Path(templates.__file__).parent.parent / "cli.py").read_text(encoding="utf-8")
    assert "con_tag += int(bool(tags))" not in src
