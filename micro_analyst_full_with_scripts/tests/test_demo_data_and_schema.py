import json
from pathlib import Path
import pytest
from core.data_models import CompanyOSINTProfile

DEMO_DIR = Path(__file__).resolve().parents[1] / "demo_data"

@pytest.mark.parametrize("filename",["blue_bottle.json","sweetgreen.json","glossier.json"])
def test_demo_files_exist(filename):
    p = DEMO_DIR/filename
    assert p.exists() and p.is_file()

@pytest.mark.parametrize("filename",["blue_bottle.json","sweetgreen.json","glossier.json"])
def test_demo_files_match_schema(filename):
    p = DEMO_DIR/filename
    data = json.loads(p.read_text())
    assert "profile" in data and "report_markdown" in data
    CompanyOSINTProfile(**data["profile"])
    assert isinstance(data["report_markdown"], str)