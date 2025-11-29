from utils.llm_client import LLMClient


def setup_client():
    return LLMClient()


def test_plan_tools_no_url_disables_all():
    client = setup_client()
    plan = client.plan_tools(company_name="Test", company_url=None, focus=None)
    # With no URL and no focus, the planner should disable all tools
    assert not any(plan.values())


def test_plan_tools_focus_flags():
    client = setup_client()
    plan = client.plan_tools(
        company_name="Test",
        company_url="https://example.com",
        focus="reviews and brand and hiring",
    )
    # Base tools should be on when we have a URL
    assert plan["use_web_scrape"]
    assert plan["use_seo_probe"]
    assert plan["use_tech_stack"]

    # Focus string should turn on reviews, social, and hiring
    assert plan["use_reviews_snapshot"]
    assert plan["use_social_snapshot"]
    assert plan["use_careers_intel"]

    # No explicit ads / growth / marketing keywords -> ads should remain off
    assert not plan["use_ads_snapshot"]


def test_synthesize_report_contains_core_headings():
    client = setup_client()
    profile = {
        "company": {"name": "Example Corp", "url": "https://example.com"},
        "web": {
            "meta": {"title": "Example", "description": "Desc", "h1": [], "h2": []},
            "clean_text": "Some content",
            "raw_html": "<html></html>",
            "error": None,
        },
        "seo": {
            "meta_issues": [],
            "heading_issues": [],
            "keyword_summary": [],
            "internal_link_summary": [],
            "error": None,
        },
        "tech_stack": {
            "frameworks": [],
            "analytics": [],
            "cms": None,
            "cdn": None,
            "other": [],
            "error": None,
        },
        "reviews": {
            "sources": [],
            "summary": None,
            "top_complaints": [],
            "top_praises": [],
            "error": None,
        },
        "social": {
            "instagram": None,
            "youtube": None,
            "twitter": None,
            "error": None,
        },
        "hiring": {
            "open_roles": [],
            "inferred_focus": None,
            "error": None,
        },
        "ads": {
            "platforms": [],
            "themes": [],
            "error": None,
        },
    }
    report = client.synthesize_report(profile, focus="Test focus")

    # Top-level heading is present
    assert "# OSINT Intelligence Report" in report

    # Section headings must match the current dummy LLM implementation
    assert "## 1. Web Presence" in report
    assert "## 2. SEO Diagnostics" in report
    assert "## 3. Tech Stack Fingerprint" in report
    assert "## 4. Customer Voice & Reviews" in report
    assert "## 5. Social Footprint" in report
    assert "## 6. Hiring & Org Signals" in report
    assert "## 7. Ads & Growth Motions" in report
    assert "## 8. Strategic Recommendations" in report
