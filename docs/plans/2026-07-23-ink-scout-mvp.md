# ink-scout MVP (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire l'MVP spedibile di ink-scout (spec §13): ingest → libreria+dedup → tagging → ideazione → generazione Modo E (offline) + Modo A (fal.ai opt-in) → export stencil, con web UI locale e le guardie etiche/IP visibili.

**Architecture:** Package Python `inkscout` a moduli con responsabilità unica (ingest, library, tagging, ideation, engine, export, web), persistenza SQLite WAL, immagini su filesystem con provenance. La generazione è dietro un unico contratto `DesignEngine` con backend pluggable selezionati da config (Modo E default offline, Modo A cloud opt-in). Web UI in stdlib. Il core è leggero; CLIP, OpenCV/vtracer e i backend cloud sono `extras` con import lazy, così l'MVP gira offline senza GPU né chiavi.

**Tech Stack:** Python 3.11+ gestito con **uv**, lint/format **ruff**, test **pytest**. Core: `pyyaml`, `Pillow`, `curl_cffi`. Extras: `[tag]` (torch/open_clip), `[export]` (opencv-python/numpy/vtracer), `[cdp]` (nodriver). Web: `http.server`/`wsgiref` stdlib. DB: SQLite WAL (stdlib `sqlite3`).

## Global Constraints

Ogni task eredita implicitamente questi vincoli (dallo spec, verbatim dove possibile):

- **Package import:** `inkscout`. **Nome distribuzione:** `ink-scout` (es. `pip install ink-scout[gen]`).
- **Zero hardcoding di temi, artisti, stili.** Sono **dati** (YAML/DB), mai `enum` nel codice. Il codice conosce *assi* (stile, forma, colore, placement, density, subject), non *valori* (Twin Peaks, Dr. Woo, cybersigilism).
- **Stile ≠ tema.** Lo **stile** è vocabolario estendibile via dati (`data/styles.seed.yaml` → tabella `style`); il **tema/soggetto** è **testo libero** (+ embedding), mai enum.
- **Generazione pluggable.** Un solo contratto `DesignEngine`, N backend selezionabili. Nessun `if provider == "..."` sparso. **Model-id e prezzi in config, mai nel sorgente.**
- **Motore pesante sempre opzionale.** L'MVP funziona offline, senza GPU, senza chiavi. Dipendenze pesanti dietro `extras` (`[tag]`, `[export]`, `[cdp]`); **import lazy** dentro le funzioni, mai a livello di modulo.
- **Scraping HTTP-first** (`curl_cffi`, impersona Chrome) → **fallback CDP** (`nodriver`) solo su fallimento. **Cache su disco** di HTML/JSON e immagini. Harvest IG/Pinterest **solo opt-in personale** con banner ToS, throttle + backoff.
- **Provenance obbligatoria** su ogni immagine: `source_url`, `artist_handle`, `fetched_at`, `license_note`.
- **Guardie etiche/IP §11 visibili nel prodotto:** attribuzione + CTA "Commissiona questo artista"; label "AI-generated / reference only" su ogni output; opt-out `artist.do_not_mimic` filtrato a monte; niente "in the style of [artista vivente]" nei prompt (solo descrittori neutri).
- **Config:** env prefix `INK_SCOUT_`. **API-key in macOS Keychain** (voce `inkscout-fal-key`), mai in chiaro nel sorgente o nei log.
- **Stile "casa":** uv/ruff/pytest, web stdlib, cache su disco, SQLite WAL, TDD, commit frequenti. Coerente con `pricehunt`/`viaggio-advisor`/`cosa-guardo`.

## Struttura dei file (decomposizione)

```
ink-scout/
  pyproject.toml                 # progetto uv, deps core + extras
  inkscout/
    __init__.py
    config.py                    # env INK_SCOUT_*, path, Keychain helper
    core/models.py               # dataclass di dominio + Axis + costanti KIND
    store/db.py                  # SQLite WAL + schema + CRUD
    library/phash.py             # dHash percettivo + hamming
    library/library.py           # add con dedup, favorite/hide, provenance
    ingest/base.py               # SourceAdapter protocol + registry + cache HTTP
    ingest/upload.py             # UploadAdapter (file locali)
    ingest/site.py               # PersonalSiteAdapter (og:image/srcset/sitemap/JSON-LD)
    ingest/instagram.py          # InstagramAdapter (harvest opt-in, throttle)
    tagging/vocab.py             # loader styles.seed.yaml → vocabolario assi
    tagging/clip.py              # Tagger protocol + ClipTagger (lazy, cache)
    tagging/vision.py            # VisionLLMTagger opzionale (Claude)
    ideation/brief.py            # reference/tema → Brief; espansione tema via libreria
    engine/base.py               # DesignEngine protocol + EngineCapabilities + registry
    engine/brief_engine.py       # Modo E: moodboard + prompt ottimizzato (offline)
    engine/hosted.py             # Modo A: fal.ai (config-driven, key Keychain)
    export/stencil.py            # binarizza → 300 DPI → watermark → SVG (vtracer lazy)
    web/templates.py             # rendering HTML (stdlib, no framework)
    web/app.py                   # server stdlib + routing + guardie §11 in UI
    cli.py                       # ingest / tag / serve
  data/styles.seed.yaml          # vocabolario stili iniziale (dati, non codice)
  tests/                         # un file per modulo
```

Ogni Fase produce software testabile in isolamento. **Milestone camminante** dopo Fase 4 (carichi immagini → libreria → Modo E → export): è il flusso end-to-end minimo che dà valore anche senza CLIP né cloud.

---

## Fase 0 — Fondamenta del progetto

### Task 1: Scaffold del progetto (uv, ruff, pytest, extras)

**Files:**
- Create: `pyproject.toml`
- Create: `inkscout/__init__.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: —
- Produces: package importabile `inkscout` con `__version__: str`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_smoke.py
import inkscout


def test_package_importable_and_versioned():
    assert isinstance(inkscout.__version__, str)
    assert inkscout.__version__ != ""
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout'`.

- [ ] **Step 3: Implementazione minima**

```toml
# pyproject.toml
[project]
name = "ink-scout"
version = "0.1.0"
description = "Motore d'ispirazione + generatore per disegni di tatuaggi (locale, offline-first)"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "pillow>=10.0",
    "curl_cffi>=0.7",
]

[project.optional-dependencies]
tag = ["torch>=2.2", "open_clip_torch>=2.24"]
export = ["opencv-python>=4.9", "numpy>=1.26", "vtracer>=0.6"]
cdp = ["nodriver>=0.35"]
dev = ["pytest>=8.0", "ruff>=0.5"]

[project.scripts]
ink-scout = "inkscout.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# inkscout/__init__.py
"""ink-scout: motore d'ispirazione + generatore per disegni di tatuaggi."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml inkscout/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold progetto ink-scout (uv/ruff/pytest, extras)"
```

---

### Task 2: Config (`inkscout/config.py`)

**Files:**
- Create: `inkscout/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `class Config` con attributi `data_dir: Path`, `db_path: Path`, `images_dir: Path`, `cache_dir: Path`, `styles_seed: Path`, `fal_model_id: str`, `fal_price_per_img: float`.
  - `def load_config(env: Mapping[str, str] | None = None) -> Config` — legge env `INK_SCOUT_*`, default sotto `~/.ink-scout`.
  - `def keychain_get(account: str, service: str = "ink-scout") -> str | None` — legge una password dal Keychain macOS via `security`; ritorna `None` se assente.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_config.py
from inkscout.config import load_config, keychain_get


def test_load_config_defaults(tmp_path):
    cfg = load_config({"INK_SCOUT_DATA_DIR": str(tmp_path)})
    assert cfg.data_dir == tmp_path
    assert cfg.db_path == tmp_path / "inkscout.db"
    assert cfg.images_dir == tmp_path / "images"
    assert cfg.cache_dir == tmp_path / "cache"
    # model-id e prezzo sono config-driven, mai nel sorgente degli engine
    assert cfg.fal_model_id  # ha un default non vuoto
    assert cfg.fal_price_per_img >= 0


def test_load_config_env_overrides(tmp_path):
    cfg = load_config({
        "INK_SCOUT_DATA_DIR": str(tmp_path),
        "INK_SCOUT_FAL_MODEL_ID": "fal-ai/flux/dev",
        "INK_SCOUT_FAL_PRICE_PER_IMG": "0.025",
    })
    assert cfg.fal_model_id == "fal-ai/flux/dev"
    assert cfg.fal_price_per_img == 0.025


def test_keychain_get_missing_returns_none(monkeypatch):
    def fake_run(*a, **k):
        raise __import__("subprocess").CalledProcessError(1, "security")
    monkeypatch.setattr("inkscout.config.subprocess.run", fake_run)
    assert keychain_get("inkscout-fal-key") is None
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.config'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/config.py
"""Configurazione: path + env INK_SCOUT_* + accesso Keychain macOS.

Model-id e prezzi degli engine vivono QUI (config-driven), mai nei sorgenti
degli engine — vincolo globale dello spec.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# Default config-driven per il backend cloud (Modo A). Sovrascrivibili via env.
_DEFAULT_FAL_MODEL_ID = "fal-ai/flux/schnell"
_DEFAULT_FAL_PRICE = 0.003


@dataclass(frozen=True)
class Config:
    data_dir: Path
    db_path: Path
    images_dir: Path
    cache_dir: Path
    styles_seed: Path
    fal_model_id: str
    fal_price_per_img: float


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    data_dir = Path(env.get("INK_SCOUT_DATA_DIR", str(Path.home() / ".ink-scout"))).expanduser()
    seed_default = Path(__file__).resolve().parent.parent / "data" / "styles.seed.yaml"
    return Config(
        data_dir=data_dir,
        db_path=data_dir / "inkscout.db",
        images_dir=data_dir / "images",
        cache_dir=data_dir / "cache",
        styles_seed=Path(env.get("INK_SCOUT_STYLES_SEED", str(seed_default))),
        fal_model_id=env.get("INK_SCOUT_FAL_MODEL_ID", _DEFAULT_FAL_MODEL_ID),
        fal_price_per_img=float(env.get("INK_SCOUT_FAL_PRICE_PER_IMG", _DEFAULT_FAL_PRICE)),
    )


def keychain_get(account: str, service: str = "ink-scout") -> str | None:
    """Legge una password dal Keychain macOS. None se assente/errore."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout.strip() or None


def ensure_dirs(cfg: Config) -> None:
    for d in (cfg.data_dir, cfg.images_dir, cfg.cache_dir):
        d.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/config.py tests/test_config.py
git commit -m "feat(config): path, env INK_SCOUT_*, helper Keychain"
```

---

### Task 3: Modello dati di dominio (`inkscout/core/models.py`)

**Files:**
- Create: `inkscout/core/__init__.py`
- Create: `inkscout/core/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `class Axis(str, Enum)` = `SUBJECT, PLACEMENT, COLOR_MODE, DENSITY, FORM` (assi ortogonali; **non** valori).
  - Costanti `SOURCE_KINDS = ("upload", "site", "instagram", "pinterest", "tattoodo")`.
  - `RESULT_KINDS = ("moodboard", "prompt", "raster", "svg")`.
  - `@dataclass SourceRef(kind, ref, harvest_optin=False, notes="")`.
  - `@dataclass RawItem(source_url, artist_handle, fetched_at, license_note, image_bytes=None, local_path=None, meta=dict)`.
  - `@dataclass Brief(...)` con `to_json()`/`from_json()`.
  - `@dataclass EngineCapabilities(needs_gpu, needs_key, cost_per_img, watermarks, offline)`.
  - `@dataclass DesignResult(kind, engine, prompt="", moodboard_paths=(), raster_path=None, svg_path=None, meta=dict)`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_models.py
import json
from inkscout.core.models import (
    Axis, SOURCE_KINDS, RESULT_KINDS, SourceRef, Brief, EngineCapabilities, DesignResult,
)


def test_axis_are_axes_not_values():
    assert Axis.SUBJECT.value == "subject"
    assert set(a.value for a in Axis) == {"subject", "placement", "color_mode", "density", "form"}


def test_source_and_result_kinds():
    assert "upload" in SOURCE_KINDS and "instagram" in SOURCE_KINDS
    assert set(RESULT_KINDS) == {"moodboard", "prompt", "raster", "svg"}


def test_source_ref_defaults():
    s = SourceRef(kind="site", ref="https://example.com")
    assert s.harvest_optin is False and s.notes == ""


def test_brief_json_roundtrip():
    b = Brief(theme_text="Twin Peaks", styles=["blackwork", "geometric"], form="round",
              color_mode="black-only", placement="forearm", size="medium",
              line_treatment="bold black outlines", reference_image_ids=[3, 7])
    raw = b.to_json()
    assert json.loads(raw)["theme_text"] == "Twin Peaks"
    assert Brief.from_json(raw) == b


def test_engine_capabilities_and_result():
    caps = EngineCapabilities(needs_gpu=False, needs_key=False, cost_per_img=0.0,
                              watermarks=False, offline=True)
    assert caps.offline is True
    r = DesignResult(kind="prompt", engine="brief", prompt="blackwork geometric ...")
    assert r.kind in RESULT_KINDS and r.raster_path is None
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.core'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/core/__init__.py
```

```python
# inkscout/core/models.py
"""Modello di dominio. Gli ASSI sono fissi (enum); i VALORI (temi/stili/artisti)
sono dati, mai enum — vincolo globale dello spec."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum


class Axis(str, Enum):
    SUBJECT = "subject"
    PLACEMENT = "placement"
    COLOR_MODE = "color_mode"
    DENSITY = "density"
    FORM = "form"


SOURCE_KINDS = ("upload", "site", "instagram", "pinterest", "tattoodo")
RESULT_KINDS = ("moodboard", "prompt", "raster", "svg")


@dataclass
class SourceRef:
    kind: str
    ref: str
    harvest_optin: bool = False
    notes: str = ""


@dataclass
class RawItem:
    source_url: str
    artist_handle: str
    fetched_at: str
    license_note: str
    image_bytes: bytes | None = None
    local_path: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Brief:
    theme_text: str = ""
    styles: list[str] = field(default_factory=list)
    form: str = ""
    color_mode: str = ""
    placement: str = ""
    size: str = ""
    line_treatment: str = ""
    reference_image_ids: list[int] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "Brief":
        return cls(**json.loads(raw))


@dataclass
class EngineCapabilities:
    needs_gpu: bool
    needs_key: bool
    cost_per_img: float
    watermarks: bool
    offline: bool


@dataclass
class DesignResult:
    kind: str
    engine: str
    prompt: str = ""
    moodboard_paths: tuple[str, ...] = ()
    raster_path: str | None = None
    svg_path: str | None = None
    meta: dict = field(default_factory=dict)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/core tests/test_models.py
git commit -m "feat(core): modello di dominio (Axis, SourceRef, Brief, DesignResult)"
```

---

### Task 4: Store SQLite WAL + schema (`inkscout/store/db.py`)

**Files:**
- Create: `inkscout/store/__init__.py`
- Create: `inkscout/store/db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Consumes: `inkscout.config.Config`.
- Produces:
  - `class Store` con:
    - `Store(db_path: Path)` — apre SQLite, imposta `PRAGMA journal_mode=WAL`, crea lo schema se assente.
    - `add_source(kind, ref, harvest_optin=False, notes="") -> int`
    - `add_artist(name, handle="", city="", source_id=None, provenance_url="", do_not_mimic=False) -> int`
    - `add_image(path, phash, width, height, artist_id, source_id, source_url, license_note, fetched_at) -> int`
    - `get_image(image_id) -> dict | None`
    - `list_images(styles=None, form=None, color_mode=None, theme=None, include_hidden=False) -> list[dict]`
    - `all_phashes() -> list[tuple[int, int]]` — `(image_id, phash)` per il dedup.
    - `set_favorite(image_id, value) -> None` / `set_hidden(image_id, value) -> None`
    - `add_image_style(image_id, style_id) -> None`
    - `add_image_tag(image_id, axis, value, confidence, tagger) -> None`
    - `upsert_style(name, aliases=(), parent_style_id=None, formal_attributes=None, description="", is_emerging=False) -> int`
    - `style_id_by_name(name) -> int | None`
    - `add_design(title, brief_json) -> int` / `add_design_version(design_id, parent_version_id, brief_json, engine, result_kind, asset_path) -> int`

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_db.py
from inkscout.store.db import Store


def _store(tmp_path):
    return Store(tmp_path / "t.db")


def test_wal_enabled(tmp_path):
    s = _store(tmp_path)
    mode = s.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_add_and_get_image_with_provenance(tmp_path):
    s = _store(tmp_path)
    src = s.add_source("site", "https://artist.example")
    art = s.add_artist("Jane", handle="@jane", source_id=src)
    img = s.add_image(path="images/a.jpg", phash=123, width=800, height=600,
                      artist_id=art, source_id=src, source_url="https://artist.example/a",
                      license_note="personal-reference", fetched_at="2026-07-23T10:00:00")
    row = s.get_image(img)
    assert row["source_url"] == "https://artist.example/a"
    assert row["license_note"] == "personal-reference"
    assert row["favorite"] == 0 and row["hidden"] == 0


def test_favorite_hidden_and_listing(tmp_path):
    s = _store(tmp_path)
    src = s.add_source("upload", "local")
    a = s.add_image("images/a.jpg", 1, 10, 10, None, src, "u://a", "n", "t")
    b = s.add_image("images/b.jpg", 2, 10, 10, None, src, "u://b", "n", "t")
    s.set_favorite(a, True)
    s.set_hidden(b, True)
    visible = s.list_images()
    ids = {r["id"] for r in visible}
    assert a in ids and b not in ids  # hidden escluso di default
    assert any(r["favorite"] == 1 for r in visible)


def test_style_upsert_is_idempotent(tmp_path):
    s = _store(tmp_path)
    id1 = s.upsert_style("blackwork", description="tratto pieno")
    id2 = s.upsert_style("blackwork", description="aggiornata")
    assert id1 == id2
    assert s.style_id_by_name("blackwork") == id1


def test_all_phashes_for_dedup(tmp_path):
    s = _store(tmp_path)
    src = s.add_source("upload", "local")
    s.add_image("images/a.jpg", 111, 10, 10, None, src, "u://a", "n", "t")
    s.add_image("images/b.jpg", 222, 10, 10, None, src, "u://b", "n", "t")
    pairs = dict(s.all_phashes())
    assert set(pairs.values()) == {111, 222}
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.store'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/store/__init__.py
```

```python
# inkscout/store/db.py
"""Persistenza SQLite (WAL). Schema data-driven: gli assi sono colonne/tabelle,
i valori (stili/temi/artisti) sono righe, mai enum nel codice."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS source (
    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, ref TEXT NOT NULL,
    added_at TEXT DEFAULT (datetime('now')), harvest_optin INTEGER DEFAULT 0, notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS artist (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, handle TEXT DEFAULT '', city TEXT DEFAULT '',
    source_id INTEGER, provenance_url TEXT DEFAULT '', do_not_mimic INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS image (
    id INTEGER PRIMARY KEY, path TEXT NOT NULL, phash INTEGER,
    width INTEGER, height INTEGER, artist_id INTEGER, source_id INTEGER,
    source_url TEXT DEFAULT '', license_note TEXT DEFAULT '', fetched_at TEXT DEFAULT '',
    favorite INTEGER DEFAULT 0, hidden INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS style (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, aliases TEXT DEFAULT '[]',
    parent_style_id INTEGER, formal_attributes TEXT DEFAULT '{}',
    description TEXT DEFAULT '', is_emerging INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS image_style (
    image_id INTEGER, style_id INTEGER, PRIMARY KEY (image_id, style_id)
);
CREATE TABLE IF NOT EXISTS image_tag (
    image_id INTEGER, axis TEXT, value TEXT, confidence REAL, tagger TEXT
);
CREATE TABLE IF NOT EXISTS embedding (image_id INTEGER, kind TEXT, vector BLOB);
CREATE TABLE IF NOT EXISTS design (
    id INTEGER PRIMARY KEY, title TEXT, brief TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS design_version (
    id INTEGER PRIMARY KEY, design_id INTEGER, parent_version_id INTEGER,
    brief TEXT, engine TEXT, result_kind TEXT, asset_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_image_tag ON image_tag(image_id, axis);
"""


class Store:
    def __init__(self, db_path: Path | str):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- source / artist ---
    def add_source(self, kind, ref, harvest_optin=False, notes="") -> int:
        cur = self.conn.execute(
            "INSERT INTO source(kind, ref, harvest_optin, notes) VALUES (?,?,?,?)",
            (kind, ref, int(harvest_optin), notes))
        self.conn.commit()
        return cur.lastrowid

    def add_artist(self, name, handle="", city="", source_id=None,
                   provenance_url="", do_not_mimic=False) -> int:
        cur = self.conn.execute(
            "INSERT INTO artist(name, handle, city, source_id, provenance_url, do_not_mimic) "
            "VALUES (?,?,?,?,?,?)",
            (name, handle, city, source_id, provenance_url, int(do_not_mimic)))
        self.conn.commit()
        return cur.lastrowid

    # --- image ---
    def add_image(self, path, phash, width, height, artist_id, source_id,
                  source_url, license_note, fetched_at) -> int:
        cur = self.conn.execute(
            "INSERT INTO image(path, phash, width, height, artist_id, source_id, "
            "source_url, license_note, fetched_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (path, phash, width, height, artist_id, source_id, source_url, license_note, fetched_at))
        self.conn.commit()
        return cur.lastrowid

    def get_image(self, image_id) -> dict | None:
        row = self.conn.execute("SELECT * FROM image WHERE id=?", (image_id,)).fetchone()
        return dict(row) if row else None

    def all_phashes(self) -> list[tuple[int, int]]:
        return [(r["id"], r["phash"]) for r in
                self.conn.execute("SELECT id, phash FROM image WHERE phash IS NOT NULL")]

    def set_favorite(self, image_id, value) -> None:
        self.conn.execute("UPDATE image SET favorite=? WHERE id=?", (int(value), image_id))
        self.conn.commit()

    def set_hidden(self, image_id, value) -> None:
        self.conn.execute("UPDATE image SET hidden=? WHERE id=?", (int(value), image_id))
        self.conn.commit()

    def list_images(self, styles=None, form=None, color_mode=None, theme=None,
                    include_hidden=False) -> list[dict]:
        sql = ["SELECT DISTINCT i.* FROM image i"]
        params: list = []
        joins, where = [], []
        if not include_hidden:
            where.append("i.hidden=0")
        if styles:
            joins.append("JOIN image_style s ON s.image_id=i.id")
            joins.append("JOIN style st ON st.id=s.style_id")
            where.append("st.name IN (%s)" % ",".join("?" * len(styles)))
            params.extend(styles)
        for axis, val in (("form", form), ("color_mode", color_mode)):
            if val:
                where.append(f"EXISTS (SELECT 1 FROM image_tag t WHERE t.image_id=i.id "
                             f"AND t.axis='{axis}' AND t.value=?)")
                params.append(val)
        if theme:
            where.append("EXISTS (SELECT 1 FROM image_tag t WHERE t.image_id=i.id "
                         "AND t.axis='subject' AND t.value LIKE ?)")
            params.append(f"%{theme}%")
        sql.extend(joins)
        if where:
            sql.append("WHERE " + " AND ".join(where))
        sql.append("ORDER BY i.favorite DESC, i.id DESC")
        return [dict(r) for r in self.conn.execute(" ".join(sql), params)]

    # --- style / tags ---
    def upsert_style(self, name, aliases=(), parent_style_id=None,
                     formal_attributes=None, description="", is_emerging=False) -> int:
        existing = self.style_id_by_name(name)
        if existing is not None:
            return existing
        cur = self.conn.execute(
            "INSERT INTO style(name, aliases, parent_style_id, formal_attributes, "
            "description, is_emerging) VALUES (?,?,?,?,?,?)",
            (name, json.dumps(list(aliases)), parent_style_id,
             json.dumps(formal_attributes or {}), description, int(is_emerging)))
        self.conn.commit()
        return cur.lastrowid

    def style_id_by_name(self, name) -> int | None:
        row = self.conn.execute("SELECT id FROM style WHERE name=?", (name,)).fetchone()
        return row["id"] if row else None

    def add_image_style(self, image_id, style_id) -> None:
        self.conn.execute("INSERT OR IGNORE INTO image_style(image_id, style_id) VALUES (?,?)",
                          (image_id, style_id))
        self.conn.commit()

    def add_image_tag(self, image_id, axis, value, confidence, tagger) -> None:
        self.conn.execute(
            "INSERT INTO image_tag(image_id, axis, value, confidence, tagger) VALUES (?,?,?,?,?)",
            (image_id, axis, value, confidence, tagger))
        self.conn.commit()

    def image_tags(self, image_id) -> list[dict]:
        return [dict(r) for r in
                self.conn.execute("SELECT axis, value, confidence, tagger FROM image_tag "
                                  "WHERE image_id=?", (image_id,))]

    # --- design ---
    def add_design(self, title, brief_json) -> int:
        cur = self.conn.execute("INSERT INTO design(title, brief) VALUES (?,?)", (title, brief_json))
        self.conn.commit()
        return cur.lastrowid

    def add_design_version(self, design_id, parent_version_id, brief_json, engine,
                           result_kind, asset_path) -> int:
        cur = self.conn.execute(
            "INSERT INTO design_version(design_id, parent_version_id, brief, engine, "
            "result_kind, asset_path) VALUES (?,?,?,?,?,?)",
            (design_id, parent_version_id, brief_json, engine, result_kind, asset_path))
        self.conn.commit()
        return cur.lastrowid

    def close(self) -> None:
        self.conn.close()
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/store tests/test_db.py
git commit -m "feat(store): SQLite WAL + schema data-driven + CRUD"
```

---

## Fase 1 — Libreria + dedup percettivo

### Task 5: Hash percettivo (`inkscout/library/phash.py`)

**Files:**
- Create: `inkscout/library/__init__.py`
- Create: `inkscout/library/phash.py`
- Create: `tests/test_phash.py`

**Interfaces:**
- Consumes: Pillow (`PIL.Image`).
- Produces:
  - `def dhash(image: "PIL.Image.Image", hash_size: int = 8) -> int` — hash percettivo a 64 bit.
  - `def hamming(a: int, b: int) -> int` — distanza di Hamming.
  - `def is_near_dup(a: int, b: int, threshold: int = 5) -> bool`.
  - `def phash_of_path(path: str | "Path") -> int`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_phash.py
from io import BytesIO
from PIL import Image
from inkscout.library.phash import dhash, hamming, is_near_dup


def _img(color, size=(64, 64)):
    return Image.new("RGB", size, color)


def test_identical_images_same_hash():
    a = dhash(_img((10, 20, 30)))
    b = dhash(_img((10, 20, 30)))
    assert a == b and hamming(a, b) == 0


def test_gradient_vs_flat_differ():
    flat = dhash(_img((0, 0, 0)))
    grad = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            grad.putpixel((x, y), x * 4 % 256)
    assert hamming(flat, dhash(grad)) > 5


def test_near_dup_threshold():
    assert is_near_dup(0b1010, 0b1011, threshold=5) is True
    assert is_near_dup(0, (1 << 40) - 1, threshold=5) is False
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_phash.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.library'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/library/__init__.py
```

```python
# inkscout/library/phash.py
"""Hash percettivo (dHash) per collassare duplicati e near-duplicati."""
from __future__ import annotations

from pathlib import Path


def dhash(image, hash_size: int = 8) -> int:
    from PIL import Image
    img = image.convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
    bits = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = img.getpixel((col, row))
            right = img.getpixel((col + 1, row))
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def is_near_dup(a: int, b: int, threshold: int = 5) -> bool:
    return hamming(a, b) <= threshold


def phash_of_path(path: str | Path) -> int:
    from PIL import Image
    with Image.open(path) as img:
        return dhash(img)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_phash.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/library/__init__.py inkscout/library/phash.py tests/test_phash.py
git commit -m "feat(library): hash percettivo dHash + distanza di Hamming"
```

---

### Task 6: Libreria con dedup e provenance (`inkscout/library/library.py`)

**Files:**
- Create: `inkscout/library/library.py`
- Create: `tests/test_library.py`

**Interfaces:**
- Consumes: `Store` (Task 4), `dhash`/`is_near_dup` (Task 5), `RawItem` (Task 3).
- Produces:
  - `@dataclass AddResult(image_id: int, is_duplicate: bool, duplicate_of: int | None)`.
  - `class Library(store: Store, images_dir: Path)`:
    - `add(raw: RawItem, artist_id: int | None = None, source_id: int | None = None, near_dup_threshold: int = 5) -> AddResult` — decodifica l'immagine, calcola pHash, se near-dup di una esistente NON reinserisce, altrimenti salva il file e inserisce la riga con provenance. **Solleva `ValueError` se manca provenance** (`source_url` o `license_note` vuoti).
    - `favorite(image_id, value=True)` / `hide(image_id, value=True)` — passthrough allo store.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_library.py
from io import BytesIO
from pathlib import Path
import pytest
from PIL import Image
from inkscout.store.db import Store
from inkscout.library.library import Library
from inkscout.core.models import RawItem


def _png_bytes(color):
    buf = BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


def _lib(tmp_path):
    store = Store(tmp_path / "t.db")
    return Library(store, tmp_path / "images"), store


def _raw(color, url="https://ex/a"):
    return RawItem(source_url=url, artist_handle="@x", fetched_at="2026-07-23T00:00:00",
                   license_note="personal-reference", image_bytes=_png_bytes(color))


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
    buf = BytesIO(); grad.save(buf, format="PNG")
    lib.add(RawItem(source_url="https://ex/g", artist_handle="@x",
                    fetched_at="t", license_note="ref", image_bytes=buf.getvalue()))
    assert len(store.all_phashes()) == 2


def test_missing_provenance_raises(tmp_path):
    lib, _ = _lib(tmp_path)
    with pytest.raises(ValueError):
        lib.add(RawItem(source_url="", artist_handle="@x", fetched_at="t",
                        license_note="ref", image_bytes=_png_bytes((1, 2, 3))))
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_library.py -v`
Expected: FAIL — `ImportError: cannot import name 'Library'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/library/library.py
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

    def add(self, raw: RawItem, artist_id: int | None = None, source_id: int | None = None,
            near_dup_threshold: int = 5) -> AddResult:
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
        dest = self.images_dir / f"{ph & 0xFFFFFFFFFFFFFFFF:016x}.{ext}"
        dest.write_bytes(data)
        image_id = self.store.add_image(
            path=str(dest), phash=ph, width=img.width, height=img.height,
            artist_id=artist_id, source_id=source_id, source_url=raw.source_url,
            license_note=raw.license_note, fetched_at=raw.fetched_at)
        return AddResult(image_id, False, None)

    def favorite(self, image_id: int, value: bool = True) -> None:
        self.store.set_favorite(image_id, value)

    def hide(self, image_id: int, value: bool = True) -> None:
        self.store.set_hidden(image_id, value)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_library.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/library/library.py tests/test_library.py
git commit -m "feat(library): add con dedup pHash + provenance obbligatoria"
```

---

## Fase 2 — Ingest / scraper

### Task 7: SourceAdapter, registry e fetch con cache (`inkscout/ingest/base.py`)

**Files:**
- Create: `inkscout/ingest/__init__.py`
- Create: `inkscout/ingest/base.py`
- Create: `tests/test_ingest_base.py`

**Interfaces:**
- Consumes: `SourceRef`, `RawItem` (Task 3).
- Produces:
  - `class SourceAdapter(Protocol)` con `kind: str` e `fetch(source: SourceRef) -> Iterable[RawItem]`.
  - `def register(kind: str)` — decoratore che registra una classe adapter.
  - `def get_adapter(kind: str) -> SourceAdapter` — dal registry (`KeyError` se ignoto).
  - `def fetch_text(url: str, cache_dir: Path, *, force: bool = False) -> str` — HTTP-first (`curl_cffi` lazy), cache su disco per URL (hash del path).
  - `def fetch_bytes(url: str, cache_dir: Path, *, force: bool = False) -> bytes`.
  - `def now_iso() -> str`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_ingest_base.py
import pytest
from inkscout.ingest import base
from inkscout.core.models import SourceRef, RawItem


def test_register_and_get_adapter():
    @base.register("dummy")
    class Dummy:
        kind = "dummy"
        def fetch(self, source):
            return [RawItem(source_url=source.ref, artist_handle="", fetched_at="t",
                            license_note="test")]
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
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_ingest_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.ingest'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/ingest/__init__.py
```

```python
# inkscout/ingest/base.py
"""Contratto adapter + registry + fetch HTTP-first con cache su disco.

`_http_get` è l'unico punto che tocca la rete: i test lo monkeypatchano."""
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
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_ingest_base.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/ingest/__init__.py inkscout/ingest/base.py tests/test_ingest_base.py
git commit -m "feat(ingest): SourceAdapter protocol, registry, fetch HTTP-first con cache"
```

---

### Task 8: UploadAdapter (`inkscout/ingest/upload.py`)

**Files:**
- Create: `inkscout/ingest/upload.py`
- Create: `tests/test_ingest_upload.py`

**Interfaces:**
- Consumes: `base.register`, `RawItem`, `SourceRef`.
- Produces:
  - `class UploadAdapter` (kind `"upload"`): `fetch(source)` dove `source.ref` è un file o una directory locale; emette un `RawItem` per ogni immagine (`.jpg/.jpeg/.png/.webp`) con `local_path`, `license_note="user-upload"`, `source_url="file://<path>"`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_ingest_upload.py
from PIL import Image
from inkscout.ingest.upload import UploadAdapter
from inkscout.core.models import SourceRef


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


from pathlib import Path  # noqa: E402
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_ingest_upload.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.ingest.upload'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/ingest/upload.py
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
            if p.suffix.lower() in _EXT and p.is_file():
                yield RawItem(
                    source_url=f"file://{p.resolve()}", artist_handle="",
                    fetched_at=now_iso(), license_note="user-upload", local_path=str(p))
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_ingest_upload.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/ingest/upload.py tests/test_ingest_upload.py
git commit -m "feat(ingest): UploadAdapter per file/directory locali"
```

---

### Task 9: PersonalSiteAdapter (`inkscout/ingest/site.py`)

**Files:**
- Create: `inkscout/ingest/site.py`
- Create: `tests/test_ingest_site.py`

**Interfaces:**
- Consumes: `base.fetch_text`/`fetch_bytes`, `RawItem`, `SourceRef`.
- Produces:
  - `def extract_image_urls(html: str, base_url: str) -> list[str]` — **funzione pura**: estrae da `<meta property="og:image">`, `<img src>`/`srcset`, e JSON-LD `image`; risolve in URL assoluti, deduplica preservando l'ordine.
  - `class PersonalSiteAdapter` (kind `"site"`): `fetch(source)` scarica la pagina, estrae gli URL immagine, scarica i byte e li emette come `RawItem` con `license_note="personal-site"`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_ingest_site.py
from inkscout.ingest.site import extract_image_urls, PersonalSiteAdapter
from inkscout.ingest import base
from inkscout.core.models import SourceRef

HTML = """
<html><head>
<meta property="og:image" content="/img/hero.jpg">
<script type="application/ld+json">{"@type":"ImageObject","image":"https://cdn.ex/j.png"}</script>
</head><body>
<img src="a.jpg" srcset="a-2x.jpg 2x, a-3x.jpg 3x">
<img src="/img/hero.jpg">
</body></html>
"""


def test_extract_dedup_and_absolute():
    urls = extract_image_urls(HTML, "https://site.ex/gallery/")
    assert "https://site.ex/img/hero.jpg" in urls
    assert "https://site.ex/gallery/a.jpg" in urls
    assert "https://cdn.ex/j.png" in urls
    assert urls.count("https://site.ex/img/hero.jpg") == 1  # deduplicato


def test_fetch_emits_rawitems(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "_http_get", lambda url: HTML.encode()
                        if url.endswith("gallery/") else b"IMGBYTES")
    items = list(PersonalSiteAdapter(cache_dir=tmp_path).fetch(
        SourceRef(kind="site", ref="https://site.ex/gallery/")))
    assert len(items) >= 3
    assert all(i.image_bytes == b"IMGBYTES" for i in items)
    assert all(i.license_note == "personal-site" for i in items)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_ingest_site.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.ingest.site'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/ingest/site.py
"""Adapter per siti personali: og:image, <img src/srcset>, JSON-LD. Via primaria e lecita."""
from __future__ import annotations

import json
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
            yield RawItem(source_url=img_url, artist_handle="", fetched_at=now_iso(),
                          license_note="personal-site", image_bytes=data)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_ingest_site.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/ingest/site.py tests/test_ingest_site.py
git commit -m "feat(ingest): PersonalSiteAdapter (og:image/srcset/JSON-LD, URL assoluti)"
```

---

### Task 10: InstagramAdapter — harvest opt-in (`inkscout/ingest/instagram.py`)

**Files:**
- Create: `inkscout/ingest/instagram.py`
- Create: `tests/test_ingest_instagram.py`

**Interfaces:**
- Consumes: `base.fetch_text`, `RawItem`, `SourceRef`.
- Produces:
  - `IG_TOS_BANNER: str` — avviso "uso personale, viola i ToS, fragile".
  - `class HarvestNotOptedIn(Exception)`.
  - `def extract_media(payload: dict) -> list[dict]` — **pura**: da un JSON profilo estrae `[{display_url, shortcode}]` (i `doc_id`/percorsi NON sono hardcodati nel codice ma passati/config).
  - `class InstagramAdapter` (kind `"instagram"`): `fetch(source)` **solleva `HarvestNotOptedIn`** se `source.harvest_optin` è False; con opt-in scarica (throttle configurabile, default lungo) ed emette `RawItem` con `artist_handle` = handle, `license_note="ig-harvest-personal"`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_ingest_instagram.py
import pytest
from inkscout.ingest import instagram as ig
from inkscout.ingest import base
from inkscout.core.models import SourceRef


def test_requires_optin():
    with pytest.raises(ig.HarvestNotOptedIn):
        list(ig.InstagramAdapter().fetch(SourceRef(kind="instagram", ref="@jane")))


def test_extract_media_is_pure():
    payload = {"data": {"user": {"media": {"edges": [
        {"node": {"display_url": "https://cdn/1.jpg", "shortcode": "AAA"}},
        {"node": {"display_url": "https://cdn/2.jpg", "shortcode": "BBB"}},
    ]}}}}
    media = ig.extract_media(payload)
    assert [m["shortcode"] for m in media] == ["AAA", "BBB"]


def test_optin_fetch_emits_rawitems(monkeypatch, tmp_path):
    import json
    payload = {"data": {"user": {"media": {"edges": [
        {"node": {"display_url": "https://cdn/1.jpg", "shortcode": "AAA"}}]}}}}
    monkeypatch.setattr(base, "_http_get", lambda url: json.dumps(payload).encode())
    adapter = ig.InstagramAdapter(cache_dir=tmp_path, throttle_s=0)
    items = list(adapter.fetch(SourceRef(kind="instagram", ref="@jane", harvest_optin=True)))
    assert items[0].artist_handle == "@jane"
    assert items[0].license_note == "ig-harvest-personal"
    assert items[0].source_url == "https://cdn/1.jpg"
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_ingest_instagram.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.ingest.instagram'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/ingest/instagram.py
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
    "(endpoint/doc_id cambiano), soggetto a rate-limit. Mai ridistribuzione.")


class HarvestNotOptedIn(Exception):
    pass


def extract_media(payload: dict) -> list[dict]:
    edges = (payload.get("data", {}).get("user", {}).get("media", {}).get("edges", []))
    out = []
    for e in edges:
        node = e.get("node", {})
        if node.get("display_url"):
            out.append({"display_url": node["display_url"], "shortcode": node.get("shortcode", "")})
    return out


@register("instagram")
class InstagramAdapter:
    kind = "instagram"

    def __init__(self, cache_dir: Path | str = ".cache", throttle_s: float = 12 * 60,
                 profile_url_tmpl: str = "https://www.instagram.com/{handle}/?__a=1"):
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
            yield RawItem(source_url=m["display_url"], artist_handle=source.ref,
                          fetched_at=now_iso(), license_note="ig-harvest-personal",
                          meta={"shortcode": m["shortcode"]})
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_ingest_instagram.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/ingest/instagram.py tests/test_ingest_instagram.py
git commit -m "feat(ingest): InstagramAdapter harvest opt-in (banner ToS, throttle)"
```

---

## Fase 3 — Tagging / stile

### Task 11: Vocabolario stili seed (`data/styles.seed.yaml` + `inkscout/tagging/vocab.py`)

**Files:**
- Create: `data/styles.seed.yaml`
- Create: `inkscout/tagging/__init__.py`
- Create: `inkscout/tagging/vocab.py`
- Create: `tests/test_vocab.py`

**Interfaces:**
- Consumes: `Store` (Task 4).
- Produces:
  - `@dataclass StyleSeed(name, aliases, parent, formal_attributes, description, is_emerging)`.
  - `def load_styles(path: str | Path) -> list[StyleSeed]` — parsa lo YAML.
  - `def sync_styles(store: Store, path: str | Path) -> int` — upsert nel DB, ritorna il numero di stili presenti. **Idempotente.**
  - `def style_names(path) -> list[str]` — comodità per il tagger.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_vocab.py
from inkscout.tagging.vocab import load_styles, sync_styles, style_names
from inkscout.store.db import Store

SEED = """
styles:
  - name: blackwork
    description: campiture nere piene, forte spazio negativo
    formal_attributes: {palette: black-only, linework: bold, density: high}
  - name: fine-line
    aliases: [fineline, single-needle]
    description: linee sottili a spessore costante
    formal_attributes: {palette: black-only, linework: thin}
"""


def test_load_styles(tmp_path):
    p = tmp_path / "s.yaml"; p.write_text(SEED)
    styles = load_styles(p)
    assert {s.name for s in styles} == {"blackwork", "fine-line"}
    fl = next(s for s in styles if s.name == "fine-line")
    assert "fineline" in fl.aliases
    assert fl.formal_attributes["linework"] == "thin"


def test_sync_is_idempotent(tmp_path):
    p = tmp_path / "s.yaml"; p.write_text(SEED)
    store = Store(tmp_path / "t.db")
    n1 = sync_styles(store, p)
    n2 = sync_styles(store, p)
    assert n1 == n2 == 2
    assert store.style_id_by_name("blackwork") is not None


def test_style_names(tmp_path):
    p = tmp_path / "s.yaml"; p.write_text(SEED)
    assert set(style_names(p)) == {"blackwork", "fine-line"}
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_vocab.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.tagging'`.

- [ ] **Step 3: Implementazione minima**

```yaml
# data/styles.seed.yaml
# Vocabolario stili INIZIALE (dati, non codice). Estendibile senza toccare il sorgente.
styles:
  - name: blackwork
    description: campiture nere piene, forte spazio negativo
    formal_attributes: {palette: black-only, linework: bold, density: high}
  - name: fine-line
    aliases: [fineline, single-needle]
    description: linee sottili a spessore costante, minimale
    formal_attributes: {palette: black-only, linework: thin, density: low}
  - name: geometric
    description: forme geometriche, simmetria, pattern
    formal_attributes: {linework: bold, density: medium}
  - name: dotwork
    description: ombreggiatura a puntinato (stippling)
    formal_attributes: {palette: black-only, technique: stippling}
  - name: traditional
    aliases: [old-school]
    description: contorni spessi, colori piatti saturi
    formal_attributes: {linework: bold, palette: saturated}
  - name: neo-traditional
    description: evoluzione del traditional, più dettaglio e palette ampia
    formal_attributes: {linework: bold, palette: wide}
  - name: realism
    description: resa realistica, gradienti morbidi
    formal_attributes: {linework: soft, palette: grayscale-or-color}
  - name: minimalist
    description: pochi elementi, molto bianco, essenziale
    formal_attributes: {density: low}
  - name: ornamental
    aliases: [mandala]
    description: motivi decorativi, mandala, gioielleria
    formal_attributes: {density: high, linework: fine}
  - name: cybersigilism
    is_emerging: true
    description: tratti affilati tribali-digitali, spuntoni sottili
    formal_attributes: {linework: thin-spiky, palette: black-only}
```

```python
# inkscout/tagging/__init__.py
```

```python
# inkscout/tagging/vocab.py
"""Carica il vocabolario stili da YAML e lo sincronizza nel DB. I valori sono DATI."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from inkscout.store.db import Store


@dataclass
class StyleSeed:
    name: str
    aliases: list[str] = field(default_factory=list)
    parent: str | None = None
    formal_attributes: dict = field(default_factory=dict)
    description: str = ""
    is_emerging: bool = False


def load_styles(path: str | Path) -> list[StyleSeed]:
    doc = yaml.safe_load(Path(path).read_text()) or {}
    out = []
    for item in doc.get("styles", []):
        out.append(StyleSeed(
            name=item["name"], aliases=item.get("aliases", []),
            parent=item.get("parent"), formal_attributes=item.get("formal_attributes", {}),
            description=item.get("description", ""), is_emerging=item.get("is_emerging", False)))
    return out


def sync_styles(store: Store, path: str | Path) -> int:
    styles = load_styles(path)
    for s in styles:
        parent_id = store.style_id_by_name(s.parent) if s.parent else None
        store.upsert_style(s.name, aliases=s.aliases, parent_style_id=parent_id,
                           formal_attributes=s.formal_attributes, description=s.description,
                           is_emerging=s.is_emerging)
    return len(styles)


def style_names(path: str | Path) -> list[str]:
    return [s.name for s in load_styles(path)]
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_vocab.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add data/styles.seed.yaml inkscout/tagging/__init__.py inkscout/tagging/vocab.py tests/test_vocab.py
git commit -m "feat(tagging): vocabolario stili seed YAML + sync idempotente nel DB"
```

---

### Task 12: Tagger protocol + ClipTagger (`inkscout/tagging/base.py`, `clip.py`)

**Files:**
- Create: `inkscout/tagging/base.py`
- Create: `inkscout/tagging/clip.py`
- Create: `tests/test_clip_tagger.py`

**Interfaces:**
- Consumes: vocabolario (Task 11).
- Produces:
  - `@dataclass Tag(axis: str, value: str, confidence: float)`.
  - `class Tagger(Protocol)`: `tag_image(self, image) -> list[Tag]`.
  - `class ClipTagger(vocab: list[str], encoder: Callable | None = None, threshold: float = 0.2)` — `encoder(image, labels) -> dict[str, float]`. Se `encoder` è None, carica CLIP (lazy, extra `[tag]`). `tag_image` emette `Tag(axis="style", value, confidence)` per le label sopra soglia.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_clip_tagger.py
from inkscout.tagging.base import Tag
from inkscout.tagging.clip import ClipTagger


def fake_encoder(image, labels):
    # punteggi deterministici: 'blackwork' vince, 'realism' sotto soglia
    base = {lbl: 0.05 for lbl in labels}
    base["blackwork"] = 0.7
    base["geometric"] = 0.4
    return base


def test_cliptagger_maps_above_threshold():
    tagger = ClipTagger(vocab=["blackwork", "geometric", "realism"],
                        encoder=fake_encoder, threshold=0.2)
    tags = tagger.tag_image(image=object())
    values = {t.value for t in tags}
    assert values == {"blackwork", "geometric"}
    assert all(t.axis == "style" for t in tags)
    assert any(isinstance(t, Tag) and t.confidence == 0.7 for t in tags)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_clip_tagger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.tagging.base'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/tagging/base.py
"""Contratto di tagging. Gli assi sono fissi; i valori vengono dai dati."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Tag:
    axis: str
    value: str
    confidence: float


@runtime_checkable
class Tagger(Protocol):
    def tag_image(self, image) -> list["Tag"]: ...
```

```python
# inkscout/tagging/clip.py
"""ClipTagger: CLIP zero-shot sul vocabolario stili. Offline, gratis, batch.
Il modello vero è import LAZY (extra [tag]); l'encoder è iniettabile per i test."""
from __future__ import annotations

from typing import Callable

from inkscout.tagging.base import Tag


class ClipTagger:
    def __init__(self, vocab: list[str], encoder: Callable | None = None, threshold: float = 0.2):
        self.vocab = list(vocab)
        self.threshold = threshold
        self._encoder = encoder

    def _encode(self, image, labels):
        if self._encoder is not None:
            return self._encoder(image, labels)
        return _clip_encode(image, labels)  # lazy, extra [tag]

    def tag_image(self, image) -> list[Tag]:
        scores = self._encode(image, self.vocab)
        return [Tag(axis="style", value=lbl, confidence=float(sc))
                for lbl, sc in scores.items() if sc >= self.threshold]


def _clip_encode(image, labels):  # pragma: no cover — richiede extra [tag]
    import open_clip
    import torch
    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    with torch.no_grad():
        img_t = preprocess(image).unsqueeze(0)
        text_t = tokenizer([f"a {lbl} tattoo" for lbl in labels])
        img_f = model.encode_image(img_t)
        txt_f = model.encode_text(text_t)
        img_f /= img_f.norm(dim=-1, keepdim=True)
        txt_f /= txt_f.norm(dim=-1, keepdim=True)
        probs = (img_f @ txt_f.T).softmax(dim=-1).squeeze(0).tolist()
    return dict(zip(labels, probs))
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_clip_tagger.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/tagging/base.py inkscout/tagging/clip.py tests/test_clip_tagger.py
git commit -m "feat(tagging): Tagger protocol + ClipTagger (encoder iniettabile, CLIP lazy)"
```

---

### Task 13: VisionLLMTagger opzionale (`inkscout/tagging/vision.py`)

**Files:**
- Create: `inkscout/tagging/vision.py`
- Create: `tests/test_vision_tagger.py`

**Interfaces:**
- Consumes: `Tag` (Task 12).
- Produces:
  - `class VisionLLMTagger(describe: Callable[[bytes], dict] | None = None)` — `describe(image_bytes) -> {"subject": [...], "form": "...", "color_mode": "...", "density": "..."}`. Se None, costruisce un client Claude (lazy). `tag_image(image_bytes) -> list[Tag]` normalizza sugli assi (subject/form/color_mode/density).

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_vision_tagger.py
from inkscout.tagging.vision import VisionLLMTagger


def fake_describe(image_bytes):
    return {"subject": ["owl", "forest"], "form": "round", "color_mode": "black-only",
            "density": "high"}


def test_vision_tagger_normalizes_axes():
    tagger = VisionLLMTagger(describe=fake_describe)
    tags = tagger.tag_image(b"IMG")
    axes = {(t.axis, t.value) for t in tags}
    assert ("subject", "owl") in axes and ("subject", "forest") in axes
    assert ("form", "round") in axes
    assert ("color_mode", "black-only") in axes
    assert ("density", "high") in axes
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_vision_tagger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.tagging.vision'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/tagging/vision.py
"""VisionLLMTagger: Vision LLM (Claude) per descrizioni sfumate / temi liberi.
`describe` è iniettabile per i test; il client reale è lazy."""
from __future__ import annotations

from typing import Callable

from inkscout.tagging.base import Tag

_MULTI_AXES = {"subject"}  # assi con valori multipli


class VisionLLMTagger:
    def __init__(self, describe: Callable[[bytes], dict] | None = None):
        self._describe = describe

    def _run(self, image_bytes: bytes) -> dict:
        if self._describe is not None:
            return self._describe(image_bytes)
        return _claude_describe(image_bytes)  # lazy

    def tag_image(self, image_bytes: bytes) -> list[Tag]:
        desc = self._run(image_bytes)
        tags: list[Tag] = []
        for axis, val in desc.items():
            values = val if isinstance(val, list) else [val]
            for v in values:
                if v:
                    tags.append(Tag(axis=axis, value=str(v), confidence=1.0))
        return tags


def _claude_describe(image_bytes: bytes) -> dict:  # pragma: no cover — richiede API key
    import base64
    import json
    import anthropic
    client = anthropic.Anthropic()
    b64 = base64.standard_b64encode(image_bytes).decode()
    msg = client.messages.create(
        model="claude-sonnet-5", max_tokens=400,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "content": "Descrivi questo tatuaggio come JSON con chiavi "
             "subject (lista), form, color_mode, density. Solo JSON."}]}])
    return json.loads(msg.content[0].text)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_vision_tagger.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/tagging/vision.py tests/test_vision_tagger.py
git commit -m "feat(tagging): VisionLLMTagger opzionale (describe iniettabile, Claude lazy)"
```

---

## Fase 4 — Ideazione + motore di generazione

### Task 14: Brief builder + espansione tema (`inkscout/ideation/brief.py`)

**Files:**
- Create: `inkscout/ideation/__init__.py`
- Create: `inkscout/ideation/brief.py`
- Create: `tests/test_brief.py`

**Interfaces:**
- Consumes: `Brief` (Task 3), `Store.list_images` (Task 4).
- Produces:
  - `def line_treatment_for(styles: list[str]) -> str` — regola: `fine-line`/`minimalist` → `"single-weight fine lines"`; `blackwork`/`traditional`/`geometric` → `"bold black outlines"`; altrimenti `"clean linework"`.
  - `def expand_theme(theme_text: str, store: Store, limit: int = 12) -> list[int]` — cerca immagini con `subject LIKE theme`, ritorna gli id.
  - `def build_brief(*, theme_text="", styles=None, form="", color_mode="", placement="", size="", reference_image_ids=None, store=None) -> Brief` — se `reference_image_ids` è vuoto e c'è un tema e uno store, li popola con `expand_theme`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_brief.py
from inkscout.ideation.brief import build_brief, line_treatment_for, expand_theme
from inkscout.store.db import Store


def test_line_treatment_rules():
    assert line_treatment_for(["fine-line"]) == "single-weight fine lines"
    assert line_treatment_for(["blackwork", "geometric"]) == "bold black outlines"
    assert line_treatment_for(["watercolor"]) == "clean linework"


def test_expand_theme_finds_by_subject(tmp_path):
    store = Store(tmp_path / "t.db")
    src = store.add_source("upload", "local")
    img = store.add_image("images/owl.jpg", 1, 10, 10, None, src, "u://owl", "ref", "t")
    store.add_image_tag(img, "subject", "owl in a dark forest", 1.0, "vision")
    assert expand_theme("owl", store) == [img]
    assert expand_theme("dragon", store) == []


def test_build_brief_autopopulates_references(tmp_path):
    store = Store(tmp_path / "t.db")
    src = store.add_source("upload", "local")
    img = store.add_image("images/owl.jpg", 1, 10, 10, None, src, "u://owl", "ref", "t")
    store.add_image_tag(img, "subject", "owl", 1.0, "vision")
    b = build_brief(theme_text="owl", styles=["blackwork"], form="round", store=store)
    assert b.reference_image_ids == [img]
    assert b.line_treatment == "bold black outlines"
    assert b.form == "round"
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_brief.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.ideation'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/ideation/__init__.py
```

```python
# inkscout/ideation/brief.py
"""Da (reference selezionata o tema libero) + assi → Brief strutturato.
Il tema è testo libero: viene espanso a runtime cercando nella libreria."""
from __future__ import annotations

from inkscout.core.models import Brief
from inkscout.store.db import Store

_BOLD = {"blackwork", "traditional", "neo-traditional", "geometric", "old-school"}
_FINE = {"fine-line", "fineline", "minimalist", "ornamental"}


def line_treatment_for(styles: list[str]) -> str:
    s = {x.lower() for x in styles}
    if s & _FINE:
        return "single-weight fine lines"
    if s & _BOLD:
        return "bold black outlines"
    return "clean linework"


def expand_theme(theme_text: str, store: Store, limit: int = 12) -> list[int]:
    if not theme_text:
        return []
    rows = store.list_images(theme=theme_text)
    return [r["id"] for r in rows][:limit]


def build_brief(*, theme_text="", styles=None, form="", color_mode="", placement="",
                size="", reference_image_ids=None, store=None) -> Brief:
    styles = styles or []
    refs = list(reference_image_ids or [])
    if not refs and theme_text and store is not None:
        refs = expand_theme(theme_text, store)
    return Brief(theme_text=theme_text, styles=styles, form=form, color_mode=color_mode,
                 placement=placement, size=size, line_treatment=line_treatment_for(styles),
                 reference_image_ids=refs)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_brief.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/ideation tests/test_brief.py
git commit -m "feat(ideation): brief builder + espansione tema da libreria"
```

---

### Task 15: DesignEngine protocol + registry (`inkscout/engine/base.py`)

**Files:**
- Create: `inkscout/engine/__init__.py`
- Create: `inkscout/engine/base.py`
- Create: `tests/test_engine_base.py`

**Interfaces:**
- Consumes: `Brief`, `DesignResult`, `EngineCapabilities` (Task 3).
- Produces:
  - `class DesignEngine(Protocol)`: `capabilities: EngineCapabilities`, `mode: str`, `generate(brief: Brief) -> DesignResult`.
  - `class EngineKeyMissing(Exception)`.
  - `def register_engine(mode: str)` decoratore; `def get_engine(mode: str, **kwargs) -> DesignEngine` — istanzia passando kwargs; `def available_modes() -> list[str]`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_engine_base.py
import pytest
from inkscout.engine import base
from inkscout.core.models import DesignResult, EngineCapabilities


@base.register_engine("fake")
class FakeEngine:
    mode = "fake"
    capabilities = EngineCapabilities(False, False, 0.0, False, True)
    def __init__(self, **kw):
        self.kw = kw
    def generate(self, brief):
        return DesignResult(kind="prompt", engine="fake", prompt="ok")


def test_register_and_get():
    eng = base.get_engine("fake", foo=1)
    assert eng.kw["foo"] == 1
    assert eng.generate(None).prompt == "ok"
    assert "fake" in base.available_modes()


def test_unknown_mode_raises():
    with pytest.raises(KeyError):
        base.get_engine("nope")
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_engine_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.engine'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/engine/__init__.py
```

```python
# inkscout/engine/base.py
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
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_engine_base.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/engine/__init__.py inkscout/engine/base.py tests/test_engine_base.py
git commit -m "feat(engine): DesignEngine protocol + registry per-mode"
```

---

### Task 16: BriefEngine — Modo E, default offline (`inkscout/engine/brief_engine.py`)

**Files:**
- Create: `inkscout/engine/brief_engine.py`
- Create: `tests/test_brief_engine.py`

**Interfaces:**
- Consumes: `register_engine` (Task 15), `Brief`/`DesignResult` (Task 3), `Store.get_image` (Task 4).
- Produces:
  - `NEGATIVE_PROMPT: str`.
  - `def build_prompt(brief: Brief) -> str` — **stile PRIMA**, poi tema, trattamento linea, boilerplate stencil, placement.
  - `class BriefEngine(store: Store | None = None)` (mode `"E"`): `capabilities = offline/no-key/cost 0`; `generate(brief)` → `DesignResult(kind="prompt")` con `prompt`, `moodboard_paths` (dai `reference_image_ids` via store) e `meta["negative_prompt"]`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_brief_engine.py
from inkscout.engine.brief_engine import BriefEngine, build_prompt, NEGATIVE_PROMPT
from inkscout.core.models import Brief
from inkscout.store.db import Store


def test_build_prompt_puts_style_first():
    b = Brief(theme_text="Twin Peaks", styles=["blackwork", "geometric"],
              line_treatment="bold black outlines", placement="forearm")
    p = build_prompt(b)
    assert p.startswith("blackwork geometric")
    assert "Twin Peaks" in p
    assert "bold black outlines" in p
    assert "tattoo stencil reference, white background, clear linework, no fuzzy edges" in p


def test_generate_offline_with_moodboard(tmp_path):
    store = Store(tmp_path / "t.db")
    src = store.add_source("upload", "local")
    img = store.add_image("images/owl.jpg", 1, 10, 10, None, src, "u://owl", "ref", "t")
    eng = BriefEngine(store=store)
    assert eng.capabilities.offline is True and eng.capabilities.needs_key is False
    res = eng.generate(Brief(theme_text="owl", styles=["blackwork"], reference_image_ids=[img]))
    assert res.kind == "prompt" and res.engine == "E"
    assert res.moodboard_paths == ("images/owl.jpg",)
    assert res.meta["negative_prompt"] == NEGATIVE_PROMPT
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_brief_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.engine.brief_engine'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/engine/brief_engine.py
"""Modo E (DEFAULT, offline, no-API): brief + moodboard + prompt ottimizzato.
Regola di prompting validata (spec §5): stile PRIMA, poi trattamento linea e boilerplate stencil."""
from __future__ import annotations

from inkscout.core.models import Brief, DesignResult, EngineCapabilities
from inkscout.engine.base import register_engine

_STENCIL = "tattoo stencil reference, white background, clear linework, no fuzzy edges"
NEGATIVE_PROMPT = ("color, colour, shading, grayscale photo, background clutter, "
                   "photorealistic skin, blurry, watermark")


def build_prompt(brief: Brief) -> str:
    parts: list[str] = []
    if brief.styles:
        parts.append(" ".join(brief.styles))  # stile PRIMA
    if brief.theme_text:
        parts.append(brief.theme_text)
    if brief.line_treatment:
        parts.append(brief.line_treatment)
    parts.append(_STENCIL)
    if brief.placement:
        parts.append(f"placement: {brief.placement}")
    return ", ".join(parts)


@register_engine("E")
class BriefEngine:
    mode = "E"
    capabilities = EngineCapabilities(needs_gpu=False, needs_key=False, cost_per_img=0.0,
                                      watermarks=False, offline=True)

    def __init__(self, store=None):
        self.store = store

    def generate(self, brief: Brief) -> DesignResult:
        moodboard: list[str] = []
        if self.store is not None:
            for img_id in brief.reference_image_ids:
                row = self.store.get_image(img_id)
                if row:
                    moodboard.append(row["path"])
        return DesignResult(kind="prompt", engine=self.mode, prompt=build_prompt(brief),
                            moodboard_paths=tuple(moodboard),
                            meta={"negative_prompt": NEGATIVE_PROMPT})
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_brief_engine.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/engine/brief_engine.py tests/test_brief_engine.py
git commit -m "feat(engine): Modo E BriefEngine (moodboard + prompt ottimizzato, offline)"
```

---

### Task 17: HostedAPIEngine — Modo A, fal.ai opt-in (`inkscout/engine/hosted.py`)

**Files:**
- Create: `inkscout/engine/hosted.py`
- Create: `tests/test_hosted_engine.py`

**Interfaces:**
- Consumes: `build_prompt` (Task 16), `Config` + `keychain_get` (Task 2), `register_engine`/`EngineKeyMissing` (Task 15).
- Produces:
  - `class HostedAPIEngine(config: Config, key_getter=keychain_get, poster=None, downloader=None)` (mode `"A"`): `capabilities` = `needs_key=True, offline=False, cost_per_img=config.fal_price_per_img`. `generate(brief)`:
    - key da `key_getter("inkscout-fal-key")`; se assente → `EngineKeyMissing`;
    - `poster(url, payload, key) -> dict` con `payload["model"]=config.fal_model_id` (config-driven) e `payload["prompt"]=build_prompt(brief)`;
    - scarica la prima immagine con `downloader(image_url) -> bytes`; salva sotto `config.images_dir`; ritorna `DesignResult(kind="raster", raster_path=...)`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_hosted_engine.py
import pytest
from inkscout.engine.hosted import HostedAPIEngine
from inkscout.engine.base import EngineKeyMissing
from inkscout.config import load_config
from inkscout.core.models import Brief


def _cfg(tmp_path):
    return load_config({"INK_SCOUT_DATA_DIR": str(tmp_path),
                        "INK_SCOUT_FAL_MODEL_ID": "fal-ai/flux/schnell"})


def test_missing_key_raises(tmp_path):
    eng = HostedAPIEngine(_cfg(tmp_path), key_getter=lambda *_: None)
    with pytest.raises(EngineKeyMissing):
        eng.generate(Brief(theme_text="owl", styles=["blackwork"]))


def test_generate_uses_config_model_and_saves(tmp_path):
    seen = {}
    def poster(url, payload, key):
        seen.update(payload); seen["key"] = key
        return {"images": [{"url": "https://cdn/out.png"}]}
    eng = HostedAPIEngine(_cfg(tmp_path), key_getter=lambda *_: "SECRET",
                          poster=poster, downloader=lambda u: b"PNGDATA")
    res = eng.generate(Brief(theme_text="owl", styles=["blackwork"], line_treatment="bold black outlines"))
    assert res.kind == "raster"
    assert seen["model"] == "fal-ai/flux/schnell"           # model-id dalla config
    assert seen["prompt"].startswith("blackwork")            # prompt riusa build_prompt
    assert seen["key"] == "SECRET"
    from pathlib import Path
    assert Path(res.raster_path).read_bytes() == b"PNGDATA"
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_hosted_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.engine.hosted'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/engine/hosted.py
"""Modo A (opt-in): backend cloud astratto, default fal.ai. Model-id e prezzo dalla config,
key dal Keychain. `poster`/`downloader` iniettabili per i test; reali via urllib (lazy)."""
from __future__ import annotations

from pathlib import Path

from inkscout.config import Config, keychain_get
from inkscout.core.models import Brief, DesignResult, EngineCapabilities
from inkscout.engine.base import EngineKeyMissing, register_engine
from inkscout.engine.brief_engine import NEGATIVE_PROMPT, build_prompt

_FAL_URL_TMPL = "https://fal.run/{model}"


@register_engine("A")
class HostedAPIEngine:
    mode = "A"

    def __init__(self, config: Config, key_getter=keychain_get, poster=None, downloader=None):
        self.config = config
        self.key_getter = key_getter
        self._poster = poster
        self._downloader = downloader
        self.capabilities = EngineCapabilities(
            needs_gpu=False, needs_key=True, cost_per_img=config.fal_price_per_img,
            watermarks=False, offline=False)

    def generate(self, brief: Brief) -> DesignResult:
        key = self.key_getter("inkscout-fal-key")
        if not key:
            raise EngineKeyMissing("manca la key fal.ai nel Keychain (voce inkscout-fal-key)")
        payload = {"model": self.config.fal_model_id, "prompt": build_prompt(brief),
                   "negative_prompt": NEGATIVE_PROMPT}
        url = _FAL_URL_TMPL.format(model=self.config.fal_model_id)
        resp = (self._poster or _http_post)(url, payload, key)
        image_url = resp["images"][0]["url"]
        data = (self._downloader or _http_download)(image_url)
        self.config.images_dir.mkdir(parents=True, exist_ok=True)
        dest = self.config.images_dir / f"gen-{abs(hash(image_url)) & 0xFFFFFFFF:08x}.png"
        dest.write_bytes(data)
        return DesignResult(kind="raster", engine=self.mode, prompt=payload["prompt"],
                            raster_path=str(dest), meta={"source_url": image_url})


def _http_post(url, payload, key):  # pragma: no cover — rete
    import json
    import urllib.request
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _http_download(url):  # pragma: no cover — rete
    import urllib.request
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_hosted_engine.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/engine/hosted.py tests/test_hosted_engine.py
git commit -m "feat(engine): Modo A HostedAPIEngine fal.ai (config-driven, key Keychain)"
```

---

## Fase 5 — Export stencil

### Task 18: Pipeline export stencil (`inkscout/export/stencil.py`)

**Files:**
- Create: `inkscout/export/__init__.py`
- Create: `inkscout/export/stencil.py`
- Create: `tests/test_export.py`

**Interfaces:**
- Consumes: Pillow (core). vtracer (lazy, extra `[export]`).
- Produces:
  - `def binarize(image) -> "PIL.Image.Image"` — grayscale → soglia → bilevel (`"1"`).
  - `def add_label(image, text) -> "PIL.Image.Image"` — banda in basso con la label (guardia §11).
  - `def to_stencil_png(src, out_path, *, dpi=300, target_long_side=2000, label="AI-generated / reference only") -> Path` — pipeline completa: apre, binarizza, upscala, applica label, salva PNG con dpi nei metadati.
  - `def to_svg(png_path, out_path) -> Path` — vettorializza via vtracer (lazy).

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_export.py
from io import BytesIO
from pathlib import Path
from PIL import Image
from inkscout.export.stencil import binarize, to_stencil_png


def _png(color=(120, 120, 120), size=(50, 40)):
    buf = BytesIO(); Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_binarize_is_bilevel():
    out = binarize(Image.new("RGB", (10, 10), (200, 200, 200)))
    assert out.mode == "1"


def test_to_stencil_png_sets_dpi_and_upscales(tmp_path):
    out = tmp_path / "s.png"
    to_stencil_png(_png(), out, dpi=300, target_long_side=500)
    assert out.exists()
    with Image.open(out) as im:
        assert im.info.get("dpi", (0, 0))[0] == 300
        assert max(im.size) >= 500          # upscalata al lato lungo richiesto
        assert im.size[1] > 40              # più alta dell'originale per via della label


def test_to_svg_optional(tmp_path):
    import pytest
    pytest.importorskip("vtracer")
    from inkscout.export.stencil import to_stencil_png, to_svg
    png = tmp_path / "s.png"; to_stencil_png(_png(), png, target_long_side=200)
    svg = to_svg(png, tmp_path / "s.svg")
    assert Path(svg).read_text().lstrip().startswith("<svg") or Path(svg).exists()
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.export'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/export/__init__.py
```

```python
# inkscout/export/stencil.py
"""Export stencil: binarizza → upscala a 300 DPI → label → PNG (+ SVG via vtracer lazy).
La label 'AI-generated / reference only' è una guardia §11 non opzionale."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path


def binarize(image, threshold: int = 128):
    from PIL import Image
    gray = image.convert("L")
    return gray.point(lambda p: 255 if p > threshold else 0).convert("1")


def add_label(image, text: str):
    from PIL import Image, ImageDraw
    band = max(24, image.size[0] // 20)
    out = Image.new("RGB", (image.size[0], image.size[1] + band), "white")
    out.paste(image.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(out)
    draw.rectangle([0, image.size[1], out.size[0], out.size[1]], fill=(20, 20, 20))
    draw.text((6, image.size[1] + max(2, (band - 12) // 2)), text, fill="white")
    return out


def to_stencil_png(src, out_path, *, dpi: int = 300, target_long_side: int = 2000,
                   label: str = "AI-generated / reference only") -> Path:
    from PIL import Image
    img = Image.open(BytesIO(src)) if isinstance(src, (bytes, bytearray)) else Image.open(src)
    bw = binarize(img)
    scale = max(1.0, target_long_side / max(bw.size))
    if scale > 1.0:
        bw = bw.resize((round(bw.size[0] * scale), round(bw.size[1] * scale)), Image.NEAREST)
    labeled = add_label(bw, label)
    out_path = Path(out_path)
    labeled.save(out_path, format="PNG", dpi=(dpi, dpi))
    return out_path


def to_svg(png_path, out_path) -> Path:
    import vtracer  # lazy, extra [export]
    out_path = Path(out_path)
    vtracer.convert_image_to_svg_py(str(png_path), str(out_path))
    return out_path
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_export.py -v`
Expected: PASS (3 passed, o 2 passed + 1 skipped se `vtracer` non installato).

- [ ] **Step 5: Commit**

```bash
git add inkscout/export tests/test_export.py
git commit -m "feat(export): pipeline stencil 300 DPI + label §11 + SVG vtracer opzionale"
```

---

## Fase 6 — Web UI locale (stdlib)

### Task 19: Templates + App + galleria con guardie §11 (`inkscout/web/`)

**Files:**
- Create: `inkscout/web/__init__.py`
- Create: `inkscout/web/templates.py`
- Create: `inkscout/web/app.py`
- Create: `tests/test_web_gallery.py`

**Interfaces:**
- Consumes: `Store` (Task 4).
- Produces:
  - `web/templates.py`: `def page(title, body) -> str`; `def image_card(row) -> str` (mostra attribuzione + CTA "Commissiona questo artista"); `def gallery(rows, filters) -> str`.
  - `web/app.py`: `@dataclass Response(status: int, content_type: str, body)`; `class App(store, images_dir)` con `handle(method, path, params) -> Response`. Rotte di questo task: `GET /` (galleria filtrabile via `params`), `GET /image/{id}` (serve i byte). `App` esclude a monte le immagini di artisti con `do_not_mimic=1` (guardia §11).

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_web_gallery.py
from pathlib import Path
from PIL import Image
from inkscout.store.db import Store
from inkscout.web.app import App


def _app(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"; Image.new("RGB", (8, 8)).save(p)
    src = store.add_source("site", "https://artist.ex")
    art = store.add_artist("Jane", handle="@jane", source_id=src, provenance_url="https://artist.ex")
    img = store.add_image(str(p), 1, 8, 8, art, src, "https://artist.ex/a", "personal-site", "t")
    return App(store, tmp_path / "images"), store, img


def test_gallery_shows_attribution_and_cta(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("GET", "/", {})
    assert r.status == 200 and "text/html" in r.content_type
    assert "@jane" in r.body                     # attribuzione
    assert "Commissiona questo artista" in r.body  # CTA guardia §11


def test_image_route_serves_bytes(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("GET", f"/image/{img}", {})
    assert r.status == 200 and r.content_type.startswith("image/")
    assert isinstance(r.body, (bytes, bytearray)) and len(r.body) > 0


def test_do_not_mimic_excluded(tmp_path):
    app, store, img = _app(tmp_path)
    store.conn.execute("UPDATE artist SET do_not_mimic=1"); store.conn.commit()
    r = app.handle("GET", "/", {})
    assert "@jane" not in r.body
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_web_gallery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.web'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/web/__init__.py
```

```python
# inkscout/web/templates.py
"""Rendering HTML in stdlib. Le guardie §11 (attribuzione, CTA, label) sono nel markup."""
from __future__ import annotations

from html import escape

_BANNER = ("ink-scout produce <b>reference privati</b> per poi "
           "<b>commissionare un tatuatore umano</b> — non tatuaggi finiti da stampare.")


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title>"
            "<style>body{font-family:system-ui;margin:1.5rem;max-width:960px}"
            ".card{display:inline-block;width:180px;vertical-align:top;margin:.4rem;"
            "border:1px solid #ddd;border-radius:8px;padding:.4rem;font-size:.8rem}"
            ".banner{background:#fff8e1;border:1px solid #f0d000;padding:.6rem;border-radius:8px}"
            "img{max-width:100%;border-radius:4px}.cta{color:#0a58ca}</style></head><body>"
            f"<div class='banner'>{_BANNER}</div><h1>{escape(title)}</h1>{body}</body></html>")


def image_card(row: dict) -> str:
    handle = escape(row.get("handle") or "")
    src = escape(row.get("source_url") or "")
    attrib = f"fonte: <a href='{src}'>{src[:40]}</a>" if src else ""
    cta = (f"<div class='cta'>@{handle} — <a href='{src}'>Commissiona questo artista</a></div>"
           if handle else "")
    fav = "★" if row.get("favorite") else "☆"
    return (f"<div class='card'><img src='/image/{row['id']}'>"
            f"<div>{attrib}</div>{cta}"
            f"<form method='post' action='/favorite'><input type='hidden' name='id' value='{row['id']}'>"
            f"<button>{fav}</button></form></div>")


def gallery(rows: list[dict], filters: dict) -> str:
    q = escape(filters.get("theme", "") or "")
    form = (f"<form method='get' action='/'>tema: <input name='theme' value='{q}'>"
            "<button>filtra</button></form>")
    cards = "".join(image_card(r) for r in rows) or "<p>Libreria vuota.</p>"
    return form + f"<p>{len(rows)} immagini</p>" + cards
```

```python
# inkscout/web/app.py
"""App web: routing testabile (handle) + server stdlib (serve)."""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from inkscout.store.db import Store
from inkscout.web import templates


@dataclass
class Response:
    status: int
    content_type: str
    body: object


class App:
    def __init__(self, store: Store, images_dir: Path | str):
        self.store = store
        self.images_dir = Path(images_dir)

    def _visible_rows(self, filters: dict) -> list[dict]:
        rows = self.store.list_images(theme=filters.get("theme") or None)
        out = []
        for r in rows:
            art = self.store.conn.execute(
                "SELECT handle, do_not_mimic, provenance_url FROM artist WHERE id=?",
                (r["artist_id"],)).fetchone() if r["artist_id"] else None
            if art and art["do_not_mimic"]:
                continue
            r["handle"] = art["handle"] if art else ""
            out.append(r)
        return out

    def handle(self, method: str, path: str, params: dict) -> Response:
        if method == "GET" and path == "/":
            rows = self._visible_rows(params)
            html = templates.page("ink-scout — libreria", templates.gallery(rows, params))
            return Response(200, "text/html; charset=utf-8", html)
        if method == "GET" and path.startswith("/image/"):
            return self._serve_image(path.rsplit("/", 1)[-1])
        return Response(404, "text/plain; charset=utf-8", "not found")

    def _serve_image(self, image_id: str) -> Response:
        row = self.store.get_image(int(image_id)) if image_id.isdigit() else None
        if not row or not Path(row["path"]).exists():
            return Response(404, "text/plain; charset=utf-8", "no image")
        ctype = mimetypes.guess_type(row["path"])[0] or "image/png"
        return Response(200, ctype, Path(row["path"]).read_bytes())


def serve(store: Store, images_dir: Path, host: str = "127.0.0.1", port: int = 8765) -> None:  # pragma: no cover
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse
    app = App(store, images_dir)

    class Handler(BaseHTTPRequestHandler):
        def _run(self, method):
            u = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(u.query).items()}
            if method == "POST":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                params.update({k: v[0] for k, v in parse_qs(body).items()})
            resp = app.handle(method, u.path, params)
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.end_headers()
            data = resp.body if isinstance(resp.body, (bytes, bytearray)) else str(resp.body).encode()
            self.wfile.write(data)

        def do_GET(self):
            self._run("GET")

        def do_POST(self):
            self._run("POST")

    HTTPServer((host, port), Handler).serve_forever()
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_web_gallery.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/web tests/test_web_gallery.py
git commit -m "feat(web): App + galleria filtrabile con attribuzione/CTA e filtro do_not_mimic"
```

---

### Task 20: Preferiti/hide + Studio + Generate Modo E (`inkscout/web/`)

**Files:**
- Modify: `inkscout/web/templates.py` (aggiunge `studio_form`, `result_view`)
- Modify: `inkscout/web/app.py` (aggiunge `headers` a `Response`, rotte POST `/favorite` e `/hide`, GET `/studio`, POST `/generate`; `App.__init__` accetta `cfg=None`)
- Create: `tests/test_web_studio.py`

**Interfaces:**
- Consumes: `build_brief` (Task 14), `BriefEngine` (Task 16), `available_modes`/`get_engine` (Task 15).
- Produces:
  - `templates.studio_form(modes: list[str], styles: list[str]) -> str`.
  - `templates.result_view(result, reference_ids: list[int]) -> str` — mostra prompt, negative, moodboard (via `/image/{id}`) e la label "AI-generated / reference only".
  - `Response` con campo `headers: dict`.
  - Rotte: `POST /favorite`, `POST /hide`, `GET /studio`, `POST /generate`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_web_studio.py
from PIL import Image
from inkscout.store.db import Store
from inkscout.web.app import App


def _app(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"; Image.new("RGB", (8, 8)).save(p)
    src = store.add_source("upload", "local")
    img = store.add_image(str(p), 1, 8, 8, None, src, "u://a", "ref", "t")
    store.add_image_tag(img, "subject", "owl", 1.0, "test")
    return App(store, tmp_path / "images"), store, img


def test_favorite_toggles(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("POST", "/favorite", {"id": str(img)})
    assert r.status in (200, 303)
    assert store.get_image(img)["favorite"] == 1


def test_studio_form_lists_mode_E(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("GET", "/studio", {})
    assert r.status == 200 and "value='E'" in r.body


def test_generate_mode_E_returns_prompt_and_label(tmp_path):
    app, store, img = _app(tmp_path)
    r = app.handle("POST", "/generate",
                   {"mode": "E", "theme": "owl", "styles": "blackwork"})
    assert r.status == 200
    assert "blackwork" in r.body
    assert "AI-generated / reference only" in r.body   # label §11
    assert f"/image/{img}" in r.body                   # moodboard dalla libreria
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_web_studio.py -v`
Expected: FAIL — `AttributeError`/404 sulle rotte non ancora presenti.

- [ ] **Step 3: Implementazione minima**

Aggiungi in `inkscout/web/templates.py`:

```python
def studio_form(modes: list[str], styles: list[str]) -> str:
    opts = "".join(f"<option value='{m}'>{m}</option>" for m in modes)
    style_hint = ", ".join(styles[:8])
    return ("<h2>Studio</h2><form method='post' action='/generate'>"
            f"modo: <select name='mode'>{opts}</select><br>"
            "tema (testo libero): <input name='theme' placeholder='es. Twin Peaks'><br>"
            f"stili (separati da virgola): <input name='styles' placeholder='{style_hint}'><br>"
            "forma: <input name='form' placeholder='round'><br>"
            "<button>Genera</button></form>")


def result_view(result, reference_ids: list[int]) -> str:
    from html import escape
    mood = "".join(f"<img src='/image/{i}' width='120'>" for i in reference_ids)
    neg = escape(result.meta.get("negative_prompt", ""))
    return ("<h2>Risultato</h2>"
            "<p style='background:#e8f5e9;padding:.4rem'>AI-generated / reference only — "
            "fallo ridisegnare a mano dal tuo tatuatore.</p>"
            f"<h3>Prompt</h3><pre>{escape(result.prompt)}</pre>"
            f"<h3>Negative</h3><pre>{neg}</pre>"
            f"<h3>Moodboard</h3>{mood or '<i>nessuna reference in libreria</i>'}")
```

Sostituisci `Response`, `App.__init__` e `App.handle` in `inkscout/web/app.py`, e aggiorna `serve()` per emettere gli header:

```python
@dataclass
class Response:
    status: int
    content_type: str
    body: object
    headers: dict = None  # type: ignore

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
```

```python
    def __init__(self, store: Store, images_dir: Path | str, cfg=None):
        self.store = store
        self.images_dir = Path(images_dir)
        self.cfg = cfg

    def handle(self, method: str, path: str, params: dict) -> Response:
        if method == "GET" and path == "/":
            rows = self._visible_rows(params)
            return Response(200, "text/html; charset=utf-8",
                            templates.page("ink-scout — libreria", templates.gallery(rows, params)))
        if method == "GET" and path.startswith("/image/"):
            return self._serve_image(path.rsplit("/", 1)[-1])
        if method == "POST" and path in ("/favorite", "/hide"):
            return self._toggle(path, params)
        if method == "GET" and path == "/studio":
            return self._studio()
        if method == "POST" and path == "/generate":
            return self._generate(params)
        return Response(404, "text/plain; charset=utf-8", "not found")

    def _toggle(self, path: str, params: dict) -> Response:
        img_id = int(params["id"])
        if path == "/favorite":
            row = self.store.get_image(img_id)
            self.store.set_favorite(img_id, not row["favorite"])
        else:
            self.store.set_hidden(img_id, True)
        return Response(303, "text/html; charset=utf-8",
                        "<meta http-equiv='refresh' content='0;url=/'>", {"Location": "/"})

    def _studio(self) -> Response:
        from inkscout.engine.base import available_modes
        from inkscout.engine import brief_engine  # noqa: F401 — registra Modo E
        styles = [r["name"] for r in self.store.conn.execute("SELECT name FROM style ORDER BY name")]
        modes = available_modes() or ["E"]
        return Response(200, "text/html; charset=utf-8",
                        templates.page("ink-scout — studio", templates.studio_form(modes, styles)))

    def _generate(self, params: dict) -> Response:
        from inkscout.engine import brief_engine  # noqa: F401 — registra Modo E
        from inkscout.engine.base import get_engine
        from inkscout.ideation.brief import build_brief
        styles = [s.strip() for s in (params.get("styles") or "").split(",") if s.strip()]
        brief = build_brief(theme_text=params.get("theme", ""), styles=styles,
                            form=params.get("form", ""), store=self.store)
        mode = params.get("mode", "E")
        if mode == "E":
            engine = get_engine("E", store=self.store)
        elif mode == "A" and self.cfg is not None:
            engine = get_engine("A", config=self.cfg)
        else:
            return Response(200, "text/html; charset=utf-8",
                            templates.page("ink-scout", f"<p>Modo {mode} non configurato.</p>"))
        result = engine.generate(brief)
        return Response(200, "text/html; charset=utf-8",
                        templates.page("ink-scout — risultato",
                                       templates.result_view(result, brief.reference_image_ids)))
```

In `serve()`, dopo `self.send_header("Content-Type", resp.content_type)`, aggiungi:

```python
            for k, v in resp.headers.items():
                self.send_header(k, v)
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_web_studio.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/web/templates.py inkscout/web/app.py tests/test_web_studio.py
git commit -m "feat(web): preferiti/hide + studio + generate Modo E (label §11 visibile)"
```

---

### Task 21: Export stencil dal web (`inkscout/web/app.py`)

**Files:**
- Modify: `inkscout/web/app.py` (rotta `POST /export`)
- Modify: `inkscout/web/templates.py` (bottone export nella card)
- Create: `tests/test_web_export.py`

**Interfaces:**
- Consumes: `to_stencil_png` (Task 18), `Store.get_image` (Task 4).
- Produces: rotta `POST /export` con `params["id"]` → genera lo stencil PNG dell'immagine e lo restituisce come download (`Content-Disposition: attachment`).

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_web_export.py
from PIL import Image
from inkscout.store.db import Store
from inkscout.web.app import App


def test_export_returns_png(tmp_path):
    store = Store(tmp_path / "t.db")
    (tmp_path / "images").mkdir()
    p = tmp_path / "images" / "a.png"; Image.new("RGB", (40, 30), (120, 120, 120)).save(p)
    src = store.add_source("upload", "local")
    img = store.add_image(str(p), 1, 40, 30, None, src, "u://a", "ref", "t")
    app = App(store, tmp_path / "images")
    r = app.handle("POST", "/export", {"id": str(img)})
    assert r.status == 200 and r.content_type == "image/png"
    assert isinstance(r.body, (bytes, bytearray)) and r.body[:8] == b"\x89PNG\r\n\x1a\n"
    assert "attachment" in r.headers.get("Content-Disposition", "")
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_web_export.py -v`
Expected: FAIL — 404 (rotta `/export` assente).

- [ ] **Step 3: Implementazione minima**

Aggiungi il ramo in `App.handle` (prima del `return Response(404, ...)`):

```python
        if method == "POST" and path == "/export":
            return self._export(params)
```

Aggiungi il metodo `_export` alla classe `App`:

```python
    def _export(self, params: dict) -> Response:
        from inkscout.export.stencil import to_stencil_png
        row = self.store.get_image(int(params["id"]))
        if not row:
            return Response(404, "text/plain; charset=utf-8", "no image")
        exports = self.images_dir / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        src = Path(row["path"]).read_bytes()
        out = to_stencil_png(src, exports / f"stencil-{row['id']}.png")
        return Response(200, "image/png", out.read_bytes(),
                        {"Content-Disposition": f"attachment; filename=stencil-{row['id']}.png"})
```

Aggiungi il bottone export in `templates.image_card` (dentro la `<div class='card'>`, dopo il form dei preferiti):

```python
    export_btn = (f"<form method='post' action='/export'>"
                  f"<input type='hidden' name='id' value='{row['id']}'>"
                  f"<button>stencil ⬇</button></form>")
```

e includilo nella stringa di ritorno della card (concatenandolo prima di `</div>`).

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_web_export.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/web/app.py inkscout/web/templates.py tests/test_web_export.py
git commit -m "feat(web): export stencil dal web come download PNG"
```

---

## Fase 7 — CLI, integrazione end-to-end, docs

### Task 22: CLI (`inkscout/cli.py`)

**Files:**
- Create: `inkscout/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config`/`ensure_dirs` (Task 2), `Store` (Task 4), `Library` (Task 6), gli adapter (Task 8–10), `sync_styles` (Task 11), `serve` (Task 19).
- Produces:
  - `def build_parser() -> argparse.ArgumentParser`.
  - `def main(argv: list[str] | None = None) -> int` con sottocomandi `ingest --kind --ref [--optin]`, `sync-styles`, `serve [--port]`.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_cli.py
from PIL import Image
from inkscout.cli import main
from inkscout.store.db import Store


def test_cli_ingest_upload(tmp_path, monkeypatch):
    imgdir = tmp_path / "in"; imgdir.mkdir()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(imgdir / "a.png")
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    rc = main(["ingest", "--kind", "upload", "--ref", str(imgdir)])
    assert rc == 0
    store = Store(tmp_path / "data" / "inkscout.db")
    assert len(store.all_phashes()) == 1


def test_cli_sync_styles(tmp_path, monkeypatch):
    monkeypatch.setenv("INK_SCOUT_DATA_DIR", str(tmp_path / "data"))
    rc = main(["sync-styles"])
    assert rc == 0
    store = Store(tmp_path / "data" / "inkscout.db")
    assert store.style_id_by_name("blackwork") is not None
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inkscout.cli'`.

- [ ] **Step 3: Implementazione minima**

```python
# inkscout/cli.py
"""CLI ink-scout: ingest / sync-styles / serve."""
from __future__ import annotations

import argparse

from inkscout.config import ensure_dirs, load_config
from inkscout.core.models import SourceRef
from inkscout.ingest import instagram, site, upload  # noqa: F401 — registra gli adapter
from inkscout.ingest.base import get_adapter
from inkscout.library.library import Library
from inkscout.store.db import Store
from inkscout.tagging.vocab import sync_styles


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ink-scout")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest")
    pi.add_argument("--kind", required=True, choices=["upload", "site", "instagram"])
    pi.add_argument("--ref", required=True)
    pi.add_argument("--optin", action="store_true", help="consenso harvest personale (IG)")
    sub.add_parser("sync-styles")
    ps = sub.add_parser("serve")
    ps.add_argument("--port", type=int, default=8765)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    ensure_dirs(cfg)
    store = Store(cfg.db_path)

    if args.cmd == "ingest":
        lib = Library(store, cfg.images_dir)
        adapter = get_adapter(args.kind)
        src = SourceRef(kind=args.kind, ref=args.ref, harvest_optin=args.optin)
        added = dup = 0
        for raw in adapter.fetch(src):
            res = lib.add(raw)
            dup += int(res.is_duplicate)
            added += int(not res.is_duplicate)
        print(f"ingest {args.kind}: {added} nuove, {dup} duplicati")
        return 0

    if args.cmd == "sync-styles":
        n = sync_styles(store, cfg.styles_seed)
        print(f"sincronizzati {n} stili")
        return 0

    if args.cmd == "serve":
        from inkscout.web.app import serve
        print(f"http://127.0.0.1:{args.port}")
        serve(store, cfg.images_dir, port=args.port)
        return 0

    return 1
```

- [ ] **Step 4: Eseguire i test e verificare che passino**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add inkscout/cli.py tests/test_cli.py
git commit -m "feat(cli): ingest / sync-styles / serve"
```

---

### Task 23: Integrazione end-to-end offline + README quickstart

**Files:**
- Create: `tests/test_integration.py`
- Modify: `README.md` (sezione Quickstart)

**Interfaces:**
- Consumes: tutto il flusso camminante (upload → libreria → brief → Modo E → export). Nessuna rete, nessun extra pesante.
- Produces: prova che l'MVP gira end-to-end offline.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_integration.py
from pathlib import Path
from PIL import Image
from inkscout.store.db import Store
from inkscout.library.library import Library
from inkscout.ingest.upload import UploadAdapter
from inkscout.core.models import SourceRef
from inkscout.ideation.brief import build_brief
from inkscout.engine.brief_engine import BriefEngine
from inkscout.export.stencil import to_stencil_png


def test_flusso_camminante_offline(tmp_path):
    # 1. ingest upload di 2 immagini distinte
    src_dir = tmp_path / "in"; src_dir.mkdir()
    Image.new("RGB", (40, 30), (10, 10, 10)).save(src_dir / "owl.png")
    grad = Image.new("L", (40, 30))
    for x in range(40):
        for y in range(30):
            grad.putpixel((x, y), (x * 6) % 256)
    grad.save(src_dir / "forest.png")

    store = Store(tmp_path / "t.db")
    lib = Library(store, tmp_path / "images")
    for raw in UploadAdapter().fetch(SourceRef(kind="upload", ref=str(src_dir))):
        lib.add(raw)
    assert len(store.all_phashes()) == 2

    # 2. tagging manuale del soggetto (simula il tagger)
    first = store.list_images()[0]["id"]
    store.add_image_tag(first, "subject", "owl", 1.0, "test")

    # 3. brief da tema libero + 4. genera Modo E (offline)
    brief = build_brief(theme_text="owl", styles=["blackwork", "geometric"], store=store)
    res = BriefEngine(store=store).generate(brief)
    assert res.prompt.startswith("blackwork geometric")
    assert res.moodboard_paths  # il tema "owl" ha agganciato la reference taggata

    # 5. export stencil di una reference reale
    img_path = store.get_image(first)["path"]
    out = to_stencil_png(Path(img_path).read_bytes(), tmp_path / "stencil.png")
    assert out.exists()
    with Image.open(out) as im:
        assert im.info.get("dpi", (0, 0))[0] == 300
```

- [ ] **Step 2: Eseguire il test e verificare che fallisca**

Run: `uv run pytest tests/test_integration.py -v`
Expected: FAIL fintanto che un pezzo del flusso manca; PASS quando l'MVP è completo.

- [ ] **Step 3: Aggiornare il README**

Aggiungi in `README.md`:

```markdown
## Quickstart (MVP offline)

```bash
uv venv && uv pip install -e ".[dev]"
uv run ink-scout sync-styles                          # popola il vocabolario stili
uv run ink-scout ingest --kind upload --ref ./le-mie-immagini
uv run ink-scout serve                                # http://127.0.0.1:8765
```

- **Modo E (default):** offline, nessuna chiave — produce brief + moodboard + prompt pronto.
- **Modo A (opt-in):** salva la key fal.ai nel Keychain e imposta il model-id:
  ```bash
  security add-generic-password -a inkscout-fal-key -s ink-scout -w
  export INK_SCOUT_FAL_MODEL_ID=fal-ai/flux/schnell
  ```
- **Extra pesanti opzionali:** `pip install -e ".[tag]"` (CLIP), `".[export]"` (SVG vtracer), `".[cdp]"` (fallback browser).

Ogni output è marcato **"AI-generated / reference only"**: ink-scout serve a preparare un reference da portare a un tatuatore umano.
```

- [ ] **Step 4: Eseguire l'intera suite**

Run: `uv run pytest -q`
Expected: PASS (tutti i test verdi; gli SVG possono risultare `skipped` senza l'extra `[export]`).

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration.py README.md
git commit -m "test: integrazione end-to-end offline + README quickstart"
```

---

## Self-Review (eseguita contro lo spec)

**1. Copertura dello spec §13 (scope MVP v1):**

| Requisito MVP (§13) | Task |
|---|---|
| Ingest: UploadAdapter | Task 8 |
| Ingest: PersonalSiteAdapter | Task 9 |
| Ingest: InstagramAdapter (harvest opt-in) | Task 10 |
| Libreria + dedup pHash + provenance | Task 5, 6 |
| Tagging: ClipTagger (default) + vocabolario seed | Task 11, 12 |
| Tagging: VisionLLMTagger opzionale | Task 13 |
| Web UI: galleria filtrabile + preferiti + ricerca tema + moodboard | Task 19, 20 |
| Ideazione: reference/tema → Brief | Task 14 |
| Engine: Modo E completo | Task 16 |
| Engine: Modo A (fal.ai) dietro key opt-in | Task 17 |
| Export: 300 DPI + SVG (nota centerline) | Task 18 |
| Guardie §11 visibili in UI | Task 19 (attribuzione+CTA+do_not_mimic), 20 (label), 18 (watermark) |
| Test | ogni task + Task 23 (integrazione) |

**Nota centerline (spec §6/§14):** l'MVP usa `vtracer` (doppio-tratto/colore) per l'SVG. Il tratto singolo via `autotrace -centerline` è un **affinamento post-v1** (richiede un binario esterno): documentato qui come debito noto, non nello scope v1.

**2. Placeholder scan:** nessun "TBD/TODO/handle edge cases/similar to Task N"; ogni step di codice mostra il codice reale. ✅

**3. Coerenza dei tipi:** `Brief`, `DesignResult`, `EngineCapabilities`, `RawItem`, `SourceRef` definiti in Task 3 e usati con la stessa firma ovunque; `build_prompt` definito in Task 16 e riusato in Task 17 (DRY); `Store` espone gli stessi metodi consumati da Library/App/CLI; registry `register`/`get_adapter` (ingest) e `register_engine`/`get_engine` (engine) coerenti tra definizione e uso. ✅

**Fuori scope MVP (rimandato, spec §13 "Dopo"):** Modo B locale GPU, Modo C avanzato (ControlNet/IP-adapter per vibe-di-X full), adapter Pinterest/Tattoodo, refine avanzato (inpainting/storico ricco), embedding semantico dei temi su larga scala (qui il match tema è testuale `LIKE` sui tag `subject`).

---

## Execution Handoff

**Piano completo e salvato in `docs/plans/2026-07-23-ink-scout-mvp.md`. Due opzioni di esecuzione:**

**1. Subagent-Driven (consigliata)** — un subagente fresco per ogni task, review tra un task e l'altro, iterazione rapida. (REQUIRED SUB-SKILL: superpowers:subagent-driven-development)

**2. Inline Execution** — esecuzione dei task in questa sessione con executing-plans, a blocchi con checkpoint di review. (REQUIRED SUB-SKILL: superpowers:executing-plans)

**Quale approccio?**

