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
    ) -> str:
        """
        Deterministic report.

        HARD OVERRIDE for debugging:
        - If `focus` contains "narrative"/"article"/"essay", FORCE a very obviously
          different narrative-style output so we can confirm this code path is active.
        """

        # --- Basic fields -----------------------------------------------------
        company = profile_dict.get("company", {}) or {}
        company_name = company.get("name") or "Unknown Company"

        # Fallback: if company name is missing, try web.meta.title
        if company_name == "Unknown Company":
            web = profile_dict.get("web") or {}
            meta = web.get("meta") or {}
            meta_title = meta.get("title")
            if meta_title:
                company_name = meta_title

        focus_str = focus or "General OSINT & growth posture"
        focus_l = (focus or "").lower()

        # --- HARD DEBUG SWITCH FOR NARRATIVE ---------------------------------
        if "narrative" in focus_l or "article" in focus_l or "essay" in focus_l:
            web = profile_dict.get("web") or {}
            meta = web.get("meta") or {}
            title = meta.get("title") or company_name or "an unnamed site"
            desc = meta.get("description") or "no explicit promise in its description"

            return (
                f"OSINT DEBUG NARRATIVE REPORT: {company_name}\n\n"
                f"_Focus: {focus_str}_\n\n"
                "Everyone else will see a boring, sectioned report. This is the special "
                "**narrative mode** path.\n\n"
                f"The company presents itself at the front door with the title “{title}” and "
                f"the promise: {desc}. From that single sentence you can already infer what "
                "they think strangers should remember about them when every other pixel is "
                "collapsed into a search snippet.\n\n"
                "This block of text exists purely so you can confirm that:\n"
                "- you are editing the correct `LLMClient.synthesize_report`, and\n"
                "- the `focus='narrative'` path is actually being used.\n\n"
                "Once you see THIS text in the UI, we can safely replace it with the more "
                "serious magazine-style narrative builder.\n"
            )

        # --- Non-narrative modes: default + red-team -------------------------
        if any(
            kw in focus_l
            for kw in ["red team", "red-team", "opfor", "attack surface", "adversarial"]
        ):
            red_team = True
        else:
            red_team = False

        body = self._build_sectioned_report(
            profile_dict,
            company_name,
            red_team=red_team,
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
    ) -> str:
        """
        Structured, sectioned report.

        When red_team=True, the language shifts into a more adversarial,
        OPFOR-style read: "if I had to break this, here’s what I’d stare at first."
        """
        web = profile_dict.get("web") or {}
        seo = profile_dict.get("seo") or {}
        tech = profile_dict.get("tech_stack") or {}
        reviews = profile_dict.get("reviews") or {}
        social = profile_dict.get("social") or {}
        hiring = profile_dict.get("hiring") or {}
        ads = profile_dict.get("ads") or {}

        def rt(normal: str, spicy: str) -> str:
            """Return red-team copy when enabled, otherwise neutral."""
            return spicy if red_team else normal

        lines: list[str] = []

        # 1. Web Presence
        lines.append("## 1. Web Presence\n\n")
        title = (web.get("meta") or {}).get("title") or "No title detected"
        desc = (web.get("meta") or {}).get("description") or "No meta description detected"

        lines.append(
            rt(
                f"- Landing page title: **{title}**\n"
                f"- Meta description (how they introduce themselves to strangers): {desc}\n",
                f"- First impression surface:\n"
                f"  - **Title**: **{title}** — this is the line they’ve decided to shout into the void.\n"
                f"  - **Meta description**: {desc}\n"
                f"- This is the copy an adversary reads before anything else, because it’s the one line "
                f"they bothered to polish for robots.\n",
            )
        )

        if web.get("error"):
            lines.append(
                rt(
                    f"- Web scrape error: `{web['error']}` (surface partially opaque).\n",
                    f"- Web scrape error: `{web['error']}` — anytime an org’s own site resists basic inspection, "
                    f"it’s either negligence or control-freakery. Both are exploitable.\n",
                )
            )

        lines.append("\n")

        # 2. SEO Diagnostics
        lines.append("## 2. SEO Diagnostics\n\n")
        if seo.get("error"):
            lines.append(
                rt(
                    f"- SEO probe error: `{seo['error']}`.\n",
                    f"- SEO probe error: `{seo['error']}` — their discoverability stack is either badly wired "
                    "or actively misconfigured. Either way, it’s a blind spot.\n",
                )
            )
        else:
            meta_issues = seo.get("meta_issues") or []
            heading_issues = seo.get("heading_issues") or []
            if not meta_issues and not heading_issues:
                lines.append(
                    rt(
                        "- No obvious on-page SEO issues detected.\n",
                        "- No easy on-page SEO own-goals. Low-hanging fruit for attack won’t be metadata; "
                        "you’ll have to look at the deeper plumbing.\n",
                    )
                )
            else:
                lines.append(
                    rt(
                        "- On-page SEO issues detected:\n",
                        "- On-page structural missteps that widen the gap between how they think they’re found "
                        "and how they actually show up:\n",
                    )
                )
                for issue in meta_issues + heading_issues:
                    lines.append(f"  - {issue}\n")

        lines.append("\n")

        # 3. Tech Stack Fingerprint
        lines.append("## 3. Tech Stack Fingerprint\n\n")
        if tech.get("error"):
            lines.append(
                rt(
                    f"- Tech stack detection error: `{tech['error']}`.\n",
                    f"- Tech stack detection error: `{tech['error']}` — partial visibility into the dependency graph. "
                    "Ideal place to push if you want to test how brittle they are under imperfect observability.\n",
                )
            )
        else:
            frameworks = ", ".join(tech.get("frameworks") or []) or "None detected"
            analytics = ", ".join(tech.get("analytics") or []) or "None detected"
            cms = tech.get("cms") or "None detected"
            cdn = tech.get("cdn") or "None detected"

            lines.append(f"- Frameworks: {frameworks}\n")
            lines.append(f"- Analytics: {analytics}\n")
            lines.append(f"- CMS: {cms}\n")
            lines.append(f"- CDN: {cdn}\n")

            if red_team:
                lines.append(
                    "\n- Each named service is a third-party trust boundary and a potential failure mode. "
                    "Every extra SaaS glued into the stack is another place they’re delegating both control "
                    "and vulnerability management.\n"
                )

        lines.append("\n")

        # 4. Customer Voice & Reviews
        lines.append("## 4. Customer Voice & Reviews\n\n")
        if reviews.get("error"):
            lines.append(
                rt(
                    f"- Reviews snapshot error: `{reviews['error']}`.\n",
                    f"- Reviews snapshot error: `{reviews['error']}` — either the signal is too thin to read, "
                    "or they’ve managed to avoid leaving public scars. Both conditions require a different attack.\n",
                )
            )
        else:
            summary = reviews.get("summary") or "No synthesized reviews summary available."
            lines.append(
                rt(
                    f"- Summary of customer sentiment: {summary}\n",
                    f"- Condensed customer sentiment: {summary}\n"
                    "- This is the discrepancy layer: the distance between how they talk about themselves and how "
                    "people talk about them when they’re annoyed and unsupervised.\n",
                )
            )
            complaints = reviews.get("top_complaints") or []
            praises = reviews.get("top_praises") or []

            if complaints:
                lines.append(
                    rt(
                        "- Recurring complaints:\n",
                        "- Recurring failure modes (things customers have already annotated for you):\n",
                    )
                )
                for c in complaints:
                    lines.append(f"  - {c}\n")

            if praises:
                lines.append("- Reliable strengths (things you’d be unwise to attack head-on):\n")
                for p in praises:
                    lines.append(f"  - {p}\n")

        lines.append("\n")

        # 5. Social Footprint
        lines.append("## 5. Social Footprint\n\n")
        if social.get("error"):
            lines.append(
                rt(
                    f"- Social snapshot error: `{social['error']}`.\n",
                    f"- Social snapshot error: `{social['error']}` — either they’re off-grid, or the crawl hit a wall. "
                    "Silence is still a posture.\n",
                )
            )
        else:
            if not any(
                social.get(k) for k in ["instagram", "youtube", "twitter", "tiktok"]
            ):
                lines.append(
                    rt(
                        "- No major social presence detected.\n",
                        "- No significant social presence: either they don’t believe in narrative control, or they’ve "
                        "outsourced it to channels you’re not seeing yet.\n",
                    )
                )
            else:
                lines.append(
                    rt(
                        "- Public channels detected and active.\n",
                        "- Active public channels detected — these are live surfaces where they improvise, panic, and "
                        "over-correct in real time.\n",
                    )
                )

        lines.append("\n")

        # 6. Hiring & Org Signals
        lines.append("## 6. Hiring & Org Signals\n\n")
        if hiring.get("error"):
            lines.append(
                rt(
                    f"- Hiring intel error: `{hiring['error']}`.\n",
                    f"- Hiring intel error: `{hiring['error']}` — their internal priorities aren’t visible through "
                    "standard job pipelines. You’ll need other telemetry to infer where the org is actually pushing.\n",
                )
            )
        else:
            inferred = hiring.get("inferred_focus") or "No clear hiring theme inferred."
            roles = hiring.get("open_roles") or []

            lines.append(
                rt(
                    f"- Inferred hiring focus: {inferred}\n",
                    f"- Inferred hiring focus: **{inferred}** — whatever they say in press releases, this is what "
                    "they’re quietly paying for.\n",
                )
            )

            if roles:
                lines.append(
                    rt(
                        "- Representative open roles:\n",
                        "- Representative open roles — where the headcount is actually moving:\n",
                    )
                )
                for r in roles[:10]:
                    title = r.get("title") or "Untitled role"
                    lines.append(f"  - {title}\n")

        lines.append("\n")

        # 7. Ads & Growth Motions
        lines.append("## 7. Ads & Growth Motions\n\n")
        if ads.get("error"):
            lines.append(
                rt(
                    f"- Ads snapshot error: `{ads['error']}`.\n",
                    f"- Ads snapshot error: `{ads['error']}` — either they aren’t paying for attention, or they’re "
                    "doing it in walled gardens you don’t have clean access to.\n",
                )
            )
        else:
            platforms = ", ".join(ads.get("platforms") or []) or "None detected"
            themes = ", ".join(ads.get("themes") or []) or "No unified theme detected"

            lines.append(f"- Paid media platforms: {platforms}\n")
            lines.append(f"- Messaging themes: {themes}\n")

            if red_team and platforms != "None detected":
                lines.append(
                    "- Every paid channel is both a spend hose and a narrative surface. "
                    "Disrupting these hits both revenue and story at the same time.\n"
                )

        lines.append("\n")

        # 8. Strategic Recommendations
        lines.append("## 8. Strategic Recommendations\n\n")
        if red_team:
            lines.append(
                "- Map the full third-party dependency graph implied by the tech stack; every external service is a "
                "potential leverage point or single point of failure.\n"
            )
            lines.append(
                "- Exploit the gap between what the marketing surface promises and what reviews describe: that delta is "
                "where trust erodes fastest.\n"
            )
        else:
            lines.append(
                "- Tighten on-page SEO metadata (titles, descriptions, headings) so the way you are found matches the "
                "way you want to be read.\n"
            )
            lines.append(
                "- Align marketing language with the actual words customers use in reviews to close the credibility gap.\n"
            )
            lines.append(
                "- Rationalize the tech stack and analytics footprint to reduce complexity and improve observability.\n"
            )
            lines.append(
                "- Use hiring and ads as explicit signals of strategy: if you’re paying for it or hiring for it, it "
                "should be legible on the public surface.\n"
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

    def synthesize_report(self, profile_dict: Dict[str, Any], focus: Optional[str]) -> str:
        """
        Enhanced multi-voice synthesis:
        - standard → normal operator brief
        - red_team → aggressive OPFOR teardown (no compliments unless weaponized)
        - narrative → longform magazine-style prose, NOT bullet points
        - investor_brief → punchy, metrics-forward
        - founder_playbook → actionable strategy blueprint
        """

        # If Gemini isn't enabled, fallback to deterministic
        if not self._enabled:
            return super().synthesize_report(profile_dict, focus)

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
Write as a hostile OPFOR analyst performing a forensic teardown.
Tone rules:
- No praise unless used as a setup for a more damaging criticism.
- Identify structural weaknesses, fragmentation points, operational liabilities.
- Treat every claim the company makes as potentially deceptive.
- Prioritize: attack surface, incompetence signals, fragility, contradiction, false narratives.
- Produce a coherent, continuous report (not bullet points).
        """
        elif style == "narrative":
            voice_block = """
Write as a long-form magazine essayist (e.g. The Atlantic, California Sunday, or long-form Wired).
Tone rules:
- Smooth, continuous prose.
- No bullet points.
- Begin with a narrative hook or observation.
- Integrate OSINT signals into storytelling.
- Make the company feel like a character in a larger narrative landscape.
- The result should feel like a polished article, not a corporate report.
        """
        elif style == "investor":
            voice_block = """
Write as a hard-nosed private equity analyst.
Tone: terse, metrics-driven, unemotional, skeptical.
Highlight market position, risk, scalability, margin threats, and execution gaps.
Allowed to use structured headings but avoid bullets unless necessary.
        """
        elif style == "founder":
            voice_block = """
Write like a YC partner or elite operator reviewing a company.
Tone: blunt, strategic, obsessed with leverage and momentum.
Provide a clear strategic blueprint for what the operator should do next.
Avoid bullets; use short crisp paragraphs of actionable insight.
        """
        else:
            voice_block = """
Write a standard OSINT intelligence brief with neutral tone.
Use short paragraphs, not bullets.
        """

        # --- Build prompt ---
        prompt = f"""
{SYNTHESIS_PROMPT}

You are in synthesis mode.

VOICE DIRECTIVE:
{voice_block}

Write a single, coherent report. Follow these rules:
- MUST be in the chosen voice exactly.
- MUST NOT output bullet points unless the mode explicitly allows them.
- MUST integrate all OSINT fields.
- MUST be readable as a continuous expert narrative.
- Output ONLY the report text.

Company OSINT profile (JSON):
{json.dumps(profile_dict, ensure_ascii=False, indent=2)}

User focus / priorities:
{focus or "None provided"}
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


def get_llm_client() -> LLMClient:
    """
    Factory: prefer GeminiLLMClient, but always guarantee *some* client.

    - If USE_GEMINI_LLM=1 and GOOGLE_API_KEY + google-generativeai
      are available -> GeminiLLMClient
    - Otherwise -> base deterministic LLMClient
    """
    try:
        client = GeminiLLMClient()
        # If Gemini isn't really enabled internally, it just behaves like LLMClient.
        return client
    except Exception as e:  # pragma: no cover - defensive
        logger.error(f"get_llm_client: failed to init GeminiLLMClient: {e}")
        return LLMClient()
