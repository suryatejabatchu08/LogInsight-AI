import re
import json
from datetime import datetime

# ── Regex patterns for common log formats ──────────────────────────────────────

# Syslog:  Nov 10 12:34:56 hostname process[pid]: message
SYSLOG_RE = re.compile(
    r"(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<source>\S+)\s+(?P<process>\S+?):\s+(?P<message>.+)"
)

# Apache/Nginx combined:  127.0.0.1 - - [10/Nov/2024:12:34:56 +0000] "GET / HTTP/1.1" 200 512
APACHE_RE = re.compile(
    r"(?P<source>\S+)\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"
    r'"(?P<request>[^"]+)"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)'
)

# Generic:  2024-11-10 12:34:56 [LEVEL] message
GENERIC_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    r"(?:\s+\[(?P<level>[A-Z]+)\])?"
    r"(?:\s+(?P<source>\S+?):)?"
    r"\s+(?P<message>.+)"
)

LEVEL_KEYWORDS = ["DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"]


def _infer_level(line: str) -> str:
    upper = line.upper()
    for kw in LEVEL_KEYWORDS:
        if kw in upper:
            return kw
    return "INFO"


def _parse_json_line(line: str) -> dict | None:
    try:
        obj = json.loads(line)
        return {
            "timestamp": str(obj.get("timestamp") or obj.get("time") or obj.get("ts") or ""),
            "level": str(obj.get("level") or obj.get("severity") or "INFO").upper(),
            "source": str(obj.get("logger") or obj.get("source") or obj.get("name") or "app"),
            "message": str(obj.get("message") or obj.get("msg") or obj.get("event") or line),
            "raw": line,
        }
    except (json.JSONDecodeError, Exception):
        return None


def _parse_syslog_line(line: str) -> dict | None:
    m = SYSLOG_RE.match(line)
    if m:
        return {
            "timestamp": m.group("timestamp"),
            "level": _infer_level(m.group("message")),
            "source": m.group("source"),
            "message": m.group("message"),
            "raw": line,
        }
    return None


def _parse_apache_line(line: str) -> dict | None:
    m = APACHE_RE.match(line)
    if m:
        status = int(m.group("status"))
        level = "ERROR" if status >= 500 else ("WARNING" if status >= 400 else "INFO")
        return {
            "timestamp": m.group("timestamp"),
            "level": level,
            "source": m.group("source"),
            "message": f'{m.group("request")} -> {status}',
            "raw": line,
        }
    return None


def _parse_generic_line(line: str) -> dict:
    m = GENERIC_RE.match(line)
    if m:
        return {
            "timestamp": m.group("timestamp") or "",
            "level": (m.group("level") or _infer_level(line)).upper(),
            "source": m.group("source") or "unknown",
            "message": m.group("message") or line,
            "raw": line,
        }
    return {
        "timestamp": "",
        "level": _infer_level(line),
        "source": "unknown",
        "message": line.strip(),
        "raw": line,
    }


def parse_logs(file_path: str, log_format: str = "auto") -> list[dict]:
    """
    Parse a log file into a list of structured log events.

    Args:
        file_path:  Path to the log file.
        log_format: One of 'auto', 'json', 'syslog', 'apache'. Defaults to 'auto'.

    Returns:
        List of dicts with keys: timestamp, level, source, message, raw.
    """
    print(f"\n[PARSER] 📖 Starting log parsing: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
    except FileNotFoundError:
        print(f"[PARSER] ❌ File not found: {file_path}")
        return [{"error": f"File not found: {file_path}"}]
    
    print(f"[PARSER] 📝 Read {len(lines)} lines from file")

    events: list[dict] = []

    # Auto-detect format from first non-empty line
    if log_format == "auto":
        sample = lines[0] if lines else ""
        if sample.strip().startswith("{"):
            log_format = "json"
        elif APACHE_RE.match(sample):
            log_format = "apache"
        elif SYSLOG_RE.match(sample):
            log_format = "syslog"
        else:
            log_format = "generic"
        print(f"[PARSER] 🔍 Auto-detected format: {log_format}")

    for line in lines:
        if not line.strip():
            continue

        event = None
        if log_format == "json":
            event = _parse_json_line(line) or _parse_generic_line(line)
        elif log_format == "syslog":
            event = _parse_syslog_line(line) or _parse_generic_line(line)
        elif log_format == "apache":
            event = _parse_apache_line(line) or _parse_generic_line(line)
        else:
            event = _parse_generic_line(line)

        events.append(event)
    
    print(f"[PARSER] ✅ Parsed {len(events)} log events")
    return events
