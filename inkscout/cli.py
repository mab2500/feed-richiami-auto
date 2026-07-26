"""CLI ink-scout: ingest / sync-styles / serve."""

from __future__ import annotations

import argparse

from inkscout.config import ensure_dirs, load_config
from inkscout.core.models import SourceRef
from inkscout.ingest import instagram, site, upload, whatsapp  # noqa: F401 — registra gli adapter
from inkscout.ingest.base import get_adapter
from inkscout.library.library import Library
from inkscout.store.db import Store
from inkscout.tagging.clip import SOGLIA_DEFAULT
from inkscout.tagging.testo import TestoTagger
from inkscout.tagging.vocab import sync_styles


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ink-scout")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest")
    pi.add_argument("--kind", required=True,
                    choices=["upload", "site", "instagram", "whatsapp"])
    pi.add_argument("--ref", required=True)
    pi.add_argument("--optin", action="store_true", help="consenso harvest personale (IG)")
    pi.add_argument("--chat", default="", help="nome della chat (solo --kind whatsapp)")
    pt = sub.add_parser("tag", help="tagga la libreria con CLIP (visivo, offline)")
    pt.add_argument("--soglia", type=float, default=SOGLIA_DEFAULT)
    pt.add_argument("--limit", type=int, default=0, help="0 = tutte")
    pt.add_argument("--rifai", action="store_true", help="ritagga anche chi ha già uno stile")
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
        src = SourceRef(kind=args.kind, ref=args.ref, harvest_optin=args.optin,
                        notes=getattr(args, "chat", ""))
        # la sorgente si registra una volta: senza, `image.source_id` resta NULL e la
        # provenance a DB (spec §11.7) è monca
        source_id = store.add_source(args.kind, args.ref, args.optin, src.notes)
        # tagger dal testo: gratis e senza modelli, sfrutta ciò che l'utente ha già scritto
        # accanto all'immagine (didascalie WhatsApp). Se non c'è testo, non produce nulla.
        tagger = TestoTagger(seed_path=cfg.styles_seed)
        added = dup = con_artista = con_tag = 0
        for raw in adapter.fetch(src):
            # ⚠️ l'artista va creato QUI, altrimenti `artist_handle` si perde e la CTA
            # «Commissiona questo artista» (guardia §11.4) non si attiva mai nel flusso reale
            artist_id = store.upsert_artist(
                raw.artist_handle, source_id=source_id,
                provenance_url=(f"https://instagram.com/{raw.artist_handle.lstrip('@')}"
                                if raw.artist_handle else ""))
            res = lib.add(raw, artist_id=artist_id, source_id=source_id)
            dup += int(res.is_duplicate)
            added += int(not res.is_duplicate)
            con_artista += int(bool(artist_id) and not res.is_duplicate)
            if not res.is_duplicate:
                tags = tagger.tag_testo(raw.meta.get("contesto", ""))
                for t in tags:
                    if t.axis == "style":
                        continue
                    store.add_image_tag(res.image_id, t.axis, t.value, t.confidence, "testo")
                for nome in tagger.stili_nel_testo(raw.meta.get("contesto", "")):
                    sid = store.style_id_by_name(nome)
                    if sid is not None:
                        store.add_image_style(res.image_id, sid)
                con_tag += int(bool(tags))
        print(f"ingest {args.kind}: {added} nuove, {dup} duplicati, "
              f"{con_artista} con artista attribuito, {con_tag} taggate dal testo")
        return 0

    if args.cmd == "tag":
        # CLIP sulle immagini che non hanno ancora uno stile: è il tagging VISIVO, quello
        # che serve qui (misurato: solo il 29% delle foto in chat ha del testo accanto).
        from PIL import Image

        from inkscout.tagging.clip import ClipTagger
        from inkscout.tagging.vocab import style_names

        vocab = style_names(cfg.styles_seed)
        tagger = ClipTagger(vocab=vocab, threshold=args.soglia)
        candidate = [r for r in store.list_images()
                     if args.rifai or not store.styles_of_image(r["id"])]
        candidate = candidate[: args.limit] if args.limit else candidate
        print(f"tagging CLIP di {len(candidate)} immagini · soglia {args.soglia} "
              f"· {len(vocab)} stili (la prima richiede il caricamento del modello)")
        taggate = 0
        for n, r in enumerate(candidate, 1):
            try:
                with Image.open(r["path"]) as im:
                    tags = tagger.tag_image(im.convert("RGB"))
            except (OSError, ValueError) as e:
                print(f"  salto #{r['id']}: {e}")
                continue
            for t in tags:
                sid = store.style_id_by_name(t.value)
                if sid is not None:
                    store.add_image_style(r["id"], sid)
                    store.add_image_tag(r["id"], "style", t.value, t.confidence, "clip")
            taggate += int(bool(tags))
            if n % 25 == 0:
                print(f"  …{n}/{len(candidate)}")
        print(f"stile assegnato a {taggate}/{len(candidate)} immagini")
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
