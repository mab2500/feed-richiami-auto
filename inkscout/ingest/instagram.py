"""Harvest IG SOLO opt-in personale, con banner ToS e throttle. Non è una feature-da-servizio.
Gli endpoint/doc_id non sono hardcodati: si passano via `profile_url_tmpl` (config)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

from inkscout.core.models import RawItem, SourceRef
from inkscout.ingest.base import fetch_text, now_iso, register

IG_TOS_BANNER = (
    "Harvest Instagram: SOLO uso personale. Viola i ToS di Instagram, è fragile "
    "(endpoint/doc_id cambiano), soggetto a rate-limit. Mai ridistribuzione."
)


class HarvestNotOptedIn(Exception):
    pass


def extract_media(payload: dict) -> list[dict]:
    """Pura: da un JSON profilo estrae [{display_url, shortcode}]. Nessun I/O."""
    edges = payload.get("data", {}).get("user", {}).get("media", {}).get("edges", [])
    out = []
    for e in edges:
        node = e.get("node", {})
        if node.get("display_url"):
            out.append({"display_url": node["display_url"], "shortcode": node.get("shortcode", "")})
    return out


@register("instagram")
class InstagramAdapter:
    """Registrato a tempo di import (`@register` istanzia subito): costruttore senza
    argomenti obbligatori."""

    kind = "instagram"

    def __init__(
        self,
        cache_dir: Path | str = ".cache",
        throttle_s: float = 12 * 60,
        profile_url_tmpl: str = "https://www.instagram.com/{handle}/?__a=1",
    ):
        self.cache_dir = Path(cache_dir)
        self.throttle_s = throttle_s
        self.profile_url_tmpl = profile_url_tmpl

    def fetch(self, source: SourceRef) -> Iterable[RawItem]:
        if not source.harvest_optin:
            raise HarvestNotOptedIn(IG_TOS_BANNER)
        handle = source.ref.lstrip("@")
        url = self.profile_url_tmpl.format(handle=handle)
        payload = json.loads(fetch_text(url, self.cache_dir))
        for m in extract_media(payload):
            time.sleep(self.throttle_s)
            yield RawItem(
                source_url=m["display_url"],
                artist_handle=source.ref,
                fetched_at=now_iso(),
                license_note="ig-harvest-personal",
                meta={"shortcode": m["shortcode"]},
            )
