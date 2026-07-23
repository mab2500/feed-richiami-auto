from inkscout.tagging.base import Tag
from inkscout.tagging.clip import ClipTagger


def fake_encoder(image, labels):
    # punteggi deterministici: 'blackwork' vince, 'realism' sotto soglia
    base = {lbl: 0.05 for lbl in labels}
    base["blackwork"] = 0.7
    base["geometric"] = 0.4
    return base


def test_cliptagger_maps_above_threshold():
    tagger = ClipTagger(
        vocab=["blackwork", "geometric", "realism"], encoder=fake_encoder, threshold=0.2
    )
    tags = tagger.tag_image(image=object())
    values = {t.value for t in tags}
    assert values == {"blackwork", "geometric"}
    assert all(t.axis == "style" for t in tags)
    assert any(isinstance(t, Tag) and t.confidence == 0.7 for t in tags)
