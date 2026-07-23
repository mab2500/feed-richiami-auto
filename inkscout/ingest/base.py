"""Contratto adapter + registry + fetch HTTP-first con cache su disco.

`_http_get` è l'unico punto che tocca la rete: i test lo monkeypatchano.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

from inkscout.core.models import RawItem, SourceRef

_REGISTRY: dict[str, "SourceAdapter"] = {}


@runtime_checkable
class SourceAdapter(Protocol):
    kind: str

    def fetch(self, source: SourceRef) -> Iterable[RawItem]: ...


def register(kind: str):
    def deco(cls):
        _REGISTRY[kind] = cls()
        return cls

    return deco


def get_adapter(kind: str) -> SourceAdapter:
    return _REGISTRY[kind]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str) -> bytes:
    """HTTP-first con curl_cffi (impersona Chrome). Import lazy."""
    from curl_cffi import requests as cffi

    resp = cffi.get(url, impersonate="chrome", timeout=30)
    resp.raise_for_status()
    return resp.content


def _cache_path(url: str, cache_dir: Path) -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()[:32]
    return Path(cache_dir) / key


def fetch_bytes(url: str, cache_dir: Path, *, force: bool = False) -> bytes:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = _cache_path(url, cache_dir)
    if cp.exists() and not force:
        return cp.read_bytes()
    data = _http_get(url)
    cp.write_bytes(data)
    return data


def fetch_text(url: str, cache_dir: Path, *, force: bool = False) -> str:
    return fetch_bytes(url, cache_dir, force=force).decode("utf-8", errors="replace")
