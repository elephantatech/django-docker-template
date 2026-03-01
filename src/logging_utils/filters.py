import logging
import re


class PasswordRedactionFilter(logging.Filter):
    """Redact password values from log messages and extra fields."""

    PASSWORD_PATTERN = re.compile(
        r'(password["\']?\s*[:=]\s*)["\']?[^"\'&\s,}]+["\']?',
        re.IGNORECASE,
    )
    REDACTED = "***REDACTED***"

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact_string(str(record.msg))

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self.REDACTED if "password" in k.lower() else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact_string(str(a)) if isinstance(a, str) else a for a in record.args
                )

        # Redact extra attributes that look like passwords
        for attr in list(record.__dict__):
            if "password" in attr.lower() and attr not in ("msg", "args"):
                setattr(record, attr, self.REDACTED)

        return True

    def _redact_string(self, text: str) -> str:
        return self.PASSWORD_PATTERN.sub(rf"\g<1>{self.REDACTED}", text)
