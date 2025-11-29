import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from agent.micro_analyst import app
from core.data_models import CompanyOSINTProfile

client = TestClient(app)

def _post_analyze(payload: dict):
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    return data

def test_analyze_contract_minimal_request():
    payload = {"company_name": "Test Co","company_url": "https://example.com","focus": None}
    data = _post_analyze(payload)
    assert set(data.keys()) == {"profile","report_markdown"}
    profile = CompanyOSINTProfile(**data["profile"])
    assert isinstance(data["report_markdown"], str)

def test_analyze_handles_bad_url_gracefully():
    payload = {"company_name": "Bad","company_url": "http://no-such-domain-12345.test","focus":"x"}
    data = _post_analyze(payload)
    assert set(data.keys()) == {"profile","report_markdown"}
    CompanyOSINTProfile(**data["profile"])

def test_analyze_idempotent_on_same_input():
    payload = {"company_name":"Idem","company_url":"https://example.com","focus":"x"}
    d1 = _post_analyze(payload); d2 = _post_analyze(payload)
    assert set(d1.keys())=={"profile","report_markdown"}
    assert set(d2.keys())=={"profile","report_markdown"}