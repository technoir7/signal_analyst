from typing import Optional, Dict, Any

from pydantic import BaseModel


class SocialSnapshotInput(BaseModel):
    """Minimal input for social snapshot."""
    company_name: Optional[str] = None
    company_url: Optional[str] = None


class SocialSnapshotOutput(BaseModel):
    """Output schema for social snapshot MCP."""
    success: bool
    instagram: Optional[Dict[str, Any]] = None
    youtube: Optional[Dict[str, Any]] = None
    twitter: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
