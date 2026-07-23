"""Configurazione: path + env INK_SCOUT_* + accesso Keychain macOS.

Model-id e prezzi degli engine vivono QUI (config-driven), mai nei sorgenti
degli engine — vincolo globale dello spec.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# Default config-driven per il backend cloud (Modo A). Sovrascrivibili via env.
_DEFAULT_FAL_MODEL_ID = "fal-ai/flux/schnell"
_DEFAULT_FAL_PRICE = 0.003


@dataclass(frozen=True)
class Config:
    data_dir: Path
    db_path: Path
    images_dir: Path
    cache_dir: Path
    styles_seed: Path
    fal_model_id: str
    fal_price_per_img: float


def load_config(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    data_dir = Path(env.get("INK_SCOUT_DATA_DIR", str(Path.home() / ".ink-scout"))).expanduser()
    seed_default = Path(__file__).resolve().parent.parent / "data" / "styles.seed.yaml"
    return Config(
        data_dir=data_dir,
        db_path=data_dir / "inkscout.db",
        images_dir=data_dir / "images",
        cache_dir=data_dir / "cache",
        styles_seed=Path(env.get("INK_SCOUT_STYLES_SEED", str(seed_default))),
        fal_model_id=env.get("INK_SCOUT_FAL_MODEL_ID", _DEFAULT_FAL_MODEL_ID),
        fal_price_per_img=float(env.get("INK_SCOUT_FAL_PRICE_PER_IMG", _DEFAULT_FAL_PRICE)),
    )


def keychain_get(account: str, service: str = "ink-scout") -> str | None:
    """Legge una password dal Keychain macOS. None se assente/errore."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout.strip() or None


def ensure_dirs(cfg: Config) -> None:
    for d in (cfg.data_dir, cfg.images_dir, cfg.cache_dir):
        d.mkdir(parents=True, exist_ok=True)
