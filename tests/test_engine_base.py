import pytest

from inkscout.engine import base
from inkscout.core.models import DesignResult, EngineCapabilities


@base.register_engine("fake")
class FakeEngine:
    mode = "fake"
    capabilities = EngineCapabilities(False, False, 0.0, False, True)

    def __init__(self, **kw):
        self.kw = kw

    def generate(self, brief):
        return DesignResult(kind="prompt", engine="fake", prompt="ok")


def test_register_and_get():
    eng = base.get_engine("fake", foo=1)
    assert eng.kw["foo"] == 1
    assert eng.generate(None).prompt == "ok"
    assert "fake" in base.available_modes()


def test_unknown_mode_raises():
    with pytest.raises(KeyError):
        base.get_engine("nope")
