from inkscout.tagging.vision import VisionLLMTagger


def fake_describe(image_bytes):
    return {
        "subject": ["owl", "forest"],
        "form": "round",
        "color_mode": "black-only",
        "density": "high",
    }


def test_vision_tagger_normalizes_axes():
    tagger = VisionLLMTagger(describe=fake_describe)
    tags = tagger.tag_image(b"IMG")
    axes = {(t.axis, t.value) for t in tags}
    assert ("subject", "owl") in axes and ("subject", "forest") in axes
    assert ("form", "round") in axes
    assert ("color_mode", "black-only") in axes
    assert ("density", "high") in axes
