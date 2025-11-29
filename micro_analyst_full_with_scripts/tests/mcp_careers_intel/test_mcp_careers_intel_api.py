import os
import sys

# Ensure project root (where mcp_careers_intel lives) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
import mcp_careers_intel.server as server


client = TestClient(server.app)


def test_careers_intel_run_smoke():
    # CareersIntelInput requires company_url (not url)
    resp = client.post(
        "/run",
        json={
            "company_url": "https://example.com",
            "company_name": "Example Corp",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "success" in body
    assert "open_roles" in body
    assert "inferred_focus" in body
    assert "error" in body
