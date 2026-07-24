"""Integrazione end-to-end offline: upload -> libreria -> tag -> brief -> Modo E -> export.

Nessuna rete, nessun extra pesante (CLIP/vtracer/CDP). Prova che il flusso
camminante dell'MVP (Fase 4, spec) funziona composto, non solo modulo per modulo.
"""

from pathlib import Path

from PIL import Image

from inkscout.core.models import SourceRef
from inkscout.engine.brief_engine import BriefEngine
from inkscout.export.stencil import to_stencil_png
from inkscout.ideation.brief import build_brief
from inkscout.ingest.upload import UploadAdapter
from inkscout.library.library import Library
from inkscout.store.db import Store


def test_flusso_camminante_offline(tmp_path):
    # 1. ingest upload di 2 immagini distinte
    src_dir = tmp_path / "in"
    src_dir.mkdir()
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
        # round(): il chunk pHYs del PNG salva pixel-per-metro come intero, quindi
        # 300 dpi fa un giro di boa impreciso (300 -> 299.9994) anche con PIL puro,
        # indipendentemente da inkscout: confronto exact-== non e' soddisfacibile.
        assert round(im.info.get("dpi", (0, 0))[0]) == 300
