from inkscout.engine.brief_engine import BriefEngine, build_prompt, NEGATIVE_PROMPT
from inkscout.core.models import Brief
from inkscout.store.db import Store


def test_build_prompt_puts_style_first():
    b = Brief(
        theme_text="Twin Peaks",
        styles=["blackwork", "geometric"],
        line_treatment="bold black outlines",
        placement="forearm",
    )
    p = build_prompt(b)
    assert p.startswith("blackwork geometric")
    assert "Twin Peaks" in p
    assert "bold black outlines" in p
    assert "tattoo stencil reference, white background, clear linework, no fuzzy edges" in p


def test_generate_offline_with_moodboard(tmp_path):
    store = Store(tmp_path / "t.db")
    src = store.add_source("upload", "local")
    img = store.add_image("images/owl.jpg", 1, 10, 10, None, src, "u://owl", "ref", "t")
    eng = BriefEngine(store=store)
    assert eng.capabilities.offline is True and eng.capabilities.needs_key is False
    res = eng.generate(Brief(theme_text="owl", styles=["blackwork"], reference_image_ids=[img]))
    assert res.kind == "prompt" and res.engine == "E"
    assert res.moodboard_paths == ("images/owl.jpg",)
    assert res.meta["negative_prompt"] == NEGATIVE_PROMPT
