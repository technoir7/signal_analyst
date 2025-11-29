import os
import sys

# Ensure project root (where mcp_web_scrape lives) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
import mcp_web_scrape.server as server


client = TestClient(server.app)


def test_web_scrape_run_smoke():
    resp = client.post("/run", json={"url": "https://example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "success" in body
    # success may be True or False depending on network, but schema should hold
    assert "url" in body
    assert "raw_html" in body
    assert "clean_text" in body
    assert "meta" in body
    assert "error" in body
