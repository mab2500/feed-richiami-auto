import pytest

from inkscout.core.models import RawItem, SourceRef
from inkscout.ingest import base


def test_register_and_get_adapter():
    @base.register("dummy")
    class Dummy:
        kind = "dummy"

        def fetch(self, source):
            return [
                RawItem(
                    source_url=source.ref,
                    artist_handle="",
                    fetched_at="t",
                    license_note="test",
                )
            ]

    got = base.get_adapter("dummy")
    items = list(got.fetch(SourceRef(kind="dummy", ref="u://x")))
    assert items[0].source_url == "u://x"


def test_get_adapter_unknown_raises():
    with pytest.raises(KeyError):
        base.get_adapter("nope-not-registered")


def test_fetch_text_uses_cache(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_http(url):
        calls["n"] += 1
        return b"<html>ok</html>"

    monkeypatch.setattr(base, "_http_get", fake_http)
    a = base.fetch_text("https://ex/p", tmp_path)
    b = base.fetch_text("https://ex/p", tmp_path)  # seconda volta: dalla cache
    assert a == b == "<html>ok</html>"
    assert calls["n"] == 1


def test_fetch_bytes_force_bypasses_cache(tmp_path, monkeypatch):
    responses = [b"first", b"second"]
    calls = {"n": 0}

    def fake_http(url):
        data = responses[calls["n"]]
        calls["n"] += 1
        return data

    monkeypatch.setattr(base, "_http_get", fake_http)
    a = base.fetch_bytes("https://ex/img.png", tmp_path)
    b = base.fetch_bytes("https://ex/img.png", tmp_path, force=True)
    assert a == b"first"
    assert b == b"second"  # force=True ignora la cache e rifetcha
    assert calls["n"] == 2


def test_fetch_bytes_never_hits_network_without_monkeypatch_when_cached(tmp_path, monkeypatch):
    # Nessuna rete reale nei test: se la cache esiste, _http_get non deve essere chiamato.
    def fail_http(url):
        raise AssertionError("non deve chiamare la rete se la cache esiste già")

    cache_dir = tmp_path
    calls = {"n": 0}

    def fake_http(url):
        calls["n"] += 1
        return b"cached-once"

    monkeypatch.setattr(base, "_http_get", fake_http)
    base.fetch_bytes("https://ex/once", cache_dir)
    assert calls["n"] == 1

    monkeypatch.setattr(base, "_http_get", fail_http)
    again = base.fetch_bytes("https://ex/once", cache_dir)
    assert again == b"cached-once"


def test_now_iso_returns_parseable_iso8601():
    from datetime import datetime

    value = base.now_iso()
    assert isinstance(value, str) and value != ""
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
