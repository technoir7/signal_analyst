from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ------------------------------------------------------------
# Web Metadata
# ------------------------------------------------------------
class WebMetadata(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    h1: List[str] = []
    h2: List[str] = []


class WebData(BaseModel):
    raw_html: Optional[str] = None
    clean_text: Optional[str] = None
    meta: WebMetadata = WebMetadata()
    error: Optional[str] = None


# ------------------------------------------------------------
# SEO
# ------------------------------------------------------------
class SEOData(BaseModel):
    meta_issues: List[str] = []
    heading_issues: List[str] = []
    # demo_data uses objects like {"term": "...", "count": ...}
    keyword_summary: List[Dict[str, Any]] = []
    internal_link_summary: List[Dict[str, Any]] = []
    error: Optional[str] = None


# ------------------------------------------------------------
# Tech Stack
# ------------------------------------------------------------
class TechStackData(BaseModel):
    frameworks: List[str] = []
    analytics: List[str] = []
    cms: Optional[str] = None
    cdn: Optional[str] = None
    other: List[str] = []
    error: Optional[str] = None


# ------------------------------------------------------------
# Reviews
# (tests expect: sources + summary + top_complaints + top_praises + error)
# ------------------------------------------------------------
class ReviewsData(BaseModel):
    sources: List[Dict[str, Any]] = []
    summary: Optional[str] = None
    top_complaints: List[str] = []
    top_praises: List[str] = []
    error: Optional[str] = None


# ------------------------------------------------------------
# Social
# ------------------------------------------------------------
class SocialData(BaseModel):
    instagram: Optional[Dict[str, Any]] = None
    youtube: Optional[Dict[str, Any]] = None
    twitter: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ------------------------------------------------------------
# Hiring
# (tests expect: open_roles + inferred_focus + error)
# ------------------------------------------------------------
class HiringData(BaseModel):
    open_roles: List[Dict[str, Any]] = []
    inferred_focus: Optional[str] = None
    error: Optional[str] = None


# ------------------------------------------------------------
# Ads
# (demo JSON has: platforms: ["Meta","Google"], themes: [...], error)
# ------------------------------------------------------------
class AdsData(BaseModel):
    platforms: List[str] = []
    themes: List[str] = []
    error: Optional[str] = None


# ------------------------------------------------------------
# Unified OSINT Profile
# ------------------------------------------------------------
class CompanyOSINTProfile(BaseModel):
    company: Dict[str, Any]
    web: WebData
    seo: SEOData
    tech_stack: TechStackData
    reviews: ReviewsData
    social: SocialData
    hiring: HiringData
    ads: AdsData

    @classmethod
    def create_empty_company_profile(
        cls,
        name: Optional[str] = None,
        url: Optional[str] = None,
    ) -> "CompanyOSINTProfile":
        """
        Wrapper classmethod so agent.micro_analyst.py can call:
            CompanyOSINTProfile.create_empty_company_profile(...)
        """
        return create_empty_company_profile(name=name, url=url)


# ------------------------------------------------------------
# Factory for empty profile
# ------------------------------------------------------------
def create_empty_company_profile(
    name: Optional[str] = None,
    url: Optional[str] = None,
) -> CompanyOSINTProfile:
    return CompanyOSINTProfile(
        company={
            "name": name or "",
            "url": url or "",
        },
        web=WebData(),
        seo=SEOData(),
        tech_stack=TechStackData(),
        reviews=ReviewsData(),
        social=SocialData(),
        hiring=HiringData(),
        ads=AdsData(),
    )
