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
            if any(word in text for word in ["review", "reviews", "brand", "reputation", "customer", "voice"]):
                plan["use_reviews_snapshot"] = True
                plan["use_social_snapshot"] = True

            # Explicit social mentions => social
            if any(word in text for word in ["social", "twitter", "instagram", "tiktok", "youtube", "community"]):
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

    def synthesize_report(
        self,
        profile_dict: Dict[str, Any],
        focus: Optional[str],
    ) -> str:
        """
        Deterministic Markdown report.

        Tests assert the presence of:
        - "# OSINT Intelligence Report"
        - Headings like "Web Presence", "SEO Diagnostics", etc.
        """
        company = profile_dict.get("company", {}) or {}
        company_name = company.get("name") or "Unknown Company"
        focus_str = focus or "General OSINT & growth posture"

        return (
            f"# OSINT Intelligence Report: {company_name}\n\n"
            f"_Focus: {focus_str}_\n\n"
            "## 1. Web Presence\n\n"
            "- Summary of site structure, clarity, and UX.\n\n"
            "## 2. SEO Diagnostics\n\n"
            "- High-level on-page SEO and discoverability notes.\n\n"
            "## 3. Tech Stack Fingerprint\n\n"
            "- Inferred frameworks, analytics, and infrastructure.\n\n"
            "## 4. Customer Voice & Reviews\n\n"
            "- Themes from public reviews and reputation signals.\n\n"
            "## 5. Social Footprint\n\n"
            "- Platform presence and engagement posture.\n\n"
            "## 6. Hiring & Org Signals\n\n"
            "- Open roles and organizational focus.\n\n"
            "## 7. Ads & Growth Motions\n\n"
            "- Paid acquisition and growth experimentation.\n\n"
            "## 8. Strategic Recommendations\n\n"
            "- Concise, actionable priorities for the operator.\n"
        )


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
            '  \"use_web_scrape\": true,\n'
            '  \"use_seo_probe\": true,\n'
            '  \"use_tech_stack\": true,\n'
            '  \"use_reviews_snapshot\": false,\n'
            '  \"use_social_snapshot\": false,\n'
            '  \"use_careers_intel\": true,\n'
            '  \"use_ads_snapshot\": false\n'
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
        if not self._enabled:
            return super().synthesize_report(profile_dict, focus)

        prompt = (
            f"{SYNTHESIS_PROMPT}\n\n"
            "You are now in the synthesis phase.\n"
            "Write a concise but complete Markdown intelligence report.\n"
            "Honor the section structure described above, but you may adapt "
            "section titles slightly if needed.\n\n"
            "Here is the OSINT profile as JSON:\n"
            f"{json.dumps(profile_dict, ensure_ascii=False, indent=2)}\n\n"
            f"User focus / priorities: {focus or 'None provided.'}\n\n"
            "Output ONLY the Markdown report, no JSON, no commentary."
        )

        try:
            model = genai.GenerativeModel(self.synth_model_name)
            resp = model.generate_content(
                prompt,
                generation_config={"temperature": self.temperature},
            )
            text = (resp.text or "").strip()
        except Exception as e:  # pragma: no cover - network/LLM failure
            logger.error(f"GeminiLLMClient.synthesize_report: LLM error: {e}")
            return super().synthesize_report(profile_dict, focus)

        if not text:
            logger.warning(
                "GeminiLLMClient.synthesize_report: empty LLM response, "
                "falling back to deterministic report."
            )
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
