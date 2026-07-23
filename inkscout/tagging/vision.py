"""VisionLLMTagger: Vision LLM (Claude) per descrizioni sfumate / temi liberi.
`describe` è iniettabile per i test; il client reale è lazy."""

from __future__ import annotations

from typing import Callable

from inkscout.tagging.base import Tag



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
        model="claude-sonnet-5",
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                    },
                    {
                        "type": "text",
                        "content": "Descrivi questo tatuaggio come JSON con chiavi "
                        "subject (lista), form, color_mode, density. Solo JSON.",
                    },
                ],
            }
        ],
    )
    return json.loads(msg.content[0].text)
