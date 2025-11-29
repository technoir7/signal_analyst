from urllib.parse import urljoin

from fastapi import FastAPI
from loguru import logger

from .schemas import CareersIntelInput, CareersIntelOutput
from utils.http_utils import fetch_url_with_retry
from utils.text_utils import clean_html_to_text

app = FastAPI(title="MCP Careers Intel", version="1.0.0")


def _extract_roles_from_text(text: str) -> list[dict]:
    """Extremely simple heuristic to extract role-like lines from text."""
    roles: list[dict] = []
    keywords = ["engineer", "designer", "manager", "specialist", "director", "lead"]

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        lower = stripped.lower()
        if any(k in lower for k in keywords):
            roles.append({"title": stripped, "location": "Unknown"})

    return roles


def _infer_focus_from_roles(roles: list[dict]) -> str | None:
    """Very rough heuristic to infer hiring focus based on titles."""
    if not roles:
        return None

    joined_titles = " ".join(r.get("title", "").lower() for r in roles)
    if any(k in joined_titles for k in ["engineer", "developer", "data", "machine learning"]):
        return "Technology & Engineering"
    if any(k in joined_titles for k in ["designer", "ux", "creative"]):
        return "Design & Product Experience"
    if any(k in joined_titles for k in ["sales", "account", "customer"]):
        return "Sales & Customer Growth"

    return "Mixed / General Growth"


@app.post("/run", response_model=CareersIntelOutput)
def run_careers_intel(payload: CareersIntelInput) -> CareersIntelOutput:
    """Probe /careers and /jobs pages and extract basic role titles."""
    try:
        base_url = str(payload.company_url)
        logger.info("mcp_careers_intel: probing careers pages for url={}", base_url)

        candidate_paths = ["/careers", "/jobs"]
        collected_roles: list[dict] = []
        errors: list[str] = []

        for path in candidate_paths:
            full_url = urljoin(base_url, path)
            html = fetch_url_with_retry(full_url)
            if not html:
                errors.append(f"Failed to fetch {full_url}")
                continue

            text = clean_html_to_text(html)
            roles = _extract_roles_from_text(text)
            if roles:
                for role in roles:
                    role.setdefault("source_url", full_url)
                collected_roles.extend(roles)

        inferred_focus = _infer_focus_from_roles(collected_roles)
        error_msg = "; ".join(errors) if errors and not collected_roles else None

        return CareersIntelOutput(
            success=True,
            open_roles=collected_roles,
            inferred_focus=inferred_focus,
            error=error_msg,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp_careers_intel: unhandled error")
        return CareersIntelOutput(
            success=False,
            open_roles=[],
            inferred_focus=None,
            error=f"Unexpected error during careers intel: {exc}",
        )
