"""
Core Cohort Logic for SaaS v1.

Orchestrates cohort discovery, confirmation, analysis fan-out, and matrix normalization.
"""
import re
from typing import Dict, Any, List, Optional
from uuid import uuid4
from loguru import logger

from core.cohort_schemas import (
    CohortCandidate,
    CohortProposeResponse,
    CohortConfirmResponse,
    CohortAnalyzeResponse,
    TargetSignals,
    CohortNorms,
    CohortOutlier,
    CohortMatrix,
    CohortResultsResponse,
)
from utils.cohort_discovery import discover_cohort, extract_domain
from utils.persistence import save_cohort, get_cohort, update_cohort_status


# ---------------------------------------------------------------------------
# Cohort Proposal
# ---------------------------------------------------------------------------

def propose_cohort(
    anchor_url: str,
    k: int = 8,
    category_hint: Optional[str] = None,
    api_key: Optional[str] = None
) -> CohortProposeResponse:
    """
    Propose a peer cohort for an anchor URL.
    
    1. Fetches anchor page
    2. Extracts category terms
    3. Runs web search + G2 scraping
    4. Filters and ranks candidates
    5. Persists proposal
    """
    cohort_id = str(uuid4())
    logger.info(f"[Cohort {cohort_id}] Proposing cohort for {anchor_url}")
    
    # Discover candidates
    candidates_raw, category_terms, sources = discover_cohort(
        anchor_url=anchor_url,
        category_hint=category_hint,
        k=k
    )
    
    # Convert to CohortCandidate models
    candidates = []
    for c in candidates_raw:
        candidates.append(CohortCandidate(
            url=c["url"],
            name=c.get("name", extract_domain(c["url"])),
            source=c.get("source", "search"),
            rationale=c.get("rationale", "Discovered via search")[:200],
            confidence=c.get("confidence", "low")
        ))
    
    # Extract anchor name
    anchor_name = extract_domain(anchor_url)
    
    # Persist proposal
    save_cohort(
        cohort_id=cohort_id,
        anchor_url=anchor_url,
        category_hint=category_hint,
        status="proposed",
        candidates=[c.model_dump() for c in candidates],
        api_key=api_key
    )
    
    return CohortProposeResponse(
        cohort_id=cohort_id,
        anchor_url=anchor_url,
        anchor_name=anchor_name,
        extracted_terms=category_terms,
        candidates=candidates,
        discovery_sources=sources
    )


# ---------------------------------------------------------------------------
# Cohort Confirmation
# ---------------------------------------------------------------------------

def confirm_cohort(
    cohort_id: str,
    final_urls: List[str],
    include_anchor: bool = True
) -> CohortConfirmResponse:
    """
    Confirm a cohort for analysis.
    
    1. Validates cohort exists
    2. Stores confirmed URLs
    3. Updates status
    """
    cohort = get_cohort(cohort_id)
    if not cohort:
        raise ValueError(f"Cohort {cohort_id} not found")
    
    if cohort["status"] != "proposed":
        raise ValueError(f"Cohort {cohort_id} is not in 'proposed' status (current: {cohort['status']})")
    
    # Build confirmed list
    confirmed = list(final_urls)
    if include_anchor and cohort["anchor_url"] not in confirmed:
        confirmed.insert(0, cohort["anchor_url"])
    
    # Update persistence
    save_cohort(
        cohort_id=cohort_id,
        anchor_url=cohort["anchor_url"],
        category_hint=cohort["category_hint"],
        status="confirmed",
        confirmed_urls=confirmed,
        api_key=cohort.get("api_key")
    )
    
    logger.info(f"[Cohort {cohort_id}] Confirmed {len(confirmed)} URLs for analysis")
    
    return CohortConfirmResponse(
        cohort_id=cohort_id,
        confirmed_urls=confirmed,
        status="confirmed"
    )


# ---------------------------------------------------------------------------
# Cohort Analysis (Fan-out)
# ---------------------------------------------------------------------------

def start_cohort_analysis(
    cohort_id: str,
    analyze_fn,  # Callable that creates analysis jobs
    api_key: str
) -> CohortAnalyzeResponse:
    """
    Start analysis for all confirmed targets.
    
    Uses the existing single-URL analysis pipeline.
    """
    cohort = get_cohort(cohort_id)
    if not cohort:
        raise ValueError(f"Cohort {cohort_id} not found")
    
    if cohort["status"] != "confirmed":
        raise ValueError(f"Cohort {cohort_id} is not confirmed (current: {cohort['status']})")
    
    confirmed_urls = cohort["confirmed_urls"]
    if not confirmed_urls:
        raise ValueError(f"Cohort {cohort_id} has no confirmed URLs")
    
    # Fan out to existing analyze endpoint
    job_ids = []
    for url in confirmed_urls:
        try:
            job_id = analyze_fn(url, api_key)
            job_ids.append(job_id)
            logger.info(f"[Cohort {cohort_id}] Started job {job_id} for {url}")
        except Exception as e:
            logger.error(f"[Cohort {cohort_id}] Failed to start job for {url}: {e}")
    
    # Update cohort with job IDs
    save_cohort(
        cohort_id=cohort_id,
        anchor_url=cohort["anchor_url"],
        category_hint=cohort["category_hint"],
        status="analyzing",
        job_ids=job_ids,
        api_key=api_key
    )
    
    return CohortAnalyzeResponse(
        cohort_id=cohort_id,
        job_ids=job_ids,
        status="analyzing"
    )


# ---------------------------------------------------------------------------
# Matrix Normalization
# ---------------------------------------------------------------------------

def normalize_job_result(job_result: Dict[str, Any], url: str) -> TargetSignals:
    """
    Extract normalized signals from a completed job result.
    
    Maps raw profile data to CMATRIX_001 fields.
    """
    profile = job_result.get("result", {})
    evidence = []
    fetch_limits = []
    
    # Tech stack
    tech = profile.get("tech_stack", {})
    tech_confidence = tech.get("confidence", "none")
    probable_cms = tech.get("probable_cms") or tech.get("detected_cms") or tech.get("cms")
    if tech.get("error"):
        fetch_limits.append(f"Tech: {tech['error']}")
    if tech.get("evidence"):
        evidence.extend(tech["evidence"][:2])
    
    # Web presence for pricing/docs detection
    web = profile.get("web", {})
    web_text = (web.get("raw_html") or web.get("text") or "").lower()
    pricing_visible = any(kw in web_text for kw in ["pricing", "plans", "price", "/pricing"])
    docs_visible = any(kw in web_text for kw in ["/docs", "/documentation", "api-docs", "developer"])
    if web.get("error"):
        fetch_limits.append(f"Web: {web['error']}")
    
    # SEO
    seo = profile.get("seo", {})
    seo_issues = (seo.get("meta_issues") or []) + (seo.get("heading_issues") or [])
    if seo.get("error"):
        seo_hygiene = "unknown"
        fetch_limits.append(f"SEO: {seo['error']}")
    elif len(seo_issues) == 0:
        seo_hygiene = "good"
    elif len(seo_issues) <= 3:
        seo_hygiene = "fair"
    else:
        seo_hygiene = "poor"
    
    # Hiring
    hiring = profile.get("hiring", {})
    jobs_visible = bool(hiring.get("open_roles"))
    if hiring.get("error"):
        fetch_limits.append(f"Hiring: {hiring['error']}")
    
    # Ads
    ads = profile.get("ads", {})
    paid_ads_detected = bool(ads.get("platforms"))
    if ads.get("error"):
        fetch_limits.append(f"Ads: {ads['error']}")
    
    # Social
    social = profile.get("social", {})
    has_social = any(social.get(k) for k in ["twitter", "linkedin", "instagram", "youtube"])
    social_visibility = "high" if has_social else "none"
    if social.get("error"):
        fetch_limits.append(f"Social: {social['error']}")
    
    # Reviews
    reviews = profile.get("reviews", {})
    review_visibility = bool(reviews.get("summary"))
    if reviews.get("error"):
        fetch_limits.append(f"Reviews: {reviews['error']}")
    
    # Name extraction
    company = profile.get("company", {})
    name = company.get("name") or extract_domain(url)
    
    return TargetSignals(
        url=url,
        name=name,
        tech_confidence=tech_confidence,
        probable_cms=probable_cms,
        pricing_visible=pricing_visible,
        docs_visible=docs_visible,
        jobs_visible=jobs_visible,
        paid_ads_detected=paid_ads_detected,
        seo_hygiene=seo_hygiene,
        social_visibility=social_visibility,
        review_visibility=review_visibility,
        evidence_snippets=evidence[:5],
        fetch_limits=fetch_limits[:5]
    )


def compute_cohort_norms(targets: List[TargetSignals]) -> CohortNorms:
    """Compute quantified norms across the cohort."""
    n = len(targets)
    if n == 0:
        return CohortNorms(total_targets=0, pricing_visible_count=0, docs_visible_count=0,
                          jobs_visible_count=0, paid_ads_count=0, seo_good_count=0,
                          social_high_count=0, review_visible_count=0)
    
    pricing_count = sum(1 for t in targets if t.pricing_visible)
    docs_count = sum(1 for t in targets if t.docs_visible)
    jobs_count = sum(1 for t in targets if t.jobs_visible)
    ads_count = sum(1 for t in targets if t.paid_ads_detected)
    seo_good_count = sum(1 for t in targets if t.seo_hygiene == "good")
    social_high_count = sum(1 for t in targets if t.social_visibility == "high")
    review_count = sum(1 for t in targets if t.review_visibility)
    
    return CohortNorms(
        total_targets=n,
        pricing_visible_count=pricing_count,
        docs_visible_count=docs_count,
        jobs_visible_count=jobs_count,
        paid_ads_count=ads_count,
        seo_good_count=seo_good_count,
        social_high_count=social_high_count,
        review_visible_count=review_count,
        pricing_visible_pct=round(pricing_count / n * 100, 1),
        docs_visible_pct=round(docs_count / n * 100, 1)
    )


def find_outliers(targets: List[TargetSignals], norms: CohortNorms) -> List[CohortOutlier]:
    """Find targets that deviate significantly from norms."""
    if norms.total_targets < 3:
        return []
    
    outliers = []
    n = norms.total_targets
    
    # Threshold: if majority (>50%) has a signal, absence is deviation and vice versa
    majority_pricing = norms.pricing_visible_count > n / 2
    majority_docs = norms.docs_visible_count > n / 2
    majority_jobs = norms.jobs_visible_count > n / 2
    majority_social = norms.social_high_count > n / 2
    
    for t in targets:
        deviations = []
        direction_up = 0
        direction_down = 0
        
        if majority_pricing and not t.pricing_visible:
            deviations.append("No visible pricing (norm: visible)")
            direction_down += 1
        elif not majority_pricing and t.pricing_visible:
            deviations.append("Visible pricing (norm: hidden)")
            direction_up += 1
        
        if majority_docs and not t.docs_visible:
            deviations.append("No visible docs (norm: visible)")
            direction_down += 1
        elif not majority_docs and t.docs_visible:
            deviations.append("Visible docs (norm: hidden)")
            direction_up += 1
        
        if majority_jobs and not t.jobs_visible:
            deviations.append("No visible jobs (norm: visible)")
            direction_down += 1
        elif not majority_jobs and t.jobs_visible:
            deviations.append("Visible jobs (norm: hidden)")
            direction_up += 1
        
        if majority_social and t.social_visibility == "none":
            deviations.append("No social presence (norm: present)")
            direction_down += 1
        elif not majority_social and t.social_visibility == "high":
            deviations.append("High social presence (norm: low)")
            direction_up += 1
        
        # Only count as outlier if 2+ deviations
        if len(deviations) >= 2:
            direction = "above" if direction_up > direction_down else "below" if direction_down > direction_up else "mixed"
            outliers.append(CohortOutlier(
                url=t.url,
                deviations=deviations,
                direction=direction
            ))
    
    return outliers


def build_cohort_matrix(
    cohort_id: str,
    get_job_fn  # Callable to get job results
) -> CohortMatrix:
    """
    Build the complete comparison matrix from completed jobs.
    """
    cohort = get_cohort(cohort_id)
    if not cohort:
        raise ValueError(f"Cohort {cohort_id} not found")
    
    job_ids = cohort.get("job_ids", [])
    confirmed_urls = cohort.get("confirmed_urls", [])
    anchor_url = cohort["anchor_url"]
    
    # Collect normalized signals
    targets: List[TargetSignals] = []
    for i, job_id in enumerate(job_ids):
        url = confirmed_urls[i] if i < len(confirmed_urls) else f"unknown_{i}"
        
        job_result = get_job_fn(job_id)
        if job_result and job_result.get("status") == "complete":
            signals = normalize_job_result(job_result, url)
            targets.append(signals)
        else:
            # Job not complete or failed
            targets.append(TargetSignals(
                url=url,
                fetch_limits=[f"Job {job_id} not complete"]
            ))
    
    # Compute norms and outliers
    norms = compute_cohort_norms(targets)
    outliers = find_outliers(targets, norms)
    
    # Find anchor deviations
    anchor_deviations = []
    anchor_target = next((t for t in targets if t.url == anchor_url), None)
    if anchor_target:
        for outlier in outliers:
            if outlier.url == anchor_url:
                anchor_deviations = outlier.deviations
                break
    
    return CohortMatrix(
        targets=targets,
        norms=norms,
        outliers=outliers,
        anchor_deviations=anchor_deviations
    )


# ---------------------------------------------------------------------------
# Comparative Report Generation
# ---------------------------------------------------------------------------

def generate_cohort_report(matrix: CohortMatrix, anchor_url: str) -> str:
    """
    Generate comparative markdown report from cohort matrix.
    """
    lines = []
    n = matrix.norms.total_targets
    
    lines.append("# SaaS Cohort Comparative Analysis\n")
    lines.append(f"_Anchor: {anchor_url}_\n")
    lines.append(f"_Cohort Size: {n} targets_\n\n")
    
    # Cohort Norms
    lines.append("## Cohort Norms\n")
    lines.append(f"- **Pricing Visible**: {matrix.norms.pricing_visible_count}/{n} ({matrix.norms.pricing_visible_pct}%)\n")
    lines.append(f"- **Docs Visible**: {matrix.norms.docs_visible_count}/{n} ({matrix.norms.docs_visible_pct}%)\n")
    lines.append(f"- **Jobs Posted**: {matrix.norms.jobs_visible_count}/{n}\n")
    lines.append(f"- **Paid Ads Active**: {matrix.norms.paid_ads_count}/{n}\n")
    lines.append(f"- **SEO Good**: {matrix.norms.seo_good_count}/{n}\n")
    lines.append(f"- **Social Presence (High)**: {matrix.norms.social_high_count}/{n}\n")
    lines.append(f"- **Review Visibility**: {matrix.norms.review_visible_count}/{n}\n\n")
    
    # Outliers
    if matrix.outliers:
        lines.append("## Outliers\n")
        for outlier in matrix.outliers:
            lines.append(f"### {outlier.url} ({outlier.direction})\n")
            for dev in outlier.deviations:
                lines.append(f"- {dev}\n")
            lines.append("\n")
    else:
        lines.append("## Outliers\n_No significant outliers detected._\n\n")
    
    # Anchor Deviations
    if matrix.anchor_deviations:
        lines.append("## Anchor Deviations\n")
        lines.append(f"The anchor ({anchor_url}) differs from the cohort norm in:\n")
        for dev in matrix.anchor_deviations:
            lines.append(f"- {dev}\n")
        lines.append("\n")
    
    # Comparison Matrix (simplified table)
    lines.append("## Comparison Matrix\n")
    lines.append("| Target | Tech | CMS | Pricing | Docs | Jobs | Ads | SEO | Social | Reviews |\n")
    lines.append("|--------|------|-----|---------|------|------|-----|-----|--------|----------|\n")
    for t in matrix.targets:
        lines.append(
            f"| {extract_domain(t.url)} | {t.tech_confidence} | {t.probable_cms or '-'} | "
            f"{'✓' if t.pricing_visible else '-'} | {'✓' if t.docs_visible else '-'} | "
            f"{'✓' if t.jobs_visible else '-'} | {'✓' if t.paid_ads_detected else '-'} | "
            f"{t.seo_hygiene} | {t.social_visibility} | {'✓' if t.review_visibility else '-'} |\n"
        )
    lines.append("\n")
    
    # Cannot Validate Section (mandatory)
    lines.append("## What Cannot Be Validated from Public Signals\n")
    lines.append("The following aspects cannot be reliably inferred from OSINT:\n\n")
    lines.append("- Internal pricing or discount structures\n")
    lines.append("- Actual revenue or growth metrics\n")
    lines.append("- Product quality or customer satisfaction beyond public reviews\n")
    lines.append("- Team size or organizational structure beyond job postings\n")
    lines.append("- Technical architecture beyond public-facing stack\n")
    lines.append("- Competitive positioning or market share\n")
    lines.append("\n_Absence of signals should not be interpreted as sophistication or prestige._\n")
    
    return "".join(lines)
