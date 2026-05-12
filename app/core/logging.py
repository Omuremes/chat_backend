import logging
import re
from typing import Any


_SENSITIVE_QUERY_RE = re.compile(r"(?i)\b((?:access_)?token|id_token)=([^&\s\"]+)")


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _SENSITIVE_QUERY_RE.sub(r"\1=<redacted>", value)
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


class SensitiveValueFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.msg)
        record.args = _redact(record.args)
        return True


def configure_sensitive_logging() -> None:
    sensitive_filter = SensitiveValueFilter()
    for logger_name in ("uvicorn.access", "uvicorn.error", "fastapi"):
        logger = logging.getLogger(logger_name)
        if not any(isinstance(existing, SensitiveValueFilter) for existing in logger.filters):
            logger.addFilter(sensitive_filter)
        for handler in logger.handlers:
            if not any(isinstance(existing, SensitiveValueFilter) for existing in handler.filters):
                handler.addFilter(sensitive_filter)
