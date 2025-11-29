import pytest

from mcp_seo_probe.server import _basic_meta_issues, _heading_issues, _keyword_summary


def test_basic_meta_issues_missing_description_and_title():
    issues = _basic_meta_issues(title=None, description=None)
    assert "Missing meta description." in issues
    assert "Missing <title> tag." in issues


def test_basic_meta_issues_short_and_long_title():
    short_title = "Too short"
    long_title = "L" * 80

    issues_short = _basic_meta_issues(title=short_title, description="desc")
    assert "Title appears too short (<20 characters)." in issues_short
    assert "Missing <title> tag." not in issues_short

    issues_long = _basic_meta_issues(title=long_title, description="desc")
    assert "Title appears too long (>70 characters)." in issues_long


def test_heading_issues_none_single_multiple():
    assert "No H1 tag found." in _heading_issues([])

    single = _heading_issues(["Main heading"])
    assert single == []

    multiple = _heading_issues(["H1 one", "H1 two"])
    assert len(multiple) == 1
    assert multiple[0].startswith("Multiple H1 tags found")


def test_keyword_summary_basic():
    text = "Example example EXAMPLE word other other text content"
    summary = _keyword_summary(text, top_n=3)
    example_entry = next((item for item in summary if item["term"] == "example"), None)
    assert example_entry is not None
    assert example_entry["count"] == 3


def test_keyword_summary_empty_or_none():
    assert _keyword_summary("", top_n=5) == []
    # type: ignore[arg-type]
    assert _keyword_summary(None, top_n=5) == []  # noqa: E501
