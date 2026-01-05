"""
Tests for Wayback Machine integration (utils/wayback.py).

All tests use mocked HTTP responses - no real network calls.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.wayback import (
    list_snapshots,
    fetch_snapshot_html,
    extract_wayback_signals,
    get_historical_snapshots,
    wayback_delta_to_markdown,
    _select_closest_snapshot,
)


# ---------------------------------------------------------------------------
# Sample Data
# ---------------------------------------------------------------------------

SAMPLE_CDX_RESPONSE = [
    ["timestamp", "original", "statuscode", "mimetype"],
    ["20231015120000", "https://example.com/", "200", "text/html"],
    ["20230815100000", "https://example.com/", "200", "text/html"],
]

SAMPLE_CDX_MULTI = [
    ["timestamp", "original", "statuscode", "mimetype"],
    ["20231010000000", "https://example.com/", "200", "text/html"],
    ["20231012000000", "https://example.com/", "200", "text/html"],
    ["20231015000000", "https://example.com/", "200", "text/html"],  # Closest to Oct 14
    ["20231018000000", "https://example.com/", "200", "text/html"],
    ["20231020000000", "https://example.com/", "200", "text/html"],
]

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Example Company - Build Better Software</title>
    <meta name="description" content="Example helps teams ship faster.">
</head>
<body>
    <h1>Welcome to Example</h1>
    <h1>Our Products</h1>
    <script src="/_next/static/chunks/main.js"></script>
    <script src="/_next/static/chunks/pages.js"></script>
    <script src="/_next/static/chunks/app.js"></script>
    <div>Check out our pricing plans</div>
    <div>Read our documentation</div>
</body>
</html>
"""

SAMPLE_HTML_MINIMAL = """
<!DOCTYPE html>
<html>
<head>
    <title>Old Site</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Tests: list_snapshots
# ---------------------------------------------------------------------------

@patch('utils.wayback.requests.get')
def test_list_snapshots_success(mock_get):
    """CDX API returns valid JSON response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_CDX_RESPONSE
    mock_get.return_value = mock_response
    
    result = list_snapshots("https://example.com/")
    
    assert len(result) == 2
    assert result[0]["timestamp"] == "20231015120000"
    assert result[0]["original"] == "https://example.com/"
    assert result[0]["statuscode"] == "200"


@patch('utils.wayback.requests.get')
def test_list_snapshots_empty_response(mock_get):
    """CDX API returns no results."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [["timestamp", "original", "statuscode", "mimetype"]]
    mock_get.return_value = mock_response
    
    result = list_snapshots("https://example.com/")
    
    assert result == []


@patch('utils.wayback.requests.get')
def test_list_snapshots_timeout(mock_get):
    """CDX API timeout returns empty list."""
    import requests
    mock_get.side_effect = requests.Timeout("Connection timed out")
    
    result = list_snapshots("https://example.com/")
    
    assert result == []


@patch('utils.wayback.requests.get')
def test_list_snapshots_http_error(mock_get):
    """CDX API returns non-200 status."""
    mock_response = Mock()
    mock_response.status_code = 503
    mock_get.return_value = mock_response
    
    result = list_snapshots("https://example.com/")
    
    assert result == []


# ---------------------------------------------------------------------------
# Tests: _select_closest_snapshot
# ---------------------------------------------------------------------------

def test_select_closest_snapshot_exact_match():
    """Select snapshot with exact timestamp match."""
    snapshots = [
        {"timestamp": "20231010000000"},
        {"timestamp": "20231015000000"},
        {"timestamp": "20231020000000"},
    ]
    target = datetime(2023, 10, 15, 0, 0, 0)
    
    result = _select_closest_snapshot(snapshots, target)
    
    assert result["timestamp"] == "20231015000000"


def test_select_closest_snapshot_nearest():
    """Select snapshot nearest to target date."""
    snapshots = [
        {"timestamp": "20231010000000"},
        {"timestamp": "20231012000000"},
        {"timestamp": "20231018000000"},
        {"timestamp": "20231020000000"},
    ]
    # Target Oct 14: closest is Oct 12 (2 days) not Oct 18 (4 days)
    target = datetime(2023, 10, 14, 0, 0, 0)
    
    result = _select_closest_snapshot(snapshots, target)
    
    assert result["timestamp"] == "20231012000000"


def test_select_closest_snapshot_empty():
    """Empty list returns None."""
    result = _select_closest_snapshot([], datetime.now())
    assert result is None


def test_select_closest_snapshot_single():
    """Single snapshot is always returned."""
    snapshots = [{"timestamp": "20231015000000"}]
    target = datetime(2023, 1, 1)  # Way off
    
    result = _select_closest_snapshot(snapshots, target)
    
    assert result["timestamp"] == "20231015000000"


# ---------------------------------------------------------------------------
# Tests: fetch_snapshot_html
# ---------------------------------------------------------------------------

@patch('utils.wayback.requests.get')
def test_fetch_snapshot_html_success(mock_get):
    """Wayback fetch returns HTML content."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = SAMPLE_HTML.encode('utf-8')
    mock_get.return_value = mock_response
    
    result = fetch_snapshot_html("20231015120000", "https://example.com/")
    
    assert result is not None
    assert "Example Company" in result
    mock_get.assert_called_once()


@patch('utils.wayback.requests.get')
def test_fetch_snapshot_html_not_found(mock_get):
    """Wayback returns 404 for missing snapshot."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    result = fetch_snapshot_html("19990101000000", "https://example.com/")
    
    assert result is None


@patch('utils.wayback.requests.get')
def test_fetch_snapshot_html_timeout(mock_get):
    """Wayback fetch timeout returns None."""
    import requests
    mock_get.side_effect = requests.Timeout("Connection timed out")
    
    result = fetch_snapshot_html("20231015120000", "https://example.com/")
    
    assert result is None


# ---------------------------------------------------------------------------
# Tests: extract_wayback_signals
# ---------------------------------------------------------------------------

def test_extract_wayback_signals_full():
    """Extract all signals from complete HTML."""
    result = extract_wayback_signals(SAMPLE_HTML)
    
    assert result["title"] == "Example Company - Build Better Software"
    assert result["description"] == "Example helps teams ship faster."
    assert result["h1_count"] == 2
    assert result["has_pricing_keywords"] is True
    assert result["has_docs_keywords"] is True
    assert "Next.js" in result["framework_hints"]
    assert result["html_bytes"] > 0
    assert result["script_count"] == 3


def test_extract_wayback_signals_minimal():
    """Extract signals from minimal HTML."""
    result = extract_wayback_signals(SAMPLE_HTML_MINIMAL)
    
    assert result["title"] == "Old Site"
    assert result["description"] is None
    assert result["h1_count"] == 1
    assert result["has_pricing_keywords"] is False
    assert result["has_docs_keywords"] is False
    assert result["framework_hints"] == []
    assert result["script_count"] == 0


def test_extract_wayback_signals_empty():
    """Handle empty HTML gracefully."""
    result = extract_wayback_signals("")
    
    assert result["title"] is None
    assert result["h1_count"] == 0
    assert result["framework_hints"] == []
    assert result["html_bytes"] == 0
    assert result["script_count"] == 0


def test_extract_wayback_signals_malformed():
    """Handle malformed HTML gracefully."""
    result = extract_wayback_signals("<html><head><title>Broken")
    
    assert result["title"] == "Broken"
    assert result["h1_count"] == 0


# ---------------------------------------------------------------------------
# Tests: wayback_delta_to_markdown
# ---------------------------------------------------------------------------

def test_wayback_delta_to_markdown_no_snapshots():
    """Empty historical snapshots produces fallback message."""
    result = wayback_delta_to_markdown({}, [])
    
    assert "## Change Over Time (Wayback)" in result
    assert "No archived snapshots available" in result


def test_wayback_delta_to_markdown_with_changes():
    """Detected changes are formatted correctly."""
    current = {
        "title": "New Title",
        "framework_hints": ["React", "Next.js"],
        "has_pricing_keywords": True,
        "html_bytes": 50000,
        "script_count": 10,
    }
    
    historical = [
        {
            "label": "~30 days ago",
            "timestamp": "20231015120000",
            "signals": {
                "title": "Old Title",
                "framework_hints": ["jQuery"],
                "has_pricing_keywords": False,
                "html_bytes": 20000,
                "script_count": 3,
            }
        }
    ]
    
    result = wayback_delta_to_markdown(current, historical)
    
    assert "## Change Over Time (Wayback)" in result
    assert "~30 days ago" in result
    assert "Title changed" in result
    assert "Old Title" in result
    assert "New Title" in result
    assert "low-confidence" in result  # Framework hint warning
    assert "Pricing emerged" in result
    assert "Page grew" in result


def test_wayback_delta_to_markdown_stable():
    """No changes produces stable message."""
    signals = {
        "title": "Same Title",
        "framework_hints": ["React"],
        "has_pricing_keywords": True,
        "html_bytes": 30000,
        "script_count": 5,
    }
    
    historical = [
        {
            "label": "~30 days ago",
            "timestamp": "20231015120000",
            "signals": signals.copy()
        }
    ]
    
    result = wayback_delta_to_markdown(signals, historical)
    
    assert "## Change Over Time (Wayback)" in result
    assert "unchanged" in result or "stable" in result


def test_wayback_delta_to_markdown_no_current():
    """current_signals=None compares historical snapshots."""
    historical = [
        {
            "label": "~30 days ago",
            "timestamp": "20231015120000",
            "signals": {"title": "Newer Title", "framework_hints": [], "html_bytes": 40000}
        },
        {
            "label": "~180 days ago",
            "timestamp": "20230415120000",
            "signals": {"title": "Older Title", "framework_hints": ["jQuery"], "html_bytes": 20000}
        }
    ]
    
    result = wayback_delta_to_markdown(None, historical)
    
    assert "## Change Over Time (Wayback)" in result
    assert "No live scrape available" in result or "Comparing historical" in result


# ---------------------------------------------------------------------------
# Tests: get_historical_snapshots (integration with mocks)
# ---------------------------------------------------------------------------

@patch('utils.wayback.fetch_snapshot_html')
@patch('utils.wayback.list_snapshots')
def test_get_historical_snapshots_success(mock_list, mock_fetch):
    """Full flow returns extracted signals with closest selection."""
    mock_list.return_value = [
        {"timestamp": "20231010000000", "original": "https://example.com/"},
        {"timestamp": "20231015000000", "original": "https://example.com/"},
        {"timestamp": "20231020000000", "original": "https://example.com/"},
    ]
    mock_fetch.return_value = SAMPLE_HTML
    
    result = get_historical_snapshots("https://example.com/")
    
    assert len(result) >= 1
    assert result[0]["label"] in ["~30 days ago", "~180 days ago"]
    assert "signals" in result[0]
    assert result[0]["signals"]["title"] == "Example Company - Build Better Software"
    assert result[0]["signals"]["script_count"] == 3


@patch('utils.wayback.list_snapshots')
def test_get_historical_snapshots_no_snapshots(mock_list):
    """No snapshots available returns empty list."""
    mock_list.return_value = []
    
    result = get_historical_snapshots("https://example.com/")
    
    assert result == []


# ---------------------------------------------------------------------------
# Tests: Integration with micro_analyst.py (mocked at module level)
# ---------------------------------------------------------------------------

@patch('utils.wayback.get_historical_snapshots')
@patch('utils.wayback.extract_wayback_signals')
def test_wayback_functions_safe_for_pipeline(mock_extract, mock_history):
    """Wayback functions handle errors gracefully for pipeline safety."""
    # Simulate extraction success
    mock_extract.return_value = {
        "title": "Test",
        "framework_hints": [],
        "has_pricing_keywords": False,
        "has_docs_keywords": False,
        "html_bytes": 1000,
        "script_count": 2,
    }
    
    # Simulate empty history (no network)
    mock_history.return_value = []
    
    # These should not raise
    result = extract_wayback_signals("<html></html>")
    history = get_historical_snapshots("https://test.com")
    
    assert result is not None
    assert history == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
