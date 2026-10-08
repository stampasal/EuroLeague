# ============================================================
# core/logger.py
# ------------------------------------------------------------
# Setup logging για όλα τα scripts.
#
# Χρήση:
#     from core.logger import get_logger
#     log = get_logger("fetch_injuries", category="fetch")
#     log.info("Ξεκίνησε")
#
# Γράφει σε:  logs/<category>/<name>.log  +  console
# ============================================================

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.paths import LOGS, LOGS_FETCH, LOGS_TRAIN, LOGS_CONVERT, LOGS_SERVER
from core.config import (
    LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT,
    LOG_MAX_BYTES, LOG_BACKUP_COUNT,
)


_CATEGORY_DIRS = {
    "fetch":   LOGS_FETCH,
    "train":   LOGS_TRAIN,
    "convert": LOGS_CONVERT,
    "server":  LOGS_SERVER,
    "general": LOGS,
}

# cache για να μην διπλογράφουμε handlers
_LOGGERS: dict[str, logging.Logger] = {}


def get_logger(name: str, category: str = "general") -> logging.Logger:
    """Επιστρέφει configured logger για το δοσμένο όνομα+κατηγορία."""
    key = f"{category}:{name}"
    if key in _LOGGERS:
        return _LOGGERS[key]

    log_dir: Path = _CATEGORY_DIRS.get(category, LOGS)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(key)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False

    # καθάρισε τυχόν παλιούς handlers
    logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # αρχείο (με rotation)
    file_handler = RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # console (stdout)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    _LOGGERS[key] = logger
    return logger
