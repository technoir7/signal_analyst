from typing import Optional, List, Dict, Any

from pydantic import BaseModel

from core.data_models import WebMetadata


class SEOProbeInput(BaseModel):
    """Input for SEO probe MCP."""
    meta: WebMetadata
    clean_text: Optional[str] = None


class SEOProbeOutput(BaseModel):
    """Output schema for SEO probe MCP."""
    success: bool
    meta_issues: List[str] = []
    heading_issues: List[str] = []
    keyword_summary: List[Dict[str, Any]] = []
    internal_link_summary: List[Dict[str, Any]] = []
    error: Optional[str] = None
