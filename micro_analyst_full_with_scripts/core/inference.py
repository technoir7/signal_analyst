from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from collections import Counter

# ---------------------------------------------------------------------------
# Key Concepts
# - Data Status: "present" | "absent" | "partial" | "error"
# - Confidence: "low" | "medium" | "high"
# - Strategic Implication: The "so what" for the client
# ---------------------------------------------------------------------------

class SignalInference(BaseModel):
    """
    Represents the interpretive layer for a specific OSINT section.
    Even if data is missing, this object MUST be populated.
    """
    section: str
    data_status: str
    confidence: str
    plausible_causes: List[str]
    strategic_implication: str
    risk_note: Optional[str] = None


class InferredProfile(BaseModel):
    """
    The full interpretive profile that replaces the raw data dict
    during report synthesis.
    """
    web: SignalInference
    seo: SignalInference
    tech_stack: SignalInference
    reviews: SignalInference
    social: SignalInference
    hiring: SignalInference
    ads: SignalInference
    strategic_posture: str  # The mandatory summary paragraph


class InferenceEngine:
    """
    Transform raw OSINT data into strategic inferences.
    This engine ensures no section is ever "empty" or "not available".
    """

    def infer(self, raw_profile: Dict[str, Any]) -> InferredProfile:
        web_inf = self._infer_web(raw_profile.get("web", {}))
        seo_inf = self._infer_seo(raw_profile.get("seo", {}))
        tech_inf = self._infer_tech(raw_profile.get("tech_stack", {}))
        reviews_inf = self._infer_reviews(raw_profile.get("reviews", {}))
        social_inf = self._infer_social(raw_profile.get("social", {}))
        hiring_inf = self._infer_hiring(raw_profile.get("hiring", {}))
        ads_inf = self._infer_ads(raw_profile.get("ads", {}))

        posture = self._synthesize_posture(
            [web_inf, seo_inf, tech_inf, reviews_inf, social_inf, hiring_inf, ads_inf]
        )

        return InferredProfile(
            web=web_inf,
            seo=seo_inf,
            tech_stack=tech_inf,
            reviews=reviews_inf,
            social=social_inf,
            hiring=hiring_inf,
            ads=ads_inf,
            strategic_posture=posture
        )

    # --- Section-Specific Inference Logic ---------------------------------

    def _infer_web(self, data: Dict[str, Any]) -> SignalInference:
        title = (data.get("meta") or {}).get("title")
        desc = (data.get("meta") or {}).get("description")
        error = data.get("error")

        if error or (not title and not desc):
            return SignalInference(
                section="Web Presence",
                data_status="absent",
                confidence="medium",
                plausible_causes=["WAF Blocking", "Single-Page App (SPA) unrendered", "Private / Intranet site"],
                strategic_implication=(
                    "The organization maintains a shielded digital perimeter. "
                    "This suggests a strategy that prioritizes security or privacy over "
                    "broad public discoverability, common in specialized B2B or defense sectors."
                ),
                risk_note="Opacity prevents verification of public messaging alignment."
            )
        
        return SignalInference(
            section="Web Presence",
            data_status="present",
            confidence="high",
            plausible_causes=["Standard public indexing"],
            strategic_implication=(
                f"The organization actively manages its digital front door, positioning itself via '{title or 'Untitled'}'. "
                "This indicates a reliance on inbound web traffic as a credibility signal."
            )
        )

    def _infer_seo(self, data: Dict[str, Any]) -> SignalInference:
        error = data.get("error")
        issues = (data.get("meta_issues") or []) + (data.get("heading_issues") or [])

        if error:
            return SignalInference(
                section="SEO Diagnostics",
                data_status="error",
                confidence="low",
                plausible_causes=["Anti-bot defenses", "Malformed HTML structure"],
                strategic_implication=(
                    "Technical barriers prevent standard SEO auditing. "
                    "Strategically, this implies organic search is not a primary growth lever, "
                    "or the brand relies on direct traffic and reputation."
                )
            )

        if not issues:
            return SignalInference(
                section="SEO Diagnostics",
                data_status="present",
                confidence="high",
                plausible_causes=["Mature marketing ops", "Technical SEO investment"],
                strategic_implication=(
                    "Zero structural SEO issues detected. This signals a disciplined, "
                    "technically mature marketing operation that treats discoverability as a core asset."
                )
            )

        return SignalInference(
            section="SEO Diagnostics",
            data_status="partial",
            confidence="high",
            plausible_causes=["Legacy CMS", "Neglected maintenance", "Brand-focused vs Search-focused"],
            strategic_implication=(
                f"Detected {len(issues)} structural gaps between the brand's intent and its technical reality. "
                "This friction suggests marketing execution lags behind strategy, potentially bleeding organic traffic."
            ),
            risk_note=f"Primary issue: {issues[0] if issues else 'Unknown'}"
        )

    def _infer_tech(self, data: Dict[str, Any]) -> SignalInference:
        # Probabilistic fields from upgraded MCP
        confidence = data.get("confidence", "none")
        detected_fw = data.get("detected_framework")
        detected_cms = data.get("detected_cms")
        probable_fw = data.get("probable_framework")
        probable_cms = data.get("probable_cms")
        evidence = data.get("evidence") or []
        absence_interp = data.get("absence_interpretation")
        limitations = data.get("limitations") or []
        
        # Fallback for legacy data (if MCP hasn't run or is old version)
        legacy_frameworks = data.get("frameworks") or []
        
        # Backwards compatibility: If legacy frameworks exist but confidence is "none", 
        # assume it came from an older MCP version that only returned successes.
        if confidence == "none" and legacy_frameworks:
            confidence = "high"

        # 1. NO DETECTION (Confidence: None)
        if confidence == "none":
            # Use specific absence interpretation if available, otherwise generic
            reason = absence_interp or "No identifiable framework markers found in HTML."
            
            return SignalInference(
                section="Tech Stack",
                data_status="absent",
                confidence="none",  # Explicitly none
                plausible_causes=limitations if limitations else ["Heavily cached", "Static HTML", "Custom"],
                strategic_implication=(
                    f"The technology stack is indeterminate based on public signals. {reason} "
                    "Infrastructure complexity and maintenance burden cannot be assessed."
                ),
                risk_note="Opacity prevents assessing maintenance risks or infrastructure capability."
            )

        # 2. PROBABLE / LOW CONFIDENCE
        if confidence in ("low", "medium"):
            signals = [s for s in [probable_fw, probable_cms] if s]
            if not signals and legacy_frameworks: # partial fallback
                 signals = legacy_frameworks[:2]

            # specific evidence list
            ev_str = "; ".join(evidence[:2]) if evidence else "weak signals"
            
            return SignalInference(
                section="Tech Stack",
                data_status="partial",
                confidence="low",
                plausible_causes=["Non-standard implementation", "Obfuscated headers"],
                strategic_implication=(
                    f"Traces suggest a likely reliance on {', '.join(signals) or 'unidentified text-based signals'}. "
                    f"Evidence is present ({ev_str}) but lacks canonical authority. "
                    "This suggests a custom implementation or a headless architecture."
                ),
                risk_note="Tech identification is tentative; verify before making integration decisions."
            )

        # 3. HIGH CONFIDENCE (Strong Detection)
        # Use detected fields if present, otherwise fall back to legacy list (backward compat)
        stack = [s for s in [detected_fw, detected_cms] if s]
        if not stack and legacy_frameworks:
            stack = legacy_frameworks[:2]
            
        stack_str = ", ".join(stack)
        
        return SignalInference(
            section="Tech Stack",
            data_status="present",
            confidence="high",
            plausible_causes=["Modern SaaS composability", "Standard CMS deployment"],
            strategic_implication=(
                f"Confirmed core infrastructure: {stack_str}. "
                "The organization relies on established, standard tooling, allowing for "
                "predictable talent sourcing and easier third-party integrations."
            )
        )

    def _infer_reviews(self, data: Dict[str, Any]) -> SignalInference:
        error = data.get("error")
        summary = data.get("summary")

        if error or not summary:
            return SignalInference(
                section="Customer Voice",
                data_status="absent",
                confidence="medium",
                plausible_causes=["B2B/Enterprise model", "NDAs", "Offline transaction loop"],
                strategic_implication=(
                    "The absence of public reviews strongly suggests an enterprise Sales-Led Growth (SLG) motion. "
                    "Trust is likely built through private relationships, RFPs, and references rather than public social proof."
                ),
                risk_note="Lack of public feedback loop creates a blind spot for market sentiment."
            )

        return SignalInference(
            section="Customer Voice",
            data_status="present",
            confidence="medium",
            plausible_causes=["PLG motion", "Consumer-facing brand"],
            strategic_implication=(
                "Public sentiment is visible and active, indicating a Product-Led or Consumer-focused model. "
                "The brand's reputation is decentralized and vulnerable to viral variance."
            )
        )

    def _infer_social(self, data: Dict[str, Any]) -> SignalInference:
        # Check if any channel has a URL/handle
        has_social = any(data.get(k) for k in ["twitter", "linkedin", "instagram", "youtube", "tiktok"])
        error = data.get("error")

        if not has_social or error:
            return SignalInference(
                section="Social Footprint",
                data_status="absent",
                confidence="high",
                plausible_causes=["Low-profile strategy", "Enterprise focus", "Resource constraint"],
                strategic_implication=(
                    "The minimal social footprint suggests a 'Quiet Professional' posture. "
                    "The organization likely views social media as a liability or irrelevant channel, "
                    "choosing to control its narrative through owned channels (website/PR) only."
                )
            )

        return SignalInference(
            section="Social Footprint",
            data_status="present",
            confidence="high",
            plausible_causes=["Brand-building investment", "Community engagement"],
            strategic_implication=(
                "Active social channels signal a desire to own the narrative in the public square. "
                "The organization invests in community engagement as a defensive moat."
            )
        )

    def _infer_hiring(self, data: Dict[str, Any]) -> SignalInference:
        error = data.get("error")
        roles = data.get("open_roles") or []

        if error or not roles:
            return SignalInference(
                section="Hiring Signals",
                data_status="absent",
                confidence="medium",
                plausible_causes=["Low turnover", "Hiring freeze", "Outsourced recruiting", "Stealth mode"],
                strategic_implication=(
                    "No visible open roles suggests a stable, low-turnover environment or a hiring freeze. "
                    "Growth is currently being absorbed by existing capacity or outsourced partners rather than "
                    "new headcount."
                )
            )
        
        return SignalInference(
            section="Hiring Signals",
            data_status="present",
            confidence="high",
            plausible_causes=["Expansion mode", "High churn", "New capability build"],
            strategic_implication=(
                f"Visible hiring ({len(roles)} roles) indicates an expansion phase. "
                "The organization is actively trading capital for human capacity to capture market share."
            )
        )

    def _infer_ads(self, data: Dict[str, Any]) -> SignalInference:
        # Note: Ads service is often feature-flagged off
        error = data.get("error")
        platforms = data.get("platforms") or []

        if error or not platforms:
            return SignalInference(
                section="Paid Media",
                data_status="absent",
                confidence="medium",
                plausible_causes=["Organic Growth", "Sales-Led Growth", "High LTV/CAC sensitivity"],
                strategic_implication=(
                    "Theoretical absence of paid media signals an Organic or Sales-Led Growth model. "
                    "The company does not appear to pay for attention, relying instead on brand equity "
                    "or direct sales outreach to generate leads."
                )
            )

        return SignalInference(
            section="Paid Media",
            data_status="present",
            confidence="high",
            plausible_causes=["Performance marketing", "Demand capture"],
            strategic_implication=(
                f"Active paid acquisition on {', '.join(platforms)} suggests a machine-like 'Pay-to-Play' growth model. "
                "The business economics likely support high CAC, implying strong LTV or aggressive land-grab goals."
            )
        )

    # --- Synthesis Logic --------------------------------------------------

    def _synthesize_posture(self, inferences: List[SignalInference]) -> str:
        """
        Produce the mandatory 'Strategic Posture Summary' paragraph.
        """
        # Count statuses
        statuses = Counter([i.data_status for i in inferences])
        present_count = statuses["present"]
        absent_count = statuses["absent"] + statuses["error"]

        # 1. Determine density profile
        if absent_count > present_count * 2:
            density_profile = (
                "The target exhibits a 'Dark Forest' signals profile. Public data is scarce, "
                "indicating an organization that operates via private relationships, legacy channels, "
                "or intentional stealth."
            )
        elif present_count > absent_count:
            density_profile = (
                "The target exhibits a 'Glass House' signals profile. Digital operations are highly visible, "
                "suggesting a modern, transparent organization that competes in the open market."
            )
        else:
            density_profile = (
                "The target exhibits a 'Hybrid' signals profile, with strong visibility in some vectors "
                "and opacity in others (likely separating public brand from private operations)."
            )

        # 2. Extract key implication (take the most confident 'present' one, or a strong 'absent' one)
        key_factor = "Unknown"
        for inf in inferences:
            if inf.section == "Customer Voice" and inf.data_status == "absent":
                key_factor = "It relies on reputation over public validation"
                break
            if inf.section == "Paid Media" and inf.data_status == "present":
                key_factor = "It uses capital to force-multiply growth"
                break
            if inf.section == "Web Presence" and inf.data_status == "present":
                key_factor = "It treats its web presence as a primary asset"
        
        return (
            f"{density_profile} "
            f"Structurally, the organization appears optimized for control and stability rather than viral speed. "
            f"{key_factor}. "
            "Primary vulnerability is likely the gap between internal reality and external perception."
        )
