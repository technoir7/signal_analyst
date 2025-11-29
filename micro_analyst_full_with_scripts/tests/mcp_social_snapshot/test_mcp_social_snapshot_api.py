import os
import sys

# Ensure project root (where mcp_social_snapshot lives) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
import mcp_social_snapshot.server as server


client = TestClient(server.app)


def test_social_snapshot_run_smoke():
    resp = client.post("/run", json={"url": "https://example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "success" in body
    assert "instagram" in body
    assert "youtube" in body
    assert "twitter" in body
    assert "error" in body
