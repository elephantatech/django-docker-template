import json
import logging

from logging_utils.filters import PasswordRedactionFilter
from logging_utils.formatters import JSONFormatter


class TestJSONFormatter:
    def test_basic_format(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "hello world"
        assert "timestamp" in data

    def test_single_line(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="line one\nline two",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "\n" not in output

    def test_exception_included(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="error occurred",
                args=(),
                exc_info=True,
            )
            # LogRecord with exc_info=True captures current exception
            import sys

            record.exc_info = sys.exc_info()
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_extra_fields_included(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="with extras",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc-123"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["request_id"] == "abc-123"


class TestPasswordRedactionFilter:
    def setup_method(self):
        self.filter = PasswordRedactionFilter()

    def test_redacts_password_in_message(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="password=secret123",
            args=(),
            exc_info=None,
        )
        self.filter.filter(record)
        assert "secret123" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_redacts_password_in_json_message(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='{"password": "mysecret"}',
            args=(),
            exc_info=None,
        )
        self.filter.filter(record)
        assert "mysecret" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_redacts_password_in_dict_args(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="login attempt",
            args={"password": "secret", "user": "admin"},
            exc_info=None,
        )
        self.filter.filter(record)
        assert record.args["password"] == "***REDACTED***"
        assert record.args["user"] == "admin"

    def test_redacts_password_extra_attr(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.password = "supersecret"
        self.filter.filter(record)
        assert record.password == "***REDACTED***"

    def test_preserves_non_password_messages(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="normal log message",
            args=(),
            exc_info=None,
        )
        self.filter.filter(record)
        assert record.msg == "normal log message"

    def test_returns_true(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        assert self.filter.filter(record) is True
