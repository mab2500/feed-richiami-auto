"""Test per Modo A (HostedAPIEngine, fal.ai opt-in): key dal Keychain, model-id/prezzo
sempre dalla config, poster/downloader iniettabili — niente rete reale nei test."""

from pathlib import Path

import pytest

from inkscout.config import load_config
from inkscout.core.models import Brief
from inkscout.engine.base import EngineKeyMissing
from inkscout.engine.hosted import HostedAPIEngine


def _cfg(tmp_path, **env):
    values = {
        "INK_SCOUT_DATA_DIR": str(tmp_path),
        "INK_SCOUT_FAL_MODEL_ID": "fal-ai/flux/schnell",
    }
    values.update(env)
    return load_config(values)


def test_nome_file_stabile_e_deduplicante(tmp_path):
    """Prima il nome veniva da `hash()` di Python, randomizzato a ogni processo: la stessa
    immagine finiva in file diversi a ogni run. Ora è sha256 del contenuto."""
    def eng(url):
        return HostedAPIEngine(
            _cfg(tmp_path), key_getter=lambda *_: "K",
            poster=lambda u, p, k: {"images": [{"url": url}]},
            downloader=lambda u: b"PNGDATA-IDENTICO")

    b = Brief(theme_text="owl", styles=["blackwork"])
    # URL diversi (fal.ai firma ogni URL) ma stesso contenuto → stesso file
    primo = eng("https://cdn/a.png?sig=1").generate(b).raster_path
    secondo = eng("https://cdn/a.png?sig=2").generate(b).raster_path
    assert primo == secondo
    assert "gen-" in Path(primo).name and Path(primo).suffix == ".png"

    diverso = HostedAPIEngine(
        _cfg(tmp_path), key_getter=lambda *_: "K",
        poster=lambda u, p, k: {"images": [{"url": "https://cdn/b.png"}]},
        downloader=lambda u: b"ALTRO-CONTENUTO").generate(b).raster_path
    assert diverso != primo


def test_missing_key_raises(tmp_path):
    eng = HostedAPIEngine(_cfg(tmp_path), key_getter=lambda *_: None)
    with pytest.raises(EngineKeyMissing):
        eng.generate(Brief(theme_text="owl", styles=["blackwork"]))


def test_missing_key_message_explains_how_to_set_it(tmp_path):
    eng = HostedAPIEngine(_cfg(tmp_path), key_getter=lambda *_: None)
    with pytest.raises(EngineKeyMissing) as exc_info:
        eng.generate(Brief(theme_text="owl"))
    message = str(exc_info.value)
    assert "inkscout-fal-key" in message
    assert "security" in message.lower()  # spiega il comando per popolare il Keychain


def test_capabilities_are_config_driven_and_coherent(tmp_path):
    cfg = _cfg(tmp_path, INK_SCOUT_FAL_PRICE_PER_IMG="0.042")
    eng = HostedAPIEngine(cfg, key_getter=lambda *_: "SECRET")
    assert eng.mode == "A"
    assert eng.capabilities.needs_key is True
    assert eng.capabilities.offline is False
    assert eng.capabilities.needs_gpu is False
    assert eng.capabilities.cost_per_img == 0.042  # dalla config, mai hardcoded


def test_generate_uses_config_model_and_saves(tmp_path):
    cfg = _cfg(tmp_path)
    seen = {}

    def poster(url, payload, key):
        seen.update(payload)
        seen["key"] = key
        seen["url"] = url
        return {"images": [{"url": "https://cdn/out.png"}]}

    eng = HostedAPIEngine(
        cfg,
        key_getter=lambda *_: "SECRET",
        poster=poster,
        downloader=lambda u: b"PNGDATA",
    )
    res = eng.generate(
        Brief(theme_text="owl", styles=["blackwork"], line_treatment="bold black outlines")
    )
    assert res.kind == "raster"
    assert res.engine == "A"
    assert seen["model"] == "fal-ai/flux/schnell"  # model-id dalla config
    assert seen["prompt"].startswith("blackwork")  # prompt riusa build_prompt (DRY)
    assert seen["key"] == "SECRET"
    assert Path(res.raster_path).read_bytes() == b"PNGDATA"
    assert Path(res.raster_path).parent == cfg.images_dir


def test_generate_key_not_leaked_into_payload_or_result(tmp_path):
    def poster(url, payload, key):
        assert "key" not in payload
        assert "SECRET-KEY" not in str(payload)
        return {"images": [{"url": "https://cdn/out.png"}]}

    eng = HostedAPIEngine(
        _cfg(tmp_path),
        key_getter=lambda *_: "SECRET-KEY",
        poster=poster,
        downloader=lambda u: b"PNGDATA",
    )
    res = eng.generate(Brief(theme_text="owl", styles=["blackwork"]))
    assert "SECRET-KEY" not in repr(res)
    assert "SECRET-KEY" not in str(res.meta)
