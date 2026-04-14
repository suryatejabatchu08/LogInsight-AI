"""
Tests for parse_logs() and detect_errors()
Run: pytest tests/ -v
"""

import tempfile
import os
import pytest
from tools.parse_logs import parse_logs
from tools.detect_errors import detect_errors


# ── Fixtures ───────────────────────────────────────────────────────────────────

GENERIC_LOG = """\
2024-11-10 12:00:01 [INFO] app: Server started on port 8080
2024-11-10 12:00:05 [ERROR] db: Connection refused to postgres:5432
2024-11-10 12:00:06 [ERROR] db: Connection refused to postgres:5432
2024-11-10 12:00:10 [CRITICAL] app: Out of memory — cannot allocate 512MB
2024-11-10 12:00:11 [WARNING] auth: Authentication failed for user admin
2024-11-10 12:00:15 [INFO] app: Retry attempt 1
"""

JSON_LOG = """\
{"timestamp": "2024-11-10T12:00:01Z", "level": "info", "message": "Starting up"}
{"timestamp": "2024-11-10T12:00:05Z", "level": "error", "message": "Database connection timeout"}
{"timestamp": "2024-11-10T12:00:06Z", "level": "error", "message": "Query failed: deadlock detected"}
"""

APACHE_LOG = """\
127.0.0.1 - - [10/Nov/2024:12:00:01 +0000] "GET /index.html HTTP/1.1" 200 1024
127.0.0.1 - - [10/Nov/2024:12:00:02 +0000] "POST /login HTTP/1.1" 401 256
10.0.0.1 - - [10/Nov/2024:12:00:03 +0000] "GET /admin HTTP/1.1" 500 512
"""


def write_tmp(content: str, suffix=".log") -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="w")
    f.write(content)
    f.close()
    return f.name


# ── parse_logs tests ───────────────────────────────────────────────────────────

class TestParseLogs:

    def test_generic_log_returns_events(self):
        path = write_tmp(GENERIC_LOG)
        events = parse_logs(path)
        os.unlink(path)
        assert len(events) == 6
        assert all("message" in e for e in events)
        assert all("level" in e for e in events)

    def test_generic_log_levels_correct(self):
        path = write_tmp(GENERIC_LOG)
        events = parse_logs(path)
        os.unlink(path)
        levels = [e["level"] for e in events]
        assert "ERROR" in levels
        assert "CRITICAL" in levels
        assert "INFO" in levels

    def test_json_log_auto_detect(self):
        path = write_tmp(JSON_LOG, suffix=".log")
        events = parse_logs(path, log_format="auto")
        os.unlink(path)
        assert len(events) == 3
        assert events[1]["level"] == "ERROR"

    def test_apache_log_auto_detect(self):
        path = write_tmp(APACHE_LOG)
        events = parse_logs(path, log_format="auto")
        os.unlink(path)
        assert len(events) == 3
        assert events[1]["level"] == "WARNING"   # 401
        assert events[2]["level"] == "ERROR"     # 500

    def test_missing_file_returns_error(self):
        events = parse_logs("/nonexistent/path/file.log")
        assert len(events) == 1
        assert "error" in events[0]

    def test_empty_log_returns_empty(self):
        path = write_tmp("   \n\n  \n")
        events = parse_logs(path)
        os.unlink(path)
        assert events == []


# ── detect_errors tests ────────────────────────────────────────────────────────

class TestDetectErrors:

    def _parsed(self, content):
        path = write_tmp(content)
        events = parse_logs(path)
        os.unlink(path)
        return events

    def test_detects_connection_failure(self):
        events = self._parsed(GENERIC_LOG)
        issues = detect_errors(events)
        labels = [i["pattern_name"] for i in issues]
        assert "Connection Failure" in labels

    def test_detects_oom(self):
        events = self._parsed(GENERIC_LOG)
        issues = detect_errors(events)
        labels = [i["pattern_name"] for i in issues]
        assert "OOM / Memory Issue" in labels

    def test_detects_auth_failure(self):
        events = self._parsed(GENERIC_LOG)
        issues = detect_errors(events)
        labels = [i["pattern_name"] for i in issues]
        assert "Auth Failure" in labels

    def test_sorted_by_severity(self):
        events = self._parsed(GENERIC_LOG)
        issues = detect_errors(events)
        assert len(issues) > 0
        # CRITICAL / ERROR should come before WARNING
        severities = [i["severity"] for i in issues]
        from tools.detect_errors import SEVERITY_RANK
        ranks = [SEVERITY_RANK.get(s, 0) for s in severities]
        assert ranks == sorted(ranks, reverse=True)

    def test_json_log_detects_db_error(self):
        events = self._parsed(JSON_LOG)
        issues = detect_errors(events)
        labels = [i["pattern_name"] for i in issues]
        assert "Database Error" in labels or "Timeout" in labels

    def test_empty_input_returns_empty(self):
        assert detect_errors([]) == []

    def test_clean_log_returns_empty(self):
        clean = """\
2024-11-10 12:00:01 [INFO] app: Started
2024-11-10 12:00:02 [INFO] app: Healthy
"""
        events = self._parsed(clean)
        issues = detect_errors(events)
        assert issues == []
