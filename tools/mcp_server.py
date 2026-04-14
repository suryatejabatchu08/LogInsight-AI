"""
FastMCP server — exposes parse_logs() and detect_errors() as MCP tools.
Run this in a separate terminal: python tools/mcp_server.py
"""

from fastmcp import FastMCP
from tools.parse_logs import parse_logs as _parse_logs
from tools.detect_errors import detect_errors as _detect_errors

mcp = FastMCP(
    name="LogInsight Tools",
    instructions=(
        "You are a log analysis assistant. "
        "Use parse_logs to parse a log file into structured events, "
        "then use detect_errors on the result to find issues. "
        "Always call both tools before generating your summary."
    ),
)


@mcp.tool()
def parse_logs(file_path: str, log_format: str = "auto") -> list[dict]:
    """
    Parse a raw log file into structured log events.

    Args:
        file_path:  Absolute or relative path to the log file.
        log_format: Format hint — 'auto' (default), 'json', 'syslog', 'apache'.

    Returns:
        List of log events, each with: timestamp, level, source, message, raw.
    """
    return _parse_logs(file_path, log_format)


@mcp.tool()
def detect_errors(parsed_logs: list[dict]) -> list[dict]:
    """
    Detect error patterns from structured log events.

    Args:
        parsed_logs: Output from the parse_logs tool.

    Returns:
        Ranked list of detected issues with severity, count, timestamps,
        and sample messages.
    """
    return _detect_errors(parsed_logs)


if __name__ == "__main__":
    mcp.run()
