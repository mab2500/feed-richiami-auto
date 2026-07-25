"""Adapter per gli export di chat WhatsApp — la fonte più ricca che Matteo ha già.

Le chat «Tatuaggi …» contengono le reference che gli piacciono **e**, nel messaggio
accanto, chi le ha fatte (handle IG, nome dello studio). Questo adapter tiene insieme le
due cose: l'immagine e il suo contesto, che è esattamente ciò che la libreria pretende
(provenance) e che il tagging può usare come soggetto libero.

**Non è scraping**: legge un export che l'utente ha prodotto e possiede (`_chat.txt` +
media nella stessa cartella), in locale. Nessuna rete, nessun ToS toccato.

⚠️ **Privacy — scelta deliberata.** Una chat è una conversazione privata, spesso con una
seconda persona. L'adapter **non copia la chat**: per ogni immagine tiene solo una
finestra di contesto di pochi messaggi, troncata (`MAX_CONTESTO`). Serve a riconoscere
l'artista e il soggetto, non a ricostruire il dialogo. Il DB di ink-scout vive fuori dal
repo (`INK_SCOUT_DATA_DIR`, default `~/.ink-scout`) e non va versionato.

Formati supportati (WhatsApp cambia a seconda di iOS/Android e lingua):
    [21/08/21, 14:32:11] Matteo: ‎<allegato: 00000042-PHOTO-2021-08-21.jpg>   (iOS)
    21/08/21, 14:32 - Matteo: IMG-20210821-WA0001.jpg (file allegato)          (Android)
    …e le varianti inglesi `<attached: …>` / `(file attached)`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from inkscout.core.models import RawItem, SourceRef
from inkscout.ingest.base import now_iso, register

_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# quanti messaggi guardare prima/dopo l'immagine per capire di chi è e cosa rappresenta
FINESTRA_CONTESTO = 2
# tetto al testo copiato per immagine: è un indizio, non un pezzo di conversazione
MAX_CONTESTO = 400

# WhatsApp infila marcatori di direzione invisibili (U+200E/U+200F) un po' ovunque
_INVISIBILI = dict.fromkeys(map(ord, "‎‏‪‬"), None)

# `[gg/mm/aa, hh:mm:ss] Mittente: testo`  oppure  `gg/mm/aa, hh:mm - Mittente: testo`
_RIGA = re.compile(
    r"^\[?(\d{1,2}[/.]\d{1,2}[/.]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)"
    r"(?:\s*[APap]\.?[Mm]\.?)?\s*(?:\]\s*|-\s+)([^:]{1,60}?):\s?(.*)$"
)

_ALLEGATI = (
    re.compile(r"<(?:allegato|attached):\s*([^>]+?)>", re.I),                      # iOS
    re.compile(r"([\w\-. ]+\.(?:jpg|jpeg|png|webp))\s*\((?:file\s+)?"
               r"(?:allegato|attached|allegata)\)", re.I),                          # Android
)

# handle IG: `@nome` o un link instagram. Il lookbehind evita di pescare le email.
_HANDLE = re.compile(r"(?:instagram\.com/|(?<![\w.@])@)([A-Za-z0-9._]{2,30})")
# parole che seguono un @ ma non sono handle (menzioni di contatti, orari…)
_NON_HANDLE = {"gmail", "libero", "icloud", "hotmail", "yahoo", "outlook"}


@dataclass
class Messaggio:
    data: str
    ora: str
    mittente: str
    testo: str
    allegato: str | None = None
    meta: dict = field(default_factory=dict)


def _pulisci(s: str) -> str:
    return s.translate(_INVISIBILI).strip()


def estrai_allegato(testo: str) -> str | None:
    """Il nome del file allegato, in qualsiasi dialetto di export. None se non c'è."""
    for rx in _ALLEGATI:
        m = rx.search(testo)
        if m:
            nome = _pulisci(m.group(1))
            if Path(nome).suffix.lower() in _EXT:
                return nome
    return None


def estrai_handle(testo: str) -> str:
    """Il primo handle IG plausibile nel testo — è così che si risale al tatuatore."""
    for m in _HANDLE.finditer(testo or ""):
        h = m.group(1).strip(".")
        if h.lower() in _NON_HANDLE or len(h) < 2:
            continue
        return f"@{h}"
    return ""


def parse_export(testo: str) -> list[Messaggio]:
    """Da `_chat.txt` a messaggi. Le righe senza timestamp sono continuazioni del
    messaggio precedente (WhatsApp manda a capo dentro un messaggio solo)."""
    messaggi: list[Messaggio] = []
    for riga_grezza in (testo or "").splitlines():
        riga = _pulisci(riga_grezza)
        if not riga:
            continue
        m = _RIGA.match(riga)
        if m:
            data, ora, mittente, corpo = m.groups()
            messaggi.append(Messaggio(
                data=data, ora=ora, mittente=_pulisci(mittente), testo=_pulisci(corpo),
                allegato=estrai_allegato(corpo)))
        elif messaggi:
            messaggi[-1].testo = f"{messaggi[-1].testo}\n{riga}".strip()
            if messaggi[-1].allegato is None:
                messaggi[-1].allegato = estrai_allegato(riga)
    return messaggi


def handle_vicino(messaggi: list[Messaggio], i: int,
                  finestra: int = FINESTRA_CONTESTO) -> str:
    """L'handle da attribuire all'immagine in posizione `i`.

    ⚠️ **Non** il primo handle della finestra: quello sbagliato di sistema. Misurato su un
    export di prova — con due foto di due tatuatori diversi nella stessa chat,
    «primo handle trovato» pescava l'artista del messaggio *precedente* e attribuiva
    entrambe le foto alla persona sbagliata. Attribuire un lavoro all'artista sbagliato è
    proprio ciò che le guardie §11 devono impedire.

    Ordine di ricerca, dal più attendibile: la didascalia dello stesso messaggio, poi il
    messaggio **successivo** (si manda la foto e poi si dice di chi è), poi il precedente,
    allargandosi per distanza crescente.
    """
    ordine = [i]
    for d in range(1, finestra + 1):
        ordine += [i + d, i - d]
    for j in ordine:
        if 0 <= j < len(messaggi):
            h = estrai_handle(messaggi[j].testo)
            if h:
                return h
    return ""


def contesto(messaggi: list[Messaggio], i: int, finestra: int = FINESTRA_CONTESTO) -> str:
    """Il testo attorno all'immagine, senza i nomi-file degli allegati (rumore).

    Ogni messaggio va all'immagine **più vicina**, non a tutte quelle che se lo trovano
    nella finestra: in una chat con più reference di artisti diversi (il caso normale)
    una finestra simmetrica cieca sconfina sui messaggi dell'immagine precedente e
    attribuisce l'opera al tatuatore sbagliato — l'opposto della guardia §11.
    A parità di distanza vince l'immagine precedente («foto, poi commento»).
    """
    immagini = [k for k, m in enumerate(messaggi) if m.allegato]
    pezzi = []
    for j in range(max(0, i - finestra), min(len(messaggi), i + finestra + 1)):
        if j != i and immagini:
            proprietario = min(immagini, key=lambda k: (abs(k - j), k > j))
            if proprietario != i:
                continue
        t = messaggi[j].testo
        if messaggi[j].allegato:
            t = t.replace(messaggi[j].allegato, "").strip()
            t = re.sub(r"<(?:allegato|attached):\s*>|\((?:file\s+)?(?:allegato|attached)\)",
                       "", t, flags=re.I).strip()
        if t:
            pezzi.append(t)
    return " · ".join(pezzi)[:MAX_CONTESTO]


def _trova_file(cartella: Path, nome: str) -> Path | None:
    """Il file accanto all'export. WhatsApp a volte rinomina: fallback sul suffisso."""
    diretto = cartella / nome
    if diretto.is_file():
        return diretto
    for p in cartella.rglob("*"):
        if p.is_file() and p.name == nome:
            return p
    return None


def trova_export(cartella: Path) -> Path | None:
    """`_chat.txt` (iOS) o `WhatsApp Chat with ….txt` (Android): il primo .txt utile."""
    if cartella.is_file():
        return cartella if cartella.suffix.lower() == ".txt" else None
    candidati = sorted(cartella.glob("*.txt"), key=lambda p: (p.name != "_chat.txt", p.name))
    return candidati[0] if candidati else None


@register("whatsapp")
class WhatsAppAdapter:
    kind = "whatsapp"

    def fetch(self, source: SourceRef) -> Iterable[RawItem]:
        """`source.ref` = la cartella dell'export (o il .txt stesso, coi media accanto)."""
        radice = Path(source.ref)
        export = trova_export(radice)
        if export is None:
            return
        cartella = export.parent
        chat = _pulisci(source.notes) or cartella.name
        messaggi = parse_export(export.read_text(encoding="utf-8", errors="ignore"))
        for i, msg in enumerate(messaggi):
            if not msg.allegato:
                continue
            percorso = _trova_file(cartella, msg.allegato)
            if percorso is None:          # export "senza media": l'immagine non c'è
                continue
            ctx = contesto(messaggi, i)
            yield RawItem(
                source_url=f"whatsapp://{chat}/{msg.allegato}",
                artist_handle=handle_vicino(messaggi, i),
                fetched_at=now_iso(),
                license_note="whatsapp-personal",
                local_path=str(percorso),
                meta={"chat": chat, "mittente": msg.mittente,
                      "data": msg.data, "contesto": ctx},
            )
