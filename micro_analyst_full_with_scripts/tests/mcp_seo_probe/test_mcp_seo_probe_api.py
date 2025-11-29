import os
import sys

# Ensure project root (where mcp_seo_probe lives) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
import mcp_seo_probe.server as server


client = TestClient(server.app)


def test_seo_probe_run_smoke():
    payload = {
        "meta": {
            "title": "Example Title",
            "description": "Example description",
            "h1": ["Heading"],
            "h2": ["Subheading"],
        },
        "clean_text": "Example text content for SEO analysis.",
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "success" in body
    assert "meta_issues" in body
    assert "heading_issues" in body
    assert "keyword_summary" in body
    assert "internal_link_summary" in body
    assert "error" in body
