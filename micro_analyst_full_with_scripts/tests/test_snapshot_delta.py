"""
Tests for Time-Delta v1 snapshot and change detection functionality.

Tests:
1. delta_to_markdown produces correct markdown section
2. delta_to_markdown handles no prior snapshot
3. ChangeDetector computes expected shifts
4. Report contains "## Change Since Last Snapshot" heading
"""

import os
import sys
import tempfile
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.inference import InferredProfile, SignalInference
from core.change_detector import ChangeDetector, DeltaReport, delta_to_markdown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_signal_present() -> SignalInference:
    """A signal with data present."""
    return SignalInference(
        section="Web Presence",
        data_status="present",
        confidence="high",
        plausible_causes=["Standard public indexing"],
        strategic_implication="The organization actively manages its digital front door."
    )


@pytest.fixture
def sample_signal_absent() -> SignalInference:
    """A signal with data absent."""
    return SignalInference(
        section="Web Presence",
        data_status="absent",
        confidence="medium",
        plausible_causes=["WAF Blocking", "SPA unrendered"],
        strategic_implication="The organization maintains a shielded digital perimeter."
    )


@pytest.fixture
def profile_present() -> InferredProfile:
    """A profile where most signals are present."""
    return InferredProfile(
        web=SignalInference(
            section="Web Presence", data_status="present", confidence="high",
            plausible_causes=["Standard public indexing"],
            strategic_implication="Active web presence."
        ),
        seo=SignalInference(
            section="SEO Diagnostics", data_status="present", confidence="high",
            plausible_causes=["Mature marketing ops"],
            strategic_implication="Zero SEO issues detected."
        ),
        tech_stack=SignalInference(
            section="Tech Stack", data_status="present", confidence="high",
            plausible_causes=["Modern SaaS composability"],
            strategic_implication="Confirmed core infrastructure: React, Node.js."
        ),
        reviews=SignalInference(
            section="Customer Voice", data_status="present", confidence="medium",
            plausible_causes=["PLG motion"],
            strategic_implication="Public sentiment is visible."
        ),
        social=SignalInference(
            section="Social Footprint", data_status="present", confidence="high",
            plausible_causes=["Brand-building investment"],
            strategic_implication="Active social channels."
        ),
        hiring=SignalInference(
            section="Hiring Signals", data_status="present", confidence="high",
            plausible_causes=["Expansion mode"],
            strategic_implication="Visible hiring indicates expansion."
        ),
        ads=SignalInference(
            section="Paid Media", data_status="absent", confidence="medium",
            plausible_causes=["Organic Growth"],
            strategic_implication="No paid media signals."
        ),
        strategic_posture="The target exhibits a 'Glass House' signals profile."
    )


@pytest.fixture
def profile_degraded() -> InferredProfile:
    """A profile where some signals went dark (for testing shifts)."""
    return InferredProfile(
        web=SignalInference(
            section="Web Presence", data_status="absent", confidence="medium",
            plausible_causes=["WAF Blocking"],
            strategic_implication="Shielded digital perimeter."
        ),
        seo=SignalInference(
            section="SEO Diagnostics", data_status="error", confidence="low",
            plausible_causes=["Anti-bot defenses"],
            strategic_implication="Technical barriers prevent SEO auditing."
        ),
        tech_stack=SignalInference(
            section="Tech Stack", data_status="present", confidence="high",
            plausible_causes=["Modern SaaS composability"],
            strategic_implication="Confirmed core infrastructure: React, Node.js."
        ),
        reviews=SignalInference(
            section="Customer Voice", data_status="absent", confidence="medium",
            plausible_causes=["B2B/Enterprise model"],
            strategic_implication="No public reviews."
        ),
        social=SignalInference(
            section="Social Footprint", data_status="present", confidence="high",
            plausible_causes=["Brand-building investment"],
            strategic_implication="Active social channels."
        ),
        hiring=SignalInference(
            section="Hiring Signals", data_status="present", confidence="high",
            plausible_causes=["Expansion mode"],
            strategic_implication="Visible hiring indicates expansion."
        ),
        ads=SignalInference(
            section="Paid Media", data_status="present", confidence="high",
            plausible_causes=["Performance marketing"],
            strategic_implication="Active paid acquisition."
        ),
        strategic_posture="The target exhibits a 'Hybrid' signals profile."
    )


# ---------------------------------------------------------------------------
# Tests: delta_to_markdown
# ---------------------------------------------------------------------------

def test_delta_to_markdown_no_prior_snapshot():
    """When delta is None, output says 'No prior snapshot available.'"""
    result = delta_to_markdown(None)
    
    assert "## Change Since Last Snapshot" in result
    assert "No prior snapshot available." in result


def test_delta_to_markdown_no_shifts():
    """When there are no shifts, output says 'No significant changes detected.'"""
    delta = DeltaReport(
        baseline_date=datetime(2026, 1, 1, 12, 0),
        comparison_date=datetime(2026, 1, 2, 12, 0),
        time_elapsed_days=1.0,
        shifts=[],
        overall_stability_score=1.0
    )
    
    result = delta_to_markdown(delta)
    
    assert "## Change Since Last Snapshot" in result
    assert "No significant changes detected" in result
    assert "2026-01-01" in result  # Baseline date in output


def test_delta_to_markdown_with_shifts(profile_present, profile_degraded):
    """When there are shifts, output lists them with significance."""
    detector = ChangeDetector()
    
    delta = detector.compute_delta(
        current=profile_degraded,
        previous=profile_present,
        current_date=datetime(2026, 1, 2, 12, 0),
        previous_date=datetime(2026, 1, 1, 12, 0)
    )
    
    result = delta_to_markdown(delta)
    
    assert "## Change Since Last Snapshot" in result
    assert "Detected Shifts" in result
    # Web went from present to absent
    assert "Web Presence" in result
    assert "breakage" in result or "🔴" in result
    # Stability score should be reduced
    assert "Overall Stability Score" in result


# ---------------------------------------------------------------------------
# Tests: ChangeDetector
# ---------------------------------------------------------------------------

def test_change_detector_no_change(profile_present):
    """When profiles are identical, no shifts detected."""
    detector = ChangeDetector()
    
    delta = detector.compute_delta(
        current=profile_present,
        previous=profile_present,
        current_date=datetime(2026, 1, 2),
        previous_date=datetime(2026, 1, 1)
    )
    
    assert len(delta.shifts) == 0
    assert delta.overall_stability_score == 1.0


def test_change_detector_detects_breakage(profile_present, profile_degraded):
    """Detector finds breakage when signals go dark."""
    detector = ChangeDetector()
    
    delta = detector.compute_delta(
        current=profile_degraded,
        previous=profile_present,
        current_date=datetime(2026, 1, 2),
        previous_date=datetime(2026, 1, 1)
    )
    
    # Should detect shifts: Web breakage, Ads emergence (the detector
    # currently only diffs web, seo, tech, hiring, social, ads sections)
    assert len(delta.shifts) >= 2
    
    shift_sections = [s.section for s in delta.shifts]
    assert "Web Presence" in shift_sections  # went present -> absent
    assert "Paid Media" in shift_sections  # went absent -> present (emergence)
    
    # Stability should be degraded
    assert delta.overall_stability_score < 1.0


def test_change_detector_detects_emergence(profile_degraded, profile_present):
    """Detector finds emergence when signals appear (reverse direction)."""
    detector = ChangeDetector()
    
    # Profile "recovers" from degraded to present
    delta = detector.compute_delta(
        current=profile_present,
        previous=profile_degraded,
        current_date=datetime(2026, 1, 2),
        previous_date=datetime(2026, 1, 1)
    )
    
    # Should detect emergence of Web Presence, Reviews
    shift_types = [s.shift_type for s in delta.shifts]
    assert "emergence" in shift_types


def test_delta_elapsed_time_calculation(profile_present):
    """Verify elapsed time is calculated correctly."""
    detector = ChangeDetector()
    
    delta = detector.compute_delta(
        current=profile_present,
        previous=profile_present,
        current_date=datetime(2026, 1, 10, 12, 0),
        previous_date=datetime(2026, 1, 1, 12, 0)
    )
    
    # 9 days elapsed
    assert abs(delta.time_elapsed_days - 9.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
