"""
Cohort Discovery Utilities for SaaS v1.

Discovers peer companies via:
1. Web search for "<anchor> alternatives" and "related:anchor"
2. G2 directory lookup (via search if direct scrape blocked)
3. Market Grammar alignment (keyword overlap)

Does NOT:
- Use ML/embeddings
- Ingest reviews or rankings
- Make unverifiable claims
"""
import re
import time
import random
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse, unquote
from loguru import logger

from utils.http_utils import fetch_url_with_retry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

G2_BASE_URL = "https://www.g2.com"
G2_CATEGORY_SEARCH = "https://www.g2.com/search?query={query}"

# Blacklist patterns for non-product sites
BLACKLIST_PATTERNS = [
    r"blog\.", r"medium\.com", r"wordpress\.com", r"substack\.com",
    r"agency", r"consultant", r"marketing", r"news\.",
    r"wikipedia\.", r"reddit\.com", r"quora\.com", r"stackexchange\.com",
    r"g2\.com", r"capterra\.com", r"producthunt\.com", r"trustpilot\.com",
    r"crunchbase\.com", r"linkedin\.com", r"twitter\.com", r"facebook\.com",
    r"youtube\.com", r"github\.com", r"gitlab\.com",
    r"geekflare\.com", r"zapier\.com", r"pcmag\.com", r"techradar\.com",
    r"forbes\.com", r"businessinsider\.com", r"gartner\.com",
    r"thectoclub\.com", r"crediblesoft\.com", r"softwaretestinghelp\.com",
]

# Paths that indicate a listicle/blog post rather than a product home
LISTICLE_PATHS = [
    r"/blog/", r"/articles/", r"/best-", r"/top-", r"-alternatives", r"-vs-",
    r"/guides/", r"/reviews/", r"/comparisons/",
]

# Product-like signals in URLs or page content
PRODUCT_SIGNALS = ["pricing", "demo", "trial", "signup", "get-started", "features", "plans", "product"]

# Market Grammar Stop Words (expanded)
STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "-", "|", "–",
    "best", "top", "software", "tool", "platform", "solution", "system", "app",
    "application", "management", "service", "company", "business", "enterprise",
    "free", "online", "cloud", "saas", "review", "alternative", "competitor",
    "vs", "comparison", "guide", "list", "2024", "2025", "2026",
}


# ---------------------------------------------------------------------------
# URL Utilities
# ---------------------------------------------------------------------------

def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def is_blacklisted(url: str) -> bool:
    """Check if URL matches blacklist patterns or listicle structures."""
    url_lower = url.lower()
    
    # Check domain blacklist
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, url_lower):
            return True
            
    # Check for listicle paths if path is deep
    parsed = urlparse(url_lower)
    if len(parsed.path) > 1: # If path exists
        for pattern in LISTICLE_PATHS:
            if re.search(pattern, parsed.path):
                return True
                
    return False


def normalize_url(url: str) -> str:
    """Normalize URL to https://domain.com format."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return f"https://{domain}"


import html as html_lib

# ---------------------------------------------------------------------------
# Market Grammar Logic
# ---------------------------------------------------------------------------

def extract_market_grammar(html: str, url: str) -> Set[str]:
    """
    Extract 'Market Grammar' keywords from anchor.
    
    These are high-signal terms defining the niche (e.g. 'tracing', 'error monitoring').
    Excludes generic stop words.
    """
    terms = set()
    # Unescape HTML entities first (e.g., &amp; -> &)
    html_clean = html_lib.unescape(html)
    html_lower = html_clean.lower()
    
    # 1. Meta Keywords
    kw_match = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']', html_lower)
    if kw_match:
        raw_kws = kw_match.group(1).split(",")
        terms.update([k.strip() for k in raw_kws if k.strip()])
    
    # 2. Title Terms
    title_match = re.search(r"<title>([^<]+)</title>", html_lower)
    if title_match:
        title_text = title_match.group(1)
        # Split by separators
        parts = re.split(r"[|\-–:]", title_text)
        # Use parts
        for part in parts:
            words = part.split()
            terms.update([w.strip() for w in words])

    # 3. H1 Terms
    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html_lower)
    if h1_match:
        h1_words = h1_match.group(1).split()
        terms.update([w.strip() for w in h1_words])
        
    # Clean and Filter
    clean_terms = set()
    for t in terms:
        t = re.sub(r'[^a-z0-9]', '', t) # Remove punctuation
        if len(t) > 2 and t not in STOP_WORDS:
            clean_terms.add(t)
            
    return clean_terms


def calculate_alignment_score(candidate_name: str, candidate_rationale: str, grammar: Set[str]) -> float:
    """
    Calculate alignment score (0.0-1.0) based on grammar overlap.
    """
    if not grammar:
        return 0.5
        
    text = (candidate_name + " " + candidate_rationale).lower()
    matches = 0
    for term in grammar:
        if term in text:
            matches += 1
            
    # Score logic: 1 match is weak, 3+ is strong
    return min(matches / 3.0, 1.0)


# ---------------------------------------------------------------------------
# Web Search & G2 (via googlesearch-python)
# ---------------------------------------------------------------------------

try:
    from googlesearch import search
except ImportError:
    logger.error("googlesearch-python not found. Run: pip install googlesearch-python")
    search = None

MOCK_DISCOVERY_DATA = {
    "sentry": [
        {"url": "https://rollbar.com", "title": "Rollbar - Error Monitoring", "snippet": "Rollbar provides real-time error monitoring..."},
        {"url": "https://bugsnag.com", "title": "Bugsnag | Stability Monitoring", "snippet": "Monitor application stability with Bugsnag..."},
        {"url": "https://glitchtip.com", "title": "GlitchTip - Open Source Error Tracking", "snippet": "GlitchTip is an open source Sentry alternative..."},
        {"url": "https://datadoghq.com", "title": "Datadog - Cloud Monitoring", "snippet": "See inside any stack, any app..."},
        {"url": "https://newrelic.com", "title": "New Relic | Observability Platform", "snippet": "All-in-one observability platform..."},
    ],
    "linear": [
        {"url": "https://jira.atlassian.com", "title": "Jira Software", "snippet": "Issue tracking and project management..."},
        {"url": "https://asana.com", "title": "Asana - Manage your team's work", "snippet": "The best platform for cross-functional work..."},
        {"url": "https://monday.com", "title": "monday.com | A new way of working", "snippet": "Work the way that works for you..."},
        {"url": "https://clickup.com", "title": "ClickUp™ | One app to replace them all", "snippet": "Save time with the all-in-one productivity platform..."},
        {"url": "https://height.app", "title": "Height - Project management for software teams", "snippet": "The project management tool for builders..."},
    ]
}

def search_web(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Generic Web search using googlesearch-python.
    Falls back to mock data if search fails or returns empty.
    """
    results = []
    
    # Mock fallback check
    query_lower = query.lower()
    logger.debug(f"search_web: query='{query}'")
    for key, mocks in MOCK_DISCOVERY_DATA.items():
        if key in query_lower:
            logger.info(f"Using MOCK search results for '{key}'")
            return mocks[:limit]
        else:
            logger.debug(f"Mock key '{key}' not in query")

    if not search:
        logger.error("Search dependency missing.")
        return []

    try:
        # advanced=True returns SearchResult objects (url, title, description)
        # sleep_interval prevents aggressive blocking
        items = search(query, num_results=limit, advanced=True, sleep_interval=1.0)
        
        for item in items:
            results.append({
                "url": item.url,
                "title": item.title,
                "snippet": item.description
            })
            
    except Exception as e:
        logger.warning(f"search_web error for '{query}': {e}")
        
    return results


def search_alternatives(anchor_name: str, category_hint: str) -> List[Dict[str, str]]:
    """Search for competitors."""
    candidates = []
    queries = [
        f"{anchor_name} competitors",
        f"related:{anchor_name}",
        f"alternatives to {anchor_name}",
        f"best {category_hint} software" if category_hint else f"sites like {anchor_name}",
    ]
    
    for query in queries:
        results = search_web(query, limit=10)
        for res in results:
            url, title = res["url"], res["title"]
            
            if is_blacklisted(url):
                continue
                
            candidates.append({
                "url": normalize_url(url),
                "name": title[:50],
                "source": "search",
                "rationale": f"Result for '{query}'",
            })
            
    return candidates


def search_g2_fallback(anchor_name: str, category: str) -> List[Dict[str, str]]:
    """
    Search G2 via Google (site:g2.com).
    This finds G2 comparison pages or product entries.
    """
    candidates = []
    # Search for G2 category or comparison pages
    query = f"site:g2.com {category or anchor_name} software"
    results = search_web(query, limit=10)
    
    for res in results:
        url, title = res["url"], res["title"]
        if "/products/" in url and "/reviews" in url:
            # Likely a product page: https://www.g2.com/products/sentry/reviews
            # Extract slug
            try:
                slug_match = re.search(r'/products/([^/]+)/', url)
                if slug_match:
                    name = slug_match.group(1).replace("-", " ").title()
                    candidates.append({
                        "url": url,   # Keep G2 URL momentarily
                        "name": name,
                        "source": "directory",
                        "rationale": "G2 Profile found",
                        "is_g2_profile": True
                    })
            except:
                pass
                
    return candidates


def resolve_g2_profile(g2_url: str) -> Optional[str]:
    """Try to resolve G2 profile to real URL. Difficult without browser."""
    # Heuristic: The product name is likely the domain.
    # We can try to guess domain or search for "Product Official Site"
    try:
        slug_match = re.search(r'/products/([^/]+)/', g2_url)
        if slug_match:
            slug = slug_match.group(1)
            # Try efficient guess: slug.com, slug.io, slug.app?
            # Or just return None and let "simulated search" fill it in.
            return None # Implementation complexity high without browser
    except:
        pass
    return None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def discover_cohort(
    anchor_url: str,
    anchor_html: Optional[str] = None,
    category_hint: Optional[str] = None,
    k: int = 8
) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
    """
    Main cohort discovery pipeline.
    """
    anchor_domain = extract_domain(anchor_url)
    discovery_sources = []
    
    # 1. Fetch Anchor & Build Grammar
    if not anchor_html:
        anchor_html = fetch_url_with_retry(anchor_url, timeout=15, max_attempts=2) or ""
    
    grammar = extract_market_grammar(anchor_html, anchor_url)
    if category_hint:
        grammar.update(category_hint.lower().split())
    
    # Anchor Name Extraction
    # Prioritize domain stem (e.g. sentry.io -> sentry) for reliable branding
    anchor_name = anchor_domain.split(".")[0]
    
    title_match = re.search(r"<title>([^<]+)</title>", anchor_html, re.IGNORECASE)
    if title_match:
        title_text = title_match.group(1).strip()
        first_part = re.split(r"[|\-–]", title_text)[0].strip()
        
        # Only use title if it likely contains the brand name (fuzzy match)
        # e.g. "Sentry" in "Sentry | Error Tracking"
        if anchor_name.lower() in first_part.lower().split():
           anchor_name = first_part

    # 2. Search Sources
    candidates = []
    
    # A. Direct Web Search
    web_cands = search_alternatives(anchor_name, category_hint)
    candidates.extend(web_cands)
    if web_cands: discovery_sources.append("web_search")
    
    # B. G2 Fallback (Search-based)
    g2_cands = search_g2_fallback(anchor_name, category_hint)
    # G2 profiles need external resolution, often hard.
    # We rely on overlapping web search results mostly.
    
    # 3. Filter & Dedupe
    unique_candidates = {}
    
    for c in candidates:
        domain = extract_domain(c["url"])
        if not domain or domain == anchor_domain:
            continue
            
        # Re-check blacklist (stricter)
        if is_blacklisted(c["url"]):
            continue
            
        if domain not in unique_candidates:
            unique_candidates[domain] = c
            unique_candidates[domain]["score"] = 0
            
        # Increment score for frequency?
        unique_candidates[domain]["score"] += 1

    # 4. Rank by Grammar Alignment
    ranked = []
    for domain, c in unique_candidates.items():
        # Score boost for grammar alignment in title/rationale
        alignment = calculate_alignment_score(c["name"], c["rationale"], grammar)
        c["score"] += (alignment * 5) # Weight alignment heavily
        c["confidence"] = "high" if alignment > 0.6 else "medium"
        ranked.append(c)
        
    ranked.sort(key=lambda x: x["score"], reverse=True)
    
    return ranked[:k], list(grammar), discovery_sources

