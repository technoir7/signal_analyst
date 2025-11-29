import os
import sys

# --- Ensure project root is on sys.path so `import agent...` works ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient

import agent.micro_analyst as micro_analyst


@pytest.fixture
def client():
    return TestClient(micro_analyst.app)


@pytest.fixture
def company_name():
    return "Example Corp"


@pytest.fixture
def company_url():
    return "https://example.com"


def _make_web_scrape_result(url: str) -> dict:
    return {
        "success": True,
        "url": url,
        "raw_html": (
            "<html><head><title>Example Title</title></head>"
            "<body><h1>Main</h1></body></html>"
        ),
        "clean_text": "Example Corp main page",
        "meta": {
            "title": "Example Title",
            "description": "Example description",
            "h1": ["Main"],
            "h2": ["Sub"],
        },
        "error": None,
    }


def _make_seo_result() -> dict:
    return {
        "success": True,
        "meta_issues": [],
        "heading_issues": [],
        "keyword_summary": [{"term": "example", "count": 3}],
        "internal_link_summary": [],
        "error": None,
    }


def _make_tech_result() -> dict:
    return {
        "success": True,
        "frameworks": ["React"],
        "analytics": ["Google Analytics"],
        "cms": "WordPress",
        "cdn": "Cloudflare",
        "other": ["Stripe"],
        "error": None,
    }


def _make_reviews_result() -> dict:
    return {
        "success": True,
        "sources": [{"source": "Stub", "avg_rating": 4.0, "review_count": 10}],
        "summary": "Stub reviews summary.",
        "top_complaints": ["Stub complaint"],
        "top_praises": ["Stub praise"],
        "error": None,
    }


def _make_social_result() -> dict:
    return {
        "success": True,
        "instagram": {"handle": "@example", "followers": 100},
        "youtube": None,
        "twitter": None,
        "error": None,
    }


def _make_careers_result() -> dict:
    return {
        "success": True,
        "open_roles": [{"title": "Engineer", "location": "Remote"}],
        "inferred_focus": "Technology & Engineering",
        "error": None,
    }


def test_analyze_happy_path(client, company_name, company_url, monkeypatch):
    """Happy path: all tools enabled, all MCP calls succeed, synthesis succeeds."""

    def fake_plan_tools(company_name=None, company_url=None, focus=None):
        return {
            "use_web_scrape": True,
            "use_seo_probe": True,
            "use_tech_stack": True,
            "use_reviews_snapshot": True,
            "use_social_snapshot": True,
            "use_careers_intel": True,
            "use_ads_snapshot": False,
        }

    def fake_synthesize_report(profile: dict, focus: str | None = None) -> str:
        return "# Stub report\n\nAll good."

    def fake_post_json(url: str, payload: dict):
        if url == micro_analyst.MCP_WEB_SCRAPE_URL:
            return _make_web_scrape_result(company_url)
        if url == micro_analyst.MCP_SEO_PROBE_URL:
            return _make_seo_result()
        if url == micro_analyst.MCP_TECH_STACK_URL:
            return _make_tech_result()
        if url == micro_analyst.MCP_REVIEWS_SNAPSHOT_URL:
            return _make_reviews_result()
        if url == micro_analyst.MCP_SOCIAL_SNAPSHOT_URL:
            return _make_social_result()
        if url == micro_analyst.MCP_CAREERS_INTEL_URL:
            return _make_careers_result()
        return None

    monkeypatch.setattr(micro_analyst._llm_client, "plan_tools", fake_plan_tools)
    monkeypatch.setattr(
        micro_analyst._llm_client, "synthesize_report", fake_synthesize_report
    )
    monkeypatch.setattr(micro_analyst, "_post_json", fake_post_json)

    resp = client.post(
        "/analyze",
        json={
            "company_name": company_name,
            "company_url": company_url,
            "focus": "Full OSINT sweep",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "profile" in body
    assert "report_markdown" in body
    assert body["report_markdown"] == "# Stub report\n\nAll good."

    profile = body["profile"]
    assert profile["company"]["name"] == company_name
    assert profile["company"]["url"] == company_url
    assert profile["web"]["meta"]["title"] == "Example Title"
    assert "React" in profile["tech_stack"]["frameworks"]
    assert profile["hiring"]["inferred_focus"] == "Technology & Engineering"
    assert profile["reviews"]["sources"][0]["source"] == "Stub"


def test_analyze_web_scrape_failure_skips_seo_and_tech(
    client, company_name, company_url, monkeypatch
):
    """If web scrape fails, SEO and Tech MCPs should not be called."""

    def fake_plan_tools(company_name=None, company_url=None, focus=None):
        return {
            "use_web_scrape": True,
            "use_seo_probe": True,
            "use_tech_stack": True,
            "use_reviews_snapshot": True,
            "use_social_snapshot": True,
            "use_careers_intel": True,
            "use_ads_snapshot": False,
        }

    calls: list[str] = []

    def fake_post_json(url: str, payload: dict):
        calls.append(url)
        if url == micro_analyst.MCP_WEB_SCRAPE_URL:
            return {
                "success": False,
                "url": company_url,
                "raw_html": None,
                "clean_text": None,
                "meta": {},
                "error": "Network error",
            }
        if url == micro_analyst.MCP_REVIEWS_SNAPSHOT_URL:
            return _make_reviews_result()
        if url == micro_analyst.MCP_SOCIAL_SNAPSHOT_URL:
            return _make_social_result()
        if url == micro_analyst.MCP_CAREERS_INTEL_URL:
            return _make_careers_result()
        return None

    def fake_synthesize_report(profile: dict, focus: str | None = None) -> str:
        return "# Stub report"

    monkeypatch.setattr(micro_analyst._llm_client, "plan_tools", fake_plan_tools)
    monkeypatch.setattr(
        micro_analyst._llm_client, "synthesize_report", fake_synthesize_report
    )
    monkeypatch.setattr(micro_analyst, "_post_json", fake_post_json)

    resp = client.post(
        "/analyze",
        json={
            "company_name": company_name,
            "company_url": company_url,
            "focus": "Full OSINT sweep",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    profile = body["profile"]

    assert micro_analyst.MCP_WEB_SCRAPE_URL in calls
    assert micro_analyst.MCP_SEO_PROBE_URL not in calls
    assert micro_analyst.MCP_TECH_STACK_URL not in calls

    assert profile["web"]["error"] == "Network error"
    assert profile["seo"]["meta_issues"] == []
    assert profile["tech_stack"]["frameworks"] == []


def test_analyze_planning_failure_uses_default_plan(
    client, company_name, company_url, monkeypatch
):
    """If planning LLM fails, the agent should fall back to default plan."""

    def fake_plan_tools(company_name=None, company_url=None, focus=None):
        raise Exception("Planning error")

    def fake_post_json(url: str, payload: dict):
        if url == micro_analyst.MCP_WEB_SCRAPE_URL:
            return _make_web_scrape_result(company_url)
        if url == micro_analyst.MCP_SEO_PROBE_URL:
            return _make_seo_result()
        if url == micro_analyst.MCP_TECH_STACK_URL:
            return _make_tech_result()
        raise AssertionError(f"Unexpected MCP call to {url}")

    def fake_synthesize_report(profile: dict, focus: str | None = None) -> str:
        return "# Stub report"

    monkeypatch.setattr(micro_analyst._llm_client, "plan_tools", fake_plan_tools)
    monkeypatch.setattr(
        micro_analyst._llm_client, "synthesize_report", fake_synthesize_report
    )
    monkeypatch.setattr(micro_analyst, "_post_json", fake_post_json)

    resp = client.post(
        "/analyze",
        json={
            "company_name": company_name,
            "company_url": company_url,
            "focus": "Anything",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    profile = body["profile"]
    assert profile["web"]["meta"]["title"] == "Example Title"
    assert "React" in profile["tech_stack"]["frameworks"]


def test_analyze_synthesis_failure_returns_fallback_report(
    client, company_name, company_url, monkeypatch
):
    """If synthesis LLM fails, the agent should return a structured fallback report."""

    def fake_plan_tools(company_name=None, company_url=None, focus=None):
        return {
            "use_web_scrape": True,
            "use_seo_probe": True,
            "use_tech_stack": True,
            "use_reviews_snapshot": False,
            "use_social_snapshot": False,
            "use_careers_intel": False,
            "use_ads_snapshot": False,
        }

    def fake_post_json(url: str, payload: dict):
        if url == micro_analyst.MCP_WEB_SCRAPE_URL:
            return _make_web_scrape_result(company_url)
        if url == micro_analyst.MCP_SEO_PROBE_URL:
            return _make_seo_result()
        if url == micro_analyst.MCP_TECH_STACK_URL:
            return _make_tech_result()
        raise AssertionError(f"Unexpected MCP call to {url}")

    def fake_synthesize_report(profile: dict, focus: str | None = None) -> str:
        raise Exception("Synthesis error")

    monkeypatch.setattr(micro_analyst._llm_client, "plan_tools", fake_plan_tools)
    monkeypatch.setattr(
        micro_analyst._llm_client, "synthesize_report", fake_synthesize_report
    )
    monkeypatch.setattr(micro_analyst, "_post_json", fake_post_json)

    resp = client.post(
        "/analyze",
        json={
            "company_name": company_name,
            "company_url": company_url,
            "focus": "Test synthesis failure",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    report = body["report_markdown"]
    assert "OSINT Intelligence Report" in report
    assert (
        "Report generation failed; no detailed web presence summary available"
        in report
    )
