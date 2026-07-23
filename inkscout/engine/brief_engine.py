"""Modo E (DEFAULT, offline, no-API): brief + moodboard + prompt ottimizzato.
Regola di prompting validata (spec §5): stile PRIMA, poi trattamento linea e boilerplate stencil."""

from __future__ import annotations

from inkscout.core.models import Brief, DesignResult, EngineCapabilities
from inkscout.engine.base import register_engine
from inkscout.store.db import Store

_STENCIL = "tattoo stencil reference, white background, clear linework, no fuzzy edges"
NEGATIVE_PROMPT = (
    "color, colour, shading, grayscale photo, background clutter, "
    "photorealistic skin, blurry, watermark"
)


def build_prompt(brief: Brief) -> str:
    parts: list[str] = []
    if brief.styles:
        parts.append(" ".join(brief.styles))  # stile PRIMA
    if brief.theme_text:
        parts.append(brief.theme_text)
    if brief.line_treatment:
        parts.append(brief.line_treatment)
    parts.append(_STENCIL)
    if brief.placement:
        parts.append(f"placement: {brief.placement}")
    return ", ".join(parts)


@register_engine("E")
class BriefEngine:
    mode = "E"
    capabilities = EngineCapabilities(
        needs_gpu=False, needs_key=False, cost_per_img=0.0, watermarks=False, offline=True
    )

    def __init__(self, store: Store | None = None):
        self.store = store

    def generate(self, brief: Brief) -> DesignResult:
        moodboard: list[str] = []
        if self.store is not None:
            for img_id in brief.reference_image_ids:
                row = self.store.get_image(img_id)
                if row:
                    moodboard.append(row["path"])
        return DesignResult(
            kind="prompt",
            engine=self.mode,
            prompt=build_prompt(brief),
            moodboard_paths=tuple(moodboard),
            meta={"negative_prompt": NEGATIVE_PROMPT},
        )
