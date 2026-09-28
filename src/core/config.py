"""Load project settings from config/settings.yaml.

Rule from the architecture: fail loudly, never guess. A missing or broken
settings file stops the program with a clear error.
"""
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.yaml"
REQUIRED_SECTIONS = ("project", "exchange", "paths", "logging")


class ConfigError(Exception):
    """Settings are missing or invalid."""


def load_config(path=CONFIG_FILE):
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Settings file not found: {path}")
    with open(path, encoding="utf-8-sig") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ConfigError(f"Settings file is empty or malformed: {path}")
    missing = [s for s in REQUIRED_SECTIONS if s not in config]
    if missing:
        raise ConfigError(f"Settings file is missing sections: {missing}")
    return config
