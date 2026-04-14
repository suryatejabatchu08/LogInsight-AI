import re
from collections import defaultdict

# ── Severity levels (higher = worse) ──────────────────────────────────────────
SEVERITY_RANK = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "WARN": 2,
    "ERROR": 3,
    "CRITICAL": 4,
    "FATAL": 4,
}

# ── Patterns that flag a line as a notable issue ───────────────────────────────
# Note: These patterns check for ACTUAL errors, not false positives
# For HTTP logs: we check the level field (extracted by parser from status code)
# For text logs: we match specific error keywords
ERROR_PATTERNS = [
    (re.compile(r"out of memory|OOMKilled|cannot allocate", re.I), "OOM / Memory Issue"),
    (re.compile(r"connection refused|connection timed out|no route to host", re.I), "Connection Failure"),
    # Auth errors - only if explicitly mentioned, not just 401/403 in URLs
    (re.compile(r"authentication fail|invalid credentials|unauthorized access|auth.*fail", re.I), "Auth Failure"),
    (re.compile(r"timeout|timed out|deadline exceeded", re.I), "Timeout"),
    (re.compile(r"disk full|no space left|ENOSPC", re.I), "Disk Full"),
    (re.compile(r"null pointer|nullpointerexception|segmentation fault|sigsegv", re.I), "Null Pointer / Segfault"),
    (re.compile(r"traceback|stack trace|exception in thread", re.I), "Stacktrace / Exception"),
    # Server errors - match in message context, not just any 5xx pattern
    (re.compile(r"internal server error|service unavailable|bad gateway|gateway timeout", re.I), "Server Error"),
    (re.compile(r"database error|sql error|query failed|deadlock|constraint violation", re.I), "Database Error"),
    (re.compile(r"file not found|no such file|enoent|404", re.I), "File Not Found"),
]


def detect_errors(parsed_logs: list[dict]) -> list[dict]:
    """
    Scan structured log events and return a ranked list of detected issues.

    Args:
        parsed_logs: Output from parse_logs() — list of log event dicts.

    Returns:
        List of issue dicts: { pattern_name, severity, count, first_seen,
                               last_seen, sample_messages }
    """
    print(f"\n[DETECTOR] 🔎 Starting error detection on {len(parsed_logs)} log events")
    
    if not parsed_logs:
        print(f"[DETECTOR] ⚠️  No logs to analyze!")
        return []

    # Group by issue pattern
    issue_buckets: dict[str, dict] = defaultdict(lambda: {
        "count": 0,
        "first_seen": None,
        "last_seen": None,
        "severity": "INFO",
        "sample_messages": [],
    })

    high_severity_count = 0

    for event in parsed_logs:
        level = event.get("level", "INFO").upper()
        message = event.get("message", "")
        timestamp = event.get("timestamp", "")

        # Count ERROR+ events even if no pattern matched
        rank = SEVERITY_RANK.get(level, 1)
        if rank >= SEVERITY_RANK["ERROR"]:
            high_severity_count += 1

        # Match against known patterns - but skip if level is already INFO (2xx-3xx responses)
        # This avoids false positives from HTTP status codes appearing in URLs
        if rank >= SEVERITY_RANK["WARNING"]:  # Only check patterns for WARNING+ level events
            for pattern, label in ERROR_PATTERNS:
                if pattern.search(message) or pattern.search(event.get("raw", "")):
                    bucket = issue_buckets[label]
                    bucket["count"] += 1

                    # Track severity (escalate if worse level seen)
                    if rank > SEVERITY_RANK.get(bucket["severity"], 0):
                        bucket["severity"] = level

                    # Track time range
                    if timestamp:
                        if bucket["first_seen"] is None:
                            bucket["first_seen"] = timestamp
                        bucket["last_seen"] = timestamp

                    # Keep up to 3 sample messages
                    if len(bucket["sample_messages"]) < 3:
                        bucket["sample_messages"].append(message[:200])

                    break  # Only match the first pattern per line

    # If there are many high-severity lines that didn't match a pattern,
    # add a generic "Unclassified Errors" entry
    unmatched_errors = high_severity_count - sum(
        b["count"] for b in issue_buckets.values()
        if SEVERITY_RANK.get(b["severity"], 0) >= SEVERITY_RANK["ERROR"]
    )
    if unmatched_errors > 0:
        issue_buckets["Unclassified Errors"] = {
            "count": unmatched_errors,
            "first_seen": None,
            "last_seen": None,
            "severity": "ERROR",
            "sample_messages": [],
        }
    
    print(f"[DETECTOR] 📋 Found {high_severity_count} high-severity log entries")
    print(f"[DETECTOR] 🎯 Detected {len(issue_buckets)} distinct issue types:")
    for label, bucket in issue_buckets.items():
        print(f"     • {label}: {bucket['count']} occurrences [{bucket['severity']}]")
    
    print(f"[DETECTOR] ✅ Error detection complete")

    # Convert to sorted list — highest severity + count first
    issues = []
    for label, data in issue_buckets.items():
        issues.append({
            "pattern_name": label,
            "severity": data["severity"],
            "count": data["count"],
            "first_seen": data["first_seen"],
            "last_seen": data["last_seen"],
            "sample_messages": data["sample_messages"],
        })

    issues.sort(
        key=lambda x: (SEVERITY_RANK.get(x["severity"], 0), x["count"]),
        reverse=True,
    )

    return issues
