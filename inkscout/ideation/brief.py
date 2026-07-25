"""Da (reference selezionata o tema libero) + assi → Brief strutturato.
Il tema è testo libero: viene espanso a runtime cercando nella libreria."""

from __future__ import annotations

from pathlib import Path

from inkscout.core.models import Brief
from inkscout.store.db import Store

_DEFAULT = "_default"


def _seed_di_default() -> Path:
    from inkscout.config import load_config

    return load_config().styles_seed


def line_treatment_for(styles: list[str], *, store: Store | None = None,
                       seed_path: str | Path | None = None) -> str:
    """Il trattamento della linea per gli stili scelti.

    ⚠️ Prima qui c'erano due set di NOMI DI STILE (`_BOLD`/`_FINE`) scritti nel sorgente:
    violava il vincolo §2 dello spec («stili = dati, non enum nel codice») e voleva dire
    che aggiungere uno stile al seed non bastava — bisognava anche ricordarsi di toccare
    questo file. Ora il codice conosce solo l'asse `linework`: quale stile abbia quale
    linework, e come si traduca, sta nei dati (`styles.seed.yaml` → DB).
    """
    from inkscout.tagging.vocab import line_treatments, linework_di

    seed = Path(seed_path) if seed_path else _seed_di_default()
    tabella = line_treatments(seed)
    default = tabella.get(_DEFAULT, "clean linework")
    trovati = {lw.lower() for lw in linework_di(list(styles or []), store=store, path=seed)}
    if not trovati:
        return default
    # l'ordine della tabella nei dati È la priorità (il tratto più fine per primo)
    for linework, trattamento in tabella.items():
        if linework != _DEFAULT and linework.lower() in trovati:
            return trattamento
    return default


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
        # con lo store il vocabolario è quello CORRENTE del DB (stili aggiunti compresi)
        line_treatment=line_treatment_for(styles, store=store),
        reference_image_ids=refs,
    )
