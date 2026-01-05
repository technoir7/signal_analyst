"""
Pydantic schemas for SaaS Cohort Mode v1.

These models define the request/response shapes for cohort analysis endpoints.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class CohortProposeRequest(BaseModel):
    """Request to propose a peer cohort for an anchor URL."""
    anchor_url: str = Field(..., max_length=2048, description="Primary target URL")
    domain: Literal["saas"] = Field("saas", description="Analysis domain (only 'saas' supported in v1)")
    k: int = Field(8, ge=4, le=12, description="Number of candidates to propose")
    category_hint: Optional[str] = Field(None, max_length=200, description="Optional category hint (e.g., 'project management')")


class CohortConfirmRequest(BaseModel):
    """Request to confirm a cohort for analysis."""
    final_urls: List[str] = Field(..., min_length=0, max_length=15, description="URLs to include in analysis")
    include_anchor: bool = Field(True, description="Whether to include anchor in analysis")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class CohortCandidate(BaseModel):
    """A proposed peer company candidate."""
    url: str
    name: str
    source: Literal["search", "directory", "both"]
    rationale: str = Field(..., max_length=200, description="Short reason for inclusion")
    confidence: Literal["low", "medium"]


class CohortProposeResponse(BaseModel):
    """Response from cohort proposal endpoint."""
    cohort_id: str
    anchor_url: str
    anchor_name: Optional[str] = None
    extracted_terms: List[str] = Field(default_factory=list, description="Category terms extracted from anchor")
    candidates: List[CohortCandidate]
    discovery_sources: List[str] = Field(default_factory=list, description="Sources used for discovery")


class CohortConfirmResponse(BaseModel):
    """Response from cohort confirmation endpoint."""
    cohort_id: str
    confirmed_urls: List[str]
    status: str = "confirmed"


class CohortAnalyzeResponse(BaseModel):
    """Response from cohort analysis trigger."""
    cohort_id: str
    job_ids: List[str]
    status: str = "analyzing"


# ---------------------------------------------------------------------------
# Matrix and Results Models
# ---------------------------------------------------------------------------

class TargetSignals(BaseModel):
    """Normalized signals for a single target (CMATRIX_001)."""
    url: str
    name: Optional[str] = None
    
    # Categorical / boolean fields only
    tech_confidence: Literal["high", "medium", "low", "none"] = "none"
    probable_cms: Optional[str] = None
    pricing_visible: bool = False
    docs_visible: bool = False
    jobs_visible: bool = False
    paid_ads_detected: bool = False
    seo_hygiene: Literal["good", "fair", "poor", "unknown"] = "unknown"
    social_visibility: Literal["high", "low", "none"] = "none"
    review_visibility: bool = False
    
    # Evidence / limits
    evidence_snippets: List[str] = Field(default_factory=list, max_length=5)
    fetch_limits: List[str] = Field(default_factory=list, description="Fetch failures or thin-HTML notes")


class CohortNorms(BaseModel):
    """Quantified norms across the cohort."""
    total_targets: int
    pricing_visible_count: int
    docs_visible_count: int
    jobs_visible_count: int
    paid_ads_count: int
    seo_good_count: int
    social_high_count: int
    review_visible_count: int
    
    # Derived percentages (for convenience)
    pricing_visible_pct: float = 0.0
    docs_visible_pct: float = 0.0


class CohortOutlier(BaseModel):
    """A target that deviates significantly from cohort norms."""
    url: str
    deviations: List[str] = Field(..., description="Fields where this target differs from norm")
    direction: Literal["above", "below", "mixed"]


class CohortMatrix(BaseModel):
    """Complete comparison matrix for a cohort."""
    targets: List[TargetSignals]
    norms: CohortNorms
    outliers: List[CohortOutlier] = Field(default_factory=list)
    anchor_deviations: List[str] = Field(default_factory=list, description="How anchor differs from norm")



class CohortDriftResponse(BaseModel):
    """Response from cohort drift analysis trigger."""
    cohort_id: str
    status: str = "analyzing_drift"


class CohortResultsResponse(BaseModel):
    """Full cohort analysis results."""
    cohort_id: str
    anchor_url: str
    status: str
    matrix: Optional[CohortMatrix] = None
    report_markdown: Optional[str] = None
    
    # Drift Extensions
    drift_matrix: Optional[Dict[str, Any]] = None
    drift_report_markdown: Optional[str] = None
    
    cannot_validate: List[str] = Field(
        default_factory=lambda: [
            "Internal pricing or discount structures",
            "Actual revenue or growth metrics",
            "Product quality or customer satisfaction beyond public reviews",
            "Team size or organizational structure beyond job postings",
            "Technical architecture beyond public-facing stack",
        ],
        description="Standard disclaimer for unverifiable claims"
    )
