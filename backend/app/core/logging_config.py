"""
Clipped-AI — Structured Logging Configuration
JSON structured logs in production, human-readable in development.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, Dict

from app.core.config import settings


class _JSONFormatter(logging.Formatter):
    """Minimal JSON log formatter — no extra deps required."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        import traceback

        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Extra fields added via logger.info("msg", extra={"key": "value"})
        for key, val in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                log_obj[key] = val

        if record.exc_info:
            log_obj["exception"] = traceback.format_exception(*record.exc_info)

        return json.dumps(log_obj, default=str)


def setup_logging() -> None:
    """Configure root logger based on environment."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Remove any existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    if settings.is_production:
        handler.setFormatter(_JSONFormatter())
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))

    root.addHandler(handler)

    # Silence noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Adapter that intercepts arbitrary keyword arguments and packs them into `extra`."""

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        std_keys = {"exc_info", "stack_info", "stacklevel", "extra"}
        std_kwargs = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in std_keys}

        extra = dict(std_kwargs.get("extra") or {})
        if self.extra:
            extra.update(self.extra)

        # Move all non-standard kwargs into extra
        if kwargs:
            extra.update(kwargs)
            if not settings.is_production:
                items_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
                msg = f"{msg} [{items_str}]"
            kwargs.clear()

        std_kwargs["extra"] = extra
        return msg, std_kwargs


def get_logger(name: str) -> StructuredLoggerAdapter:
    base_logger = logging.getLogger(name)
    return StructuredLoggerAdapter(base_logger, {})
