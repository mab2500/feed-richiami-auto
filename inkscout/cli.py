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
