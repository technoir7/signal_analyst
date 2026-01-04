"""
FastAPI Router for SaaS Cohort Mode v1.

Provides 4 endpoints:
- POST /cohorts/propose
- POST /cohorts/{cohort_id}/confirm
- POST /cohorts/{cohort_id}/analyze
- GET /cohorts/{cohort_id}/results
"""
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from loguru import logger

from core.cohort_schemas import (
    CohortProposeRequest,
    CohortConfirmRequest,
    CohortProposeResponse,
    CohortConfirmResponse,
    CohortAnalyzeResponse,
    CohortResultsResponse,
)
from agent.cohort import (
    propose_cohort,
    confirm_cohort,
    start_cohort_analysis,
    build_cohort_matrix,
    generate_cohort_report,
)
from utils.persistence import get_cohort, save_cohort, get_job_db

# Create router with /cohorts prefix (added when including in main app)
router = APIRouter(tags=["cohorts"])


# ---------------------------------------------------------------------------
# Helper to verify API key (mirrors main app logic)
# ---------------------------------------------------------------------------

import os
VALID_API_KEYS = set(k.strip() for k in os.getenv("VALID_API_KEYS", "").split(",") if k.strip())
AUTH_ENABLED = bool(os.getenv("ENABLE_AUTH", "1") == "1")


def verify_api_key_cohort(x_api_key: Optional[str]) -> str:
    """Verify API key if auth is enabled."""
    if not AUTH_ENABLED:
        return "anonymous"
    if not x_api_key or x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/propose", response_model=CohortProposeResponse)
def cohort_propose(
    req: CohortProposeRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> CohortProposeResponse:
    """
    Propose a peer cohort for an anchor URL.
    
    Returns candidate list with sources and rationale.
    User must review and confirm before analysis.
    """
    api_key = verify_api_key_cohort(x_api_key)
    
    try:
        result = propose_cohort(
            anchor_url=req.anchor_url,
            k=req.k,
            category_hint=req.category_hint,
            api_key=api_key
        )
        logger.info(f"Proposed cohort {result.cohort_id} with {len(result.candidates)} candidates")
        return result
    except Exception as e:
        logger.error(f"Cohort proposal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{cohort_id}/confirm", response_model=CohortConfirmResponse)
def cohort_confirm(
    cohort_id: str,
    req: CohortConfirmRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> CohortConfirmResponse:
    """
    Confirm a cohort for analysis.
    
    User selects which candidates to include.
    Optionally includes anchor in the analysis.
    """
    verify_api_key_cohort(x_api_key)
    
    try:
        result = confirm_cohort(
            cohort_id=cohort_id,
            final_urls=req.final_urls,
            include_anchor=req.include_anchor
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cohort confirmation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{cohort_id}/analyze", response_model=CohortAnalyzeResponse)
def cohort_analyze(
    cohort_id: str,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> CohortAnalyzeResponse:
    """
    Start analysis for all confirmed targets.
    
    Fans out to existing single-URL analysis pipeline.
    Returns list of job IDs for tracking.
    """
    api_key = verify_api_key_cohort(x_api_key)
    
    # Import here to avoid circular imports
    from agent.micro_analyst import analyze, AnalyzeRequest, jobs
    from uuid import uuid4
    
    def create_analysis_job(url: str, api_key: str) -> str:
        """Create a single-URL analysis job."""
        # Create minimal request
        req = AnalyzeRequest(
            company_url=url,
            company_name=None,
            focus="SaaS cohort analysis"
        )
        
        # Generate job ID
        job_id = str(uuid4())
        
        # Import the background task runner
        from agent.micro_analyst import _run_analysis_task
        
        # Initialize job in memory
        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "company_url": url,
            "company_name": None,
            "focus": "SaaS cohort analysis",
            "api_key": api_key,
            "result": None,
            "error": None,
        }
        
        # Run in background
        background_tasks.add_task(_run_analysis_task, job_id, req, api_key)
        
        return job_id
    
    try:
        result = start_cohort_analysis(
            cohort_id=cohort_id,
            analyze_fn=lambda url, key: create_analysis_job(url, key),
            api_key=api_key
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cohort analysis start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{cohort_id}/results", response_model=CohortResultsResponse)
def cohort_results(
    cohort_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> CohortResultsResponse:
    """
    Get cohort analysis results.
    
    Returns normalized comparison matrix and markdown report.
    Only available after all jobs complete.
    """
    verify_api_key_cohort(x_api_key)
    
    # Import here to avoid circular imports
    from agent.micro_analyst import jobs
    
    cohort = get_cohort(cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail=f"Cohort {cohort_id} not found")
    
    # Check job completion status
    job_ids = cohort.get("job_ids", [])
    if not job_ids:
        return CohortResultsResponse(
            cohort_id=cohort_id,
            anchor_url=cohort["anchor_url"],
            status=cohort["status"],
            matrix=None,
            report_markdown=None
        )
    
    # Check if all jobs are complete
    def get_job_result(job_id: str):
        # Try in-memory first, then database
        if job_id in jobs:
            return jobs[job_id]
        return get_job_db(job_id)
    
    all_complete = True
    for job_id in job_ids:
        job = get_job_result(job_id)
        if not job or job.get("status") not in ("complete", "failed"):
            all_complete = False
            break
    
    if not all_complete:
        # Return progress status
        complete_count = sum(
            1 for jid in job_ids
            if (j := get_job_result(jid)) and j.get("status") in ("complete", "failed")
        )
        return CohortResultsResponse(
            cohort_id=cohort_id,
            anchor_url=cohort["anchor_url"],
            status=f"analyzing ({complete_count}/{len(job_ids)} complete)",
            matrix=None,
            report_markdown=None
        )
    
    # Build matrix and report
    try:
        matrix = build_cohort_matrix(cohort_id, get_job_result)
        report_md = generate_cohort_report(matrix, cohort["anchor_url"])
        
        # Persist results
        save_cohort(
            cohort_id=cohort_id,
            anchor_url=cohort["anchor_url"],
            category_hint=cohort["category_hint"],
            status="complete",
            matrix=matrix.model_dump(),
            report_md=report_md,
            api_key=cohort.get("api_key")
        )
        
        return CohortResultsResponse(
            cohort_id=cohort_id,
            anchor_url=cohort["anchor_url"],
            status="complete",
            matrix=matrix,
            report_markdown=report_md
        )
    except Exception as e:
        logger.error(f"Cohort results generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
