import os
import sys

# Ensure project root (where mcp_tech_stack lives) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
import mcp_tech_stack.server as server


client = TestClient(server.app)


def test_tech_stack_run_smoke():
    html = (
        "<html><head></head><body>"
        "This site uses React and Shopify with Cloudflare CDN."
        "</body></html>"
    )
    resp = client.post("/run", json={"raw_html": html})
    assert resp.status_code == 200
    body = resp.json()
    assert "success" in body
    assert "frameworks" in body
    assert "analytics" in body
    assert "cms" in body
    assert "cdn" in body
    assert "other" in body
    assert "error" in body
