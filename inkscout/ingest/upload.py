"""Adapter per file/directory locali caricati dall'utente."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from inkscout.core.models import RawItem, SourceRef
from inkscout.ingest.base import now_iso, register

_EXT = {".jpg", ".jpeg", ".png", ".webp"}


@register("upload")
class UploadAdapter:
    kind = "upload"

    def fetch(self, source: SourceRef) -> Iterable[RawItem]:
        root = Path(source.ref)
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for p in paths:
            if p.is_file() and p.suffix.lower() in _EXT:
                yield RawItem(
                    source_url=f"file://{p.resolve()}",
                    artist_handle="",
                    fetched_at=now_iso(),
                    license_note="user-upload",
                    local_path=str(p),
                )
