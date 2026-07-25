"""Il vincolo §2 dello spec, verificato: stili = DATI, non enum nel codice.

Il test che conta è quello con uno stile **inventato**: se aggiungerlo al seed basta a
farlo funzionare, allora il vocabolario è davvero nei dati. Se servisse toccare il
sorgente, il vincolo sarebbe violato — ed è com'era fino al 24/07 (`_BOLD`/`_FINE`).
"""

import inkscout.ideation.brief as brief_mod
from inkscout.ideation.brief import build_brief, line_treatment_for
from inkscout.store.db import Store
from inkscout.tagging.vocab import line_treatments, linework_di, sync_styles

SEED_INVENTATO = """
line_treatments:
  thin: single-weight fine lines
  bold: bold black outlines
  _default: clean linework
styles:
  - name: stile-che-non-esiste
    description: inventato apposta per il test
    formal_attributes: {linework: thin}
  - name: altro-stile-finto
    formal_attributes: {linework: bold}
"""


def _seed(tmp_path, testo=SEED_INVENTATO):
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "s.yaml"
    p.write_text(testo, encoding="utf-8")
    return p


def test_uno_stile_mai_visto_dal_codice_funziona_lo_stesso(tmp_path):
    """LA prova del vincolo: nessuno di questi nomi compare nel sorgente."""
    p = _seed(tmp_path)
    assert line_treatment_for(["stile-che-non-esiste"], seed_path=p) == "single-weight fine lines"
    assert line_treatment_for(["altro-stile-finto"], seed_path=p) == "bold black outlines"
    assert line_treatment_for(["mai-sentito"], seed_path=p) == "clean linework"


def test_nessun_nome_di_stile_nel_sorgente():
    """Guardia anti-regressione: se qualcuno rimette una lista di stili nel codice,
    questo test lo becca."""
    codice = open(brief_mod.__file__, encoding="utf-8").read().lower()
    for nome in ("blackwork", "fine-line", "fineline", "traditional", "geometric",
                 "minimalist", "ornamental", "old-school"):
        assert nome not in codice, f"«{nome}» è tornato nel codice: violazione del vincolo §2"


def test_ordine_della_tabella_e_la_priorita(tmp_path):
    """Stili misti: vince il primo linework elencato nei dati (il tratto più fine)."""
    p = _seed(tmp_path)
    assert line_treatment_for(["altro-stile-finto", "stile-che-non-esiste"],
                              seed_path=p) == "single-weight fine lines"
    # invertendo l'ordine NEI DATI cambia la priorità, senza toccare il codice
    p2 = _seed(tmp_path / "b", SEED_INVENTATO.replace(
        "  thin: single-weight fine lines\n  bold: bold black outlines",
        "  bold: bold black outlines\n  thin: single-weight fine lines"))
    assert line_treatment_for(["altro-stile-finto", "stile-che-non-esiste"],
                              seed_path=p2) == "bold black outlines"


def test_dal_db_dopo_il_sync(tmp_path):
    store = Store(tmp_path / "t.db")
    sync_styles(store, _seed(tmp_path))
    assert linework_di(["stile-che-non-esiste"], store=store) == ["thin"]
    b = build_brief(theme_text="gufo", styles=["stile-che-non-esiste"], store=store)
    assert b.line_treatment == "single-weight fine lines"


def test_sync_styles_propaga_le_modifiche_al_seed(tmp_path):
    """Debito segnalato dagli esecutori: correggere il seed dopo il primo sync non
    aggiornava il DB — restava alla prima versione, in silenzio."""
    store = Store(tmp_path / "t.db")
    p = _seed(tmp_path)
    sync_styles(store, p)
    assert store.styles_formal_attributes()["stile-che-non-esiste"]["linework"] == "thin"

    p.write_text(SEED_INVENTATO.replace("{linework: thin}", "{linework: bold}"),
                 encoding="utf-8")
    n = sync_styles(store, p)
    assert n == 2
    attrs = store.styles_formal_attributes()
    assert attrs["stile-che-non-esiste"]["linework"] == "bold", "il seed non è stato propagato"
    assert len(store.conn.execute("SELECT id FROM style").fetchall()) == 2  # niente doppioni


def test_line_treatments_dal_seed_reale():
    """Il seed di produzione deve avere la tabella: senza, ogni brief cadrebbe sul default."""
    from inkscout.config import load_config

    tabella = line_treatments(load_config().styles_seed)
    assert tabella and "_default" in tabella
    assert "bold" in tabella and "thin" in tabella
