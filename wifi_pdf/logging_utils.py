from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .utils import ensure_directory


def configure_logging(log_dir: Path, log_level: str = "INFO") -> logging.Logger:
    ensure_directory(log_dir)
    logger = logging.getLogger("wifi_pdf")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if logger.handlers:
        for handler in logger.handlers:
            handler.setLevel(level)
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_dir / "wifi_pdf.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
