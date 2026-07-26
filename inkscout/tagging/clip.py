"""ClipTagger: CLIP zero-shot sul vocabolario stili. Offline, gratis, batch.
Il modello vero è import LAZY (extra [tag]); l'encoder è iniettabile per i test."""

from __future__ import annotations

from typing import Callable

from inkscout.tagging.base import Tag


# Soglia TARATA su 40 reference vere di Matteo (25/07), dopo il fix di `logit_scale`:
# distribuzione del primo stile → min 0,252 · mediana 0,428 · max 0,914.
# Copertura misurata: 0,20 → 100% · **0,30 → 87%** · 0,40 → 62% · 0,50 → 32%.
# 0,30 tiene fuori i casi in cui il modello è quasi indeciso senza svuotare la libreria.
# ⚠️ È tarata sulla COPERTURA, non sulla precisione: che il tag sia *giusto* va guardato a
# occhio su un campione — il numero non lo dimostra.
SOGLIA_DEFAULT = 0.30


class ClipTagger:
    def __init__(self, vocab: list[str], encoder: Callable | None = None,
                 threshold: float = SOGLIA_DEFAULT):
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
        # ⚠️ `logit_scale` NON è un dettaglio: senza, la softmax lavora su similarità
        # coseno (~0,2-0,3) tutte vicine e restituisce una distribuzione **quasi
        # uniforme**. MISURATO su 40 reference vere di Matteo: min 0,101 · mediana 0,103
        # · max 0,105 — con 10 stili l'uniforme è 0,100, cioè il tagger non discriminava
        # NULLA e nessun tag passava mai la soglia, qualunque essa fosse. Il guasto è muto:
        # il modello gira e i numeri escono. CLIP è addestrato con questa temperatura
        # (exp(logit_scale) ≈ 100): va applicata prima della softmax.
        logits = model.logit_scale.exp() * (img_f @ txt_f.T)
        probs = logits.softmax(dim=-1).squeeze(0).tolist()
    return dict(zip(labels, probs))
