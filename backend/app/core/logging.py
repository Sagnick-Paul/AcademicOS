"""Centralized logging configuration.

Structured logging via stdlib `logging` with a consistent format. Plug in
JSON output, log shipping, or OpenTelemetry later without changing call
sites.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import settings


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Initialize root logging once at application startup."""
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


__all__: list[str] = ["configure_logging", "get_logger"]
