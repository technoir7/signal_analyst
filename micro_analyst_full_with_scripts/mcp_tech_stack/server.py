from fastapi import FastAPI
from loguru import logger

from .schemas import TechStackInput, TechStackOutput

app = FastAPI(title="MCP Tech Stack Fingerprinting", version="1.0.0")


FRAMEWORK_KEYWORDS = {
    "react": "React",
    "vue": "Vue",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "angular": "Angular",
}

ANALYTICS_KEYWORDS = {
    "gtm.js": "Google Tag Manager",
    "gtm-": "Google Tag Manager",
    "datalayer": "Google Tag Manager / dataLayer",
    "segment.com": "Segment",
    "mixpanel": "Mixpanel",
    "ga4": "Google Analytics 4",
    "google-analytics.com": "Google Analytics",
}

CMS_KEYWORDS = {
    "wordpress": "WordPress",
    "wp-content": "WordPress",
    "shopify": "Shopify",
    "cdn.shopify.com": "Shopify",
    "contentful": "Contentful",
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


@app.post("/run", response_model=TechStackOutput)
def run_tech_stack(payload: TechStackInput) -> TechStackOutput:
    """Heuristically fingerprint a tech stack based on HTML substrings."""
    try:
        logger.info("mcp_tech_stack: received request")

        html = (payload.raw_html or "").lower()

        if not html:
            return TechStackOutput(
                success=True,
                frameworks=[],
                analytics=[],
                cms=None,
                cdn=None,
                other=[],
                error="No HTML content provided.",
            )

        frameworks: list[str] = []
        analytics: list[str] = []
        cms = None
        cdn = None
        other: list[str] = []

        for key, label in FRAMEWORK_KEYWORDS.items():
            if key in html and label not in frameworks:
                frameworks.append(label)

        for key, label in ANALYTICS_KEYWORDS.items():
            if key in html and label not in analytics:
                analytics.append(label)

        for key, label in CMS_KEYWORDS.items():
            if key in html:
                cms = cms or label

        for key, label in CDN_KEYWORDS.items():
            if key in html:
                cdn = cdn or label

        for key, label in OTHER_KEYWORDS.items():
            if key in html and label not in other:
                other.append(label)

        return TechStackOutput(
            success=True,
            frameworks=frameworks,
            analytics=analytics,
            cms=cms,
            cdn=cdn,
            other=other,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_tech_stack: unhandled error")
        return TechStackOutput(
            success=False,
            frameworks=[],
            analytics=[],
            cms=None,
            cdn=None,
            other=[],
            error=f"Unexpected error during tech stack fingerprinting: {exc}",
        )
