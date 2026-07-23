"""Contratto di tagging. Gli assi sono fissi; i valori vengono dai dati."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Tag:
    axis: str
    value: str
    confidence: float


@runtime_checkable
class Tagger(Protocol):
    def tag_image(self, image) -> list["Tag"]: ...
