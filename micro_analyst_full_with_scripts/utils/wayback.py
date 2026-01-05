"""
Wayback Machine integration for historical baseline detection.

Uses the Internet Archive CDX API to retrieve archived snapshots and
extract lightweight signals for comparison with current state.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import requests
from bs4 import BeautifulSoup
from loguru import logger


# Conservative timeouts and user agent
WAYBACK_TIMEOUT = 10
WAYBACK_USER_AGENT = "SignalAnalyst/1.0 (OSINT Research Tool; +https://github.com/signal-analyst)"

# CDX API base
CDX_API_URL = "https://web.archive.org/cdx/search/cdx"

# Max HTML bytes to process (500KB cap for safety)
MAX_HTML_BYTES = 500_000


def list_snapshots(
    url: str,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, str]]:
    """
    Query Wayback CDX API for available snapshots.
    
    Args:
        url: The URL to search for in the archive
        from_ts: Start timestamp (YYYYMMDD or YYYYMMDDHHMMSS)
        to_ts: End timestamp
        limit: Maximum number of results (default 10 for closest selection)
        
    Returns:
        List of dicts with keys: timestamp, original, statuscode, mimetype
        Returns empty list on any failure.
    """
    try:
        params = {
            "url": url,
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype",
            "filter": "statuscode:200",
            "collapse": "digest",
            "limit": str(limit),
        }
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
            
        headers = {"User-Agent": WAYBACK_USER_AGENT}
        
        resp = requests.get(
            CDX_API_URL,
            params=params,
            headers=headers,
            timeout=WAYBACK_TIMEOUT
        )
        
        if resp.status_code != 200:
            logger.warning(f"Wayback CDX API returned {resp.status_code}")
            return []
            
        data = resp.json()
        
        # First row is header, rest are data
        if len(data) < 2:
            return []
            
        header = data[0]
        results = []
        for row in data[1:]:
            results.append(dict(zip(header, row)))
            
        return results
        
    except requests.Timeout:
        logger.warning(f"Wayback CDX API timeout for {url}")
        return []
    except requests.RequestException as e:
        logger.warning(f"Wayback CDX API error for {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error querying Wayback CDX for {url}: {e}")
        return []


def _select_closest_snapshot(
    snapshots: List[Dict[str, str]],
    target_date: datetime
) -> Optional[Dict[str, str]]:
    """
    Select the snapshot closest to the target date.
    
    Args:
        snapshots: List of snapshot dicts with 'timestamp' key
        target_date: Target datetime to match
        
    Returns:
        The snapshot dict closest to target, or None if empty list.
    """
    if not snapshots:
        return None
    
    target_ts = target_date.strftime("%Y%m%d%H%M%S")
    
    def distance(snap: Dict[str, str]) -> int:
        ts = snap.get("timestamp", "")
        # Pad to 14 chars if needed
        ts = ts.ljust(14, "0")
        target = target_ts.ljust(14, "0")
        try:
            return abs(int(ts) - int(target))
        except ValueError:
            return float('inf')
    
    return min(snapshots, key=distance)


def fetch_snapshot_html(timestamp: str, original_url: str) -> Optional[str]:
    """
    Fetch archived HTML from Wayback Machine.
    
    Args:
        timestamp: Wayback timestamp (YYYYMMDDHHMMSS)
        original_url: The original URL
        
    Returns:
        HTML content as string (capped at MAX_HTML_BYTES), or None on failure.
    """
    try:
        # Use id_ modifier to get original HTML without Wayback toolbar
        wayback_url = f"https://web.archive.org/web/{timestamp}id_/{original_url}"
        
        headers = {"User-Agent": WAYBACK_USER_AGENT}
        
        resp = requests.get(
            wayback_url,
            headers=headers,
            timeout=WAYBACK_TIMEOUT,
            stream=True  # Stream for size control
        )
        
        if resp.status_code != 200:
            logger.warning(f"Wayback fetch returned {resp.status_code} for {wayback_url}")
            return None
        
        # Read up to MAX_HTML_BYTES
        content = resp.content[:MAX_HTML_BYTES]
        return content.decode('utf-8', errors='replace')
        
    except requests.Timeout:
        logger.warning(f"Wayback fetch timeout for {original_url} @ {timestamp}")
        return None
    except requests.RequestException as e:
        logger.warning(f"Wayback fetch error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching Wayback snapshot: {e}")
        return None


def extract_wayback_signals(html: str) -> Dict[str, Any]:
    """
    Extract lightweight signals from archived HTML.
    
    These are shallow, deterministic signals that don't require
    full MCP pipeline execution.
    
    Returns:
        {
            "title": str|None,
            "description": str|None,
            "h1_count": int,
            "has_pricing_keywords": bool,
            "has_docs_keywords": bool,
            "framework_hints": list[str],
            "html_bytes": int,
            "script_count": int
        }
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None
        
        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        description = desc_tag.get("content", "").strip() if desc_tag else None
        
        # H1 count
        h1_count = len(soup.find_all("h1"))
        
        # Script count (cheap complexity signal)
        script_count = len(soup.find_all("script"))
        
        # HTML bytes
        html_bytes = len(html.encode('utf-8', errors='replace'))
        
        # Lowercase HTML for keyword detection
        html_lower = html.lower()
        
        # Pricing keywords
        pricing_keywords = ["pricing", "plans", "cost", "subscribe", "buy now", "free trial"]
        has_pricing = any(kw in html_lower for kw in pricing_keywords)
        
        # Documentation keywords
        docs_keywords = ["documentation", "docs", "api reference", "developer", "getting started"]
        has_docs = any(kw in html_lower for kw in docs_keywords)
        
        # Framework hints (shallow detection)
        framework_hints = []
        framework_markers = {
            "__NEXT_DATA__": "Next.js",
            "_next/static": "Next.js",
            "/__nuxt/": "Nuxt.js",
            "ng-version=": "Angular",
            'data-reactroot': "React",
            "wp-content": "WordPress",
            "shopify": "Shopify",
        }
        for marker, framework in framework_markers.items():
            if marker.lower() in html_lower:
                if framework not in framework_hints:
                    framework_hints.append(framework)
        
        # Login/Auth keywords
        login_keywords = ["log in", "login", "sign in", "signin", "start free"]
        has_login = any(kw in html_lower for kw in login_keywords)

        # Trust signals
        trust_keywords = ["security", "soc2", "gdpr", "enterprise", "compliance", "iso 27001"]
        has_trust = any(kw in html_lower for kw in trust_keywords)

        return {
            "title": title,
            "description": description,
            "h1_count": h1_count,
            "has_pricing_keywords": has_pricing,
            "has_docs_keywords": has_docs,
            "has_login": has_login,
            "has_trust": has_trust,
            "framework_hints": framework_hints,
            "html_bytes": html_bytes,
            "script_count": script_count,
            "institutional_signals": extract_institutional_signals(html, soup),
        }
        
    except Exception as e:
        logger.error(f"Error extracting Wayback signals: {e}")
        return {
            "title": None,
            "description": None,
            "h1_count": 0,
            "has_pricing_keywords": False,
            "has_docs_keywords": False,
            "has_login": False,
            "has_trust": False,
            "framework_hints": [],
            "html_bytes": 0,
            "script_count": 0,
            "institutional_signals": _empty_institutional_signals(),
        }


# ---------------------------------------------------------------------------
# Institutional Drift Signal Extraction
# ---------------------------------------------------------------------------

import re

# Section heading patterns for institutional sites
SECTION_PATTERNS = {
    "about": [r"\babout\b", r"\bwho we are\b", r"\bour story\b", r"\bmission\b"],
    "admissions": [r"\badmissions?\b", r"\bapply\b", r"\benrollment\b", r"\bapplication\b"],
    "programs": [r"\bprograms?\b", r"\bcurriculum\b", r"\bcourses?\b", r"\bdegrees?\b"],
    "faculty": [r"\bfaculty\b", r"\binstructors?\b", r"\bteachers?\b", r"\bstaff\b"],
    "contact": [r"\bcontact\b", r"\bget in touch\b", r"\breach us\b"],
}

# Prestige keywords
ACCREDITATION_PATTERN = re.compile(r"\baccredit(?:ed|ation|ing)?\b", re.IGNORECASE)
FOUNDING_YEAR_PATTERN = re.compile(
    r"(?:since|founded|est\.?|established|circa)\s*(\d{4})", re.IGNORECASE
)
EXHIBITION_PATTERN = re.compile(r"\b(?:exhibition|exhibit|show|gallery|galleries)\b", re.IGNORECASE)
PARTNER_PATTERN = re.compile(r"\b(?:partner(?:ship)?|affiliate|collaboration|in partnership)\b", re.IGNORECASE)

# Faculty name heuristic: Two or more capitalized words
FACULTY_NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


def _empty_institutional_signals() -> Dict[str, Any]:
    """Return empty/default institutional signals for error cases."""
    return {
        "text_metrics": {
            "char_count": 0,
            "word_count": 0,
            "section_presence": {k: False for k in SECTION_PATTERNS.keys()}
        },
        "prestige_signals": {
            "has_accreditation": False,
            "founding_year": None,
            "faculty_name_count": 0,
            "exhibition_mentions": 0,
            "partner_mentions": 0,
        },
        "structural_signals": {
            "img_count": 0,
            "section_count": 0,
            "nav_link_count": 0,
            "footer_link_count": 0,
            "heading_count": 0,
        }
    }


def extract_institutional_signals(html: str, soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract institutional-specific signals for static/legacy sites.
    
    Returns nested dict with:
    - text_metrics: char/word counts, section presence
    - prestige_signals: accreditation, founding year, faculty, exhibitions
    - structural_signals: img/section/nav/footer counts
    """
    try:
        return {
            "text_metrics": _extract_text_metrics(soup),
            "prestige_signals": _extract_prestige_signals(html, soup),
            "structural_signals": _extract_structural_signals(soup),
        }
    except Exception as e:
        logger.warning(f"Error extracting institutional signals: {e}")
        return _empty_institutional_signals()


def _extract_text_metrics(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract textual churn signals."""
    # Get visible text (exclude script/style)
    for element in soup(["script", "style", "noscript", "meta", "link"]):
        element.decompose()
    
    visible_text = soup.get_text(separator=" ", strip=True)
    
    # Metrics
    char_count = len(visible_text)
    words = visible_text.split()
    word_count = len(words)
    
    # Section presence detection via headings
    all_headings_text = " ".join(
        h.get_text(strip=True).lower() 
        for h in soup.find_all(["h1", "h2", "h3", "h4"])
    )
    
    section_presence = {}
    for section_name, patterns in SECTION_PATTERNS.items():
        section_presence[section_name] = any(
            re.search(p, all_headings_text, re.IGNORECASE) 
            for p in patterns
        )
    
    return {
        "char_count": char_count,
        "word_count": word_count,
        "section_presence": section_presence,
    }


def _extract_prestige_signals(html: str, soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract trust and prestige markers."""
    html_lower = html.lower()
    
    # Accreditation
    has_accreditation = bool(ACCREDITATION_PATTERN.search(html))
    
    # Founding year (find earliest)
    year_matches = FOUNDING_YEAR_PATTERN.findall(html)
    founding_year = None
    if year_matches:
        years = [int(y) for y in year_matches if 1800 <= int(y) <= 2030]
        if years:
            founding_year = min(years)
    
    # Exhibition mentions
    exhibition_mentions = len(EXHIBITION_PATTERN.findall(html))
    
    # Partner mentions
    partner_mentions = len(PARTNER_PATTERN.findall(html))
    
    # Faculty name count (heuristic)
    # Look for names near faculty/instructor sections
    faculty_section = None
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        heading_text = heading.get_text(strip=True).lower()
        if any(kw in heading_text for kw in ["faculty", "instructor", "teacher", "staff"]):
            # Get parent section or next siblings
            parent = heading.find_parent(["section", "div", "article"])
            if parent:
                faculty_section = parent.get_text()
                break
    
    faculty_name_count = 0
    if faculty_section:
        # Count capitalized name patterns
        names = FACULTY_NAME_PATTERN.findall(faculty_section)
        # Filter common false positives
        filtered_names = [
            n for n in names 
            if not any(fp in n.lower() for fp in ["learn more", "read more", "view all", "see more"])
        ]
        faculty_name_count = len(filtered_names)
    
    return {
        "has_accreditation": has_accreditation,
        "founding_year": founding_year,
        "faculty_name_count": faculty_name_count,
        "exhibition_mentions": exhibition_mentions,
        "partner_mentions": partner_mentions,
    }


def _extract_structural_signals(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract structural complexity proxies."""
    # Image count
    img_count = len(soup.find_all("img"))
    
    # Section count
    section_count = len(soup.find_all("section"))
    
    # Navigation links
    nav_link_count = 0
    for nav in soup.find_all("nav"):
        nav_link_count += len(nav.find_all("a"))
    
    # Footer links
    footer_link_count = 0
    for footer in soup.find_all("footer"):
        footer_link_count += len(footer.find_all("a"))
    
    # Heading count (h2-h4, excluding h1)
    heading_count = len(soup.find_all(["h2", "h3", "h4"]))
    
    return {
        "img_count": img_count,
        "section_count": section_count,
        "nav_link_count": nav_link_count,
        "footer_link_count": footer_link_count,
        "heading_count": heading_count,
    }


def compute_institutional_delta(
    older: Dict[str, Any], 
    newer: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute delta between two institutional signal snapshots.
    
    Args:
        older: institutional_signals dict from older snapshot
        newer: institutional_signals dict from newer snapshot
        
    Returns:
        Dict with absolute and percentage changes
    """
    old_text = older.get("text_metrics", {})
    new_text = newer.get("text_metrics", {})
    old_prestige = older.get("prestige_signals", {})
    new_prestige = newer.get("prestige_signals", {})
    old_struct = older.get("structural_signals", {})
    new_struct = newer.get("structural_signals", {})
    
    # Text delta
    old_words = old_text.get("word_count", 0)
    new_words = new_text.get("word_count", 0)
    word_delta = new_words - old_words
    text_delta_pct = (abs(word_delta) / max(old_words, 1)) * 100
    
    # Section changes
    old_sections = old_text.get("section_presence", {})
    new_sections = new_text.get("section_presence", {})
    sections_added = [s for s, present in new_sections.items() if present and not old_sections.get(s, False)]
    sections_removed = [s for s, present in old_sections.items() if present and not new_sections.get(s, False)]
    
    # Prestige changes
    old_accred = old_prestige.get("has_accreditation", False)
    new_accred = new_prestige.get("has_accreditation", False)
    
    old_year = old_prestige.get("founding_year")
    new_year = new_prestige.get("founding_year")
    founding_year_change = None
    if old_year != new_year and (old_year or new_year):
        founding_year_change = (old_year, new_year)
    
    faculty_delta = new_prestige.get("faculty_name_count", 0) - old_prestige.get("faculty_name_count", 0)
    exhibition_delta = new_prestige.get("exhibition_mentions", 0) - old_prestige.get("exhibition_mentions", 0)
    partner_delta = new_prestige.get("partner_mentions", 0) - old_prestige.get("partner_mentions", 0)
    
    # Structural changes
    img_delta = new_struct.get("img_count", 0) - old_struct.get("img_count", 0)
    nav_delta = new_struct.get("nav_link_count", 0) - old_struct.get("nav_link_count", 0)
    section_delta = new_struct.get("section_count", 0) - old_struct.get("section_count", 0)
    heading_delta = new_struct.get("heading_count", 0) - old_struct.get("heading_count", 0)
    
    return {
        "text_delta_pct": round(text_delta_pct, 1),
        "word_delta": word_delta,
        "sections_added": sections_added,
        "sections_removed": sections_removed,
        "prestige_changes": {
            "accreditation_gained": new_accred and not old_accred,
            "accreditation_lost": old_accred and not new_accred,
            "founding_year_change": founding_year_change,
            "faculty_count_delta": faculty_delta,
            "exhibition_delta": exhibition_delta,
            "partner_delta": partner_delta,
        },
        "structural_changes": {
            "img_delta": img_delta,
            "nav_link_delta": nav_delta,
            "section_delta": section_delta,
            "heading_delta": heading_delta,
        }
    }


def institutional_delta_to_markdown(
    delta: Dict[str, Any], 
    label: str,
    old_words: int = 0,
    new_words: int = 0
) -> str:
    """
    Render institutional drift delta as markdown.
    
    Args:
        delta: Output from compute_institutional_delta()
        label: Time period label (e.g., "~180 days ago → Today")
        old_words: Word count from older snapshot
        new_words: Word count from newer snapshot
        
    Returns:
        Markdown string block
    """
    lines = [f"\n### Institutional Drift: {label}\n\n"]
    
    # Content Volume
    lines.append("**Content Volume**\n")
    word_delta = delta.get("word_delta", 0)
    delta_pct = delta.get("text_delta_pct", 0)
    direction = "+" if word_delta >= 0 else ""
    lines.append(f"- Words: {old_words:,} → {new_words:,} ({direction}{word_delta:,}, {delta_pct:.1f}% change)\n")
    
    sections_added = delta.get("sections_added", [])
    sections_removed = delta.get("sections_removed", [])
    if sections_added:
        lines.append(f"- Sections appeared: {', '.join(s.title() for s in sections_added)}\n")
    if sections_removed:
        lines.append(f"- Sections removed: {', '.join(s.title() for s in sections_removed)}\n")
    if not sections_added and not sections_removed:
        lines.append("- Sections: stable\n")
    
    lines.append("\n")
    
    # Prestige Markers
    prestige = delta.get("prestige_changes", {})
    has_prestige_change = any([
        prestige.get("accreditation_gained"),
        prestige.get("accreditation_lost"),
        prestige.get("founding_year_change"),
        abs(prestige.get("faculty_count_delta", 0)) > 0,
        abs(prestige.get("exhibition_delta", 0)) > 0,
    ])
    
    if has_prestige_change:
        lines.append("**Prestige Markers**\n")
        if prestige.get("accreditation_gained"):
            lines.append("- Accreditation: Now claims accreditation\n")
        if prestige.get("accreditation_lost"):
            lines.append("- Accreditation: No longer claims accreditation\n")
        if prestige.get("founding_year_change"):
            old_yr, new_yr = prestige["founding_year_change"]
            lines.append(f"- Founding year: {old_yr or '(none)'} → {new_yr or '(none)'}\n")
        
        faculty_delta = prestige.get("faculty_count_delta", 0)
        if faculty_delta != 0:
            lines.append(f"- Faculty names: {'+' if faculty_delta > 0 else ''}{faculty_delta}\n")
        
        exhibit_delta = prestige.get("exhibition_delta", 0)
        if exhibit_delta != 0:
            lines.append(f"- Exhibition mentions: {'+' if exhibit_delta > 0 else ''}{exhibit_delta}\n")
        
        lines.append("\n")
    
    # Structural Changes
    struct = delta.get("structural_changes", {})
    has_struct_change = any(abs(v) >= 3 for v in struct.values())
    
    if has_struct_change:
        lines.append("**Site Structure**\n")
        for key, value in struct.items():
            if abs(value) >= 3:
                label_nice = key.replace("_delta", "").replace("_", " ").title()
                lines.append(f"- {label_nice}: {'+' if value > 0 else ''}{value}\n")
        lines.append("\n")
    
    # If nothing notable changed
    if not has_prestige_change and not has_struct_change and not sections_added and not sections_removed and abs(delta_pct) < 10:
        lines.append("_No significant institutional changes detected._\n\n")
    
    return "".join(lines)



def get_historical_snapshots(url: str) -> List[Dict[str, Any]]:
    """
    Get snapshots from approximately 30 days and 180 days ago.
    
    Uses closest-snapshot selection to find the best match within
    a +/- 15 day window around each target date.
    
    Returns list of dicts with timestamp, signals, and age label.
    Max 2 snapshots fetched to bound work.
    """
    results = []
    now = datetime.now()
    
    targets = [
        ("~30 days ago", now - timedelta(days=30)),
        ("~180 days ago", now - timedelta(days=180)),
    ]
    
    for label, target_date in targets:
        # Search for snapshots around target date (+/- 15 days)
        from_ts = (target_date - timedelta(days=15)).strftime("%Y%m%d")
        to_ts = (target_date + timedelta(days=15)).strftime("%Y%m%d")
        
        # Request multiple snapshots for closest selection
        snapshots = list_snapshots(url, from_ts=from_ts, to_ts=to_ts, limit=10)
        
        if snapshots:
            # Select the snapshot closest to target date
            closest = _select_closest_snapshot(snapshots, target_date)
            
            if closest:
                html = fetch_snapshot_html(closest["timestamp"], closest["original"])
                
                if html:
                    signals = extract_wayback_signals(html)
                    tier = determine_signal_tier(signals)
                    
                    result_entry = {
                        "label": label,
                        "timestamp": closest["timestamp"],
                        "signals": signals,
                        "tier": tier,
                    }
                    
                    # If Tier 2 (fallback), add structural-only summary
                    if tier == "fallback_structural":
                        result_entry["fallback_signals"] = extract_fallback_structural_signals(signals)
                    
                    results.append(result_entry)
    
    return results


def determine_signal_tier(signals: Dict[str, Any]) -> str:
    """
    Determine which signal tier applies based on data quality.
    
    Tier 1 ("semantic"): Title present AND visible text > 100 chars
    Tier 2 ("fallback_structural"): Otherwise
    
    Returns:
        "semantic" or "fallback_structural"
    """
    title = signals.get("title")
    inst = signals.get("institutional_signals", {})
    text_metrics = inst.get("text_metrics", {})
    char_count = text_metrics.get("char_count", 0)
    
    # Tier 1 requires meaningful semantic content
    has_title = bool(title and len(title.strip()) > 0)
    has_text = char_count > 100
    
    if has_title and has_text:
        return "semantic"
    else:
        return "fallback_structural"


def extract_fallback_structural_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract Tier 2 fallback signals from existing signal dict.
    
    Used when semantic signals (title, text) are unavailable.
    These are purely structural, deterministic, non-semantic.
    """
    inst = signals.get("institutional_signals", {})
    struct = inst.get("structural_signals", {})
    
    return {
        "html_bytes": signals.get("html_bytes", 0),
        "section_count": struct.get("section_count", 0),
        "nav_link_count": struct.get("nav_link_count", 0),
        "image_count": struct.get("img_count", 0),
        "script_count": signals.get("script_count", 0),
        "footer_link_count": struct.get("footer_link_count", 0),
    }



def wayback_delta_to_markdown(
    current_signals: Optional[Dict[str, Any]],
    historical_snapshots: List[Dict[str, Any]]
) -> str:
    """
    Format Wayback comparison as a markdown section.
    
    Args:
        current_signals: Current web signals (title, frameworks, etc.)
                        If None, compares historical snapshots to each other.
        historical_snapshots: List from get_historical_snapshots()
        
    Returns:
        Markdown string for "## Change Over Time (Wayback)" section
    """
    if not historical_snapshots:
        return "\n\n## Change Over Time (Wayback)\n\n_No archived snapshots available for this URL._\n"
    
    lines = ["\n\n## Change Over Time (Wayback)\n"]
    lines.append("_Historical comparison using Internet Archive snapshots._\n\n")
    
    # If no current signals, use oldest snapshot as baseline for comparison
    if current_signals is None:
        if len(historical_snapshots) >= 2:
            # Compare newer to older
            lines.append("> ⚠️ _No live scrape available. Comparing historical snapshots only._\n\n")
            newer = historical_snapshots[0]
            older = historical_snapshots[1]
            lines.append(_format_snapshot_comparison(
                older["signals"], 
                newer["signals"],
                f"{older['label']} → {newer['label']}"
            ))
        else:
            # Single snapshot, just display it
            snap = historical_snapshots[0]
            lines.append(f"### {snap['label']}\n\n")
            lines.append(_format_snapshot_signals(snap["signals"]))
        return "".join(lines)
    
    # Compare each historical snapshot to current
    for snapshot in historical_snapshots:
        label = snapshot["label"]
        ts = snapshot["timestamp"]
        signals = snapshot["signals"]
        
        # Format timestamp for display
        try:
            dt = datetime.strptime(ts[:8], "%Y%m%d")
            date_str = dt.strftime("%B %d, %Y")
        except:
            date_str = ts
        
        lines.append(f"### {label} ({date_str})\n\n")
        
        # Title comparison
        hist_title = signals.get("title") or "(unknown)"
        curr_title = current_signals.get("title") or "(unknown)"
        if hist_title != curr_title:
            lines.append(f"- **Title changed**: \"{hist_title}\" → \"{curr_title}\"\n")
        else:
            lines.append(f"- **Title**: unchanged\n")
        
        # Framework comparison (with low-confidence warning)
        hist_frameworks = signals.get("framework_hints", [])
        curr_frameworks = current_signals.get("framework_hints", [])
        if set(hist_frameworks) != set(curr_frameworks):
            if hist_frameworks and curr_frameworks:
                lines.append(f"- **Tech stack shift** _(low-confidence)_: {', '.join(hist_frameworks)} → {', '.join(curr_frameworks)}\n")
            elif curr_frameworks:
                lines.append(f"- **Tech stack emerged** _(low-confidence)_: Now using {', '.join(curr_frameworks)}\n")
            elif hist_frameworks:
                lines.append(f"- **Tech stack hidden** _(low-confidence)_: Previously showed {', '.join(hist_frameworks)}\n")
        else:
            if curr_frameworks:
                lines.append(f"- **Tech stack** _(low-confidence)_: stable ({', '.join(curr_frameworks)})\n")
        
        # Pricing/docs presence
        hist_pricing = signals.get("has_pricing_keywords", False)
        curr_pricing = current_signals.get("has_pricing_keywords", False)
        if hist_pricing != curr_pricing:
            if curr_pricing:
                lines.append("- **Pricing emerged**: Now shows pricing/plans keywords\n")
            else:
                lines.append("- **Pricing removed**: No longer shows pricing/plans keywords\n")
        
        # HTML size change (if significant)
        hist_bytes = signals.get("html_bytes", 0)
        curr_bytes = current_signals.get("html_bytes", 0)
        if hist_bytes > 0 and curr_bytes > 0:
            ratio = curr_bytes / hist_bytes
            if ratio > 1.5:
                lines.append(f"- **Page grew**: {hist_bytes:,} → {curr_bytes:,} bytes (+{(ratio-1)*100:.0f}%)\n")
            elif ratio < 0.67:
                lines.append(f"- **Page shrank**: {hist_bytes:,} → {curr_bytes:,} bytes ({(ratio-1)*100:.0f}%)\n")
        
        # Script count change
        hist_scripts = signals.get("script_count", 0)
        curr_scripts = current_signals.get("script_count", 0)
        if abs(curr_scripts - hist_scripts) >= 5:
            lines.append(f"- **Script complexity**: {hist_scripts} → {curr_scripts} scripts\n")
        
        lines.append("\n")
    
    return "".join(lines)


def _format_snapshot_signals(signals: Dict[str, Any]) -> str:
    """Format a single snapshot's signals as bullet points."""
    lines = []
    lines.append(f"- **Title**: {signals.get('title') or '(unknown)'}\n")
    if signals.get("framework_hints"):
        lines.append(f"- **Tech hints** _(low-confidence)_: {', '.join(signals['framework_hints'])}\n")
    lines.append(f"- **Pricing keywords**: {'Yes' if signals.get('has_pricing_keywords') else 'No'}\n")
    lines.append(f"- **Docs keywords**: {'Yes' if signals.get('has_docs_keywords') else 'No'}\n")
    lines.append(f"- **Page size**: {signals.get('html_bytes', 0):,} bytes, {signals.get('script_count', 0)} scripts\n")
    return "".join(lines)


def _format_snapshot_comparison(older: Dict[str, Any], newer: Dict[str, Any], label: str) -> str:
    """Format comparison between two historical snapshots."""
    lines = [f"### {label}\n\n"]
    
    old_title = older.get("title") or "(unknown)"
    new_title = newer.get("title") or "(unknown)"
    if old_title != new_title:
        lines.append(f"- **Title changed**: \"{old_title}\" → \"{new_title}\"\n")
    
    old_fw = older.get("framework_hints", [])
    new_fw = newer.get("framework_hints", [])
    if set(old_fw) != set(new_fw):
        lines.append(f"- **Tech stack shift** _(low-confidence)_: {', '.join(old_fw) or 'none'} → {', '.join(new_fw) or 'none'}\n")
    
    old_bytes = older.get("html_bytes", 0)
    new_bytes = newer.get("html_bytes", 0)
    if old_bytes > 0 and new_bytes > 0:
        ratio = new_bytes / old_bytes
        if abs(ratio - 1.0) > 0.25:
            lines.append(f"- **Page size**: {old_bytes:,} → {new_bytes:,} bytes\n")
    
    lines.append("\n")
    return "".join(lines)


def fallback_structural_drift_to_markdown(
    historical_snapshots: List[Dict[str, Any]]
) -> str:
    """
    Render structural drift (Tier 2 fallback) as markdown.
    
    Used when semantic signals are unavailable (JS-heavy sites, thin snapshots).
    Reports only deterministic, structural changes with no interpretation.
    """
    # Check if any snapshots used fallback tier
    fallback_snapshots = [s for s in historical_snapshots if s.get("tier") == "fallback_structural"]
    
    if not fallback_snapshots:
        return ""  # Only render when fallback tier was used
    
    lines = ["\n\n## Structural Drift (Wayback Fallback Signals)\n"]
    lines.append("_Semantic signals unavailable. Showing structural-only metrics._\n\n")
    lines.append("| Period | HTML Bytes | Sections | Nav Links | Images | Scripts | Footer Links |\n")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
    
    for snap in fallback_snapshots:
        label = snap.get("label", "?")
        fb = snap.get("fallback_signals", {})
        
        lines.append(
            f"| {label} | {fb.get('html_bytes', 0):,} | "
            f"{fb.get('section_count', 0)} | {fb.get('nav_link_count', 0)} | "
            f"{fb.get('image_count', 0)} | {fb.get('script_count', 0)} | "
            f"{fb.get('footer_link_count', 0)} |\n"
        )
    
    lines.append("\n_Note: These are shell-level HTML metrics only. No semantic interpretation is possible._\n")
    
    return "".join(lines)
