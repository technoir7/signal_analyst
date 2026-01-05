"""
Cohort Pattern Synthesis.

Aggregates individual peer drift profiles into ecosystem-level patterns.
Detects convergence, divergence, and outliers.
"""
from typing import List, Dict, Any, Tuple
from loguru import logger

from utils.cohort_drift import PeerDriftProfile

# ---------------------------------------------------------------------------
# Pattern Detection Logic
# ---------------------------------------------------------------------------

class CohortPatternDetector:
    def __init__(self, profiles: List[PeerDriftProfile]):
        self.profiles = [p for p in profiles if p.has_history]
        self.total = len(self.profiles)
        
    def detect_patterns(self) -> Dict[str, List[str]]:
        if self.total < 2:
            return {
                "convergence": [],
                "divergence": [],
                "outliers": ["Insufficient historical data for pattern detection."]
            }
            
        patterns = {
            "convergence": [],
            "divergence": [],
            "outliers": []
        }
        
        # 1. Pricing Visibility
        self._analyze_boolean_shift(
            "has_pricing_keywords", 
            "Pricing Visibility", 
            "made pricing public", 
            "hid pricing",
            patterns
        )
        
        # 2. Trust Signaling
        self._analyze_boolean_shift(
            "has_trust",
            "Trust Signaling",
            "added strict trust/compliance signaling",
            "removed trust signaling",
            patterns
        )
        
        # 3. Login/Auth
        self._analyze_boolean_shift(
            "has_login",
            "Auth Posture",
            "adopted self-serve login",
            "moved to sales-gated (no login)",
            patterns
        )
        
        # 4. Tech/Complexity
        self._analyze_complexity_shift(patterns)
        
        return patterns
        
    def _analyze_boolean_shift(self, key: str, label: str, gained_msg: str, lost_msg: str, patterns: Dict):
        """Analyze shifts in boolean signals (e.g. has_pricing)."""
        gained = []
        lost = []
        stable_true = []
        stable_false = []
        
        for p in self.profiles:
            delta = p.get_delta(key)
            if delta == "gained": gained.append(p.name)
            elif delta == "lost": lost.append(p.name)
            elif p.t0_signals.get(key): stable_true.append(p.name)
            else: stable_false.append(p.name)
            
        # Convergence: > 60% of cohort moved in one direction OR > 80% are in one state
        if len(gained) / self.total > 0.6:
            patterns["convergence"].append(f"Major shift towards {label}: {', '.join(gained)} {gained_msg}.")
        elif len(lost) / self.total > 0.6:
            patterns["convergence"].append(f"Retreat from {label}: {', '.join(lost)} {lost_msg}.")
            
        # State Convergence
        if len(stable_true) + len(gained) >= self.total * 0.8:
             patterns["convergence"].append(f"Consensus on {label}: {len(stable_true)+len(gained)}/{self.total} peers now exhibit this.")
             
        # Divergence: Split movement
        if len(gained) > 0 and len(lost) > 0:
            patterns["divergence"].append(f"Split strategy on {label}: {len(gained)} gained, while {len(lost)} lost.")
            
        # Outliers
        if len(stable_true) == 1 and self.total >= 4:
            patterns["outliers"].append(f"{stable_true[0]} is the only peer maintaining {label}.")
        if len(stable_false) == 1 and self.total >= 4:
            patterns["outliers"].append(f"{stable_false[0]} is the only peer without {label}.")

    def _analyze_complexity_shift(self, patterns: Dict):
        """Analyze HTML size / script count shifts."""
        bloat_peers = []
        lean_peers = []
        
        for p in self.profiles:
            t0_bytes = p.t0_signals.get("html_bytes", 0)
            t1_bytes = p.t1_signals.get("html_bytes", 0)
            
            if t1_bytes > 0:
                ratio = t0_bytes / t1_bytes
                if ratio > 1.5: bloat_peers.append(p.name)
                elif ratio < 0.7: lean_peers.append(p.name)
                
        if len(bloat_peers) >= self.total * 0.6:
            patterns["convergence"].append(f"Technical Inflation: Most peers ({len(bloat_peers)}/{self.total}) significantly increased page weight.")
        elif len(lean_peers) >= self.total * 0.6:
            patterns["convergence"].append(f"Technical Consolidation: Most peers ({len(lean_peers)}/{self.total}) reduced page weight.")
        elif bloat_peers and lean_peers:
            patterns["divergence"].append("Complexity Split: Some peers grew significantly heavy, others streamlined.")


def generate_cohort_report_markdown(cohort_name: str, profiles: List[PeerDriftProfile]) -> str:
    """Generate Markdown report from analysis."""
    detector = CohortPatternDetector(profiles)
    patterns = detector.detect_patterns()
    
    lines = [f"# Cohort Analysis: {cohort_name}\n"]
    lines.append(f"_{len(profiles)} peers analyzed via Wayback Machine._\n\n")
    
    # 1. Convergence
    if patterns["convergence"]:
        lines.append("## Observed Convergences\n")
        for p in patterns["convergence"]:
            lines.append(f"- {p}\n")
        lines.append("\n")
        
    # 2. Divergence
    if patterns["divergence"]:
        lines.append("## Observed Divergences\n")
        for p in patterns["divergence"]:
            lines.append(f"- {p}\n")
        lines.append("\n")
        
    # 3. Outliers
    if patterns["outliers"]:
        lines.append("## Notable Outliers\n")
        for p in patterns["outliers"]:
            lines.append(f"- {p}\n")
        lines.append("\n")
        
    # 4. Peer Details Table
    lines.append("## Peer Drift Details\n")
    lines.append("| Peer | Pricing | Auth | Trust | Complexity |\n")
    lines.append("| --- | --- | --- | --- | --- |\n")
    
    for p in profiles:
        if not p.has_history:
            lines.append(f"| {p.name} | (no history) | - | - | - |\n")
            continue
            
        pricing_d = p.get_delta("has_pricing_keywords") or "stable"
        auth_d = p.get_delta("has_login") or "stable"
        trust_d = p.get_delta("has_trust") or "stable"
        
        # Format complexity
        t0_b = p.t0_signals.get("html_bytes", 0)
        t1_b = p.t1_signals.get("html_bytes", 0)
        if t1_b > 0:
            ratio = (t0_b / t1_b - 1) * 100
            comp_str = f"{ratio:+.0f}%"
        else:
            comp_str = "N/A"
            
        lines.append(f"| {p.name} | {pricing_d} | {auth_d} | {trust_d} | {comp_str} |\n")
        
    return "".join(lines)
