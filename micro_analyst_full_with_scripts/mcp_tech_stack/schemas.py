from typing import Optional, List

from pydantic import BaseModel


class TechStackInput(BaseModel):
    """Input for tech stack fingerprinting MCP."""
    raw_html: Optional[str] = None


class TechStackOutput(BaseModel):
    """Output for tech stack fingerprinting MCP."""
    success: bool
    frameworks: List[str] = []
    analytics: List[str] = []
    cms: Optional[str] = None
    cdn: Optional[str] = None
    other: List[str] = []
    error: Optional[str] = None
