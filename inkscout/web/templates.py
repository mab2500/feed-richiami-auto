"""Rendering HTML in stdlib. Le guardie §11 (attribuzione, CTA, label) sono nel markup."""

from __future__ import annotations

from html import escape

_BANNER = (
    "ink-scout produce <b>reference privati</b> per poi "
    "<b>commissionare un tatuatore umano</b> — non tatuaggi finiti da stampare."
)


def page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title>"
        "<style>body{font-family:system-ui;margin:1.5rem;max-width:960px}"
        ".card{display:inline-block;width:180px;vertical-align:top;margin:.4rem;"
        "border:1px solid #ddd;border-radius:8px;padding:.4rem;font-size:.8rem}"
        ".banner{background:#fff8e1;border:1px solid #f0d000;padding:.6rem;border-radius:8px}"
        "img{max-width:100%;border-radius:4px}.cta{color:#0a58ca}</style></head><body>"
        f"<div class='banner'>{_BANNER}</div><h1>{escape(title)}</h1>{body}</body></html>"
    )


def image_card(row: dict) -> str:
    handle = escape(row.get("handle") or "")
    src = escape(row.get("source_url") or "")
    attrib = f"fonte: <a href='{src}'>{src[:40]}</a>" if src else ""
    cta = (
        f"<div class='cta'>@{handle} — <a href='{src}'>Commissiona questo artista</a></div>"
        if handle
        else ""
    )
    fav = "★" if row.get("favorite") else "☆"
    return (
        f"<div class='card'><img src='/image/{row['id']}'>"
        f"<div>{attrib}</div>{cta}"
        "<form method='post' action='/favorite'>"
        f"<input type='hidden' name='id' value='{row['id']}'>"
        f"<button>{fav}</button></form></div>"
    )


def gallery(rows: list[dict], filters: dict) -> str:
    q = escape(filters.get("theme", "") or "")
    form = (
        f"<form method='get' action='/'>tema: <input name='theme' value='{q}'>"
        "<button>filtra</button></form>"
    )
    cards = "".join(image_card(r) for r in rows) or "<p>Libreria vuota.</p>"
    return form + f"<p>{len(rows)} immagini</p>" + cards


def studio_form(modes: list[str], styles: list[str]) -> str:
    opts = "".join(f"<option value='{m}'>{m}</option>" for m in modes)
    style_hint = ", ".join(styles[:8])
    return (
        "<h2>Studio</h2><form method='post' action='/generate'>"
        f"modo: <select name='mode'>{opts}</select><br>"
        "tema (testo libero): <input name='theme' placeholder='es. Twin Peaks'><br>"
        f"stili (separati da virgola): <input name='styles' placeholder='{style_hint}'><br>"
        "forma: <input name='form' placeholder='round'><br>"
        "<button>Genera</button></form>"
    )


def result_view(result, reference_ids: list[int]) -> str:
    mood = "".join(f"<img src='/image/{i}' width='120'>" for i in reference_ids)
    neg = escape(result.meta.get("negative_prompt", ""))
    return (
        "<h2>Risultato</h2>"
        "<p style='background:#e8f5e9;padding:.4rem'>AI-generated / reference only — "
        "fallo ridisegnare a mano dal tuo tatuatore.</p>"
        f"<h3>Prompt</h3><pre>{escape(result.prompt)}</pre>"
        f"<h3>Negative</h3><pre>{neg}</pre>"
        f"<h3>Moodboard</h3>{mood or '<i>nessuna reference in libreria</i>'}"
    )
