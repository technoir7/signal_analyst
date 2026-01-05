from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel
from core.inference import InferredProfile, SignalInference

# ---------------------------------------------------------------------------
# Data Models for Change Detection
# ---------------------------------------------------------------------------

class SignalShift(BaseModel):
    section: str            # e.g., "Tech Stack", "Hiring"
    shift_type: str         # "stability", "volatility", "breakage", "emergence"
    description: str        # "React removed, jQuery added"
    significance: str       # "high", "medium", "low"

class DeltaReport(BaseModel):
    baseline_date: datetime
    comparison_date: datetime
    time_elapsed_days: float
    shifts: List[SignalShift] = []
    overall_stability_score: float = 1.0 # 0.0 (Chaotic) to 1.0 (Stable)

# ---------------------------------------------------------------------------
# Change Detector Engine
# ---------------------------------------------------------------------------

class ChangeDetector:
    """
    Compares two InferredProfiles (current vs previous) to detect strategic shifts.
    """

    def compute_delta(
        self, 
        current: InferredProfile, 
        previous: InferredProfile,
        current_date: datetime,
        previous_date: datetime
    ) -> DeltaReport:
        
        shifts: List[SignalShift] = []
        elapsed = (current_date - previous_date).total_seconds() / 86400.0
        
        # 1. Compare Web Presence (Availability)
        shifts.extend(self._diff_section_status(current.web, previous.web, "Web Presence"))
        
        # 2. Compare SEO
        shifts.extend(self._diff_seo(current.seo, previous.seo))
        
        # 3. Compare Tech Stack (High signal)
        shifts.extend(self._diff_tech(current.tech_stack, previous.tech_stack))
        
        # 4. Compare Hiring (Growth signal)
        shifts.extend(self._diff_hiring(current.hiring, previous.hiring))
        
        # 5. Compare Social (Brand signal)
        shifts.extend(self._diff_section_status(current.social, previous.social, "Social Footprint"))
        
        # 6. Compare Ads
        shifts.extend(self._diff_section_status(current.ads, previous.ads, "Paid Media"))

        # Calculate Stability Score (Naïve implementation)
        # Start at 1.0, deduct for every High/Medium shift
        score = 1.0
        for s in shifts:
            if s.significance == "high":
                score -= 0.2
            elif s.significance == "medium":
                score -= 0.05
        
        return DeltaReport(
            baseline_date=previous_date,
            comparison_date=current_date,
            time_elapsed_days=elapsed,
            shifts=shifts,
            overall_stability_score=max(0.0, score)
        )

    # --- Section Diffs -----------------------------------------------------

    def _diff_section_status(self, curr: SignalInference, prev: SignalInference, section_name: str) -> List[SignalShift]:
        """Generic diff for presence/absence."""
        shifts = []
        
        # Case: Went Dark
        if prev.data_status == "present" and curr.data_status != "present":
            # Ignore if it's just an error
            if curr.data_status == "error":
                return [] 
                
            shifts.append(SignalShift(
                section=section_name,
                shift_type="breakage",
                description=f"{section_name} signals have vanished (was present, now {curr.data_status}).",
                significance="high"
            ))
            
        # Case: Emerged
        elif prev.data_status != "present" and curr.data_status == "present":
             shifts.append(SignalShift(
                section=section_name,
                shift_type="emergence",
                description=f"{section_name} signals have emerged (previously {prev.data_status}).",
                significance="high"
            ))
            
        return shifts

    def _diff_tech(self, curr: SignalInference, prev: SignalInference) -> List[SignalShift]:
        shifts = self._diff_section_status(curr, prev, "Tech Stack")
        if shifts: return shifts # Status change dominates details
        
        if curr.data_status != "present": return []

        # Extract tech from strategic implication or use raw data if we had access (we only have Inferred here)
        # Since InferredProfile loses the raw lists, we have to rely on what's in the implication 
        # OR we need to update InferredProfile to carry more structured data.
        # For now, let's look at the "Strategic Implication" text change if it's significant.
        
        # NOTE: Ideally InferredProfile should have a 'key_assets' list. 
        # For this minimal implementation, we assume stability unless implication changes drastically.
        return []

    def _diff_hiring(self, curr: SignalInference, prev: SignalInference) -> List[SignalShift]:
        shifts = self._diff_section_status(curr, prev, "Hiring Signals")
        if shifts: return shifts
        
        if curr.data_status != "present": return []

        # We can't easily diff counts because InferredProfile abstracts them into text.
        # This highlights a need to minorly update InferredProfile if we want precise diffs.
        # For phase 1, we stick to status checks.
        
        return []

    def _diff_seo(self, curr: SignalInference, prev: SignalInference) -> List[SignalShift]:
        return self._diff_section_status(curr, prev, "SEO Diagnostics")
