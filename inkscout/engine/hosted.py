"""Modo A (opt-in): backend cloud astratto, default fal.ai. Model-id e prezzo dalla config,
key dal Keychain. `poster`/`downloader` iniettabili per i test; reali via urllib (lazy)."""

from __future__ import annotations

from inkscout.config import Config, keychain_get
from inkscout.core.models import Brief, DesignResult, EngineCapabilities
from inkscout.engine.base import EngineKeyMissing, register_engine
from inkscout.engine.brief_engine import NEGATIVE_PROMPT, build_prompt

_FAL_URL_TMPL = "https://fal.run/{model}"
_KEYCHAIN_ACCOUNT = "inkscout-fal-key"


@register_engine("A")
class HostedAPIEngine:
    mode = "A"

    def __init__(
        self,
        config: Config,
        key_getter=keychain_get,
        poster=None,
        downloader=None,
    ):
        self.config = config
        self.key_getter = key_getter
        self._poster = poster
        self._downloader = downloader
        self.capabilities = EngineCapabilities(
            needs_gpu=False,
            needs_key=True,
            cost_per_img=config.fal_price_per_img,
            watermarks=False,
            offline=False,
        )

    def generate(self, brief: Brief) -> DesignResult:
        key = self.key_getter(_KEYCHAIN_ACCOUNT)
        if not key:
            raise EngineKeyMissing(
                "manca la API key di fal.ai nel Keychain macOS. Aggiungila con: "
                f"security add-generic-password -a {_KEYCHAIN_ACCOUNT} -s ink-scout "
                "-w '<LA-TUA-API-KEY>' "
                f"(voce '{_KEYCHAIN_ACCOUNT}')."
            )
        payload = {
            "model": self.config.fal_model_id,
            "prompt": build_prompt(brief),
            "negative_prompt": NEGATIVE_PROMPT,
        }
        url = _FAL_URL_TMPL.format(model=self.config.fal_model_id)
        resp = (self._poster or _http_post)(url, payload, key)
        image_url = resp["images"][0]["url"]
        data = (self._downloader or _http_download)(image_url)
        self.config.images_dir.mkdir(parents=True, exist_ok=True)
        dest = self.config.images_dir / f"gen-{abs(hash(image_url)) & 0xFFFFFFFF:08x}.png"
        dest.write_bytes(data)
        return DesignResult(
            kind="raster",
            engine=self.mode,
            prompt=payload["prompt"],
            raster_path=str(dest),
            meta={"source_url": image_url},
        )


def _http_post(url: str, payload: dict, key: str) -> dict:  # pragma: no cover — rete
    import json
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _http_download(url: str) -> bytes:  # pragma: no cover — rete
    import urllib.request

    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()
