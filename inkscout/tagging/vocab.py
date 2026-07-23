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
