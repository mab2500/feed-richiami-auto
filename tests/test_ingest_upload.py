"""Test per UploadAdapter (inkscout/ingest/upload.py)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from inkscout.core.models import SourceRef
from inkscout.ingest.base import get_adapter
from inkscout.ingest.upload import UploadAdapter


def test_upload_dir_emits_one_rawitem_per_image(tmp_path):
    for name in ("a.png", "b.jpg", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    Image.new("RGB", (8, 8)).save(tmp_path / "a.png")
    Image.new("RGB", (8, 8)).save(tmp_path / "b.jpg")
    items = list(UploadAdapter().fetch(SourceRef(kind="upload", ref=str(tmp_path))))
    paths = sorted(Path(i.local_path).name for i in items)
    assert paths == ["a.png", "b.jpg"]
    assert all(i.license_note == "user-upload" for i in items)
    assert all(i.source_url.startswith("file://") for i in items)


def test_upload_single_file_ref_emits_one_rawitem(tmp_path):
    img_path = tmp_path / "solo.webp"
    Image.new("RGB", (8, 8)).save(img_path, format="WEBP")
    items = list(UploadAdapter().fetch(SourceRef(kind="upload", ref=str(img_path))))
    assert len(items) == 1
    item = items[0]
    assert item.local_path == str(img_path)
    assert item.source_url == f"file://{img_path.resolve()}"
    assert item.license_note == "user-upload"


def test_upload_item_has_full_provenance(tmp_path):
    img_path = tmp_path / "prov.png"
    Image.new("RGB", (8, 8)).save(img_path)
    item = next(iter(UploadAdapter().fetch(SourceRef(kind="upload", ref=str(tmp_path)))))
    # Provenance obbligatoria anche per gli upload locali (vincolo globale §spec).
    assert item.source_url == f"file://{img_path.resolve()}"
    assert item.license_note == "user-upload"
    assert item.fetched_at != ""


def test_upload_adapter_has_no_required_constructor_args_and_is_registered():
    # @register("upload") istanzia la classe a tempo di import: il costruttore
    # non deve richiedere argomenti, altrimenti l'import di questo modulo fallirebbe.
    adapter = get_adapter("upload")
    assert adapter.kind == "upload"
    assert isinstance(adapter, UploadAdapter)
