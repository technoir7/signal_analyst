from typing import Optional, List, Dict, Any

from pydantic import BaseModel, HttpUrl


class CareersIntelInput(BaseModel):
    """Input for careers intel MCP."""
    company_url: HttpUrl
    company_name: Optional[str] = None


class CareersIntelOutput(BaseModel):
    """Output schema for careers intel MCP."""
    success: bool
    open_roles: List[Dict[str, Any]] = []
    inferred_focus: Optional[str] = None
    error: Optional[str] = None
