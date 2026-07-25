"""Carica il vocabolario stili da YAML e lo sincronizza nel DB. I valori sono DATI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from inkscout.store.db import Store


@dataclass
class StyleSeed:
    name: str
    aliases: list[str] = field(default_factory=list)
    parent: str | None = None
    formal_attributes: dict = field(default_factory=dict)
    description: str = ""
    is_emerging: bool = False


def load_styles(path: str | Path) -> list[StyleSeed]:
    doc = yaml.safe_load(Path(path).read_text()) or {}
    out = []
    for item in doc.get("styles", []):
        out.append(
            StyleSeed(
                name=item["name"],
                aliases=item.get("aliases", []),
                parent=item.get("parent"),
                formal_attributes=item.get("formal_attributes", {}),
                description=item.get("description", ""),
                is_emerging=item.get("is_emerging", False),
            )
        )
    return out


def sync_styles(store: Store, path: str | Path) -> int:
    styles = load_styles(path)
    for s in styles:
        parent_id = store.style_id_by_name(s.parent) if s.parent else None
        store.upsert_style(
            s.name,
            aliases=s.aliases,
            parent_style_id=parent_id,
            formal_attributes=s.formal_attributes,
            description=s.description,
            is_emerging=s.is_emerging,
        )
    return len(styles)


def style_names(path: str | Path) -> list[str]:
    return [s.name for s in load_styles(path)]


def line_treatments(path: str | Path) -> dict[str, str]:
    """La tabella `linework → istruzione di linea`, dai DATI (vincolo §2: il codice
    conosce l'asse `linework`, non i valori). L'ordine del dizionario è la priorità."""
    doc = yaml.safe_load(Path(path).read_text()) or {}
    return {str(k): str(v) for k, v in (doc.get("line_treatments") or {}).items()}


def linework_di(styles: list[str], *, store: Store | None = None,
                path: str | Path | None = None) -> list[str]:
    """I valori `linework` degli stili richiesti. In nessun caso stanno nel sorgente.

    Il DB è la verità **corrente** (contiene anche gli stili aggiunti dopo il seed), ma se
    lì non c'è nulla si ricade sul seed: senza questo fallback, chi non ha ancora lanciato
    `sync-styles` otterrebbe in silenzio il trattamento di default su ogni brief.
    """
    voluti = {s.strip().lower() for s in styles if s and s.strip()}
    if not voluti:
        return []
    trovati: list[str] = []
    if store is not None:
        for name, attrs in store.styles_formal_attributes().items():
            if name.lower() in voluti and attrs.get("linework"):
                trovati.append(str(attrs["linework"]))
    if not trovati and path is not None:
        for s in load_styles(path):
            if s.name.lower() in voluti and s.formal_attributes.get("linework"):
                trovati.append(str(s.formal_attributes["linework"]))
    return trovati
