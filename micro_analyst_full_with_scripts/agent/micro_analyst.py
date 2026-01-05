import os
from collections import defaultdict
from time import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from core.data_models import CompanyOSINTProfile
from core.inference import InferenceEngine, InferredProfile, SignalInference
from core.change_detector import ChangeDetector, delta_to_markdown
from utils.wayback import (
    get_historical_snapshots,
    extract_wayback_signals,
    wayback_delta_to_markdown,
)

from core.merge_profiles import (
    merge_web_data,
    merge_seo_data,
    merge_tech_stack_data,
    merge_reviews_data,
    merge_social_data,
    merge_hiring_data,
    merge_ads_data,
)
from utils.llm_client import LLMClient, get_llm_client
from agent.web_surfaces import fetch_web_surfaces, aggregate_web_surfaces
from utils.persistence import (
    init_db, save_report, get_report, increment_usage, markdown_to_pdf,
    check_quota, save_job, get_job_db, load_pending_jobs, DAILY_QUOTA_PER_KEY,
    get_latest_reports
)
from fastapi.responses import Response

# ---------------------------------------------------------------------------
# Load environment from project-level .env
# ---------------------------------------------------------------------------

# BASE_DIR = .../micro_analyst_full_with_scripts
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

logger.info(
    "LLM ENV DEBUG: USE_GEMINI_LLM=%r, GOOGLE_API_KEY_SET=%r",
    os.getenv("USE_GEMINI_LLM"),
    bool(os.getenv("GOOGLE_API_KEY")),
)

app = FastAPI(title="Micro Analyst Agent")

# CORS configuration (Default to strict in prod, configurable via env)
cors_origins_str = os.getenv("CORS_ORIGINS", "*")
allow_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Initialize persistence layer
# ---------------------------------------------------------------------------
try:
    init_db()
    logger.info("Persistence layer initialized")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

# ---------------------------------------------------------------------------
# Include Cohort Mode Router
# ---------------------------------------------------------------------------
from agent.cohort_endpoints import router as cohort_router
app.include_router(cohort_router, prefix="/cohorts")

@app.on_event("startup")
def startup_event():
    """
    Recover state from database on startup.
    - Loads pending jobs.
    - Marks 'running' jobs as failed (interrupted by restart).
    - Populates in-memory jobs dict for continuity.
    """
    logger.info("Startup: Recovering pending jobs from database...")
    pending = load_pending_jobs()
    
    count_recovered = 0
    count_failed = 0
    
    for jid, job in pending.items():
        # If job was running when server died, it's now failed
        if job["status"] == "running":
            job["status"] = "failed"
            job["error"] = "Job interrupted by server restart."
            # Update DB to reflect failure
            save_job(
                job_id=jid,
                status="failed",
                progress=job["progress"],
                company_url=job["company_url"],
                company_name=job["company_name"],
                focus=job["focus"],
                api_key=job["api_key"],
                error=job["error"]
            )
            count_failed += 1
        
        # Load into memory so clients can still poll them
        jobs[jid] = job
        count_recovered += 1
        
    logger.info(f"Recovery complete: {count_recovered} jobs loaded ({count_failed} marked as interrupted).")
    logger.info("Backend ready at http://localhost:8000 — /health, /docs, /analyze available.")


@app.get("/health")
def health_check():
    """
    Simple health check endpoint for startup verification.
    Returns 200 OK if the server is running.
    """
    return {"status": "ok", "service": "signal-analyst", "port": 8000}

# ---------------------------------------------------------------------------
# MCP endpoint URLs (used by tests via micro_analyst.MCP_... constants)
# ---------------------------------------------------------------------------
MCP_WEB_SCRAPE_URL = os.getenv("MCP_WEB_SCRAPE_URL", "http://127.0.0.1:8001/run")
MCP_SEO_PROBE_URL = os.getenv("MCP_SEO_PROBE_URL", "http://127.0.0.1:8002/run")
MCP_TECH_STACK_URL = os.getenv("MCP_TECH_STACK_URL", "http://127.0.0.1:8003/run")
MCP_REVIEWS_SNAPSHOT_URL = os.getenv(
    "MCP_REVIEWS_SNAPSHOT_URL", "http://127.0.0.1:8004/run"
)
MCP_SOCIAL_SNAPSHOT_URL = os.getenv(
    "MCP_SOCIAL_SNAPSHOT_URL", "http://127.0.0.1:8005/run"
)
MCP_CAREERS_INTEL_URL = os.getenv(
    "MCP_CAREERS_INTEL_URL", "http://127.0.0.1:8006/run"
)
MCP_ADS_SNAPSHOT_URL = os.getenv("MCP_ADS_SNAPSHOT_URL", "http://127.0.0.1:8007/run")

# Public constants so tests can import and assert
MCP_URLS: Dict[str, str] = {
    "web_scrape": MCP_WEB_SCRAPE_URL,
    "seo_probe": MCP_SEO_PROBE_URL,
    "tech_stack": MCP_TECH_STACK_URL,
    "reviews_snapshot": MCP_REVIEWS_SNAPSHOT_URL,
    "social_snapshot": MCP_SOCIAL_SNAPSHOT_URL,
    "careers_intel": MCP_CAREERS_INTEL_URL,
    "ads_snapshot": MCP_ADS_SNAPSHOT_URL,
}

# ---------------------------------------------------------------------------
# Default tool plan used when planner fails or returns nothing
# ---------------------------------------------------------------------------
DEFAULT_TOOL_PLAN: Dict[str, bool] = {
    "use_web_scrape": True,
    "use_seo_probe": True,
    "use_tech_stack": True,
    "use_reviews_snapshot": False,
    "use_social_snapshot": False,
    "use_careers_intel": False,
    "use_ads_snapshot": False,
}

# ---------------------------------------------------------------------------
# LLM client (tests monkeypatch _llm_client)
# ---------------------------------------------------------------------------
_llm_client = get_llm_client()
llm_client = _llm_client  # public alias used in code

# ---------------------------------------------------------------------------
# Job state tracking (in-memory for single-tenant)
# ---------------------------------------------------------------------------
jobs: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------
# Fix: Filter empty strings from API keys to prevent empty key bypass
# Requirement 3: Default to {"demo_key_abc123"} if env not set
_raw_keys = os.getenv("VALID_API_KEYS", "")
_parsed_keys = set(k.strip() for k in _raw_keys.split(",") if k.strip())
VALID_API_KEYS = _parsed_keys if _parsed_keys else {"demo_key_abc123"}
AUTH_ENABLED = bool(os.getenv("ENABLE_AUTH", "1") == "1")
ENABLE_WAYBACK = os.getenv("ENABLE_WAYBACK", "0") == "1"


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key if auth is enabled."""
    if not AUTH_ENABLED:
        return "no-auth"
    if not x_api_key or x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


# ---------------------------------------------------------------------------
# Rate Limiting (per API key)
# ---------------------------------------------------------------------------
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10"))
rate_limits: Dict[str, List[float]] = defaultdict(list)

# Requirement 4: Detect pytest to bypass rate limiting
def _is_pytest_running() -> bool:
    """Check if running under pytest."""
    return os.getenv("PYTEST_CURRENT_TEST") is not None

def check_rate_limit(api_key: str) -> bool:
    """
    Sliding window rate limiter.
    Returns True if request allowed, False if rate limited.
    Bypasses rate limiting during pytest runs.
    """
    # Requirement 4: Bypass during pytest
    if _is_pytest_running():
        return True
    now = time()
    # Clean old entries
    window = [t for t in rate_limits[api_key] if now - t < 60]
    if len(window) >= MAX_REQUESTS_PER_MINUTE:
        return False
    rate_limits[api_key] = window + [now]
    return True


# ---------------------------------------------------------------------------
# Job Cleanup (TTL and max jobs)
# ---------------------------------------------------------------------------
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))  # 1 hour default
MAX_JOBS_IN_MEMORY = int(os.getenv("MAX_JOBS_IN_MEMORY", "500"))

def cleanup_old_jobs() -> int:
    """
    Remove expired jobs from memory.
    Returns number of jobs removed.
    """
    now = time()
    expired = [jid for jid, job in jobs.items() 
               if now - job.get("created_at", now) > JOB_TTL_SECONDS]
    for jid in expired:
        del jobs[jid]
    return len(expired)


# ---------------------------------------------------------------------------
# SSRF Protection: Validate URLs before scraping
# ---------------------------------------------------------------------------
import ipaddress
from urllib.parse import urlparse

def validate_company_url(url: str) -> bool:
    """
    Validate company_url to prevent SSRF attacks.
    Blocks: localhost, private IPs, loopback, link-local, file:// schemes.
    """
    try:
        parsed = urlparse(url)
        
        # Only allow http/https
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Block localhost variants
        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False
        
        # Block internal hostnames
        if hostname.lower().endswith(".local") or hostname.lower().endswith(".internal"):
            return False
        
        # Block private/internal IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            # Not an IP address, hostname is acceptable
            pass
        
        # Block cloud metadata endpoints
        if hostname in ("169.254.169.254", "metadata.google.internal"):
            return False
        
        return True
    except Exception:
        return False


class AnalyzeRequest(BaseModel):
    """Request model with input validation limits."""
    company_name: Optional[str] = Field(None, max_length=500)
    company_url: str = Field(..., max_length=2048)
    focus: Optional[str] = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# HTTP helper – tests monkeypatch _post_json to simulate MCPs
# ---------------------------------------------------------------------------
def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("MCP returned non-dict JSON")
        return data
    except Exception as e:
        logger.error(f"Error calling MCP at {url}: {e}")
        # Uniform failure shape: tests assert behavior when MCPs fail.
        return {"ok": False, "error": str(e)}


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, api_key: str = Header(None, alias="X-API-Key")) -> Dict[str, Any]:
    """
    Get status of a background analysis job.
    Requires authentication and ownership validation.
    Falls back to database if job not in memory (for restart survival).
    """
    # Verify API key if auth is enabled
    effective_key = api_key or "no-auth"
    if AUTH_ENABLED:
        if not api_key or api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Check in-memory first
    job = jobs.get(job_id)
    
    # Fall back to database if not in memory
    if not job:
        db_job = get_job_db(job_id)
        if db_job:
            job = db_job
        else:
            raise HTTPException(status_code=404, detail="Job ID not found")
    
    # Ownership validation: user can only access their own jobs
    if AUTH_ENABLED and job.get("api_key") != effective_key:
        raise HTTPException(status_code=403, detail="Access denied: job belongs to another user")
    
    # Return job without exposing api_key
    return {
        "status": job.get("status"),
        "progress": job.get("progress"),
        "result": job.get("result"),
        "error": job.get("error"),
        "company_url": job.get("company_url"),
        "company_name": job.get("company_name"),
    }


def _run_analysis_task(job_id: str, req: AnalyzeRequest, api_key: str) -> None:
    """
    Background task: orchestrates MCP calls and stores result in jobs dict.
    """
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 10
        save_job(
            job_id=job_id,
            status="running",
            progress=10,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )
        logger.info(f"[Job {job_id}] Starting analysis for URL={req.company_url!r}")

        # 1) Initialize empty OSINT profile
        profile = CompanyOSINTProfile.create_empty_company_profile(
            name=req.company_name,
            url=req.company_url,
        )
        jobs[job_id]["progress"] = 20
        save_job(
            job_id=job_id,
            status="running",
            progress=20,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # 2) Planning step: decide which MCPs to call
        try:
            plan = llm_client.plan_tools(
                company_name=req.company_name,
                company_url=req.company_url,
                focus=req.focus,
            )
            if not isinstance(plan, dict):
                raise TypeError("plan_tools returned non-dict")
        except Exception as e:
            logger.error(f"[Job {job_id}] Planning LLM failed: {e}")
            plan = DEFAULT_TOOL_PLAN.copy()
        
        jobs[job_id]["progress"] = 30
        save_job(
            job_id=job_id,
            status="running",
            progress=30,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # 3) Execute MCPs according to plan (with failure resilience)

        # --- Web scrape (Tier-1 multi-surface) -----------------------------------
        if plan.get("use_web_scrape"):
            try:
                surfaces = fetch_web_surfaces(
                    company_url=req.company_url,
                    web_scrape_endpoint=MCP_WEB_SCRAPE_URL,
                    post_json_fn=_post_json,
                )
                logger.info(f"[Job {job_id}] Web surfaces scraped: %d", len(surfaces))
                web_result = aggregate_web_surfaces(req.company_url, surfaces)
                profile = merge_web_data(profile, web_result)
            except Exception as e:
                logger.error(f"[Job {job_id}] Web scrape failed: {e}")
                # Continue with empty web data
        
        jobs[job_id]["progress"] = 40
        save_job(
            job_id=job_id,
            status="running",
            progress=40,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # For convenience, pull out the web text + meta we just merged
        web_text = ""
        web_meta: Dict[str, Any] = {
            "title": None,
            "description": None,
            "h1": [],
            "h2": [],
        }

        try:
            web = getattr(profile, "web", None)
            if web is not None:
                web_text = getattr(web, "clean_text", "") or ""
                meta_obj = getattr(web, "meta", None)
                if meta_obj is not None:
                    web_meta = {
                        "title": getattr(meta_obj, "title", None),
                        "description": getattr(meta_obj, "description", None),
                        "h1": getattr(meta_obj, "h1", []) or [],
                        "h2": getattr(meta_obj, "h2", []) or [],
                    }
        except Exception as e:
            logger.error(f"[Job {job_id}] Error extracting web text/meta: {e}")

        logger.info(
            f"[Job {job_id}] Web surface summary: text_len=%d, title=%r",
            len(web_text or ""),
            web_meta.get("title"),
        )

        # --- SEO probe ------------------------------------------------------------
        if plan.get("use_seo_probe"):
            try:
                seo_payload: Dict[str, Any] = {
                    "url": req.company_url,
                    "text": web_text,
                    "meta": web_meta,
                }
                seo_result = _post_json(MCP_SEO_PROBE_URL, seo_payload)
                if seo_result.get("ok") is not False:
                    profile = merge_seo_data(profile, seo_result)
                else:
                    logger.warning(f"[Job {job_id}] SEO probe failed: {seo_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] SEO probe exception: {e}")
        
        jobs[job_id]["progress"] = 50
        save_job(
            job_id=job_id,
            status="running",
            progress=50,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # --- Tech stack -----------------------------------------------------------
        if plan.get("use_tech_stack"):
            try:
                # EXTRACT raw_html from the profile for tech stack fingerprinting
                raw_html_for_tech = ""
                try:
                    if hasattr(profile, "web") and profile.web:
                         raw_html_for_tech = getattr(profile.web, "raw_html", "") or ""
                except Exception:
                    pass

                tech_payload: Dict[str, Any] = {
                    "url": req.company_url,
                    "raw_html": raw_html_for_tech,
                }
                tech_result = _post_json(MCP_TECH_STACK_URL, tech_payload)
                if tech_result.get("ok") is not False:
                    profile = merge_tech_stack_data(profile, tech_result)
                else:
                    logger.warning(f"[Job {job_id}] Tech stack failed: {tech_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Tech stack exception: {e}")
        
        jobs[job_id]["progress"] = 60
        save_job(
            job_id=job_id,
            status="running",
            progress=60,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # --- Reviews snapshot -----------------------------------------------------
        if plan.get("use_reviews_snapshot"):
            try:
                reviews_payload = {"url": req.company_url}
                reviews_result = _post_json(MCP_REVIEWS_SNAPSHOT_URL, reviews_payload)
                if reviews_result.get("ok") is not False:
                    profile = merge_reviews_data(profile, reviews_result)
                else:
                    logger.warning(f"[Job {job_id}] Reviews failed: {reviews_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Reviews exception: {e}")
        
        jobs[job_id]["progress"] = 70
        save_job(
            job_id=job_id,
            status="running",
            progress=70,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # --- Social snapshot ------------------------------------------------------
        if plan.get("use_social_snapshot"):
            try:
                social_payload = {"url": req.company_url}
                social_result = _post_json(MCP_SOCIAL_SNAPSHOT_URL, social_payload)
                if social_result.get("ok") is not False:
                    profile = merge_social_data(profile, social_result)
                else:
                    logger.warning(f"[Job {job_id}] Social failed: {social_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Social exception: {e}")
        
        jobs[job_id]["progress"] = 80
        save_job(
            job_id=job_id,
            status="running",
            progress=80,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # --- Careers intel --------------------------------------------------------
        if plan.get("use_careers_intel"):
            try:
                careers_payload = {"url": req.company_url}
                careers_result = _post_json(MCP_CAREERS_INTEL_URL, careers_payload)
                if careers_result.get("ok") is not False:
                    profile = merge_hiring_data(profile, careers_result)
                else:
                    logger.warning(f"[Job {job_id}] Careers failed: {careers_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Careers exception: {e}")
        
        jobs[job_id]["progress"] = 85
        save_job(
            job_id=job_id,
            status="running",
            progress=85,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # --- Ads snapshot ---------------------------------------------------------
        # --- Ads snapshot ---------------------------------------------------------
        # GUARD: Ads service is missing in prototype. Explicitly feature-flagged off.
        ENABLE_ADS_SERVICE = os.getenv("ENABLE_ADS_SERVICE", "0") == "1"
        
        if plan.get("use_ads_snapshot"):
            if ENABLE_ADS_SERVICE:
                try:
                    ads_payload = {"url": req.company_url}
                    ads_result = _post_json(MCP_ADS_SNAPSHOT_URL, ads_payload)
                    if ads_result.get("ok") is not False:
                        profile = merge_ads_data(profile, ads_result)
                    else:
                        logger.warning(f"[Job {job_id}] Ads failed: {ads_result.get('error')}")
                except Exception as e:
                    logger.error(f"[Job {job_id}] Ads exception: {e}")
            else:
                logger.info(f"[Job {job_id}] Ads snapshot skipped (ENABLE_ADS_SERVICE=0)")
                # No-op: profile remains unchanged regarding ads

        
        jobs[job_id]["progress"] = 90

        # 4) Synthesize final report
        # RAW profile (for logging/debugging if needed, but we proceed with Inference)
        raw_profile_dict = profile.model_dump()
        
        # TRANSFORM: Run Interpretive Inference Layer
        inference_engine = InferenceEngine()
        inferred_profile = inference_engine.infer(raw_profile_dict)
        
        # We use the INFERRED profile for synthesis and persistence
        profile_dict = inferred_profile.model_dump()
        
        jobs[job_id]["progress"] = 95
        save_job(
            job_id=job_id,
            status="running",
            progress=95,
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key
        )

        # CHANGE DETECTION: Compare with previous report
        delta_context = None
        try:
            # Get latest 2 reports (index 0 is current if we saved it? No, we haven't saved current report yet.)
            # So get_latest_reports returns previous reports existing in DB.
            history = get_latest_reports(req.company_url, limit=1)
            
            if history:
                prev_report = history[0] # The most recent one
                prev_date = datetime.strptime(prev_report["created_at"], "%Y-%m-%d %H:%M:%S") if isinstance(prev_report["created_at"], str) else prev_report["created_at"]
                
                # We need to reconstruct InferredProfile from the JSON dict
                prev_profile_dict = prev_report["profile"]
                
                # Pydantic reconstruction
                prev_profile = InferredProfile(**prev_profile_dict)
                
                change_detector = ChangeDetector()
                delta_report = change_detector.compute_delta(
                    current=inferred_profile,
                    previous=prev_profile,
                    current_date=datetime.utcnow(),
                    previous_date=prev_date
                )
                
                delta_context = delta_report.model_dump()
                logger.info(f"[Job {job_id}] Computed delta against report {prev_report['id']} (Score: {delta_report.overall_stability_score})")
            else:
                logger.info(f"[Job {job_id}] No history found for delta computation")
        
        except Exception as e:
            logger.error(f"[Job {job_id}] Change detection failed: {e}")
            # Non-blocking failure; proceed without delta

        try:
            report_markdown = llm_client.synthesize_report(
                profile_dict,
                req.focus,
                delta_context=delta_context
            )
        except Exception as e:
            logger.error(f"[Job {job_id}] Synthesis LLM failed: {e}")
            safe_company_name = (
                profile.company.get("name")
                if isinstance(profile.company, dict)
                else str(profile.company)
            )
            report_markdown = (
                f"# OSINT Intelligence Report: {safe_company_name}\n\n"
                "Report generation failed; no detailed web presence summary available. "
                "Upstream LLM synthesis error."
            )

        # 5) Store result in memory and database
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = {
            "profile": profile_dict,
            "report_markdown": report_markdown,
        }
        
        # Persist to database
        try:
            save_report(
                job_id=job_id,
                company_name=req.company_name,
                company_url=req.company_url,
                focus=req.focus,
                profile=profile_dict,
                report_markdown=report_markdown,
                api_key=api_key
            )
            increment_usage(api_key)
            logger.info(f"[Job {job_id}] Report persisted to database")
        except Exception as e:
            logger.error(f"[Job {job_id}] Failed to persist report: {e}")
        
        logger.info(f"[Job {job_id}] Analysis complete")

    except Exception as e:
        logger.exception(f"[Job {job_id}] Fatal error during analysis")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        save_job(
            job_id=job_id,
            status="failed",
            progress=jobs[job_id]["progress"],
            company_url=req.company_url,
            company_name=req.company_name,
            focus=req.focus,
            api_key=api_key,
            error=str(e)
        )


@app.post("/analyze")
def analyze(req: AnalyzeRequest, api_key: str = Header(None, alias="X-API-Key")) -> Dict[str, Any]:
    """
    Run analysis synchronously and return {profile, report_markdown}.
    
    Requirement 1: Must return JSON keys exactly {"profile", "report_markdown"}.
    Requirement 2: Auth must be enforced BEFORE rate limiting.
    """
    # REQUIREMENT 2: Auth check first - before rate limiting
    effective_key = api_key or "no-auth"
    if AUTH_ENABLED:
        if not api_key or api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Rate limiting (after auth, so 401 is returned before 429)
    if not check_rate_limit(effective_key):
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded: max {MAX_REQUESTS_PER_MINUTE} requests per minute"
        )
    
    # SSRF protection: validate URL before processing
    if not validate_company_url(req.company_url):
        raise HTTPException(
            status_code=400, 
            detail="Invalid company_url: must be a public http/https URL (no localhost, internal IPs, or cloud metadata)"
        )
    
    # Quota enforcement (bypassed during pytest via check_rate_limit logic)
    if not _is_pytest_running():
        is_allowed, remaining = check_quota(effective_key)
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Daily quota exceeded: limit is {DAILY_QUOTA_PER_KEY} reports per day"
            )
    
    # Run analysis synchronously to return direct result
    job_id = str(uuid4())
    logger.info(f"[Job {job_id}] Starting synchronous analysis for URL={req.company_url!r}")
    
    # 1) Initialize empty OSINT profile
    profile = CompanyOSINTProfile.create_empty_company_profile(
        name=req.company_name,
        url=req.company_url,
    )
    
    # 2) Planning step: decide which MCPs to call
    try:
        plan = llm_client.plan_tools(
            company_name=req.company_name,
            company_url=req.company_url,
            focus=req.focus,
        )
        if not isinstance(plan, dict):
            raise TypeError("plan_tools returned non-dict")
    except Exception as e:
        logger.error(f"[Job {job_id}] Planning LLM failed: {e}")
        plan = DEFAULT_TOOL_PLAN.copy()
    
    # 3) Execute MCPs according to plan (with failure resilience)
    
    # --- Web scrape (Tier-1 multi-surface) ---
    if plan.get("use_web_scrape"):
        try:
            surfaces = fetch_web_surfaces(
                company_url=req.company_url,
                web_scrape_endpoint=MCP_WEB_SCRAPE_URL,
                post_json_fn=_post_json,
            )
            logger.info(f"[Job {job_id}] Web surfaces scraped: %d", len(surfaces))
            web_result = aggregate_web_surfaces(req.company_url, surfaces)
            profile = merge_web_data(profile, web_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] Web scrape failed: {e}")
    
    # Extract web text + meta for downstream MCPs
    web_text = ""
    web_meta: Dict[str, Any] = {"title": None, "description": None, "h1": [], "h2": []}
    try:
        web = getattr(profile, "web", None)
        if web is not None:
            web_text = getattr(web, "clean_text", "") or ""
            meta_obj = getattr(web, "meta", None)
            if meta_obj is not None:
                web_meta = {
                    "title": getattr(meta_obj, "title", None),
                    "description": getattr(meta_obj, "description", None),
                    "h1": getattr(meta_obj, "h1", []) or [],
                    "h2": getattr(meta_obj, "h2", []) or [],
                }
    except Exception as e:
        logger.error(f"[Job {job_id}] Error extracting web text/meta: {e}")
    
    # --- SEO probe ---
    if plan.get("use_seo_probe"):
        try:
            seo_payload = {"url": req.company_url, "text": web_text, "meta": web_meta}
            seo_result = _post_json(MCP_SEO_PROBE_URL, seo_payload)
            if seo_result.get("ok") is not False:
                profile = merge_seo_data(profile, seo_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] SEO probe exception: {e}")
    
    # --- Tech stack ---
    if plan.get("use_tech_stack"):
        try:
            raw_html_for_tech = ""
            if hasattr(profile, "web") and profile.web:
                raw_html_for_tech = getattr(profile.web, "raw_html", "") or ""
            tech_payload = {"url": req.company_url, "raw_html": raw_html_for_tech}
            tech_result = _post_json(MCP_TECH_STACK_URL, tech_payload)
            if tech_result.get("ok") is not False:
                profile = merge_tech_stack_data(profile, tech_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] Tech stack exception: {e}")
    
    # --- Reviews snapshot ---
    if plan.get("use_reviews_snapshot"):
        try:
            reviews_result = _post_json(MCP_REVIEWS_SNAPSHOT_URL, {"url": req.company_url})
            if reviews_result.get("ok") is not False:
                profile = merge_reviews_data(profile, reviews_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] Reviews exception: {e}")
    
    # --- Social snapshot ---
    if plan.get("use_social_snapshot"):
        try:
            social_result = _post_json(MCP_SOCIAL_SNAPSHOT_URL, {"url": req.company_url})
            if social_result.get("ok") is not False:
                profile = merge_social_data(profile, social_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] Social exception: {e}")
    
    # --- Careers intel ---
    if plan.get("use_careers_intel"):
        try:
            careers_result = _post_json(MCP_CAREERS_INTEL_URL, {"url": req.company_url})
            if careers_result.get("ok") is not False:
                profile = merge_hiring_data(profile, careers_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] Careers exception: {e}")
    
    # --- Ads snapshot ---
    ENABLE_ADS_SERVICE = os.getenv("ENABLE_ADS_SERVICE", "0") == "1"
    if plan.get("use_ads_snapshot") and ENABLE_ADS_SERVICE:
        try:
            ads_result = _post_json(MCP_ADS_SNAPSHOT_URL, {"url": req.company_url})
            if ads_result.get("ok") is not False:
                profile = merge_ads_data(profile, ads_result)
        except Exception as e:
            logger.error(f"[Job {job_id}] Ads exception: {e}")
    
    # 4) Run inference and synthesize report
    raw_profile_dict = profile.model_dump()
    inference_engine = InferenceEngine()
    inferred_profile = inference_engine.infer(raw_profile_dict)
    profile_dict = inferred_profile.model_dump()
    
    # Change detection (optional) - compute delta but inject AFTER synthesis
    delta_report = None  # Will hold DeltaReport object if prior snapshot exists
    try:
        history = get_latest_reports(req.company_url, limit=1)
        if history:
            prev_report = history[0]
            prev_date = datetime.strptime(prev_report["created_at"], "%Y-%m-%d %H:%M:%S") if isinstance(prev_report["created_at"], str) else prev_report["created_at"]
            prev_profile = InferredProfile(**prev_report["profile"])
            change_detector = ChangeDetector()
            delta_report = change_detector.compute_delta(
                current=inferred_profile,
                previous=prev_profile,
                current_date=datetime.utcnow(),
                previous_date=prev_date
            )
    except Exception as e:
        logger.error(f"[Job {job_id}] Change detection failed: {e}")
    
    # Synthesize report WITHOUT delta_context (avoid signature issues with Ollama client)
    try:
        report_markdown = llm_client.synthesize_report(profile_dict, req.focus)
    except Exception as e:
        logger.error(f"[Job {job_id}] Synthesis LLM failed: {e}")
        safe_company_name = profile.company.get("name") if isinstance(profile.company, dict) else str(profile.company)
        report_markdown = (
            f"# OSINT Intelligence Report: {safe_company_name}\n\n"
            "Report generation failed; no detailed web presence summary available. "
            "Upstream LLM synthesis error.\n\n"
            "## 8. Strategic Recommendations\n\n"
            "Unable to generate recommendations due to synthesis failure."
        )
    
    # Append delta section AFTER synthesis (Time-Delta v1)
    report_markdown += delta_to_markdown(delta_report)
    
    # Append Wayback delta section if enabled (Wayback v1)
    if ENABLE_WAYBACK and not _is_pytest_running():
        try:
            # Extract current signals from live HTML if available
            current_signals = None
            try:
                if hasattr(profile, "web") and profile.web:
                    live_html = getattr(profile.web, "raw_html", None)
                    if live_html:
                        current_signals = extract_wayback_signals(live_html)
            except Exception as e:
                logger.warning(f"[Job {job_id}] Could not extract current signals: {e}")
            
            historical = get_historical_snapshots(req.company_url)
            if historical or current_signals:
                wayback_section = wayback_delta_to_markdown(current_signals, historical)
                report_markdown += wayback_section
        except Exception as e:
            logger.error(f"[Job {job_id}] Wayback delta failed: {e}")
    
    
    # Persist report if not in pytest
    if not _is_pytest_running():
        try:
            save_report(
                job_id=job_id,
                company_name=req.company_name,
                company_url=req.company_url,
                focus=req.focus,
                profile=profile_dict,
                report_markdown=report_markdown,
                api_key=effective_key
            )
            increment_usage(effective_key)
        except Exception as e:
            logger.error(f"[Job {job_id}] Failed to persist report: {e}")
    
    logger.info(f"[Job {job_id}] Analysis complete")
    
    # REQUIREMENT 1: Return exactly {"profile", "report_markdown"}
    return {
        "profile": profile_dict,
        "report_markdown": report_markdown,
    }


@app.get("/reports/{job_id}/pdf")
def export_pdf(job_id: str, api_key: str = Header(None, alias="X-API-Key")) -> Response:
    """
    Export a completed report as PDF.
    """
    # Verify API key if auth is enabled
    if AUTH_ENABLED:
        if not api_key or api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Try to get from database first
    report = get_report(job_id)
    
    if not report:
        # Fallback to in-memory jobs
        job = jobs.get(job_id)
        if not job or job.get("status") != "complete":
            raise HTTPException(status_code=404, detail="Report not found or not yet complete")
        
        # Ownership validation for in-memory jobs
        if AUTH_ENABLED and job.get("api_key") != api_key:
            raise HTTPException(status_code=403, detail="Access denied: report belongs to another user")
        
        report_markdown = job["result"]["report_markdown"]
        company_name = job.get("company_name", "Company")
    else:
        # Ownership validation for database reports
        if AUTH_ENABLED and report.get("api_key") != api_key:
            raise HTTPException(status_code=403, detail="Access denied: report belongs to another user")
        
        report_markdown = report["report_markdown"]
        company_name = report.get("company_name", "Company")
    
    try:
        pdf_bytes = markdown_to_pdf(report_markdown, company_name)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=osint_report_{job_id[:8]}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation failed for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

