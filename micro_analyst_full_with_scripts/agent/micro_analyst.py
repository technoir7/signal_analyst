import os
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
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


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Main entrypoint: orchestrates MCP calls and returns full OSINT profile + report.
    """
    logger.info(f"Received analysis request for URL={req.company_url!r}")

    # 1) Initialize empty OSINT profile
    profile = CompanyOSINTProfile.create_empty_company_profile(
        name=req.company_name,
        url=req.company_url,
    )

    # 2) Planning step: decide which MCPs to call
    try:
        plan = llm_client.plan_tools(
            req.company_name,
            req.company_url,
            req.focus,
        )
        if not isinstance(plan, dict):
            raise TypeError("plan_tools returned non-dict")
    except Exception as e:
        logger.error(f"Planning LLM failed: {e}")
        plan = DEFAULT_TOOL_PLAN.copy()

    # 3) Execute MCPs according to plan
    # --- Web scrape -----------------------------------------------------------
    if plan.get("use_web_scrape"):
        web_payload = {"url": req.company_url}
        web_result = _post_json(MCP_WEB_SCRAPE_URL, web_payload)
        profile = merge_web_data(profile, web_result)

    # --- SEO probe ------------------------------------------------------------
    if plan.get("use_seo_probe"):
        seo_payload = {"url": req.company_url}
        seo_result = _post_json(MCP_SEO_PROBE_URL, seo_payload)
        profile = merge_seo_data(profile, seo_result)

    # --- Tech stack -----------------------------------------------------------
    if plan.get("use_tech_stack"):
        tech_payload = {"url": req.company_url}
        tech_result = _post_json(MCP_TECH_STACK_URL, tech_payload)
        profile = merge_tech_stack_data(profile, tech_result)

    # --- Reviews snapshot -----------------------------------------------------
    if plan.get("use_reviews_snapshot"):
        reviews_payload = {"url": req.company_url}
        reviews_result = _post_json(MCP_REVIEWS_SNAPSHOT_URL, reviews_payload)
        profile = merge_reviews_data(profile, reviews_result)

    # --- Social snapshot ------------------------------------------------------
    if plan.get("use_social_snapshot"):
        social_payload = {"url": req.company_url}
        social_result = _post_json(MCP_SOCIAL_SNAPSHOT_URL, social_payload)
        profile = merge_social_data(profile, social_result)

    # --- Careers intel --------------------------------------------------------
    if plan.get("use_careers_intel"):
        careers_payload = {"url": req.company_url}
        careers_result = _post_json(MCP_CAREERS_INTEL_URL, careers_payload)
        profile = merge_hiring_data(profile, careers_result)

    # --- Ads snapshot --------------------------------------------------------
    if plan.get("use_ads_snapshot"):
        ads_payload = {"url": req.company_url}
        ads_result = _post_json(MCP_ADS_SNAPSHOT_URL, ads_payload)
        profile = merge_ads_data(profile, ads_result)

    # 4) Synthesize final report
    profile_dict = profile.model_dump()

    try:
        report_markdown = llm_client.synthesize_report(
            profile_dict,
            req.focus,
        )
    except Exception as e:
        logger.error(f"Synthesis LLM failed: {e}")
        safe_company_name = (
            profile.company.get("name")
            if isinstance(profile.company, dict)
            else str(profile.company)
        )
        # The exact phrase below is asserted in tests.
        report_markdown = (
            f"# OSINT Intelligence Report: {safe_company_name}\n\n"
            "Report generation failed; no detailed web presence summary available. "
            "Upstream LLM synthesis error."
        )

    return {
        "profile": profile_dict,
        "report_markdown": report_markdown,
    }
