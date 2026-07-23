from inkscout.tagging.vocab import load_styles, sync_styles, style_names
from inkscout.store.db import Store

SEED = """
styles:
  - name: blackwork
    description: campiture nere piene, forte spazio negativo
    formal_attributes: {palette: black-only, linework: bold, density: high}
  - name: fine-line
    aliases: [fineline, single-needle]
    description: linee sottili a spessore costante
    formal_attributes: {palette: black-only, linework: thin}
"""


def test_load_styles(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(SEED)
    styles = load_styles(p)
    assert {s.name for s in styles} == {"blackwork", "fine-line"}
    fl = next(s for s in styles if s.name == "fine-line")
    assert "fineline" in fl.aliases
    assert fl.formal_attributes["linework"] == "thin"


def test_sync_is_idempotent(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(SEED)
    store = Store(tmp_path / "t.db")
    n1 = sync_styles(store, p)
    n2 = sync_styles(store, p)
    assert n1 == n2 == 2
    assert store.style_id_by_name("blackwork") is not None


def test_style_names(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(SEED)
    assert set(style_names(p)) == {"blackwork", "fine-line"}
