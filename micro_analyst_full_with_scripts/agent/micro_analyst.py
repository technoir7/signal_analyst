import os
from typing import Optional, Dict, Any
from uuid import uuid4

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from core.data_models import CompanyOSINTProfile
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
from utils.persistence import init_db, save_report, get_report, increment_usage, markdown_to_pdf
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

# CORS for local UI / other tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev: permissive
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
VALID_API_KEYS = set(os.getenv("VALID_API_KEYS", "").split(","))
AUTH_ENABLED = bool(os.getenv("ENABLE_AUTH", "0") == "1")

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key if auth is enabled."""
    if not AUTH_ENABLED:
        return "no-auth"
    if not x_api_key or x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


class AnalyzeRequest(BaseModel):
    company_name: Optional[str] = None
    company_url: str
    focus: Optional[str] = None


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
def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of a background analysis job."""
    job = jobs.get(job_id)
    if not job:
        return {"status": "not_found", "error": "Job ID not found"}
    return job


def _run_analysis_task(job_id: str, req: AnalyzeRequest, api_key: str) -> None:
    """
    Background task: orchestrates MCP calls and stores result in jobs dict.
    """
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 10
        logger.info(f"[Job {job_id}] Starting analysis for URL={req.company_url!r}")

        # 1) Initialize empty OSINT profile
        profile = CompanyOSINTProfile.create_empty_company_profile(
            name=req.company_name,
            url=req.company_url,
        )
        jobs[job_id]["progress"] = 20

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

        # --- Tech stack -----------------------------------------------------------
        if plan.get("use_tech_stack"):
            try:
                tech_payload: Dict[str, Any] = {
                    "url": req.company_url,
                    "text": web_text,
                }
                tech_result = _post_json(MCP_TECH_STACK_URL, tech_payload)
                if tech_result.get("ok") is not False:
                    profile = merge_tech_stack_data(profile, tech_result)
                else:
                    logger.warning(f"[Job {job_id}] Tech stack failed: {tech_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Tech stack exception: {e}")
        
        jobs[job_id]["progress"] = 60

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

        # --- Ads snapshot ---------------------------------------------------------
        if plan.get("use_ads_snapshot"):
            try:
                ads_payload = {"url": req.company_url}
                ads_result = _post_json(MCP_ADS_SNAPSHOT_URL, ads_payload)
                if ads_result.get("ok") is not False:
                    profile = merge_ads_data(profile, ads_result)
                else:
                    logger.warning(f"[Job {job_id}] Ads failed: {ads_result.get('error')}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Ads exception: {e}")
        
        jobs[job_id]["progress"] = 90

        # 4) Synthesize final report
        profile_dict = profile.model_dump()
        jobs[job_id]["progress"] = 95

        try:
            report_markdown = llm_client.synthesize_report(
                profile_dict,
                req.focus,
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


@app.post("/analyze")
def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks, api_key: str = Header(None, alias="X-API-Key")) -> Dict[str, Any]:
    """
    Start a background analysis job and return job ID immediately.
    """
    # Verify API key if auth is enabled
    if AUTH_ENABLED:
        if not api_key or api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    job_id = str(uuid4())
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
        "company_url": req.company_url,
        "company_name": req.company_name,
    }
    
    background_tasks.add_task(_run_analysis_task, job_id, req, api_key or "no-auth")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Analysis started. Poll /jobs/{job_id} for status."
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
        
        report_markdown = job["result"]["report_markdown"]
        company_name = job.get("company_name", "Company")
    else:
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

