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
            art = (
                self.store.conn.execute(
                    "SELECT handle, do_not_mimic, provenance_url FROM artist WHERE id=?",
                    (r["artist_id"],),
                ).fetchone()
                if r["artist_id"]
                else None
            )
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


def serve(  # pragma: no cover
    store: Store, images_dir: Path, host: str = "127.0.0.1", port: int = 8765
) -> None:
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
            data = (
                resp.body if isinstance(resp.body, (bytes, bytearray)) else str(resp.body).encode()
            )
            self.wfile.write(data)

        def do_GET(self):
            self._run("GET")

        def do_POST(self):
            self._run("POST")

    HTTPServer((host, port), Handler).serve_forever()
