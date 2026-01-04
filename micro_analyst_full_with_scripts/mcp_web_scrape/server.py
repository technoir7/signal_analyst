# mcp_web_scrape/server.py

from typing import Any, Dict, Optional

from bs4 import BeautifulSoup  # type: ignore
from fastapi import FastAPI
from loguru import logger

from .schemas import WebScrapeInput, WebScrapeOutput
from utils.text_utils import clean_html_to_text, truncate_text
from utils.http_utils import fetch_url_with_retry

app = FastAPI(title="MCP Web Scraper", version="1.0.0")


RAW_HTML_LIMIT = 100_000
CLEAN_TEXT_LIMIT = 20_000


def _extract_meta(html: str) -> Dict[str, Any]:
    """
    Very small, deterministic metadata extractor.

    Returns:
    {
      "title": ...,
      "description": ...,
      "h1": [...],
      "h2": [...]
    }
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "").strip() if desc_tag else None

    # Headings
    h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(strip=True) for h in soup.find_all("h2")]

    return {
        "title": title or None,
        "description": description or None,
        "h1": h1,
        "h2": h2,
    }


def _looks_like_bot_challenge(
    html: Optional[str],
    clean_text: Optional[str],
    title: Optional[str],
) -> bool:
    """
    Heuristic to detect "you are a bot" / JS challenge pages.

    We keep it extremely simple and deterministic.
    """
    if not html and not clean_text and not title:
        return False

    markers = [
        "just a moment...",
        "checking your browser",
        "enable javascript",
        "cloudflare",
        "access denied",
        "request blocked",
        "unusual traffic",
    ]

    haystack_parts = [
        (title or ""),
        (clean_text or ""),
        (html[:2000] if html else ""),
    ]
    haystack = " ".join(haystack_parts).lower()

    return any(m in haystack for m in markers)


@app.post("/run", response_model=WebScrapeOutput)
def run(payload: WebScrapeInput) -> WebScrapeOutput:
    """
    Deterministic, single-page HTML scraper.

    - Fetches the URL with a small, fixed retry budget.
    - Extracts basic metadata (title, meta description, h1, h2).
    - Produces a cleaned text surface via utils.clean_html_to_text.
    - Truncates raw_html and clean_text to deterministic limits.
    - Adds a human-readable error message if a bot-challenge is suspected.
    """
    url_str = str(payload.url)
    logger.info("mcp_web_scrape: fetching %s", url_str)

    try:
        raw_html = fetch_url_with_retry(url_str, timeout=15, max_attempts=3)
        if raw_html is None:
            return WebScrapeOutput(
                success=False,
                url=url_str,
                raw_html=None,
                clean_text=None,
                meta={},  # WebMetadata will accept this dict
                error="Failed to fetch URL after deterministic retry budget.",
            )

        raw_html_truncated = truncate_text(raw_html, RAW_HTML_LIMIT)

        meta_dict = _extract_meta(raw_html_truncated)
        clean_text = clean_html_to_text(raw_html_truncated)
        clean_text_truncated = truncate_text(clean_text, CLEAN_TEXT_LIMIT)

        suspected_challenge = _looks_like_bot_challenge(
            raw_html_truncated,
            clean_text_truncated,
            meta_dict.get("title"),
        )

        error_msg = None
        if suspected_challenge:
            error_msg = (
                "Site appears to be behind an anti-bot or JavaScript challenge; "
                "scraped content may be incomplete or non-representative."
            )

        return WebScrapeOutput(
            success=True,
            url=url_str,
            raw_html=raw_html_truncated,
            clean_text=clean_text_truncated,
            meta=meta_dict,
            error=error_msg,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_web_scrape: unhandled error")
        return WebScrapeOutput(
            success=False,
            url=url_str,
            raw_html=None,
            clean_text=None,
            meta={},
            error=f"Unexpected error during web scrape: {exc}",
        )
