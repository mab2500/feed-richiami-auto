"""Libreria: persiste immagini + provenance, collassa i near-duplicati."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from inkscout.core.models import RawItem
from inkscout.library.phash import dhash, is_near_dup
from inkscout.store.db import Store

@dataclass
class AddResult:
    image_id: int
    is_duplicate: bool
    duplicate_of: int | None


class Library:
    def __init__(self, store: Store, images_dir: Path | str):
        self.store = store
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        raw: RawItem,
        artist_id: int | None = None,
        source_id: int | None = None,
        near_dup_threshold: int = 5,
    ) -> AddResult:
        if not raw.source_url or not raw.license_note:
            raise ValueError("provenance obbligatoria: servono source_url e license_note")
        from PIL import Image

        if raw.image_bytes is not None:
            img = Image.open(BytesIO(raw.image_bytes))
            data = raw.image_bytes
        elif raw.local_path:
            with open(raw.local_path, "rb") as fh:
                data = fh.read()
            img = Image.open(BytesIO(data))
        else:
            raise ValueError("RawItem senza image_bytes né local_path")

        ph = dhash(img)
        for existing_id, other in self.store.all_phashes():
            if is_near_dup(ph, other, near_dup_threshold):
                return AddResult(existing_id, True, existing_id)

        ext = (img.format or "PNG").lower()
        dest = self.images_dir / f"{ph:016x}.{ext}"
        dest.write_bytes(data)
        image_id = self.store.add_image(
            path=str(dest),
            phash=ph,
            width=img.width,
            height=img.height,
            artist_id=artist_id,
            source_id=source_id,
            source_url=raw.source_url,
            license_note=raw.license_note,
            fetched_at=raw.fetched_at,
        )
        return AddResult(image_id, False, None)

    def favorite(self, image_id: int, value: bool = True) -> None:
        self.store.set_favorite(image_id, value)

    def hide(self, image_id: int, value: bool = True) -> None:
        self.store.set_hidden(image_id, value)
