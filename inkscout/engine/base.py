"""Un solo contratto DesignEngine, N backend registrati per `mode`.
Provider/modello dietro interfaccia; nessun `if provider == ...` altrove."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from inkscout.core.models import Brief, DesignResult, EngineCapabilities

_ENGINES: dict[str, type] = {}


class EngineKeyMissing(Exception):
    pass


@runtime_checkable
class DesignEngine(Protocol):
    mode: str
    capabilities: EngineCapabilities

    def generate(self, brief: Brief) -> DesignResult: ...


def register_engine(mode: str):
    def deco(cls):
        _ENGINES[mode] = cls
        return cls

    return deco


def get_engine(mode: str, **kwargs) -> DesignEngine:
    return _ENGINES[mode](**kwargs)


def available_modes() -> list[str]:
    return sorted(_ENGINES)
