"""Da (reference selezionata o tema libero) + assi → Brief strutturato.
Il tema è testo libero: viene espanso a runtime cercando nella libreria."""

from __future__ import annotations

from inkscout.core.models import Brief
from inkscout.store.db import Store

_BOLD = {"blackwork", "traditional", "neo-traditional", "geometric", "old-school"}
_FINE = {"fine-line", "fineline", "minimalist", "ornamental"}


def line_treatment_for(styles: list[str]) -> str:
    s = {x.lower() for x in styles}
    if s & _FINE:
        return "single-weight fine lines"
    if s & _BOLD:
        return "bold black outlines"
    return "clean linework"


def expand_theme(theme_text: str, store: Store, limit: int = 12) -> list[int]:
    if not theme_text:
        return []
    rows = store.list_images(theme=theme_text)
    return [r["id"] for r in rows][:limit]


def build_brief(
    *,
    theme_text="",
    styles=None,
    form="",
    color_mode="",
    placement="",
    size="",
    reference_image_ids=None,
    store=None,
) -> Brief:
    styles = styles or []
    refs = list(reference_image_ids or [])
    if not refs and theme_text and store is not None:
        refs = expand_theme(theme_text, store)
    return Brief(
        theme_text=theme_text,
        styles=styles,
        form=form,
        color_mode=color_mode,
        placement=placement,
        size=size,
        line_treatment=line_treatment_for(styles),
        reference_image_ids=refs,
    )
