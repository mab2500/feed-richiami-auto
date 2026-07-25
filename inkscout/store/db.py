"""Persistenza SQLite (WAL). Schema data-driven: gli assi sono colonne/tabelle,
i valori (stili/temi/artisti) sono righe, mai enum nel codice."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_U64 = 1 << 64
_I64_MAX = (1 << 63) - 1


def _phash_to_sql(value: int | None) -> int | None:
    """dhash() produce un intero NON firmato a 64 bit; sqlite3 vincola i bind
    al range firmato ([-2**63, 2**63-1]) e oltre solleva OverflowError.
    Rimappa preservando il bit-pattern (complemento a due). L'inverso è
    _phash_from_sql: l'API dello Store parla SEMPRE unsigned, la codifica
    firmata resta un dettaglio interno della colonna."""
    if value is None:
        return None
    return value - _U64 if value > _I64_MAX else value


def _phash_from_sql(value: int | None) -> int | None:
    if value is None:
        return None
    return value & (_U64 - 1)


def _row_with_unsigned_phash(row: dict) -> dict:
    if "phash" in row:
        row["phash"] = _phash_from_sql(row["phash"])
    return row


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
            (kind, ref, int(harvest_optin), notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_artist(
        self, name, handle="", city="", source_id=None, provenance_url="", do_not_mimic=False
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO artist(name, handle, city, source_id, provenance_url, do_not_mimic) "
            "VALUES (?,?,?,?,?,?)",
            (name, handle, city, source_id, provenance_url, int(do_not_mimic)),
        )
        self.conn.commit()
        return cur.lastrowid

    def artist_id_by_handle(self, handle: str) -> int | None:
        if not handle:
            return None
        row = self.conn.execute("SELECT id FROM artist WHERE handle=?", (handle,)).fetchone()
        return row["id"] if row else None

    def upsert_artist(self, handle: str, name: str = "", source_id=None,
                      provenance_url: str = "") -> int | None:
        """Un artista per handle. Senza questo ogni immagine ne creerebbe uno nuovo e
        l'attribuzione (guardia §11) mostrerebbe lo stesso tatuatore N volte."""
        if not handle:
            return None
        esistente = self.artist_id_by_handle(handle)
        if esistente is not None:
            return esistente
        return self.add_artist(name=name or handle.lstrip("@"), handle=handle,
                               source_id=source_id, provenance_url=provenance_url)

    # --- image ---
    def add_image(
        self, path, phash, width, height, artist_id, source_id, source_url, license_note, fetched_at
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO image(path, phash, width, height, artist_id, source_id, "
            "source_url, license_note, fetched_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                path,
                _phash_to_sql(phash),
                width,
                height,
                artist_id,
                source_id,
                source_url,
                license_note,
                fetched_at,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_image(self, image_id) -> dict | None:
        row = self.conn.execute("SELECT * FROM image WHERE id=?", (image_id,)).fetchone()
        return _row_with_unsigned_phash(dict(row)) if row else None

    def all_phashes(self) -> list[tuple[int, int]]:
        return [
            (r["id"], _phash_from_sql(r["phash"]))
            for r in self.conn.execute("SELECT id, phash FROM image WHERE phash IS NOT NULL")
        ]

    def set_favorite(self, image_id, value) -> None:
        self.conn.execute("UPDATE image SET favorite=? WHERE id=?", (int(value), image_id))
        self.conn.commit()

    def set_hidden(self, image_id, value) -> None:
        self.conn.execute("UPDATE image SET hidden=? WHERE id=?", (int(value), image_id))
        self.conn.commit()

    def list_images(
        self, styles=None, form=None, color_mode=None, theme=None, include_hidden=False
    ) -> list[dict]:
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
                where.append(
                    f"EXISTS (SELECT 1 FROM image_tag t WHERE t.image_id=i.id "
                    f"AND t.axis='{axis}' AND t.value=?)"
                )
                params.append(val)
        if theme:
            where.append(
                "EXISTS (SELECT 1 FROM image_tag t WHERE t.image_id=i.id "
                "AND t.axis='subject' AND t.value LIKE ?)"
            )
            params.append(f"%{theme}%")
        sql.extend(joins)
        if where:
            sql.append("WHERE " + " AND ".join(where))
        sql.append("ORDER BY i.favorite DESC, i.id DESC")
        return [_row_with_unsigned_phash(dict(r)) for r in self.conn.execute(" ".join(sql), params)]

    # --- style / tags ---
    def upsert_style(
        self,
        name,
        aliases=(),
        parent_style_id=None,
        formal_attributes=None,
        description="",
        is_emerging=False,
    ) -> int:
        existing = self.style_id_by_name(name)
        if existing is not None:
            return existing
        cur = self.conn.execute(
            "INSERT INTO style(name, aliases, parent_style_id, formal_attributes, "
            "description, is_emerging) VALUES (?,?,?,?,?,?)",
            (
                name,
                json.dumps(list(aliases)),
                parent_style_id,
                json.dumps(formal_attributes or {}),
                description,
                int(is_emerging),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def style_id_by_name(self, name) -> int | None:
        row = self.conn.execute("SELECT id FROM style WHERE name=?", (name,)).fetchone()
        return row["id"] if row else None

    def add_image_style(self, image_id, style_id) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO image_style(image_id, style_id) VALUES (?,?)",
            (image_id, style_id),
        )
        self.conn.commit()

    def add_image_tag(self, image_id, axis, value, confidence, tagger) -> None:
        self.conn.execute(
            "INSERT INTO image_tag(image_id, axis, value, confidence, tagger) VALUES (?,?,?,?,?)",
            (image_id, axis, value, confidence, tagger),
        )
        self.conn.commit()

    def image_tags(self, image_id) -> list[dict]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT axis, value, confidence, tagger FROM image_tag WHERE image_id=?",
                (image_id,),
            )
        ]

    # --- design ---
    def add_design(self, title, brief_json) -> int:
        cur = self.conn.execute(
            "INSERT INTO design(title, brief) VALUES (?,?)", (title, brief_json)
        )
        self.conn.commit()
        return cur.lastrowid

    def add_design_version(
        self, design_id, parent_version_id, brief_json, engine, result_kind, asset_path
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO design_version(design_id, parent_version_id, brief, engine, "
            "result_kind, asset_path) VALUES (?,?,?,?,?,?)",
            (design_id, parent_version_id, brief_json, engine, result_kind, asset_path),
        )
        self.conn.commit()
        return cur.lastrowid

    def close(self) -> None:
        self.conn.close()
