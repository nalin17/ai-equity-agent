"""Project-wide logging: messages go to the screen and to one log file."""
import logging

from core.config import PROJECT_ROOT, load_config

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(config=None):
    config = config or load_config()
    log_settings = config["logging"]
    log_file = PROJECT_ROOT / log_settings["file"]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=log_settings["level"],
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )
    return logging.getLogger("equity_agent")
