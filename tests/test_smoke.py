import inkscout


def test_package_importable_and_versioned():
    assert isinstance(inkscout.__version__, str)
    assert inkscout.__version__ != ""
