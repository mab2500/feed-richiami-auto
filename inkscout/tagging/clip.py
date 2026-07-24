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
        return [
            Tag(axis="style", value=lbl, confidence=float(sc))
            for lbl, sc in scores.items()
            if sc >= self.threshold
        ]


def _clip_encode(image, labels):  # pragma: no cover — richiede extra [tag]
    import open_clip
    import torch

    # "-quickgelu": i pesi 'openai' usano QuickGELU; il config liscio degrada
    # l'accuratezza in silenzio (UserWarning di open_clip >= 2.24, misurato qui).
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32-quickgelu", pretrained="openai"
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32-quickgelu")
    with torch.no_grad():
        img_t = preprocess(image).unsqueeze(0)
        text_t = tokenizer([f"a {lbl} tattoo" for lbl in labels])
        img_f = model.encode_image(img_t)
        txt_f = model.encode_text(text_t)
        img_f /= img_f.norm(dim=-1, keepdim=True)
        txt_f /= txt_f.norm(dim=-1, keepdim=True)
        probs = (img_f @ txt_f.T).softmax(dim=-1).squeeze(0).tolist()
    return dict(zip(labels, probs))
