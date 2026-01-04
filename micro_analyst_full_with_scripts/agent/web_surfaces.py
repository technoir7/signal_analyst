# agent/web_surfaces.py
#
# Fast, lean surface collector for the Micro-Analyst OSINT agent.
# Replaces the original noisy, slow, many-404 version.
#
# Collects only high-value pages and stops early so the backend
# returns in < 5 seconds even for large targets.

from typing import List, Dict, Any
from urllib.parse import urljoin
from loguru import logger


def fetch_web_surfaces(
    company_url: str,
    web_scrape_endpoint: str,
    post_json_fn,
    max_surfaces: int = 4,
) -> List[Dict[str, Any]]:
    """
    Probe a *small*, strategic set of “likely structural pages”
    for the target domain. This keeps /analyze fast and prevents
    browser timeouts.

    Returns a list of web surface dicts:
        { "url", "raw_html", "clean_text", "meta" }

    We intentionally avoid hitting dozens of paths; we only fetch
    a handful of meaningful ones:
        - homepage
        - /home
        - /about
        - /locations
        - /programs
        - /contact
    """
    # --- high-value paths only --------------------------------------
    candidate_paths = [
        "",           # homepage
        "/home",
        "/about",
        "/locations",
        "/programs",
        "/contact",
    ]

    surfaces: List[Dict[str, Any]] = []

    for path in candidate_paths:
        if len(surfaces) >= max_surfaces:
            break

        # Clean join: always ensures <domain>/<path>
        target_url = urljoin(company_url.rstrip("/") + "/", path.lstrip("/"))

        logger.info("Agent: probing web surface %s", target_url)

        payload = {"url": target_url}
        result = post_json_fn(web_scrape_endpoint, payload)

        # Skip surfaces that return structured errors from MCP
        # NOTE: MCP returns 'success' field, not 'ok'
        if not isinstance(result, dict) or result.get("success") is False:
            logger.warning(
                "web_scrape failed for %s: %s",
                target_url,
                result.get("error") if isinstance(result, dict) else "Non-dict response",
            )
            continue
        
        # Soft fail: HTML returned but too thin to be useful
        html_content = result.get("raw_html", "") or ""
        if len(html_content) < 500:
            logger.warning(
                "web_scrape for %s returned thin HTML (%d bytes); treating as low-surface",
                target_url,
                len(html_content),
            )
            # Still append, but downstream should be aware

        surfaces.append(
            {
                "url": target_url,
                "raw_html": result.get("raw_html", "") or "",
                "clean_text": result.get("clean_text", "") or "",
                "meta": result.get("meta", {}) or {},
            }
        )

    return surfaces


# -------------------------------------------------------------------
# Aggregation logic (unchanged from your existing version)
# -------------------------------------------------------------------

def aggregate_web_surfaces(company_url: str, surfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine the text, meta tags, and snapshots across multiple scraped pages.

    Returns:
        {
          "url": <base_url>,
          "raw_html": <combined_html>,
          "clean_text": <combined_text>,
          "meta": {
             "title": <first_title>,
             "description": <first_description>,
             "h1": list_of_all_h1s,
             "h2": list_of_all_h2s
          },
          "snapshot_summary": <text summary or empty>
        }
    """
    combined_html = []
    combined_text = []
    titles = []
    descriptions = []
    h1s = []
    h2s = []

    for s in surfaces:
        combined_html.append(s.get("raw_html", ""))
        combined_text.append(s.get("clean_text", ""))

        meta = s.get("meta", {}) or {}
        title = meta.get("title")
        desc = meta.get("description")
        page_h1 = meta.get("h1", []) or []
        page_h2 = meta.get("h2", []) or []

        if title:
            titles.append(title)
        if desc:
            descriptions.append(desc)

        h1s.extend(page_h1)
        h2s.extend(page_h2)

    return {
        "url": company_url,
        "raw_html": "\n".join(combined_html),
        "clean_text": "\n".join(combined_text),
        "meta": {
            "title": titles[0] if titles else None,
            "description": descriptions[0] if descriptions else None,
            "h1": h1s,
            "h2": h2s,
        },
        "snapshot_summary": "",  # filled in by downstream logic
    }
