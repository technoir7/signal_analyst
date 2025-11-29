from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class ReviewsSnapshotInput(BaseModel):
    """Minimal input for reviews snapshot."""
    company_name: Optional[str] = None
    company_url: Optional[str] = None


class ReviewsSnapshotOutput(BaseModel):
    """Output schema for reviews snapshot MCP."""
    success: bool
    sources: List[Dict[str, Any]] = []
    summary: Optional[str] = None
    top_complaints: List[str] = []
    top_praises: List[str] = []
    error: Optional[str] = None
