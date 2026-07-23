from inkscout.config import load_config, keychain_get


def test_load_config_defaults(tmp_path):
    cfg = load_config({"INK_SCOUT_DATA_DIR": str(tmp_path)})
    assert cfg.data_dir == tmp_path
    assert cfg.db_path == tmp_path / "inkscout.db"
    assert cfg.images_dir == tmp_path / "images"
    assert cfg.cache_dir == tmp_path / "cache"
    # model-id e prezzo sono config-driven, mai nel sorgente degli engine
    assert cfg.fal_model_id  # ha un default non vuoto
    assert cfg.fal_price_per_img >= 0


def test_load_config_env_overrides(tmp_path):
    cfg = load_config(
        {
            "INK_SCOUT_DATA_DIR": str(tmp_path),
            "INK_SCOUT_FAL_MODEL_ID": "fal-ai/flux/dev",
            "INK_SCOUT_FAL_PRICE_PER_IMG": "0.025",
        }
    )
    assert cfg.fal_model_id == "fal-ai/flux/dev"
    assert cfg.fal_price_per_img == 0.025


def test_keychain_get_missing_returns_none(monkeypatch):
    def fake_run(*a, **k):
        raise __import__("subprocess").CalledProcessError(1, "security")

    monkeypatch.setattr("inkscout.config.subprocess.run", fake_run)
    assert keychain_get("inkscout-fal-key") is None
