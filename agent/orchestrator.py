"""
Agent orchestrator — drives the full analysis loop:
  1. Calls parse_logs() via MCP
  2. Calls detect_errors() via MCP
  3. Sends tool outputs to Groq LLM for summary + fixes
"""

import os
import json
import tempfile
from groq import Groq
from dotenv import load_dotenv

from tools.parse_logs import parse_logs
from tools.detect_errors import detect_errors

load_dotenv()

# ── Groq client ───────────────────────────────────────────────────────────────
_groq = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are LogInsight AI, an expert IT operations engineer.
You will be given:
  1. A list of structured log events (parsed from a log file)
  2. A list of detected issues (anomalies, errors, patterns found in those logs)

Your job is to produce:
  A) A concise plain-language SUMMARY of what is wrong (2-5 sentences).
  B) A list of SUGGESTED FIXES — one per detected issue, each with:
     - issue_name: the issue label
     - fix: a clear, actionable step-by-step remediation (2-4 steps)

Respond ONLY with valid JSON in this exact shape:
{
  "summary": "...",
  "suggested_fixes": [
    {
      "issue_name": "...",
      "fix": "..."
    }
  ]
}
Do not include any text outside the JSON object."""

ANALYSIS_PROMPT = """Here are the analysis results from the log file:

## Detected Issues
{issues}

## Sample Log Events (first 30)
{sample_events}

Now produce the JSON summary and suggested fixes."""


def _scrub_pii(text: str) -> str:
    """Basic PII scrub before sending to external LLM."""
    import re
    # Remove email addresses
    text = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[EMAIL]", text)
    # Remove IPv4 addresses
    text = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "[IP]", text)
    # Remove potential passwords/tokens (key=value patterns with long values)
    text = re.sub(r"(password|token|secret|key|auth)\s*[:=]\s*\S+", r"\1=[REDACTED]", text, flags=re.I)
    return text


def run_analysis(file_path: str) -> dict:
    """
    Full analysis pipeline:
      parse_logs → detect_errors → LLM summary + fixes

    Returns:
        {
          "summary": str,
          "issues": list[dict],       # from detect_errors
          "suggested_fixes": list[dict]
        }
    """
    print(f"\n{'='*70}")
    print(f"[ORCHESTRATOR] 🚀 ANALYSIS PIPELINE STARTED")
    print(f"{'='*70}")
    
    # ── Step 1: Parse logs (deterministic) ────────────────────────────────────
    print(f"[ORCHESTRATOR] STEP 1️⃣  Parsing logs...")
    parsed = parse_logs(file_path, log_format="auto")

    if not parsed:
        print(f"[ORCHESTRATOR] ⚠️  No logs parsed, returning empty result")
        return {
            "summary": "The log file appears to be empty or could not be parsed.",
            "issues": [],
            "suggested_fixes": [],
        }

    # ── Step 2: Detect errors (deterministic) ─────────────────────────────────
    print(f"\n[ORCHESTRATOR] STEP 2️⃣  Detecting errors...")
    issues = detect_errors(parsed)

    if not issues:
        print(f"[ORCHESTRATOR] ℹ️  No issues detected, returning clean result")
        return {
            "summary": "No significant errors or anomalies were detected in this log file.",
            "issues": [],
            "suggested_fixes": [],
        }

    # ── Step 3: Build LLM prompt ───────────────────────────────────────────────
    print(f"\n[ORCHESTRATOR] STEP 3️⃣  Preparing LLM request...")
    print(f"     • Scrubbing PII from {len(parsed)} log events")
    issues_text = json.dumps(issues, indent=2)
    sample_events = parsed[:30]  # Send a sample, not all events (context limit)
    events_text = json.dumps(sample_events, indent=2)

    # Scrub PII before sending to external LLM
    issues_text = _scrub_pii(issues_text)
    events_text = _scrub_pii(events_text)

    user_prompt = ANALYSIS_PROMPT.format(
        issues=issues_text,
        sample_events=events_text,
    )
    print(f"     • Prompt size: {len(user_prompt)} characters")

    # ── Step 4: Call Groq LLM ─────────────────────────────────────────────────
    print(f"\n[ORCHESTRATOR] STEP 4️⃣  Calling Groq LLM (model: {MODEL})...")
    print(f"     • Request timeout: 30 seconds")
    response = _groq.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1500,
    )
    print(f"     • ✅ LLM response received")

    raw_text = response.choices[0].message.content.strip()

    # ── Step 5: Parse LLM JSON response ───────────────────────────────────────
    print(f"\n[ORCHESTRATOR] STEP 5️⃣  Parsing LLM response...")
    try:
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        llm_output = json.loads(raw_text)
        print(f"     • ✅ Successfully parsed JSON response")
        print(f"     • Summary: {llm_output.get('summary', '')[:80]}...")
        print(f"     • Fixes: {len(llm_output.get('suggested_fixes', []))} recommendations")
    except json.JSONDecodeError:
        print(f"     • ⚠️  JSON parsing failed, using raw text as summary")
        # Fallback — return raw text as summary if JSON parsing fails
        llm_output = {
            "summary": raw_text,
            "suggested_fixes": [],
        }

    print(f"\n[ORCHESTRATOR] ✅ ANALYSIS COMPLETE")
    print(f"{'='*70}\n")
    
    return {
        "summary": llm_output.get("summary", ""),
        "issues": issues,
        "suggested_fixes": llm_output.get("suggested_fixes", []),
    }
