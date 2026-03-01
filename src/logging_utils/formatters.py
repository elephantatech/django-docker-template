import json
import logging
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields passed via the `extra` kwarg
        standard_attrs = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in log_entry:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)
