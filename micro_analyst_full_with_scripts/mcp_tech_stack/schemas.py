from typing import Optional, List, Literal

from pydantic import BaseModel


class TechStackInput(BaseModel):
    """Input for tech stack fingerprinting MCP."""
    raw_html: Optional[str] = None


class TechStackOutput(BaseModel):
    """
    Output for tech stack fingerprinting MCP.
    
    Now includes probabilistic detection with confidence tiers:
    - detected_* fields: High confidence (strong indicators found)
    - probable_* fields: Low/medium confidence (weak indicators found)
    - confidence: Overall confidence level
    - evidence: Concrete signals that led to detection
    - absence_interpretation: What missing markers imply
    - limitations: What prevented stronger detection
    
    Backwards-compatible: Original fields preserved.
    """
    success: bool
    
    # --- Original fields (preserved for backwards compatibility) ---
    frameworks: List[str] = []
    analytics: List[str] = []
    cms: Optional[str] = None
    cdn: Optional[str] = None
    other: List[str] = []
    error: Optional[str] = None
    
    # --- New probabilistic fields ---
    detected_framework: Optional[str] = None  # High confidence only
    detected_cms: Optional[str] = None        # High confidence only
    probable_framework: Optional[str] = None  # Low/medium confidence
    probable_cms: Optional[str] = None        # Low/medium confidence
    
    confidence: Literal["high", "medium", "low", "none"] = "none"
    evidence: List[str] = []                  # Concrete signals found
    absence_interpretation: Optional[str] = None  # What missing markers imply
    limitations: List[str] = []               # What prevented stronger detection
