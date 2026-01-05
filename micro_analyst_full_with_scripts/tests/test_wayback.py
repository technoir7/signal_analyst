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


# ---------------------------------------------------------------------------
# Tests: Institutional Drift Signals
# ---------------------------------------------------------------------------

from utils.wayback import (
    extract_institutional_signals,
    compute_institutional_delta,
    institutional_delta_to_markdown,
    _empty_institutional_signals,
)
from bs4 import BeautifulSoup


# Sample HTML for institutional sites
SAMPLE_INSTITUTIONAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Academy of Fine Arts - Since 1892</title>
</head>
<body>
    <nav>
        <a href="/about">About</a>
        <a href="/admissions">Admissions</a>
        <a href="/programs">Programs</a>
        <a href="/faculty">Faculty</a>
        <a href="/contact">Contact</a>
    </nav>
    
    <section>
        <h1>Welcome to the Academy</h1>
        <p>We are an accredited institution founded in 1892.</p>
    </section>
    
    <section>
        <h2>About Us</h2>
        <p>Our mission is to educate the next generation of artists.</p>
    </section>
    
    <section>
        <h2>Faculty</h2>
        <div>
            <p>John Smith - Painting</p>
            <p>Jane Doe - Sculpture</p>
            <p>Robert Johnson - Digital Art</p>
        </div>
    </section>
    
    <section>
        <h2>Exhibitions</h2>
        <p>Student gallery show</p>
        <p>Annual exhibition 2023</p>
        <p>Partner collaboration with Museum of Art</p>
    </section>
    
    <img src="/images/campus.jpg">
    <img src="/images/studio.jpg">
    <img src="/images/gallery.jpg">
    
    <footer>
        <a href="/privacy">Privacy</a>
        <a href="/terms">Terms</a>
        <a href="/accessibility">Accessibility</a>
    </footer>
</body>
</html>
"""

SAMPLE_MINIMAL_INSTITUTIONAL_HTML = """
<!DOCTYPE html>
<html>
<head><title>Small School</title></head>
<body>
    <h1>Welcome</h1>
    <p>We are a small art school.</p>
</body>
</html>
"""

SAMPLE_NO_SECTIONS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <p>Just some text content here.</p>
</body>
</html>
"""


class TestExtractInstitutionalSignals:
    """Tests for extract_institutional_signals function."""
    
    def test_full_institutional_page(self):
        """Extract signals from complete institutional page."""
        soup = BeautifulSoup(SAMPLE_INSTITUTIONAL_HTML, "html.parser")
        result = extract_institutional_signals(SAMPLE_INSTITUTIONAL_HTML, soup)
        
        # Text metrics
        text = result["text_metrics"]
        assert text["word_count"] > 50
        assert text["char_count"] > 200
        assert text["section_presence"]["about"] is True
        assert text["section_presence"]["faculty"] is True
        
        # Prestige signals
        prestige = result["prestige_signals"]
        assert prestige["has_accreditation"] is True
        assert prestige["founding_year"] == 1892
        assert prestige["exhibition_mentions"] >= 2
        assert prestige["partner_mentions"] >= 1
        
        # Structural signals
        struct = result["structural_signals"]
        assert struct["img_count"] == 3
        assert struct["section_count"] == 4
        assert struct["nav_link_count"] == 5
        assert struct["footer_link_count"] == 3
    
    def test_minimal_page(self):
        """Extract signals from minimal page."""
        soup = BeautifulSoup(SAMPLE_MINIMAL_INSTITUTIONAL_HTML, "html.parser")
        result = extract_institutional_signals(SAMPLE_MINIMAL_INSTITUTIONAL_HTML, soup)
        
        assert result["text_metrics"]["word_count"] > 0
        assert result["prestige_signals"]["has_accreditation"] is False
        assert result["prestige_signals"]["founding_year"] is None
        assert result["structural_signals"]["nav_link_count"] == 0
    
    def test_empty_html(self):
        """Handle empty HTML gracefully."""
        soup = BeautifulSoup("", "html.parser")
        result = extract_institutional_signals("", soup)
        
        assert result["text_metrics"]["word_count"] == 0
        assert result["prestige_signals"]["faculty_name_count"] == 0
        assert result["structural_signals"]["img_count"] == 0
    
    def test_malformed_html(self):
        """Handle malformed HTML gracefully."""
        malformed = "<html><body><h1>Broken"
        soup = BeautifulSoup(malformed, "html.parser")
        result = extract_institutional_signals(malformed, soup)
        
        # Should not raise, should return valid structure
        assert "text_metrics" in result
        assert "prestige_signals" in result
        assert "structural_signals" in result


class TestComputeInstitutionalDelta:
    """Tests for compute_institutional_delta function."""
    
    def test_no_change(self):
        """Identical snapshots produce zero deltas."""
        signals = {
            "text_metrics": {"word_count": 100, "char_count": 500, "section_presence": {"about": True, "faculty": True}},
            "prestige_signals": {"has_accreditation": True, "founding_year": 1950, "faculty_name_count": 5, "exhibition_mentions": 3, "partner_mentions": 2},
            "structural_signals": {"img_count": 10, "section_count": 5, "nav_link_count": 8, "footer_link_count": 5, "heading_count": 6}
        }
        
        delta = compute_institutional_delta(signals, signals)
        
        assert delta["word_delta"] == 0
        assert delta["text_delta_pct"] == 0.0
        assert delta["sections_added"] == []
        assert delta["sections_removed"] == []
        assert delta["prestige_changes"]["accreditation_gained"] is False
        assert delta["prestige_changes"]["accreditation_lost"] is False
        assert delta["structural_changes"]["img_delta"] == 0
    
    def test_increased_complexity(self):
        """Detect increased site complexity."""
        older = {
            "text_metrics": {"word_count": 100, "section_presence": {"about": True}},
            "prestige_signals": {"has_accreditation": False, "founding_year": None, "faculty_name_count": 2, "exhibition_mentions": 1, "partner_mentions": 0},
            "structural_signals": {"img_count": 5, "section_count": 2, "nav_link_count": 4, "footer_link_count": 2, "heading_count": 3}
        }
        newer = {
            "text_metrics": {"word_count": 250, "section_presence": {"about": True, "faculty": True, "programs": True}},
            "prestige_signals": {"has_accreditation": True, "founding_year": 1920, "faculty_name_count": 8, "exhibition_mentions": 5, "partner_mentions": 3},
            "structural_signals": {"img_count": 15, "section_count": 6, "nav_link_count": 10, "footer_link_count": 6, "heading_count": 8}
        }
        
        delta = compute_institutional_delta(older, newer)
        
        assert delta["word_delta"] == 150
        assert delta["text_delta_pct"] == 150.0
        assert "faculty" in delta["sections_added"]
        assert "programs" in delta["sections_added"]
        assert delta["prestige_changes"]["accreditation_gained"] is True
        assert delta["prestige_changes"]["faculty_count_delta"] == 6
        assert delta["structural_changes"]["img_delta"] == 10
    
    def test_removed_section(self):
        """Detect removed sections."""
        older = {
            "text_metrics": {"word_count": 200, "section_presence": {"about": True, "admissions": True, "faculty": True}},
            "prestige_signals": {},
            "structural_signals": {}
        }
        newer = {
            "text_metrics": {"word_count": 150, "section_presence": {"about": True, "faculty": True}},
            "prestige_signals": {},
            "structural_signals": {}
        }
        
        delta = compute_institutional_delta(older, newer)
        
        assert "admissions" in delta["sections_removed"]
        assert delta["sections_added"] == []
    
    def test_prestige_markers_gained(self):
        """Detect newly appearing prestige markers."""
        older = {
            "text_metrics": {"word_count": 100, "section_presence": {}},
            "prestige_signals": {"has_accreditation": False, "founding_year": None, "faculty_name_count": 0, "exhibition_mentions": 0, "partner_mentions": 0},
            "structural_signals": {}
        }
        newer = {
            "text_metrics": {"word_count": 120, "section_presence": {}},
            "prestige_signals": {"has_accreditation": True, "founding_year": 1885, "faculty_name_count": 5, "exhibition_mentions": 3, "partner_mentions": 2},
            "structural_signals": {}
        }
        
        delta = compute_institutional_delta(older, newer)
        
        assert delta["prestige_changes"]["accreditation_gained"] is True
        assert delta["prestige_changes"]["founding_year_change"] == (None, 1885)
        assert delta["prestige_changes"]["faculty_count_delta"] == 5
        assert delta["prestige_changes"]["exhibition_delta"] == 3
    
    def test_accreditation_lost(self):
        """Detect accreditation claim removal."""
        older = {
            "text_metrics": {},
            "prestige_signals": {"has_accreditation": True},
            "structural_signals": {}
        }
        newer = {
            "text_metrics": {},
            "prestige_signals": {"has_accreditation": False},
            "structural_signals": {}
        }
        
        delta = compute_institutional_delta(older, newer)
        
        assert delta["prestige_changes"]["accreditation_lost"] is True
        assert delta["prestige_changes"]["accreditation_gained"] is False


class TestInstitutionalDeltaToMarkdown:
    """Tests for institutional_delta_to_markdown function."""
    
    def test_significant_changes(self):
        """Render markdown for significant changes."""
        delta = {
            "word_delta": 500,
            "text_delta_pct": 50.0,
            "sections_added": ["faculty", "programs"],
            "sections_removed": [],
            "prestige_changes": {
                "accreditation_gained": True,
                "accreditation_lost": False,
                "founding_year_change": None,
                "faculty_count_delta": 5,
                "exhibition_delta": 3,
                "partner_delta": 0,
            },
            "structural_changes": {
                "img_delta": 10,
                "nav_link_delta": 5,
                "section_delta": 4,
                "heading_delta": 3,
            }
        }
        
        result = institutional_delta_to_markdown(delta, "~180 days ago → Today", 1000, 1500)
        
        assert "Institutional Drift" in result
        assert "Content Volume" in result
        assert "1,000" in result
        assert "1,500" in result
        assert "Faculty" in result
        assert "Programs" in result
        assert "Accreditation" in result
        assert "Faculty names" in result
    
    def test_no_significant_changes(self):
        """Render markdown for stable site."""
        delta = {
            "word_delta": 10,
            "text_delta_pct": 2.0,
            "sections_added": [],
            "sections_removed": [],
            "prestige_changes": {
                "accreditation_gained": False,
                "accreditation_lost": False,
                "founding_year_change": None,
                "faculty_count_delta": 0,
                "exhibition_delta": 0,
                "partner_delta": 0,
            },
            "structural_changes": {
                "img_delta": 1,
                "nav_link_delta": 0,
                "section_delta": 0,
                "heading_delta": 1,
            }
        }
        
        result = institutional_delta_to_markdown(delta, "~30 days ago → Today", 500, 510)
        
        assert "No significant institutional changes" in result


class TestEmptyInstitutionalSignals:
    """Tests for _empty_institutional_signals helper."""
    
    def test_returns_valid_structure(self):
        """Empty signals have correct structure."""
        result = _empty_institutional_signals()
        
        assert "text_metrics" in result
        assert "prestige_signals" in result
        assert "structural_signals" in result
        assert result["text_metrics"]["word_count"] == 0
        assert result["prestige_signals"]["has_accreditation"] is False
        assert result["structural_signals"]["img_count"] == 0


# Ensure institutional signals are included in main extract
def test_extract_wayback_signals_includes_institutional():
    """Main extraction includes institutional signals."""
    result = extract_wayback_signals(SAMPLE_INSTITUTIONAL_HTML)
    
    assert "institutional_signals" in result
    assert "text_metrics" in result["institutional_signals"]
    assert "prestige_signals" in result["institutional_signals"]
    assert "structural_signals" in result["institutional_signals"]



if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ---------------------------------------------------------------------------
# Tests: Signal Tier Detection and Fallback
# ---------------------------------------------------------------------------

from utils.wayback import (
    determine_signal_tier,
    extract_fallback_structural_signals,
    fallback_structural_drift_to_markdown,
)


SAMPLE_RICH_SIGNALS = {
    "title": "Complete Website Title",
    "description": "Full description here",
    "h1_count": 2,
    "has_pricing_keywords": True,
    "html_bytes": 50000,
    "script_count": 10,
    "institutional_signals": {
        "text_metrics": {
            "char_count": 5000,
            "word_count": 800,
            "section_presence": {"about": True}
        },
        "prestige_signals": {},
        "structural_signals": {
            "img_count": 10,
            "section_count": 5,
            "nav_link_count": 8,
            "footer_link_count": 4,
            "heading_count": 6
        }
    }
}


SAMPLE_THIN_SIGNALS = {
    "title": None,
    "description": None,
    "h1_count": 0,
    "has_pricing_keywords": False,
    "html_bytes": 15000,
    "script_count": 25,
    "institutional_signals": {
        "text_metrics": {
            "char_count": 50,  # Too few chars
            "word_count": 10,
            "section_presence": {}
        },
        "prestige_signals": {},
        "structural_signals": {
            "img_count": 3,
            "section_count": 2,
            "nav_link_count": 5,
            "footer_link_count": 2,
            "heading_count": 1
        }
    }
}


class TestSignalTierDetection:
    """Tests for determine_signal_tier function."""
    
    def test_tier1_with_title_and_text(self):
        """Rich signals should return semantic tier."""
        tier = determine_signal_tier(SAMPLE_RICH_SIGNALS)
        assert tier == "semantic"
    
    def test_tier2_without_title(self):
        """Missing title should return fallback tier."""
        tier = determine_signal_tier(SAMPLE_THIN_SIGNALS)
        assert tier == "fallback_structural"
    
    def test_tier2_with_title_but_no_text(self):
        """Title present but no text should return fallback."""
        signals = {
            "title": "Has Title",
            "institutional_signals": {
                "text_metrics": {"char_count": 20}  # Too short
            }
        }
        tier = determine_signal_tier(signals)
        assert tier == "fallback_structural"
    
    def test_tier1_threshold_boundary(self):
        """Exactly 101 chars with title should be semantic."""
        signals = {
            "title": "Title",
            "institutional_signals": {
                "text_metrics": {"char_count": 101}
            }
        }
        tier = determine_signal_tier(signals)
        assert tier == "semantic"


class TestFallbackSignalExtraction:
    """Tests for extract_fallback_structural_signals function."""
    
    def test_extracts_all_fields(self):
        """All structural fields should be extracted."""
        result = extract_fallback_structural_signals(SAMPLE_RICH_SIGNALS)
        
        assert result["html_bytes"] == 50000
        assert result["section_count"] == 5
        assert result["nav_link_count"] == 8
        assert result["image_count"] == 10
        assert result["script_count"] == 10
        assert result["footer_link_count"] == 4
    
    def test_handles_missing_data(self):
        """Missing data should return zeros."""
        result = extract_fallback_structural_signals({})
        
        assert result["html_bytes"] == 0
        assert result["section_count"] == 0
        assert result["nav_link_count"] == 0
        assert result["image_count"] == 0


class TestFallbackMarkdownRendering:
    """Tests for fallback_structural_drift_to_markdown function."""
    
    def test_renders_fallback_snapshots(self):
        """Fallback tier snapshots should render structural table."""
        snapshots = [
            {
                "label": "~30 days ago",
                "timestamp": "20231015000000",
                "tier": "fallback_structural",
                "fallback_signals": {
                    "html_bytes": 25000,
                    "section_count": 4,
                    "nav_link_count": 6,
                    "image_count": 8,
                    "script_count": 12,
                    "footer_link_count": 3
                }
            }
        ]
        
        result = fallback_structural_drift_to_markdown(snapshots)
        
        assert "Structural Drift (Wayback Fallback Signals)" in result
        assert "~30 days ago" in result
        assert "25,000" in result
        assert "No semantic interpretation" in result
    
    def test_empty_for_semantic_only(self):
        """Semantic-only snapshots should return empty string."""
        snapshots = [
            {
                "label": "~30 days ago",
                "tier": "semantic",
                "signals": SAMPLE_RICH_SIGNALS
            }
        ]
        
        result = fallback_structural_drift_to_markdown(snapshots)
        assert result == ""
    
    def test_empty_for_no_snapshots(self):
        """Empty snapshot list should return empty string."""
        result = fallback_structural_drift_to_markdown([])
        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
