from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from inkscout.core.models import RawItem
from inkscout.library.library import Library
from inkscout.store.db import Store


def _png_bytes(color):
    buf = BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


def _lib(tmp_path):
    store = Store(tmp_path / "t.db")
    return Library(store, tmp_path / "images"), store


def _raw(color, url="https://ex/a"):
    return RawItem(
        source_url=url,
        artist_handle="@x",
        fetched_at="2026-07-23T00:00:00",
        license_note="personal-reference",
        image_bytes=_png_bytes(color),
    )


def test_add_creates_row_and_file(tmp_path):
    lib, store = _lib(tmp_path)
    res = lib.add(_raw((10, 20, 30)))
    assert res.is_duplicate is False
    row = store.get_image(res.image_id)
    assert Path(row["path"]).exists()
    assert row["source_url"] == "https://ex/a" and row["width"] == 64


def test_near_duplicate_not_reinserted(tmp_path):
    lib, store = _lib(tmp_path)
    first = lib.add(_raw((10, 20, 30), url="https://ex/a"))
    dup = lib.add(_raw((10, 20, 30), url="https://ex/b"))
    assert dup.is_duplicate is True and dup.duplicate_of == first.image_id
    assert len(store.all_phashes()) == 1


def test_distinct_images_both_stored(tmp_path):
    lib, store = _lib(tmp_path)
    lib.add(_raw((0, 0, 0)))
    grad = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            grad.putpixel((x, y), x * 4 % 256)
    buf = BytesIO()
    grad.save(buf, format="PNG")
    lib.add(
        RawItem(
            source_url="https://ex/g",
            artist_handle="@x",
            fetched_at="t",
            license_note="ref",
            image_bytes=buf.getvalue(),
        )
    )
    assert len(store.all_phashes()) == 2


def test_missing_provenance_raises(tmp_path):
    lib, _ = _lib(tmp_path)
    with pytest.raises(ValueError):
        lib.add(
            RawItem(
                source_url="",
                artist_handle="@x",
                fetched_at="t",
                license_note="ref",
                image_bytes=_png_bytes((1, 2, 3)),
            )
        )


# --- Test aggiuntivi rispetto al piano (non nel piano, aggiunti per copertura) ---


def test_missing_license_note_raises(tmp_path):
    """Simmetrico a test_missing_provenance_raises: la provenance manca anche
    quando source_url c'è ma license_note e' vuota (§interfaccia: 'source_url o
    license_note vuoti')."""
    lib, _ = _lib(tmp_path)
    with pytest.raises(ValueError):
        lib.add(
            RawItem(
                source_url="https://ex/a",
                artist_handle="@x",
                fetched_at="t",
                license_note="",
                image_bytes=_png_bytes((1, 2, 3)),
            )
        )


def test_add_from_local_path(tmp_path):
    """RawItem può portare l'immagine come local_path invece di image_bytes
    (branch non esercitato dai test del piano ma parte del contratto RawItem)."""
    lib, store = _lib(tmp_path)
    src_path = tmp_path / "source.png"
    src_path.write_bytes(_png_bytes((5, 6, 7)))
    raw = RawItem(
        source_url="https://ex/local",
        artist_handle="@x",
        fetched_at="t",
        license_note="ref",
        local_path=str(src_path),
    )
    res = lib.add(raw)
    assert res.is_duplicate is False
    row = store.get_image(res.image_id)
    assert Path(row["path"]).exists()
    assert row["width"] == 64
