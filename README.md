# LogInsight AI 🔍
**Intelligent Log Analyzer** — FastAPI + FastMCP + Groq + Supabase

Upload a log file → get a plain-language summary of issues + suggested fixes, powered by an LLM agent that calls deterministic parsing tools via MCP.

---

## How It Works

```
POST /analyze  (upload log file)
      ↓
parse_logs()        ← FastMCP tool  (deterministic)
      ↓
detect_errors()     ← FastMCP tool  (deterministic)
      ↓
Groq LLM            ← generates summary + fixes
      ↓
Result saved to Supabase + returned to you
```

---

## Prerequisites

| Tool | Install |
|------|---------|
| Python 3.11+ | [python.org](https://python.org) or `winget install Python.Python.3.11` |
| Git | `winget install Git.Git` |
| Groq API key (free) | [console.groq.com](https://console.groq.com) |
| Supabase project (free) | [supabase.com](https://supabase.com) |

---

## Setup

### 1. Clone & install

```powershell
git clone https://github.com/your-org/loginsight-ai
cd loginsight-ai
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
copy .env.example .env
```

Edit `.env` and fill in:
```
GROQ_API_KEY=your-groq-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 3. Set up Supabase table

Go to your Supabase project → **SQL Editor** → paste and run `supabase_schema.sql`:

```sql
CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'processing',
    summary     TEXT,
    issues      JSONB,
    fixes       JSONB,
    error       TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 4. Run the app

**Terminal 1 — MCP tool server:**
```powershell
python tools/mcp_server.py
```

**Terminal 2 — FastAPI:**
```powershell
uvicorn api.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** to see the interactive API docs.

---

## API Usage

### Analyze a log file

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@/path/to/your/app.log"
```

Response:
```json
{
  "job_id": "abc-123",
  "filename": "app.log",
  "status": "complete",
  "summary": "The service experienced repeated database connection failures starting at 12:00:05, followed by an out-of-memory event that likely caused the crash at 12:00:10. Three authentication failures were also observed.",
  "issues": [
    {
      "pattern_name": "OOM / Memory Issue",
      "severity": "CRITICAL",
      "count": 1,
      "first_seen": "2024-11-10 12:00:10",
      "last_seen": "2024-11-10 12:00:10",
      "sample_messages": ["Out of memory — cannot allocate 512MB"]
    }
  ],
  "suggested_fixes": [
    {
      "issue_name": "OOM / Memory Issue",
      "fix": "1. Check current memory usage with `free -m`. 2. Identify memory-heavy processes with `top` or Task Manager. 3. Increase heap size in your app config or add more RAM. 4. Enable memory limits and alerts to catch this earlier."
    }
  ]
}
```

### Get a past result by job ID

```bash
curl http://localhost:8000/results/abc-123
```

### View job history

```bash
curl http://localhost:8000/history
```

---

## Run Tests

```powershell
pytest tests/ -v
```

---

## Project Structure

```
loginsight-ai/
├── api/
│   └── main.py              # FastAPI — /analyze, /results, /history, /health
├── tools/
│   ├── mcp_server.py        # FastMCP server with @mcp.tool() decorators
│   ├── parse_logs.py        # parse_logs() — tokenizes log lines
│   └── detect_errors.py     # detect_errors() — pattern matching + ranking
├── agent/
│   └── orchestrator.py      # Calls tools + Groq LLM, returns final result
├── storage/
│   └── supabase_client.py   # Supabase DB helpers (save/get/list jobs)
├── tests/
│   └── test_tools.py        # pytest tests for both tools
├── supabase_schema.sql      # Paste into Supabase SQL editor
├── .env.example
├── requirements.txt
└── README.md
```

---

## Supported Log Formats

| Format | Auto-detected? | Example |
|--------|---------------|---------|
| Generic (timestamped) | ✅ | `2024-11-10 12:00:01 [ERROR] app: message` |
| JSON structured | ✅ | `{"level":"error","message":"..."}` |
| Apache/Nginx access | ✅ | `127.0.0.1 - - [date] "GET /" 200 512` |
| Syslog RFC 5424 | ✅ | `Nov 10 12:00:01 hostname app[123]: message` |

---

## Detected Error Patterns

| Pattern | Triggers on |
|---------|------------|
| OOM / Memory Issue | `out of memory`, `OOMKilled`, `cannot allocate` |
| Connection Failure | `connection refused`, `connection timed out` |
| Auth Failure | `authentication failed`, `unauthorized`, `401`, `403` |
| Timeout | `timeout`, `timed out`, `deadline exceeded` |
| Disk Full | `disk full`, `no space left`, `ENOSPC` |
| Null Pointer / Segfault | `NullPointerException`, `segmentation fault` |
| Stacktrace / Exception | `Traceback`, `stack trace`, `Exception in thread` |
| HTTP 5xx Error | `500`, `503`, `internal server error` |
| Database Error | `SQL error`, `query failed`, `deadlock` |
| Missing File | `file not found`, `No such file`, `ENOENT` |
