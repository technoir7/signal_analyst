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
        }


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
                    results.append({
                        "label": label,
                        "timestamp": closest["timestamp"],
                        "signals": signals,
                    })
    
    return results


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
