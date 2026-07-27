"""Due dei difetti «MECCANICO» del 26/07 provati sul COMPORTAMENTO, non sul sorgente.

`tests/test_difetti_meccanici.py` chiude gli 8 del triage, ma per due di essi il test
guarda il testo del file (`assert "con_tag += int(bool(tags))" not in src`,
`assert testo.count('read_text(encoding="utf-8")') >= 3`). Quei due passano anche se il
bug torna scritto in un altro modo, e falliscono per una riformattazione innocua: pinnano
la stringa, non l'invariante. Qui gli stessi due difetti vengono esercitati.

Entrambi provati contro il codice pre-correzione (447a4a2): falliscono senza la fix.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

import inkscout
from inkscout.cli import main
from inkscout.store.db import Store

_RADICE = Path(inkscout.__file__).resolve().parent.parent


# --------------------------------------------------------------------------------- cli

# Didascalia scelta apposta: «cybersigilism» è uno stile del seed ma NON è una parola
# «pertinente» per `tagging/testo.py` (non contiene tatu*/ink/blackwork/...). Quindi
# `tag_testo` non produce nulla e il vecchio `int(bool(tags))` contava zero — mentre lo
# stile finiva a DB davvero. Il numero stampato a fine ingest diceva meno del lavoro fatto.
CHAT = (
    "[06/09/24, 21:14:02] Matteo: cybersigilism\n"
    "[06/09/24, 21:14:20] Matteo: ‎<allegato: FOTO-1.jpg>\n"
)


def test_ingest_conta_la_foto_taggata_col_solo_stile_nel_testo(tmp_path, monkeypatch, capsys):
    """Il conteggio di fine ingest deve valere quanto è stato SCRITTO a DB.

    Prima: «0 taggate dal testo» con uno stile associato all'immagine — cioè il messaggio
    dichiarava un lavoro non fatto, nella direzione che lo fa sembrare più povero.
    """
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    d = tmp_path / "Tatuaggi mab"
    d.mkdir(parents=True)
    (d / "_chat.txt").write_text(CHAT, encoding="utf-8")
    Image.new("RGB", (32, 32), (7, 7, 7)).save(d / "FOTO-1.jpg")

    assert main(["sync-styles"]) == 0          # gli stili devono esistere a DB
    capsys.readouterr()
    assert main(["ingest", "--kind", "whatsapp", "--ref", str(d), "--chat", "t"]) == 0
    out = capsys.readouterr().out

    store = Store(tmp_path / "data" / "inkscout.db")
    riga = store.list_images()[0]
    # l'invariante vera: lo stile È a DB, quindi la foto va contata
    assert "cybersigilism" in store.styles_of_image(riga["id"])
    assert "1 taggate dal testo" in out, out


# ------------------------------------------------------------------------------ tagging/vocab

_SEED_NON_ASCII = (
    "line_treatments:\n"
    "  thin: linee sottili — spessore costante\n"
    "assi:\n"
    "  form:\n"
    "    round: [rotondo, circolare]\n"
    "styles:\n"
    "  - name: cybersigilism\n"
    "    description: tratti affilati, più spuntoni — è così\n"
)


def test_seed_non_ascii_si_carica_anche_se_il_locale_non_e_utf8(tmp_path):
    """`read_text()` senza encoding usa il default di sistema.

    Latente su macOS solo perché qui la modalità UTF-8 è attiva; con `PYTHONUTF8=0` e
    `LC_ALL=C` il default torna US-ASCII e il vocabolario degli stili — che contiene
    accenti e trattini lunghi, `data/styles.seed.yaml` compreso — non si carica più.
    Il tagging dal testo si spegnerebbe in silenzio.
    """
    seed = tmp_path / "s.yaml"
    seed.write_text(_SEED_NON_ASCII, encoding="utf-8")
    codice = (
        "from inkscout.tagging.vocab import load_assi, line_treatments, load_styles\n"
        f"p = {str(seed)!r}\n"
        "assert [s.name for s in load_styles(p)] == ['cybersigilism']\n"
        "assert load_assi(p)['form']['round'] == ['rotondo', 'circolare']\n"
        "assert list(line_treatments(p)) == ['thin']\n"
    )
    env = {**os.environ, "PYTHONUTF8": "0", "LC_ALL": "C", "PYTHONPATH": str(_RADICE)}
    r = subprocess.run([sys.executable, "-c", codice], env=env, cwd=str(tmp_path),
                       capture_output=True, text=True, errors="replace")
    assert r.returncode == 0, r.stderr
