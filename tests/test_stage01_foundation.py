"""Stage 1 acceptance tests: settings load, bad settings fail loudly, logging works."""
import logging

import pytest

from core.config import PROJECT_ROOT, ConfigError, load_config
from core.logging_setup import setup_logging


def test_settings_load():
    config = load_config()
    assert config["exchange"] == "NSE"
    assert config["project"]["architecture_version"] == "1.11"


def test_missing_settings_file_fails_loudly(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_incomplete_settings_file_fails_loudly(tmp_path):
    bad = tmp_path / "settings.yaml"
    bad.write_text("project:\n  name: test\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_logging_writes_to_file(tmp_path):
    config = load_config()
    log_file = tmp_path / "test.log"
    config["logging"]["file"] = str(log_file)
    logger = setup_logging(config)
    logger.info("stage 1 logging check")
    logging.shutdown()
    assert "stage 1 logging check" in log_file.read_text(encoding="utf-8")


def test_architecture_folders_exist():
    # Section 39 of the architecture: these folders must exist.
    for folder in ["src/ingestion", "src/data_quality", "src/provenance",
                   "src/universe", "src/features", "src/targets", "src/models",
                   "src/calibration", "src/validation", "src/experiments",
                   "src/ledger", "src/regimes", "src/abstention", "src/research",
                   "tests", "config", "docs"]:
        assert (PROJECT_ROOT / folder).is_dir(), f"missing folder: {folder}"
