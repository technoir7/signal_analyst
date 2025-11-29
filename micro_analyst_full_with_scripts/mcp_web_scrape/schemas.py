from typing import Optional

from pydantic import BaseModel, HttpUrl

from core.data_models import WebMetadata


class WebScrapeInput(BaseModel):
    """Input schema for the web scraper MCP."""
    url: HttpUrl


class WebScrapeOutput(BaseModel):
    """Output schema for the web scraper MCP."""
    success: bool
    url: str
    raw_html: Optional[str] = None
    clean_text: Optional[str] = None
    meta: WebMetadata = WebMetadata()
    error: Optional[str] = None
