from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from loguru import logger

try:
    import google.generativeai as genai  # type: ignore
except ImportError:  # optional dependency
    genai = None


class LLMClient:
    """
    Deterministic, test-friendly LLM client.

    - plan_tools(...) returns a dict of booleans indicating which MCPs to call.
    - synthesize_report(...) returns a stable Markdown report.

    This version is fully self-contained: no external LLMs, no API keys.
    """

    def __init__(self) -> None:
        # No external configuration; deterministic by design.
        ...

    @staticmethod
    def _empty_plan() -> Dict[str, bool]:
        return {
            "use_web_scrape": False,
            "use_seo_probe": False,
            "use_tech_stack": False,
            "use_reviews_snapshot": False,
            "use_social_snapshot": False,
            "use_careers_intel": False,
            "use_ads_snapshot": False,
        }

    @staticmethod
    def _base_plan_for_url() -> Dict[str, bool]:
        """
        Default plan when we at least have a URL:
        web + seo + tech on; everything else off.
        """
        plan = LLMClient._empty_plan()
        plan["use_web_scrape"] = True
        plan["use_seo_probe"] = True
        plan["use_tech_stack"] = True
        return plan

    def plan_tools(
        self,
        company_name: Optional[str],
        company_url: Optional[str],
        focus: Optional[str],
    ) -> Dict[str, bool]:
        """
        Deterministic planning heuristic (no external LLM).

        Decide which MCPs to use based on the presence of a URL and the focus string.

        Test expectations:
        - If company_url is None and focus is None -> all tools disabled.
        - If company_url is present -> web/seo/tech enabled by default.
        - If focus mentions reviews / brand / reputation / hiring / ads / etc.,
          turn on the corresponding MCPs.
        """
        text = (focus or "").lower()

        # No URL and no focus context: do nothing.
        if not company_url and not text:
            return self._empty_plan()

        # Start from base plan when we have a URL; otherwise, all off and only enable
        # what the focus strictly demands.
        if company_url:
            plan = self._base_plan_for_url()
        else:
            plan = self._empty_plan()

        # --- Focus heuristics -------------------------------------------------
        if text:
            # Reviews / brand / reputation => reviews + social
            if any(
                word in text
                for word in ["review", "reviews", "brand", "reputation", "customer", "voice"]
            ):
                plan["use_reviews_snapshot"] = True
                plan["use_social_snapshot"] = True

            # Explicit social mentions => social
            if any(
                word in text
                for word in ["social", "twitter", "instagram", "tiktok", "youtube", "community"]
            ):
                plan["use_social_snapshot"] = True

            # Hiring / org / team => careers intel
            if any(
                word in text
                for word in [
                    "hiring",
                    "hire",
                    "recruit",
                    "talent",
                    "headcount",
                    "org",
                    "organization",
                    "team",
                ]
            ):
                plan["use_careers_intel"] = True

            # Ads / paid / growth / marketing => ads snapshot
            if any(
                word in text
                for word in [
                    "ads",
                    "advertising",
                    "campaign",
                    "cpc",
                    "paid",
                    "growth",
                    "marketing",
                ]
            ):
                plan["use_ads_snapshot"] = True

        return plan

    # ------------------------------------------------------------------ #
    # Synthesis: default, red-team, and narrative/article modes
    # ------------------------------------------------------------------ #

    def synthesize_report(
        self,
        profile_dict: Dict[str, Any],
        focus: Optional[str],
        delta_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Deterministic Markdown report.

        Tests assert the presence of:
        - "# OSINT Intelligence Report"
        - Headings like "Web Presence", "SEO Diagnostics", etc.

        Tone / style is controlled via the `focus` string:

        - If focus mentions "red team", "red-team", "opfor", "attack surface", or
          "adversarial", the report is framed in an OPFOR / hostile auditor voice.

        - If focus mentions "narrative", "article", "case study", "essay", or "story",
          the report maintains the same headings but reads more like a human-written
          article than a bullet list.

        - Otherwise, a neutral consultant voice is used.
        """
        company = profile_dict.get("company", {}) or {}
        company_name = company.get("name") or "Unknown Company"

        # If we still don't know the company name, try to fall back to the web meta title
        if company_name == "Unknown Company":
            web_meta = (profile_dict.get("web") or {}).get("meta") or {}
            fallback_title = web_meta.get("title")
            if fallback_title:
                company_name = fallback_title

        focus_str = focus or "General OSINT & growth posture"

        focus_l = (focus or "").lower()
        if any(
            kw in focus_l
            for kw in ["red team", "red-team", "opfor", "attack surface", "adversarial"]
        ):
            mode = "red_team"
        elif any(
            kw in focus_l
            for kw in ["narrative", "article", "case study", "essay", "story"]
        ):
            mode = "narrative"
        else:
            mode = "default"

        if mode == "narrative":
            body = self._build_narrative_report(profile_dict, company_name)
        else:
            body = self._build_sectioned_report(
                profile_dict,
                company_name,
                red_team=(mode == "red_team"),
                delta_context=delta_context
            )

        return (
            f"# OSINT Intelligence Report: {company_name}\n\n"
            f"_Focus: {focus_str}_\n\n"
            f"{body}"
        )

    # ------------------------------------------------------------------ #
    # Internal helpers for different styles
    # ------------------------------------------------------------------ #

    def _build_sectioned_report(
        self,
        profile_dict: Dict[str, Any],
        company_name: str,
        red_team: bool = False,
        delta_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Structured, sectioned report using the Interpretive Inference Layer.
        Now consumes SignalInference objects instead of raw data.
        """
        lines: list[str] = []
        
        # 0. Strategic Trajectory (if delta exists)
        if delta_context and delta_context.get("shifts"):
            lines.append(f"> **Strategic Trajectory (Last {int(delta_context.get('time_elapsed_days', 30))} Days)**\n")
            stab_score = delta_context.get("overall_stability_score", 1.0)
            stab_label = "High" if stab_score > 0.8 else "Medium" if stab_score > 0.5 else "Low"
            lines.append(f"> * **Stability**: {stab_label}\n")
            lines.append(f"> * **Major Shifts**:\n")
            
            for shift in delta_context.get("shifts", []):
                # Only show High/Medium significance in summary to avoid noise
                if shift.get("significance") in ("high", "medium"):
                    icon = "CRITICAL" if shift.get("significance") == "high" else "WARNING"
                    lines.append(f">     * [{icon}] {shift.get('section')}: {shift.get('description')}\n")
            lines.append("\n")
        
        section_keys = [
            ("web", "1. Web Presence"),
            ("seo", "2. SEO Diagnostics"),
            ("tech_stack", "3. Tech Stack Fingerprint"),
            ("reviews", "4. Customer Voice & Reviews"),
            ("social", "5. Social Footprint"),
            ("hiring", "6. Hiring & Org Signals"),
            ("ads", "7. Ads & Growth Motions"),
        ]

        def rt(normal: str, spicy: str) -> str:
            return spicy if red_team else normal

        for key, title in section_keys:
            inf = profile_dict.get(key)
            if not inf:
                lines.append(f"## {title}\n\n*No inference data available.*\n\n")
                continue
            
            # Logic: If raw data was error/absent, we use the strategic implication.
            # If present, we also use the strategic implication but maybe format it differently?
            # actually, the requirement is to ALWAYS use the inference.
            
            lines.append(f"## {title}\n\n")
            
            status_line = f"**Status**: {inf.get('data_status', 'detecting').upper()}"
            conf_line = f"**Confidence**: {inf.get('confidence', 'medium').upper()}"
            lines.append(f"{status_line} | {conf_line}\n\n")
            
            impl = inf.get("strategic_implication")
            lines.append(f"{impl}\n\n")
            
            risk = inf.get("risk_note")
            if risk:
                lines.append(f"> [!NOTE]\n> **Risk Factor**: {risk}\n\n")
                
            if inf.get("data_status") != "present":
                 causes = ", ".join(inf.get("plausible_causes") or [])
                 if causes:
                     lines.append(f"_Potential causes: {causes}_\n\n")
        
        # 8. Strategic Posture (Mandatory)
        lines.append("## 8. Strategic Recommendations\n\n")
        posture = profile_dict.get("strategic_posture") or "System failed to synthesize posture."
        lines.append(f"{posture}\n\n")

        # Add red team addendum if requested
        if red_team:
             lines.append("## 9. Red Team Addendum\n\n")
             lines.append(
                 "- **Attack Surface**: The gaps identified above (Absent/Partial signals) are the primary entry points. "
                 "Opacity is not security; it often masks negligence.\n"
             )

        return "".join(lines)

    def _build_narrative_report(
        self,
        profile_dict: Dict[str, Any],
        company_name: str,
    ) -> str:
        """
        Narrative / article-style report.

        Keeps the same numbered headings (for test compatibility) but writes more
        in paragraphs than bullets, so it reads like a short, opinionated essay.
        """
        web = profile_dict.get("web") or {}
        seo = profile_dict.get("seo") or {}
        tech = profile_dict.get("tech_stack") or {}
        reviews = profile_dict.get("reviews") or {}
        social = profile_dict.get("social") or {}
        hiring = profile_dict.get("hiring") or {}
        ads = profile_dict.get("ads") or {}

        meta = web.get("meta") or {}
        title = meta.get("title") or "an unnamed site"
        desc = meta.get("description") or "no explicit promise in its description"

        pieces: list[str] = []

        # 1. Web Presence
        pieces.append("## 1. Web Presence\n\n")
        pieces.append(
            f"{company_name} introduces itself through a site whose primary page is titled **{title}**. "
            f"For search engines and link previews, it offers {desc}. "
            "This tiny block of text is effectively the company’s elevator pitch to people who haven’t "
            "decided yet whether to care.\n\n"
        )

        # 2. SEO Diagnostics
        pieces.append("## 2. SEO Diagnostics\n\n")
        meta_issues = seo.get("meta_issues") or []
        heading_issues = seo.get("heading_issues") or []
        if seo.get("error"):
            pieces.append(
                f"The SEO probe did not complete cleanly (`{seo['error']}`), which means we only have a partial view "
                "into how the site is structured for discoverability.\n\n"
            )
        elif meta_issues or heading_issues:
            pieces.append(
                "Looking at the on-page structure, a few seams show through. Titles, descriptions, and headings don’t "
                "fully support the story the company seems to want to tell. The following structural issues stand out:\n\n"
            )
            for issue in meta_issues + heading_issues:
                pieces.append(f"- {issue}\n")
            pieces.append("\n")
        else:
            pieces.append(
                "On-page SEO appears mostly coherent. If the company is difficult to find or understand, the problem "
                "likely lives in channel strategy, messaging, or execution rather than basic HTML scaffolding.\n\n"
            )

        # 3. Tech Stack Fingerprint
        pieces.append("## 3. Tech Stack Fingerprint\n\n")
        if tech.get("error"):
            pieces.append(
                f"The underlying stack could not be fully identified (`{tech['error']}`), leaving the exact tooling "
                "and hosting picture slightly blurred.\n\n"
            )
        else:
            frameworks = ", ".join(tech.get("frameworks") or []) or "no visible frontend framework layer"
            analytics = ", ".join(tech.get("analytics") or []) or "no obvious analytics tags"
            cms = tech.get("cms") or "no recognizable CMS"
            cdn = tech.get("cdn") or "no clearly fingerprinted CDN"
            pieces.append(
                f"Under the surface, the site appears to run on {frameworks}, with {analytics} observing traffic. "
                f"Content is managed through {cms}, and distribution is handled by {cdn}. "
                "These choices tell us how quickly the organization can change its mind and how much of its "
                "infrastructure it has chosen to outsource.\n\n"
            )

        # 4. Customer Voice & Reviews
        pieces.append("## 4. Customer Voice & Reviews\n\n")
        if reviews.get("error"):
            pieces.append(
                f"Public review data was not successfully consolidated (`{reviews['error']}`), so we do not yet have a "
                "reliable aggregate of how customers narrate their experience.\n\n"
            )
        else:
            summary = reviews.get("summary")
            if summary:
                pieces.append(
                    f"Outside the company’s own channels, reviews sketch a parallel narrative. {summary} "
                    "The contrast between that story and the one told on the official site is where trust is "
                    "either reinforced or quietly eroded.\n\n"
                )
            else:
                pieces.append(
                    "At the moment, there is not enough structured review data to draw a strong conclusion about how "
                    "customers talk about the company in public.\n\n"
                )

        # 5. Social Footprint
        pieces.append("## 5. Social Footprint\n\n")
        if social.get("error"):
            pieces.append(
                f"Social channels could not be reliably captured (`{social['error']}`). As a result, the live, "
                "conversational edge of the brand remains partially off-stage in this snapshot.\n\n"
            )
        else:
            pieces.append(
                "Social platforms, when active, function as the company’s running internal monologue. They show how "
                "the organization responds to minor crises, which stories it repeats, and which audiences it actually "
                "spends attention on. Even a quiet feed tells us something about where narrative control sits on the "
                "priority list.\n\n"
            )

        # 6. Hiring & Org Signals
        pieces.append("## 6. Hiring & Org Signals\n\n")
        if hiring.get("error"):
            pieces.append(
                f"Hiring signals were not available in a structured way (`{hiring['error']}`), limiting our view into "
                "where the organization is investing headcount.\n\n"
            )
        else:
            inferred = hiring.get("inferred_focus") or "no single dominant hiring theme yet"
            pieces.append(
                f"Job postings are often a more honest lens into strategy than public statements. In this snapshot, "
                f"the pattern of roles suggests **{inferred}** as a central concern. "
                "The teams being grown today will set the shape of the organization a year from now.\n\n"
            )

        # 7. Ads & Growth Motions
        pieces.append("## 7. Ads & Growth Motions\n\n")
        if ads.get("error"):
            pieces.append(
                f"Paid media activity could not be fully read (`{ads['error']}`), so the picture of how the company "
                "buys attention remains incomplete.\n\n"
            )
        else:
            platforms = ", ".join(ads.get("platforms") or []) or "no obvious paid media channels in this sample"
            themes = ", ".join(ads.get("themes") or []) or "no clearly repeating message"
            pieces.append(
                f"Where a company spends on ads is a concrete record of which audiences it believes matter most. "
                f"In this case, the visible channels are {platforms}, and the recurring themes cluster around "
                f"{themes}. Together, they indicate how the organization is trying to grow and what it thinks is "
                "persuasive.\n\n"
            )

        # 8. Strategic Recommendations
        pieces.append("## 8. Strategic Recommendations\n\n")
        pieces.append(
            "Taken together, these signals describe not just how the company looks from the outside, but how quickly "
            "it can adapt. Tightening the alignment between the promise on the landing page, the language customers "
            "actually use, and the internal bets visible in hiring and ads would make the overall posture more "
            "coherent—and easier for outsiders to trust.\n"
        )

        return "".join(pieces)


from core.analyst_prompts import PLANNING_PROMPT, SYNTHESIS_PROMPT


class GeminiLLMClient(LLMClient):
    """
    Real LLM-backed client using Google Gemini.

    Behavior:
    - If USE_GEMINI_LLM is not set/enabled, or GOOGLE_API_KEY / google-generativeai
      are missing, fall back to the deterministic LLMClient behavior.
    - Otherwise, use Gemini for:
        * plan_tools(...)        -> JSON tool plan
        * synthesize_report(...) -> Markdown report
    """

    def __init__(self) -> None:
        super().__init__()

        raw_flag = os.getenv("USE_GEMINI_LLM", "0")
        api_key = os.getenv("GOOGLE_API_KEY")

        logger.info(
            "GeminiLLMClient INIT DEBUG: raw_flag=%r, api_key_set=%r, genai_imported=%r",
            raw_flag,
            bool(api_key),
            genai is not None,
        )

        use_gemini = raw_flag in {"1", "true", "True"}
        self._enabled = bool(use_gemini and api_key and genai is not None)

        if not self._enabled:
            # Soft failure: keep deterministic behavior
            if not use_gemini:
                logger.info(
                    "GeminiLLMClient: USE_GEMINI_LLM not enabled; "
                    "using deterministic LLMClient behavior."
                )
            elif not api_key:
                logger.warning(
                    "GeminiLLMClient: GOOGLE_API_KEY not set; "
                    "falling back to deterministic LLMClient."
                )
            elif genai is None:
                logger.warning(
                    "GeminiLLMClient: google-generativeai not installed; "
                    "falling back to deterministic LLMClient."
                )
            return

        genai.configure(api_key=api_key)

        self.plan_model_name = os.getenv("GEMINI_PLANNING_MODEL", "gemini-2.5-flash")
        self.synth_model_name = os.getenv("GEMINI_SYNTHESIS_MODEL", "gemini-2.5-flash")
        try:
            self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
        except ValueError:
            self.temperature = 0.1

        logger.info(
            f"GeminiLLMClient enabled with planning={self.plan_model_name}, "
            f"synthesis={self.synth_model_name}, temperature={self.temperature}"
        )

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #

    def plan_tools(
        self,
        company_name: Optional[str],
        company_url: Optional[str],
        focus: Optional[str],
    ) -> Dict[str, bool]:
        # If Gemini isn't actually enabled, use the deterministic logic.
        if not self._enabled:
            return super().plan_tools(company_name, company_url, focus)

        # If literally no signal, still bail out early.
        if not company_url and not (focus or "").strip():
            return self._empty_plan()

        prompt = (
            f"{PLANNING_PROMPT}\n\n"
            "You are the planning LLM for Micro-Analyst.\n"
            "Decide which MCP tools to call for this analysis.\n\n"
            f"Company name: {company_name or 'Unknown'}\n"
            f"Company URL: {company_url or 'None'}\n"
            f"User focus / priorities: {focus or 'None provided'}\n\n"
            "Return ONLY a JSON object with these boolean keys:\n"
            "  use_web_scrape,\n"
            "  use_seo_probe,\n"
            "  use_tech_stack,\n"
            "  use_reviews_snapshot,\n"
            "  use_social_snapshot,\n"
            "  use_careers_intel,\n"
            "  use_ads_snapshot.\n"
            "Example:\n"
            "{\n"
            '  "use_web_scrape": true,\n'
            '  "use_seo_probe": true,\n'
            '  "use_tech_stack": true,\n'
            '  "use_reviews_snapshot": false,\n'
            '  "use_social_snapshot": false,\n'
            '  "use_careers_intel": true,\n'
            '  "use_ads_snapshot": false\n'
            "}\n"
        )

        try:
            model = genai.GenerativeModel(self.plan_model_name)
            resp = model.generate_content(
                prompt,
                generation_config={"temperature": self.temperature},
            )
            text = (resp.text or "").strip()
        except Exception as e:  # pragma: no cover - network/LLM failure
            logger.error(f"GeminiLLMClient.plan_tools: LLM error: {e}")
            return super().plan_tools(company_name, company_url, focus)

        plan = self._parse_plan_json(text)
        if plan is None:
            logger.warning(
                "GeminiLLMClient.plan_tools: could not parse JSON, "
                "falling back to deterministic planner."
            )
            return super().plan_tools(company_name, company_url, focus)

        return plan

    @classmethod
    def _parse_plan_json(cls, text: str) -> Optional[Dict[str, bool]]:
        """
        Best-effort parse of a JSON object from arbitrary LLM text.

        Returns None on failure.
        """
        if not text:
            return None

        # Try to extract the first {...} block.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            raw = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

        # Normalize into the full plan dict.
        plan = LLMClient._empty_plan()
        for key in list(plan.keys()):
            if key in raw:
                plan[key] = bool(raw[key])

        return plan

    # ------------------------------------------------------------------ #
    # Synthesis
    # ------------------------------------------------------------------ #

    def synthesize_report(
        self,
        profile_dict: Dict[str, Any],
        focus: Optional[str],
        delta_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enhanced multi-voice synthesis:
        - standard        → normal operator brief
        - red_team        → explicit OPFOR teardown + attack plan
        - narrative       → longform magazine-style prose, NOT bullets
        - investor_brief  → punchy, metrics-forward
        - founder_playbook→ actionable strategy blueprint
        """

        # If Gemini isn't enabled, fallback to deterministic
        if not self._enabled:
            return super().synthesize_report(profile_dict, focus, delta_context)

        # --- Detect voice ---
        style = "standard"
        lf = (focus or "").lower()

        if "red team" in lf or "opfor" in lf or "adversarial" in lf:
            style = "red_team"
        elif "narrative" in lf or "article" in lf or "essay" in lf:
            style = "narrative"
        elif "investor" in lf:
            style = "investor"
        elif "founder" in lf or "playbook" in lf:
            style = "founder"

        # --- Voice-specific instructions ---
        if style == "red_team":
            voice_block = """
You are an OPFOR red-team strategist writing for another attacker.

Goal:
- Design a realistic, OSINT-grounded plan for how to break or seriously damage this company.

Required structure:
1. Start with a short "Vulnerability Overview" (2–4 sentences) summarizing why this org is structurally vulnerable.
2. Then add a section titled "Primary Attack Paths" with a numbered list.
   - Each item MUST:
     * Name the vector (e.g. "Third-party stack sprawl", "Brand–reality gap in reviews", "Single-channel growth dependency").
     * Tie it directly to specific OSINT signals from the profile (tech stack, reviews, hiring, ads, social, web surface).
     * Explain expected impact if exploited (e.g. operational paralysis, narrative collapse, churn spike).
3. Add a short section "Campaign Design" that explains how you would sequence these attacks over time for maximum effect.
4. End with "Most Exploitable Asymmetry" — one paragraph on the single easiest high-leverage way to hurt them.

Tone rules:
- Write entirely from attacker POV: "We would exploit...", "We would start by...", "We should prioritize...".
- No generic advice like "they should improve X". You are not helping them; you are planning against them.
- No praise except as setup for exploitation (e.g. "Their strong brand reliance becomes a liability because...").
- Clinical, hostile, unsentimental.
- You MAY use numbered lists and bullets for attack paths; keep everything tightly reasoned and concrete.
            """
        elif style == "narrative":
            voice_block = """
Write as a senior strategy analyst writing a long-form brief for smart operators.
Think closer to The Economist, FT Big Read, or Stratechery than a lifestyle blog.

Tone rules:
- Analytical, concrete, mildly opinionated.
- NO poetic metaphors about "tapestries", "whispers", "sanctuaries", "canvases", or similar.
- Avoid vague praise like "vibrant community", "deep roots", "sanctuary", "timeless" unless you immediately ground it in specific observable signals.
- Ground every claim in OSINT evidence: metadata, copy, tech stack, hiring, reviews, ads, or the absence of these signals.
- If a signal is missing (no reviews, no social, no ads), say so plainly and analyze what that absence likely means; do NOT romanticize the silence.
- Use smooth, continuous prose with clear paragraphs.
- You MAY end with a short numbered list of 3–5 operator-grade recommendations; the rest of the report must be prose, not bullets.
- Assume the reader is an experienced founder or investor; keep sentences tight, avoid filler, and do not roleplay as marketing copy.
            """

        elif style == "investor":
            voice_block = """
Write as a hard-nosed private equity analyst.

Tone & structure:
- Terse, metrics-driven, skeptical.
- Focus on: market position, unit economics proxies, scalability, margin threats, execution risk, and moats.
- Organize with short, clearly titled sections (e.g. "Market Position", "Unit Economics Proxies", "Execution Risk").
- You MAY use brief bullet lists for metrics or key risks, but avoid long bullet forests.
- Default stance: "What would break if we put real money behind this, and is it worth fixing?"
            """
        elif style == "founder":
            voice_block = """
Write like a YC partner or elite operator reviewing a company.

Tone & structure:
- Blunt, strategic, leverage-focused.
- Assume the reader is the founder; speak directly to them.
- Provide a clear strategic blueprint for the next 90–180 days.
- Organize as short, crisp paragraphs labeled by focus ("Positioning", "Product Surface", "Ops & Org", "Growth System").
- Avoid bullets unless absolutely necessary; favor readable blocks of concrete, actionable guidance.
            """
        else:
            voice_block = """
Write a standard OSINT intelligence brief with neutral tone.

Tone & structure:
- Neutral, analytic, slightly consultant-y but not fluffy.
- Use short paragraphs.
- Section the report logically by surface: Web / SEO / Tech / Reviews / Social / Hiring / Ads / Strategy.
- Bullets are allowed but keep them compact and information-dense.
            """

        # --- Build prompt ---
        prompt = f"""
{SYNTHESIS_PROMPT}

You are in synthesis mode for Micro-Analyst.

VOICE DIRECTIVE:
{voice_block}

Global rules:
- ALWAYS stay in the chosen voice and perspective.
- For red_team and investor modes, you MAY use numbered lists or bullets where they make the structure clearer.
- For narrative and founder modes, strongly prefer continuous prose and avoid bullets unless explicitly justified.
- ALWAYS ground your claims in the OSINT profile fields when possible (web, seo, tech_stack, reviews, social, hiring, ads).
- Do NOT repeat raw JSON; interpret it.
- Output ONLY the report text (no JSON, no explanations of your reasoning).

Company OSINT profile (JSON):
{json.dumps(profile_dict, ensure_ascii=False, indent=2)}

User focus / priorities:
{focus or "None provided"}

Strategic Trajectory (Delta / Changes):
{json.dumps(delta_context, ensure_ascii=False, indent=2) if delta_context else "No historical baseline available."}

INSTRUCTION ON TRAJECTORY:
If "Strategic Trajectory" data is present (delta_context), you MUST start the report (before Section 1) with a special section:
> **Strategic Trajectory (Last 30 Days)**
> *   **Stability**: [High/Medium/Low]
> *   **Major Shifts**:
>     *   [CRITICAL/WARNING/INFO] [Signal Description]
If NO "Strategic Trajectory" data is present, omit this section entirely.
"""

        try:
            model = genai.GenerativeModel(self.synth_model_name)
            resp = model.generate_content(
                prompt,
                generation_config={"temperature": self.temperature},
            )
            text = (resp.text or "").strip()
        except Exception as e:
            logger.error(f"GeminiLLMClient.synthesize_report: LLM error: {e}")
            return super().synthesize_report(profile_dict, focus)

        if not text:
            logger.warning("Empty LLM response; falling back to deterministic.")
            return super().synthesize_report(profile_dict, focus)

        return text


class OllamaLLMClient(LLMClient):
    """
    Local LLM client using Ollama for development and testing.
    
    Avoids API costs by using locally-hosted models.
    
    Environment variables:
    - USE_OLLAMA_LLM: Set to "1" to enable
    - OLLAMA_MODEL: Model name (default: gemma3:27b)
    - OLLAMA_BASE_URL: Ollama API URL (default: http://localhost:11434)
    """
    
    def __init__(self) -> None:
        super().__init__()
        
        raw_flag = os.getenv("USE_OLLAMA_LLM", "0")
        self._enabled = raw_flag in {"1", "true", "True"}
        
        if not self._enabled:
            logger.info("OllamaLLMClient: USE_OLLAMA_LLM not enabled; using deterministic behavior.")
            return
        
        self.model_name = os.getenv("OLLAMA_MODEL", "gemma3:27b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        try:
            self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
        except ValueError:
            self.temperature = 0.1
        
        logger.info(
            f"OllamaLLMClient enabled with model={self.model_name}, "
            f"base_url={self.base_url}, temperature={self.temperature}"
        )
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Make a request to the Ollama API."""
        import requests
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }
        
        try:
            # Increased timeout to 300s (5 min) for 27b model synthesis on large contexts
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            result = resp.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"OllamaLLMClient: API error: {e}")
            return None
    
    def plan_tools(
        self,
        company_name: Optional[str],
        company_url: Optional[str],
        focus: Optional[str],
    ) -> Dict[str, bool]:
        if not self._enabled:
            return super().plan_tools(company_name, company_url, focus)
        
        if not company_url and not (focus or "").strip():
            return self._empty_plan()
        
        prompt = (
            "You are the planning LLM for Micro-Analyst, an OSINT intelligence system.\n"
            "Decide which MCP tools to call for this analysis.\n\n"
            f"Company name: {company_name or 'Unknown'}\n"
            f"Company URL: {company_url or 'None'}\n"
            f"User focus / priorities: {focus or 'None provided'}\n\n"
            "Return ONLY a JSON object with these boolean keys:\n"
            "  use_web_scrape,\n"
            "  use_seo_probe,\n"
            "  use_tech_stack,\n"
            "  use_reviews_snapshot,\n"
            "  use_social_snapshot,\n"
            "  use_careers_intel,\n"
            "  use_ads_snapshot.\n"
            "Example:\n"
            "{\n"
            '  "use_web_scrape": true,\n'
            '  "use_seo_probe": true,\n'
            '  "use_tech_stack": true,\n'
            '  "use_reviews_snapshot": false,\n'
            '  "use_social_snapshot": false,\n'
            '  "use_careers_intel": true,\n'
            '  "use_ads_snapshot": false\n'
            "}\n"
            "Return ONLY the JSON, no other text."
        )
        
        text = self._call_ollama(prompt)
        if not text:
            logger.warning("OllamaLLMClient.plan_tools: empty response, falling back to deterministic.")
            return super().plan_tools(company_name, company_url, focus)
        
        plan = GeminiLLMClient._parse_plan_json(text)
        if plan is None:
            logger.warning("OllamaLLMClient.plan_tools: could not parse JSON, falling back to deterministic.")
            return super().plan_tools(company_name, company_url, focus)
        
        return plan
    
    def synthesize_report(self, profile_dict: Dict[str, Any], focus: Optional[str]) -> str:
        if not self._enabled:
            return super().synthesize_report(profile_dict, focus)
        
        # Detect voice mode
        style = "standard"
        lf = (focus or "").lower()
        
        if "red team" in lf or "opfor" in lf or "adversarial" in lf:
            style = "red_team"
        elif "narrative" in lf or "article" in lf or "essay" in lf:
            style = "narrative"
        elif "investor" in lf:
            style = "investor"
        elif "founder" in lf or "playbook" in lf:
            style = "founder"
        
        # Voice-specific instructions
        if style == "red_team":
            voice_block = """
You are an OPFOR red-team strategist writing for another attacker.
Goal: Design a realistic, OSINT-grounded plan for how to break or seriously damage this company.
Required structure:
1. Start with a short "Vulnerability Overview" (2–4 sentences).
2. Then add "Primary Attack Paths" with a numbered list.
3. Add "Campaign Design" explaining how to sequence attacks.
4. End with "Most Exploitable Asymmetry".
Tone: Write from attacker POV. Clinical, hostile, unsentimental.
"""
        elif style == "narrative":
            voice_block = """
Write as a senior strategy analyst for smart operators (FT/Economist style).
Analytical, concrete, mildly opinionated. NO poetic metaphors.
Ground every claim in OSINT evidence. Use smooth prose, not bullets.
"""
        elif style == "investor":
            voice_block = """
Write as a hard-nosed private equity analyst.
Terse, metrics-driven, skeptical.
Focus on: market position, unit economics, scalability, margin threats, execution risk.
"""
        elif style == "founder":
            voice_block = """
Write like a YC partner reviewing a company.
Blunt, strategic, leverage-focused.
Provide a clear 90-180 day strategic blueprint.
"""
        else:
            voice_block = """
Write a standard OSINT intelligence brief with neutral tone.
Use short paragraphs, structured by surface: Web / SEO / Tech / Reviews / Social / Hiring / Ads / Strategy.
"""
        
        prompt = f"""
You are an OSINT intelligence analyst synthesizing a report.

VOICE DIRECTIVE:
{voice_block}

CRITICAL DATA INSTRUCTION:
You are provided with an **Inferred Intelligence Profile**. 
- Each section contains a `strategic_implication` field. 
- You MUST use this field as the ground truth. 
- If `data_status` is 'absent' or 'error', rely on the `strategic_implication` to explain WHAT that absence means.
- DO NOT say "data unavailable". Say what the absence suggests (e.g., "The absence of reviews suggests a B2B relationship-based sales motion").
- The profile ends with a `strategic_posture` summary. You MUST include this insight in your conclusion or executive summary.

Global rules:
- ALWAYS stay in the chosen voice and perspective.
- Output ONLY the report text (no JSON, no meta-commentary).

Company OSINT profile (JSON):
{json.dumps(profile_dict, ensure_ascii=False, indent=2)}

User focus / priorities:
{focus or "None provided"}

Generate the report now:
"""
        
        text = self._call_ollama(prompt)
        if not text:
            logger.warning("OllamaLLMClient.synthesize_report: empty response, falling back to deterministic.")
            return super().synthesize_report(profile_dict, focus)
        
        return text.strip()


def get_llm_client() -> LLMClient:
    """
    Factory: returns the appropriate LLM client based on environment configuration.
    
    Priority order (first enabled wins):
    1. USE_OLLAMA_LLM=1 -> OllamaLLMClient (local, free)
    2. USE_GEMINI_LLM=1 -> GeminiLLMClient (cloud, paid API)
    3. Neither -> base deterministic LLMClient
    
    This prioritizes local Ollama to avoid accidental API costs during development.
    """
    # Check Ollama first (local, free)
    if os.getenv("USE_OLLAMA_LLM", "0") in {"1", "true", "True"}:
        try:
            client = OllamaLLMClient()
            logger.info("get_llm_client: Using OllamaLLMClient (local)")
            return client
        except Exception as e:
            logger.error(f"get_llm_client: Failed to init OllamaLLMClient: {e}")
    
    # Check Gemini second (cloud, paid)
    if os.getenv("USE_GEMINI_LLM", "0") in {"1", "true", "True"}:
        try:
            client = GeminiLLMClient()
            logger.info("get_llm_client: Using GeminiLLMClient (cloud)")
            return client
        except Exception as e:
            logger.error(f"get_llm_client: Failed to init GeminiLLMClient: {e}")
    
    # Fallback to deterministic
    logger.info("get_llm_client: Using deterministic LLMClient (no external LLM)")
    return LLMClient()
