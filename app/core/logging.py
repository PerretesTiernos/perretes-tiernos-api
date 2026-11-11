import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

import sentry_sdk

from app.core.config import settings

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
    "api_key",
    "tax_id",
    "phone",
    "email",
}


class StructuredJsonFormatter(logging.Formatter):
    """JSON log formatter that strips sensitive PII fields for Railway logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.ENVIRONMENT,
        }
        extra_context = getattr(record, "context", None)
        if isinstance(extra_context, dict):
            payload["context"] = {
                k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else v)
                for k, v in extra_context.items()
            }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Configures structured JSON logging and optional Sentry error tracking."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.handlers = [handler]

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=settings.APP_VERSION,
            send_default_pii=False,
            traces_sample_rate=0.2 if settings.is_production else 1.0,
        )

