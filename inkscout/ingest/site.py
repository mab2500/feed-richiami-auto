"""Adapter per siti personali: og:image, <img src/srcset>, JSON-LD. Via primaria e lecita."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from inkscout.core.models import RawItem, SourceRef
from inkscout.ingest.base import fetch_bytes, fetch_text, now_iso, register


class _ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta" and d.get("property") == "og:image" and d.get("content"):
            self.found.append(d["content"])
        if tag == "img":
            if d.get("src"):
                self.found.append(d["src"])
            for part in (d.get("srcset") or "").split(","):
                url = part.strip().split(" ")[0]
                if url:
                    self.found.append(url)


def extract_image_urls(html: str, base_url: str) -> list[str]:
    """Funzione pura: estrae URL immagine da og:image, img src/srcset e JSON-LD `image`.

    Risolve i relativi in assoluti rispetto a `base_url` e deduplica preservando l'ordine.
    """
    p = _ImgParser()
    p.feed(html)
    raw = list(p.found)
    for m in re.finditer(r'"image"\s*:\s*"([^"]+)"', html):  # JSON-LD (semplice)
        raw.append(m.group(1))
    out, seen = [], set()
    for u in raw:
        absu = urljoin(base_url, u)
        if absu not in seen:
            seen.add(absu)
            out.append(absu)
    return out


@register("site")
class PersonalSiteAdapter:
    kind = "site"

    def __init__(self, cache_dir: Path | str = ".cache"):
        self.cache_dir = Path(cache_dir)

    def fetch(self, source: SourceRef) -> Iterable[RawItem]:
        html = fetch_text(source.ref, self.cache_dir)
        for img_url in extract_image_urls(html, source.ref):
            data = fetch_bytes(img_url, self.cache_dir)
            yield RawItem(
                source_url=img_url,
                artist_handle="",
                fetched_at=now_iso(),
                license_note="personal-site",
                image_bytes=data,
            )
