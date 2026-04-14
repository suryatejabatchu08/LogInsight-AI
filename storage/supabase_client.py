import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def save_job(job_id: str, filename: str) -> None:
    """Insert a new job row with status 'processing'."""
    get_supabase().table("jobs").insert({
        "id": job_id,
        "filename": filename,
        "status": "processing",
    }).execute()


def complete_job(job_id: str, summary: str, issues: list, fixes: list) -> None:
    """Update job row with results and mark complete."""
    get_supabase().table("jobs").update({
        "status": "complete",
        "summary": summary,
        "issues": issues,
        "fixes": fixes,
    }).eq("id", job_id).execute()


def fail_job(job_id: str, error: str) -> None:
    """Mark a job as failed with an error message."""
    get_supabase().table("jobs").update({
        "status": "failed",
        "error": error,
    }).eq("id", job_id).execute()


def get_job(job_id: str) -> dict | None:
    """Fetch a job row by ID."""
    response = get_supabase().table("jobs").select("*").eq("id", job_id).execute()
    return response.data[0] if response.data else None


def list_jobs(limit: int = 20) -> list[dict]:
    """Fetch recent jobs ordered by created_at descending."""
    response = (
        get_supabase()
        .table("jobs")
        .select("id, filename, status, created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data
