from typing import Any

from bs4 import BeautifulSoup  # type: ignore
from fastapi import FastAPI
from loguru import logger

from .schemas import WebScrapeInput, WebScrapeOutput
from utils.text_utils import clean_html_to_text, truncate_text
from utils.http_utils import fetch_url_with_retry

app = FastAPI(title="MCP Web Scraper", version="1.0.0")


RAW_HTML_LIMIT = 100_000
CLEAN_TEXT_LIMIT = 20_000


@app.post("/run", response_model=WebScrapeOutput)
def run_web_scrape(payload: WebScrapeInput) -> WebScrapeOutput:
    """Fetch a URL and extract raw HTML, clean text, and basic metadata."""
    try:
        logger.info("mcp_web_scrape: received request for url={}", payload.url)

        html = fetch_url_with_retry(str(payload.url))
        if html is None:
            return WebScrapeOutput(
                success=False,
                url=str(payload.url),
                raw_html=None,
                clean_text=None,
                meta={},
                error="Failed to fetch URL after retries.",
            )

        html_truncated = truncate_text(html, RAW_HTML_LIMIT)
        soup = BeautifulSoup(html_truncated, "lxml")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        desc_tag = soup.find("meta", attrs={"name": "description"})
        description = desc_tag.get("content", "").strip() if desc_tag and desc_tag.get("content") else None

        h1_texts = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2_texts = [h.get_text(strip=True) for h in soup.find_all("h2")]

        clean_text = clean_html_to_text(html_truncated)
        clean_text_truncated = truncate_text(clean_text, CLEAN_TEXT_LIMIT)

        meta_dict: dict[str, Any] = {
            "title": title,
            "description": description,
            "h1": h1_texts,
            "h2": h2_texts,
        }

        return WebScrapeOutput(
            success=True,
            url=str(payload.url),
            raw_html=html_truncated,
            clean_text=clean_text_truncated,
            meta=meta_dict,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_web_scrape: unhandled error")
        return WebScrapeOutput(
            success=False,
            url=str(payload.url),
            raw_html=None,
            clean_text=None,
            meta={},
            error=f"Unexpected error during web scrape: {exc}",
        )
