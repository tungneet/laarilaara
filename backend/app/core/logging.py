"""Structured JSON logging.

CloudWatch ingests stdout from Lambda line by line, so emitting one JSON object
per log line makes logs queryable in CloudWatch Logs Insights without extra
parsing. Never log secrets or personal data.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import get_settings

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["requestId"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Allow structured extras without clobbering reserved keys.
        for key, value in getattr(record, "extra_fields", {}).items():
            payload.setdefault(key, value)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
