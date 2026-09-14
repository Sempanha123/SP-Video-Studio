from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .constants import DEFAULT_LOG_FILE


def configure_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sp_video_studio")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = RotatingFileHandler(log_dir / DEFAULT_LOG_FILE,maxBytes=2_000_000,backupCount=5,encoding="utf-8")
    handler.setFormatter(formatter); logger.addHandler(handler)
    if sys.stderr is not None:
        console = logging.StreamHandler(); console.setFormatter(formatter); logger.addHandler(console)
    return logger
