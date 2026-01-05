from typing import List, Optional, Tuple
from fastapi import FastAPI
from loguru import logger

from .schemas import TechStackInput, TechStackOutput

app = FastAPI(title="MCP Tech Stack Fingerprinting", version="2.0.0")

# =============================================================================
# INDICATOR CLASSIFICATIONS
# =============================================================================

# STRONG indicators: Unmistakable, canonical markers -> HIGH confidence
STRONG_CMS_INDICATORS = {
    # WordPress canonical paths
    "/wp-content/": "WordPress",
    "/wp-includes/": "WordPress",
    "/wp-admin/": "WordPress",
    'name="generator" content="wordpress': "WordPress",
    # Shopify canonical
    "cdn.shopify.com/s/files": "Shopify",
    "shopify.com/shopifycloud": "Shopify",
    # Drupal
    "/sites/default/files": "Drupal",
    'name="generator" content="drupal': "Drupal",
    # Squarespace
    "static1.squarespace.com": "Squarespace",
    "squarespace-cdn.com": "Squarespace",
}

STRONG_FRAMEWORK_INDICATORS = {
    # React unmistakable
    "__NEXT_DATA__": "Next.js",
    "_next/static": "Next.js",
    "/__nuxt/": "Nuxt.js",
    # Vue canonical
    "__VUE__": "Vue",
    # Angular canonical
    "ng-version=": "Angular",
}

# WEAK indicators: Suggestive but not conclusive -> LOW/MEDIUM confidence
WEAK_CMS_INDICATORS = {
    # WordPress weak signals
    "wp-json": "WordPress",
    "wordpress": "WordPress",
    "woocommerce": "WordPress (WooCommerce)",
    "wp-emoji": "WordPress",
    "wp-block": "WordPress",
    # Shopify weak
    "shopify": "Shopify",
    # General CMS patterns
    "contentful": "Contentful",
    "prismic": "Prismic",
}

WEAK_FRAMEWORK_INDICATORS = {
    "react": "React",
    "next.js": "Next.js",  # Requirement 7: detect Next.js from plain text
    "vue": "Vue",
    "angular": "Angular",
    "svelte": "Svelte",
    "gatsby": "Gatsby",
    "remix": "Remix",
}

# Analytics (kept as-is, not probabilistic)
ANALYTICS_KEYWORDS = {
    "gtm.js": "Google Tag Manager",
    "gtm-": "Google Tag Manager",
    "datalayer": "Google Tag Manager / dataLayer",
    "segment.com": "Segment",
    "mixpanel": "Mixpanel",
    "ga4": "Google Analytics 4",
    "google-analytics.com": "Google Analytics",
}

CDN_KEYWORDS = {
    "cloudflare": "Cloudflare",
    "cdn.cloudflare.net": "Cloudflare",
    "akamai": "Akamai",
    "fastly": "Fastly",
}

OTHER_KEYWORDS = {
    "stripe": "Stripe",
    "paypal": "PayPal",
    "auth0": "Auth0",
}


def _detect_strong(html: str, indicators: dict) -> Tuple[Optional[str], List[str]]:
    """Detect strong indicators. Returns (label, evidence_list)."""
    detected = None
    evidence = []
    for marker, label in indicators.items():
        if marker in html:
            detected = detected or label
            evidence.append(f"Strong: '{marker}' → {label}")
    return detected, evidence


def _detect_weak(html: str, indicators: dict) -> Tuple[Optional[str], List[str]]:
    """Detect weak indicators. Returns (label, evidence_list)."""
    detected = None
    evidence = []
    for marker, label in indicators.items():
        if marker in html:
            detected = detected or label
            evidence.append(f"Weak: '{marker}' → {label}")
    return detected, evidence


def _detect_all(html: str, indicators: dict) -> List[str]:
    """Detect all matches (for backwards-compatible list fields)."""
    found = []
    for marker, label in indicators.items():
        if marker in html and label not in found:
            found.append(label)
    return found


def _build_absence_interpretation(html_len: int, has_any_signals: bool) -> Optional[str]:
    """
    Build a conservative explanation for why detection failed.
    Never implies prestige or enterprise sophistication.
    """
    if html_len < 500:
        return "HTML content too thin for reliable detection (possible CDN cache, JS-rendered SPA, or fetch failure)."
    
    if not has_any_signals:
        return (
            "No recognizable CMS or framework markers found. Possible explanations: "
            "(1) Static HTML without framework, "
            "(2) Heavily cached/CDN-stripped response, "
            "(3) Generator tags intentionally removed, "
            "(4) Minimal/custom theme without typical asset paths, "
            "(5) Server-side rendering without client markers."
        )
    
    return None


def _build_limitations(html_len: int, strong_found: bool, weak_found: bool) -> List[str]:
    """List what prevented stronger detection."""
    limits = []
    if html_len < 2000:
        limits.append("Limited HTML sample size.")
    if not strong_found and weak_found:
        limits.append("Only weak/ambiguous markers found; no canonical paths or generator tags.")
    if not strong_found and not weak_found:
        limits.append("No framework or CMS markers detected in HTML.")
    return limits


@app.post("/run", response_model=TechStackOutput)
def run_tech_stack(payload: TechStackInput) -> TechStackOutput:
    """
    Probabilistic tech stack fingerprinting with tiered confidence.
    
    Detection tiers:
    - HIGH: Strong canonical indicators (e.g., /wp-content/, __NEXT_DATA__)
    - MEDIUM: Multiple weak indicators converging on same tech
    - LOW: Single weak indicator
    - NONE: No signals found
    """
    try:
        logger.info("mcp_tech_stack: received request")

        html = (payload.raw_html or "").lower()
        html_len = len(html)

        if not html:
            return TechStackOutput(
                success=True,
                error="No HTML content provided.",
                confidence="none",
                absence_interpretation="No HTML was provided for analysis.",
                limitations=["Empty or missing HTML input."],
            )

        # --- Tiered Detection ---
        strong_cms, strong_cms_evidence = _detect_strong(html, STRONG_CMS_INDICATORS)
        strong_fw, strong_fw_evidence = _detect_strong(html, STRONG_FRAMEWORK_INDICATORS)
        weak_cms, weak_cms_evidence = _detect_weak(html, WEAK_CMS_INDICATORS)
        weak_fw, weak_fw_evidence = _detect_weak(html, WEAK_FRAMEWORK_INDICATORS)

        # Backwards-compatible list detection
        analytics = _detect_all(html, ANALYTICS_KEYWORDS)
        cdn_list = _detect_all(html, CDN_KEYWORDS)
        other = _detect_all(html, OTHER_KEYWORDS)
        
        # Legacy fields (first match)
        cdn = cdn_list[0] if cdn_list else None

        # Aggregate evidence
        all_evidence = strong_cms_evidence + strong_fw_evidence + weak_cms_evidence + weak_fw_evidence

        # --- Confidence Calculation ---
        has_strong = bool(strong_cms or strong_fw)
        has_weak = bool(weak_cms or weak_fw)
        weak_count = len(weak_cms_evidence) + len(weak_fw_evidence)

        if has_strong:
            confidence = "high"
        elif weak_count >= 3:
            confidence = "medium"
        elif has_weak:
            confidence = "low"
        else:
            confidence = "none"

        # --- Build Output ---
        detected_framework = strong_fw
        detected_cms = strong_cms
        probable_framework = weak_fw if not strong_fw else None
        probable_cms = weak_cms if not strong_cms else None

        # Backwards compatibility: populate legacy fields with ALL detected frameworks
        frameworks = []
        if detected_framework:
            frameworks.append(detected_framework)
        # Also add all weak framework detections (Requirement 7: include Next.js)
        for marker, label in WEAK_FRAMEWORK_INDICATORS.items():
            if marker in html and label not in frameworks:
                frameworks.append(label)

        cms_final = detected_cms or probable_cms

        # Absence interpretation & limitations
        has_any = has_strong or has_weak or analytics or cdn
        absence_interpretation = _build_absence_interpretation(html_len, has_any)
        limitations = _build_limitations(html_len, has_strong, has_weak)

        return TechStackOutput(
            success=True,
            # Legacy fields
            frameworks=frameworks,
            analytics=analytics,
            cms=cms_final,
            cdn=cdn,
            other=other,
            error=None,
            # Probabilistic fields
            detected_framework=detected_framework,
            detected_cms=detected_cms,
            probable_framework=probable_framework,
            probable_cms=probable_cms,
            confidence=confidence,
            evidence=all_evidence,
            absence_interpretation=absence_interpretation,
            limitations=limitations,
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_tech_stack: unhandled error")
        return TechStackOutput(
            success=False,
            error=f"Unexpected error during tech stack fingerprinting: {exc}",
            confidence="none",
            limitations=["Internal error prevented analysis."],
        )
