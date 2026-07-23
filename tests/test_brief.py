from inkscout.ideation.brief import build_brief, line_treatment_for, expand_theme
from inkscout.store.db import Store


def test_line_treatment_rules():
    assert line_treatment_for(["fine-line"]) == "single-weight fine lines"
    assert line_treatment_for(["blackwork", "geometric"]) == "bold black outlines"
    assert line_treatment_for(["watercolor"]) == "clean linework"


def test_expand_theme_finds_by_subject(tmp_path):
    store = Store(tmp_path / "t.db")
    src = store.add_source("upload", "local")
    img = store.add_image("images/owl.jpg", 1, 10, 10, None, src, "u://owl", "ref", "t")
    store.add_image_tag(img, "subject", "owl in a dark forest", 1.0, "vision")
    assert expand_theme("owl", store) == [img]
    assert expand_theme("dragon", store) == []


def test_build_brief_autopopulates_references(tmp_path):
    store = Store(tmp_path / "t.db")
    src = store.add_source("upload", "local")
    img = store.add_image("images/owl.jpg", 1, 10, 10, None, src, "u://owl", "ref", "t")
    store.add_image_tag(img, "subject", "owl", 1.0, "vision")
    b = build_brief(theme_text="owl", styles=["blackwork"], form="round", store=store)
    assert b.reference_image_ids == [img]
    assert b.line_treatment == "bold black outlines"
    assert b.form == "round"
