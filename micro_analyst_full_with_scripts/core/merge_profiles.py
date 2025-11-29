from typing import Any, Dict

from .data_models import (
    CompanyOSINTProfile,
    WebData,
    WebMetadata,
    SEOData,
    TechStackData,
    ReviewsData,
    SocialData,
    HiringData,
    AdsData,
)


def merge_web_data(profile: CompanyOSINTProfile, web_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    meta_dict = web_payload.get("meta") or {}
    meta = WebMetadata(**meta_dict)
    web_data = WebData(
        raw_html=web_payload.get("raw_html"),
        clean_text=web_payload.get("clean_text"),
        meta=meta,
        error=web_payload.get("error"),
    )
    return profile.model_copy(update={"web": web_data})


def merge_seo_data(profile: CompanyOSINTProfile, seo_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    seo_data = SEOData(
        meta_issues=seo_payload.get("meta_issues") or [],
        heading_issues=seo_payload.get("heading_issues") or [],
        keyword_summary=seo_payload.get("keyword_summary") or [],
        internal_link_summary=seo_payload.get("internal_link_summary") or [],
        error=seo_payload.get("error"),
    )
    return profile.model_copy(update={"seo": seo_data})


def merge_tech_stack_data(profile: CompanyOSINTProfile, tech_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    tech_data = TechStackData(
        frameworks=tech_payload.get("frameworks") or [],
        analytics=tech_payload.get("analytics") or [],
        cms=tech_payload.get("cms"),
        cdn=tech_payload.get("cdn"),
        other=tech_payload.get("other") or [],
        error=tech_payload.get("error"),
    )
    return profile.model_copy(update={"tech_stack": tech_data})


def merge_reviews_data(profile: CompanyOSINTProfile, reviews_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    reviews_data = ReviewsData(
        sources=reviews_payload.get("sources") or [],
        summary=reviews_payload.get("summary"),
        top_complaints=reviews_payload.get("top_complaints") or [],
        top_praises=reviews_payload.get("top_praises") or [],
        error=reviews_payload.get("error"),
    )
    return profile.model_copy(update={"reviews": reviews_data})


def merge_social_data(profile: CompanyOSINTProfile, social_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    social_data = SocialData(
        instagram=social_payload.get("instagram"),
        youtube=social_payload.get("youtube"),
        twitter=social_payload.get("twitter"),
        error=social_payload.get("error"),
    )
    return profile.model_copy(update={"social": social_data})


def merge_hiring_data(profile: CompanyOSINTProfile, hiring_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    hiring_data = HiringData(
        open_roles=hiring_payload.get("open_roles") or [],
        inferred_focus=hiring_payload.get("inferred_focus"),
        error=hiring_payload.get("error"),
    )
    return profile.model_copy(update={"hiring": hiring_data})


def merge_ads_data(profile: CompanyOSINTProfile, ads_payload: Dict[str, Any]) -> CompanyOSINTProfile:
    ads_data = AdsData(
        platforms=ads_payload.get("platforms") or [],
        themes=ads_payload.get("themes") or [],
        error=ads_payload.get("error"),
    )
    return profile.model_copy(update={"ads": ads_data})
