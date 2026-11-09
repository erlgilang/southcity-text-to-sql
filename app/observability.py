import json
import logging
import sys
from datetime import UTC, datetime

LOGGER = logging.getLogger("southcity")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    """Send JSON log lines to stdout. Call once at startup with LOG_LEVEL."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    LOGGER.handlers = [handler]
    LOGGER.setLevel(level.upper())
    LOGGER.propagate = False


def log_event(event: str, *, level: int = logging.INFO, **fields) -> None:
    """Log one structured line. Never pass secrets, connection strings or result rows."""
    LOGGER.log(level, event, extra={"fields": fields})
