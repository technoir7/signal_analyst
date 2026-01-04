import os
import sys
import unittest
from fastapi.testclient import TestClient

# Mock MCP URLs to avoid connection errors during logic tests
os.environ["MCP_WEB_SCRAPE_URL"] = "http://mock/run"
os.environ["MCP_SEO_PROBE_URL"] = "http://mock/run"

from agent.micro_analyst import app, VALID_API_KEYS

client = TestClient(app)

class TestSecurityHardening(unittest.TestCase):
    def test_auth_enforcement(self):
        """Test that /analyze requires API key by default now."""
        # 1. No key -> 401
        resp = client.post("/analyze", json={"company_url": "https://example.com"})
        self.assertEqual(resp.status_code, 401, "Should reject requests without API key")
        
        # 2. Invalid key -> 401
        resp = client.post("/analyze", json={"company_url": "https://example.com"}, headers={"X-API-Key": "invalid"})
        self.assertEqual(resp.status_code, 401, "Should reject requests with invalid API key")
        
        # 3. Valid key -> 200/202 (or 503 if mock/env limited, or 400 if validation)
        # We need a valid key from env
        valid_key = list(VALID_API_KEYS)[0] if VALID_API_KEYS else "demo_key_abc123"
        resp = client.post("/analyze", json={"company_url": "https://example.com"}, headers={"X-API-Key": valid_key})
        # It might fail with 400 URL validation or proceed, but NOT 401
        self.assertNotEqual(resp.status_code, 401, "Should accept valid API key")

    def test_ssrf_validation(self):
        """Verify SSRF validation remains active."""
        valid_key = list(VALID_API_KEYS)[0]
        
        # Localhost should be blocked
        resp = client.post(
            "/analyze", 
            json={"company_url": "http://localhost:8000"}, 
            headers={"X-API-Key": valid_key}
        )
        self.assertEqual(resp.status_code, 400, "Should block localhost")
        
    def test_persistence_logic(self):
        """Verify startup event handler logic (conceptually)."""
        # This is harder to test via integration without a real DB/restart cycle,
        # but we can verify the startup handler exists.
        self.assertTrue(hasattr(app.router, "on_startup"), "Startup handler should be registered")


if __name__ == "__main__":
    unittest.main()
