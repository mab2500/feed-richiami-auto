"""Tagger dal TESTO: usa le parole che l'utente ha già scritto, invece di indovinare.

È il complemento naturale dell'adapter WhatsApp. Se accanto alla foto c'è scritto
«questo serpente fine-line, rotondo, sul polso», quelle sono informazioni migliori di
qualsiasi inferenza automatica: le ha scritte un umano guardando l'immagine.

Vantaggi rispetto a `ClipTagger`: gira **ovunque** (nessun modello, nessuna GPU, nessuna
API), è deterministico e spiegabile. Limite dichiarato: se la chat non dice niente, non
inventa nulla — restituisce zero tag, e tocca a CLIP o al Vision LLM.

Il vocabolario (stili e valori degli assi, coi modi in cui si scrivono in italiano) sta
nei DATI (`styles.seed.yaml`), mai qui: vincolo §2 dello spec.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from inkscout.tagging.base import Tag

# frammenti che non sono mai un soggetto utile
_STOPWORD = {
    "questo", "questa", "questi", "queste", "guarda", "che", "roba", "bello", "bella",
    "belli", "belle", "mi", "piace", "molto", "anche", "come", "per", "con", "del",
    "della", "dei", "delle", "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
    "di", "da", "in", "su", "e", "o", "ma", "poi", "sempre", "tipo", "forse", "magari",
    "vorrei", "voglio", "fatto", "fa", "lo", "ha", "sta", "studio", "https", "http",
}
_PAROLA = re.compile(r"[a-zàèéìòóùA-ZÀÈÉÌÒÓÙ][\w'àèéìòóù-]{2,}")
MAX_SUBJECT = 200


def _normalizza(s: str) -> str:
    """Minuscolo e senza accenti: «rotondò» e «Rotondo» devono valere uguale."""
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _contiene(testo_norm: str, frase: str) -> bool:
    """Confine di parola vero: `nero` non deve matchare dentro `nerofumo`, e la frase
    multi-parola («bianco e nero») va cercata intera."""
    f = _normalizza(frase).strip()
    if not f:
        return False
    return re.search(rf"(?<![\w-]){re.escape(f)}(?![\w-])", testo_norm) is not None


class TestoTagger:
    """`vocabolario`/`stili` sono iniettabili; di default vengono dal seed di config."""

    __test__ = False        # non è una classe di test: il nome inganna pytest

    def __init__(self, assi: dict | None = None, stili: dict | None = None,
                 seed_path: str | Path | None = None):
        if assi is None or stili is None:
            from inkscout.tagging.vocab import alias_stili, load_assi

            seed = Path(seed_path) if seed_path else self._seed_default()
            assi = load_assi(seed) if assi is None else assi
            stili = alias_stili(seed) if stili is None else stili
        self.assi = assi
        self.stili = stili

    @staticmethod
    def _seed_default() -> Path:
        from inkscout.config import load_config

        return load_config().styles_seed

    def stili_nel_testo(self, testo: str) -> list[str]:
        """Gli stili nominati, riconosciuti anche dagli alias del seed."""
        t = _normalizza(testo)
        return [nome for nome, alias in self.stili.items()
                if _contiene(t, nome) or any(_contiene(t, a) for a in alias)]

    def tag_testo(self, testo: str) -> list[Tag]:
        """Tag dagli assi + il testo stesso come soggetto (ricerca per tema libera)."""
        if not (testo or "").strip():
            return []
        t = _normalizza(testo)
        tags: list[Tag] = []
        for asse, valori in self.assi.items():
            for canonico, modi in valori.items():
                if _contiene(t, canonico) or any(_contiene(t, m) for m in modi):
                    tags.append(Tag(axis=asse, value=canonico, confidence=1.0))
                    break            # un valore per asse: il primo che compare nei dati
        soggetto = self.soggetto(testo)
        if soggetto:
            tags.append(Tag(axis="subject", value=soggetto, confidence=0.6))
        return tags

    def soggetto(self, testo: str) -> str:
        """Il testo ripulito da stopword e handle: diventa il tag `subject`, che è testo
        LIBERO (spec §2) e rende la galleria cercabile con le parole di Matteo."""
        senza_handle = re.sub(r"(?:https?://\S+|@[\w.]+)", " ", testo or "")
        parole = [p for p in _PAROLA.findall(senza_handle)
                  if _normalizza(p) not in _STOPWORD]
        return " ".join(parole)[:MAX_SUBJECT].strip()
