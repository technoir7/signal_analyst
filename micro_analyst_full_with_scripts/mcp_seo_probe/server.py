import re
from collections import Counter
from typing import List

from fastapi import FastAPI
from loguru import logger

from .schemas import SEOProbeInput, SEOProbeOutput

app = FastAPI(title="MCP SEO Probe", version="1.0.0")


def _basic_meta_issues(title: str | None, description: str | None) -> List[str]:
    issues: List[str] = []

    if not description:
        issues.append("Missing meta description.")

    if not title:
        issues.append("Missing <title> tag.")
        return issues

    length = len(title)
    if length < 20:
        issues.append("Title appears too short (<20 characters).")
    if length > 70:
        issues.append("Title appears too long (>70 characters).")

    return issues


def _heading_issues(h1_list: List[str]) -> List[str]:
    issues: List[str] = []
    count = len(h1_list)
    if count == 0:
        issues.append("No H1 tag found.")
    if count > 1:
        issues.append(f"Multiple H1 tags found ({count}).")
    return issues


def _keyword_summary(clean_text: str | None, top_n: int = 10):
    if not clean_text:
        return []

    tokens = re.findall(r"[a-zA-Z]{3,}", clean_text.lower())
    stopwords = {
        "the", "and", "for", "with", "you", "your", "that", "this", "from",
        "are", "our", "was", "were", "have", "has", "but", "not", "one",
        "all", "can", "will", "their", "about", "more", "into",
    }

    filtered = [t for t in tokens if t not in stopwords]
    counts = Counter(filtered)
    most_common = counts.most_common(top_n)

    return [{"term": term, "count": count} for term, count in most_common]


@app.post("/run", response_model=SEOProbeOutput)
def run_seo_probe(payload: SEOProbeInput) -> SEOProbeOutput:
    """Perform deterministic SEO heuristics."""
    try:
        logger.info("mcp_seo_probe: received request")

        meta = payload.meta
        meta_issues = _basic_meta_issues(meta.title, meta.description)
        heading_issues = _heading_issues(meta.h1 or [])

        keyword_summary = _keyword_summary(payload.clean_text)
        internal_link_summary: list[dict] = []

        return SEOProbeOutput(
            success=True,
            meta_issues=meta_issues,
            heading_issues=heading_issues,
            keyword_summary=keyword_summary,
            internal_link_summary=internal_link_summary,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_seo_probe: unhandled error")
        return SEOProbeOutput(
            success=False,
            meta_issues=[],
            heading_issues=[],
            keyword_summary=[],
            internal_link_summary=[],
            error=f"Unexpected error during SEO probe: {exc}",
        )
