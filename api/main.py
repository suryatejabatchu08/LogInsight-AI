"""
LogInsight AI — FastAPI application
Endpoints:
  POST /analyze          Upload a log file and get analysis results
  GET  /results/{job_id} Retrieve a past analysis by job ID
  GET  /history          List recent analyses
  GET  /health           Health check
"""

import uuid
import tempfile
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.orchestrator import run_analysis
from storage.supabase_client import save_job, complete_job, fail_job, get_job, list_jobs

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LogInsight AI",
    description="Intelligent log analyzer powered by FastMCP + Groq",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# ── Response schemas ───────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    summary: str
    issues: list
    suggested_fixes: list


class JobSummary(BaseModel):
    id: str
    filename: str
    status: str
    created_at: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=AnalyzeResponse, summary="Upload and analyze a log file")
async def analyze(file: UploadFile = File(..., description="Log file (.log, .txt, .json)")):
    """
    Upload a log file. The server will:
    1. Parse it using parse_logs() via FastMCP
    2. Detect errors using detect_errors() via FastMCP
    3. Generate a summary and suggested fixes via Groq LLM
    4. Save the result to Supabase for history
    """
    job_id = str(uuid.uuid4())
    filename = file.filename or "upload.log"
    
    print(f"\n{'='*70}")
    print(f"[API] 📥 NEW ANALYSIS REQUEST")
    print(f"  Job ID: {job_id}")
    print(f"  Filename: {filename}")
    print(f"{'='*70}\n")

    # Save job to Supabase as 'processing'
    print(f"[API] 💾 Saving job to database...")
    save_job(job_id, filename)

    # Write uploaded file to a temp file on disk so tools can read it
    suffix = Path(filename).suffix or ".log"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="wb") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        print(f"[API] 🔍 Starting analysis pipeline...")
        result = run_analysis(tmp_path)
        print(f"[API] ✅ Analysis complete! Summary: {result['summary'][:100]}...")
        print(f"[API] 📊 Found {len(result['issues'])} issues, {len(result['suggested_fixes'])} fixes")
        print(f"[API] 💾 Updating job status to complete...")
        complete_job(
            job_id,
            summary=result["summary"],
            issues=result["issues"],
            fixes=result["suggested_fixes"],
        )
        print(f"[API] 🎉 Job {job_id} completed successfully!\n")
        return AnalyzeResponse(
            job_id=job_id,
            filename=filename,
            status="complete",
            summary=result["summary"],
            issues=result["issues"],
            suggested_fixes=result["suggested_fixes"],
        )
    except Exception as exc:
        print(f"[API] ❌ ERROR during analysis: {exc}")
        fail_job(job_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        os.unlink(tmp_path)  # Clean up temp file


@app.get("/results/{job_id}", response_model=AnalyzeResponse, summary="Get analysis by job ID")
def get_result(job_id: str):
    """Retrieve a previously run analysis from Supabase by job ID."""
    print(f"[API] 🔍 Retrieving job: {job_id}")
    job = get_job(job_id)
    if not job:
        print(f"[API] ❌ Job not found: {job_id}")
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    print(f"[API] ✅ Job found: {job['filename']}")
    return AnalyzeResponse(
        job_id=job["id"],
        filename=job["filename"],
        status=job["status"],
        summary=job.get("summary") or "",
        issues=job.get("issues") or [],
        suggested_fixes=job.get("fixes") or [],
    )


@app.get("/history", response_model=list[JobSummary], summary="List recent analyses")
def history(limit: int = 20):
    """Return the most recent analyses (up to 50)."""
    print(f"[API] 📜 Fetching analysis history (limit: {limit})")
    limit = min(limit, 50)
    jobs = list_jobs(limit)
    print(f"[API] ✅ Found {len(jobs)} analyses in history")
    return [
        JobSummary(
            id=j["id"],
            filename=j["filename"],
            status=j["status"],
            created_at=j["created_at"],
        )
        for j in jobs
    ]


@app.get("/health", summary="Health check")
def health():
    print(f"[API] 💚 Health check")
    return {"status": "ok", "service": "LogInsight AI"}


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def root():
    """Serve the frontend UI"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        with open(frontend_path, "r") as f:
            return f.read()
    return "<h1>Frontend not found</h1>"
