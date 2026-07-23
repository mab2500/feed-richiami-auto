import json

from inkscout.core.models import (
    Axis,
    SOURCE_KINDS,
    RESULT_KINDS,
    SourceRef,
    Brief,
    EngineCapabilities,
    DesignResult,
)


def test_axis_are_axes_not_values():
    assert Axis.SUBJECT.value == "subject"
    assert set(a.value for a in Axis) == {"subject", "placement", "color_mode", "density", "form"}


def test_source_and_result_kinds():
    assert "upload" in SOURCE_KINDS and "instagram" in SOURCE_KINDS
    assert set(RESULT_KINDS) == {"moodboard", "prompt", "raster", "svg"}


def test_source_ref_defaults():
    s = SourceRef(kind="site", ref="https://example.com")
    assert s.harvest_optin is False and s.notes == ""


def test_brief_json_roundtrip():
    b = Brief(
        theme_text="Twin Peaks",
        styles=["blackwork", "geometric"],
        form="round",
        color_mode="black-only",
        placement="forearm",
        size="medium",
        line_treatment="bold black outlines",
        reference_image_ids=[3, 7],
    )
    raw = b.to_json()
    assert json.loads(raw)["theme_text"] == "Twin Peaks"
    assert Brief.from_json(raw) == b


def test_engine_capabilities_and_result():
    caps = EngineCapabilities(
        needs_gpu=False, needs_key=False, cost_per_img=0.0, watermarks=False, offline=True
    )
    assert caps.offline is True
    r = DesignResult(kind="prompt", engine="brief", prompt="blackwork geometric ...")
    assert r.kind in RESULT_KINDS and r.raster_path is None
