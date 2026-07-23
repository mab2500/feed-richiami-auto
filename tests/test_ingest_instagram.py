import pytest

from inkscout.ingest import instagram as ig
from inkscout.ingest import base
from inkscout.core.models import SourceRef


def test_requires_optin():
    with pytest.raises(ig.HarvestNotOptedIn):
        list(ig.InstagramAdapter().fetch(SourceRef(kind="instagram", ref="@jane")))


def test_extract_media_is_pure():
    payload = {
        "data": {
            "user": {
                "media": {
                    "edges": [
                        {"node": {"display_url": "https://cdn/1.jpg", "shortcode": "AAA"}},
                        {"node": {"display_url": "https://cdn/2.jpg", "shortcode": "BBB"}},
                    ]
                }
            }
        }
    }
    media = ig.extract_media(payload)
    assert [m["shortcode"] for m in media] == ["AAA", "BBB"]


def test_optin_fetch_emits_rawitems(monkeypatch, tmp_path):
    import json

    payload = {
        "data": {
            "user": {
                "media": {
                    "edges": [{"node": {"display_url": "https://cdn/1.jpg", "shortcode": "AAA"}}]
                }
            }
        }
    }
    monkeypatch.setattr(base, "_http_get", lambda url: json.dumps(payload).encode())
    adapter = ig.InstagramAdapter(cache_dir=tmp_path, throttle_s=0)
    items = list(adapter.fetch(SourceRef(kind="instagram", ref="@jane", harvest_optin=True)))
    assert items[0].artist_handle == "@jane"
    assert items[0].license_note == "ig-harvest-personal"
    assert items[0].source_url == "https://cdn/1.jpg"
