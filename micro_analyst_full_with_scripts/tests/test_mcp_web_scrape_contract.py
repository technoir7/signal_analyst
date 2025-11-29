from fastapi.testclient import TestClient
from mcp_web_scrape.server import app

client = TestClient(app)

def test_web_scrape_invalid_url():
    r = client.post("/run", json={"url":"http://no-such-domain-12345.test"})
    assert r.status_code == 200
    d = r.json()
    for k in ["success","url","raw_html","clean_text","meta","error"]:
        assert k in d
    assert d["success"] is False
    assert isinstance(d["error"], str)