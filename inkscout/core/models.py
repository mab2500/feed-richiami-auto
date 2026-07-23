"""Modello di dominio. Gli ASSI sono fissi (enum); i VALORI (temi/stili/artisti)
sono dati, mai enum — vincolo globale dello spec."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum


class Axis(str, Enum):
    SUBJECT = "subject"
    PLACEMENT = "placement"
    COLOR_MODE = "color_mode"
    DENSITY = "density"
    FORM = "form"


SOURCE_KINDS = ("upload", "site", "instagram", "pinterest", "tattoodo")
RESULT_KINDS = ("moodboard", "prompt", "raster", "svg")


@dataclass
class SourceRef:
    kind: str
    ref: str
    harvest_optin: bool = False
    notes: str = ""


@dataclass
class RawItem:
    source_url: str
    artist_handle: str
    fetched_at: str
    license_note: str
    image_bytes: bytes | None = None
    local_path: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Brief:
    theme_text: str = ""
    styles: list[str] = field(default_factory=list)
    form: str = ""
    color_mode: str = ""
    placement: str = ""
    size: str = ""
    line_treatment: str = ""
    reference_image_ids: list[int] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "Brief":
        return cls(**json.loads(raw))


@dataclass
class EngineCapabilities:
    needs_gpu: bool
    needs_key: bool
    cost_per_img: float
    watermarks: bool
    offline: bool


@dataclass
class DesignResult:
    kind: str
    engine: str
    prompt: str = ""
    moodboard_paths: tuple[str, ...] = ()
    raster_path: str | None = None
    svg_path: str | None = None
    meta: dict = field(default_factory=dict)
