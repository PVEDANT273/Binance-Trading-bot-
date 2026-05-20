"""
bot/logging_config.py
~~~~~~~~~~~~~~~~~~~~~
Centralised logging setup for the trading bot.

Features:
  - Rotating file handler  → logs/trading_bot.log (5 MB × 3 backups)
  - Rich console handler   → WARNING+ only, colour-coded via `rich`
  - One shared formatter   → timestamp | level | module | message
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

#    Constants          
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB
BACKUP_COUNT = 3

# File log format — verbose
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(level: int = logging.DEBUG) -> None:
    """
    Configure the root logger once at application startup.

    Call this exactly once from cli.py before any other imports trigger
    logging. Subsequent calls are idempotent (handlers are not duplicated).
    """
    root = logging.getLogger()

    # Idempotency guard
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    #File handler (DEBUG+, rotating)                                     
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))

    # Rich console handler (WARNING+)                                     
    console_handler = RichHandler(
        level=logging.WARNING,
        rich_tracebacks=True,
        show_path=False,
        markup=True,
    )

    root.addHandler(file_handler)
    root.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Always call setup_logging() first."""
    return logging.getLogger(name)
