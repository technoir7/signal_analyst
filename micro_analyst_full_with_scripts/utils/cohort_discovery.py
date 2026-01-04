"""
Cohort Discovery Utilities for SaaS v1.

Discovers peer companies via:
1. Web search for "<anchor> alternatives"
2. G2 directory category page scraping

Does NOT:
- Use ML/embeddings
- Ingest reviews or rankings
- Make unverifiable claims
"""
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin
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
]

# Product-like signals in URLs or page content
PRODUCT_SIGNALS = ["pricing", "demo", "trial", "signup", "get-started", "features", "plans"]


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
    """Check if URL matches blacklist patterns."""
    url_lower = url.lower()
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, url_lower):
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


# ---------------------------------------------------------------------------
# Category Term Extraction
# ---------------------------------------------------------------------------

def extract_category_terms(html: str, url: str) -> List[str]:
    """
    Extract potential category terms from anchor page.
    
    Looks for:
    - Meta keywords
    - Title keywords
    - Common SaaS category patterns
    """
    terms = []
    html_lower = html.lower()
    
    # Extract from meta keywords
    kw_match = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']', html_lower)
    if kw_match:
        terms.extend([t.strip() for t in kw_match.group(1).split(",")][:5])
    
    # Extract from title
    title_match = re.search(r"<title>([^<]+)</title>", html_lower)
    if title_match:
        title_words = title_match.group(1).split()
        # Filter common stop words
        stop_words = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "-", "|", "–"}
        terms.extend([w for w in title_words if w.lower() not in stop_words and len(w) > 2][:3])
    
    # Common SaaS categories to detect
    saas_categories = [
        "project management", "crm", "marketing", "sales", "analytics",
        "collaboration", "communication", "productivity", "design", "development",
        "hr", "recruiting", "accounting", "finance", "support", "helpdesk",
        "automation", "integration", "security", "monitoring", "devops",
    ]
    for cat in saas_categories:
        if cat in html_lower:
            terms.append(cat)
    
    # Dedupe and limit
    seen = set()
    unique_terms = []
    for t in terms:
        t_clean = t.lower().strip()
        if t_clean and t_clean not in seen and len(t_clean) > 2:
            seen.add(t_clean)
            unique_terms.append(t_clean)
    
    return unique_terms[:10]


# ---------------------------------------------------------------------------
# Web Search (Simulated via DuckDuckGo HTML)
# ---------------------------------------------------------------------------

def search_alternatives(anchor_name: str, category_hint: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Search for alternatives using DuckDuckGo HTML results.
    
    Returns list of {url, name, rationale}.
    """
    candidates = []
    
    queries = [
        f"{anchor_name} alternatives",
        f"best {category_hint or 'saas'} software" if category_hint else f"{anchor_name} competitors",
    ]
    
    for query in queries:
        try:
            # DuckDuckGo HTML search
            search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            html = fetch_url_with_retry(search_url, timeout=10, max_attempts=2)
            
            if not html:
                logger.warning(f"cohort_discovery: search failed for '{query}'")
                continue
            
            # Extract result links (DuckDuckGo format)
            # Pattern: <a class="result__a" href="...">
            links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html)
            
            for url, title in links[:10]:
                # DuckDuckGo uses redirect URLs, extract actual URL
                actual_url_match = re.search(r'uddg=([^&]+)', url)
                if actual_url_match:
                    from urllib.parse import unquote
                    actual_url = unquote(actual_url_match.group(1))
                else:
                    actual_url = url
                
                if is_blacklisted(actual_url):
                    continue
                
                normalized = normalize_url(actual_url)
                candidates.append({
                    "url": normalized,
                    "name": title.strip()[:50],
                    "source": "search",
                    "rationale": f"Found via '{query}'",
                })
                
        except Exception as e:
            logger.error(f"cohort_discovery: search error for '{query}': {e}")
    
    return candidates


# ---------------------------------------------------------------------------
# G2 Directory Scraping
# ---------------------------------------------------------------------------

def scrape_g2_category(category: str) -> List[Dict[str, str]]:
    """
    Scrape G2 category/search page for top products.
    
    Returns list of {url, name, rationale}.
    """
    candidates = []
    
    try:
        search_url = G2_CATEGORY_SEARCH.format(query=category.replace(" ", "+"))
        html = fetch_url_with_retry(search_url, timeout=15, max_attempts=2)
        
        if not html:
            logger.warning(f"cohort_discovery: G2 scrape failed for '{category}'")
            return []
        
        # G2 product links pattern: /products/<slug>/reviews or /products/<slug>
        # Product name is typically in data-product-name or nearby text
        product_links = re.findall(
            r'href="(/products/[^/"]+)"[^>]*>([^<]*)</a>',
            html
        )
        
        seen_slugs = set()
        for path, name in product_links[:20]:
            slug = path.split("/")[2] if len(path.split("/")) > 2 else ""
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            
            # Try to find the product's actual website
            # G2 pages often have "Visit Website" links
            product_url = f"{G2_BASE_URL}{path}"
            
            # For now, we'll use the slug as a hint and let the caller resolve
            # the actual website. We mark source as "directory".
            product_name = name.strip() if name.strip() else slug.replace("-", " ").title()
            
            candidates.append({
                "url": product_url,  # G2 product page (caller should resolve to actual site)
                "name": product_name[:50],
                "source": "directory",
                "rationale": f"Listed in G2 '{category}' category",
                "g2_slug": slug,
            })
    
    except Exception as e:
        logger.error(f"cohort_discovery: G2 scrape error for '{category}': {e}")
    
    return candidates[:10]


def resolve_g2_to_website(g2_product_url: str) -> Optional[str]:
    """
    Resolve a G2 product page to the actual company website.
    
    Looks for "Visit Website" link on G2 product page.
    """
    try:
        html = fetch_url_with_retry(g2_product_url, timeout=10, max_attempts=2)
        if not html:
            return None
        
        # Look for external website link patterns
        # G2 uses various patterns: "Visit Website", "Go to website", external links
        website_patterns = [
            r'href="(https?://[^"]+)"[^>]*>\s*(?:Visit Website|Go to|Official Site)',
            r'data-website="(https?://[^"]+)"',
            r'"website":\s*"(https?://[^"]+)"',
        ]
        
        for pattern in website_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                if not is_blacklisted(url) and "g2.com" not in url:
                    return normalize_url(url)
        
        return None
    except Exception as e:
        logger.error(f"cohort_discovery: G2 resolution error: {e}")
        return None


# ---------------------------------------------------------------------------
# Candidate Filtering and Ranking
# ---------------------------------------------------------------------------

def filter_candidates(
    candidates: List[Dict[str, str]],
    anchor_domain: str
) -> List[Dict[str, str]]:
    """
    Filter candidates to product companies only.
    
    Removes:
    - Anchor domain itself
    - Blacklisted sites
    - Duplicates
    """
    seen_domains = {anchor_domain}
    filtered = []
    
    for c in candidates:
        domain = extract_domain(c["url"])
        if not domain or domain in seen_domains:
            continue
        if is_blacklisted(c["url"]):
            continue
        
        seen_domains.add(domain)
        filtered.append(c)
    
    return filtered


def rank_candidates(
    candidates: List[Dict[str, str]],
    category_terms: List[str]
) -> List[Dict[str, str]]:
    """
    Rank candidates by relevance signals.
    
    Scoring:
    - +2 for appearing in multiple sources
    - +1 for category term overlap in name
    - +1 for product-like signals in URL
    """
    # Count source appearances
    url_sources: Dict[str, List[str]] = {}
    for c in candidates:
        domain = extract_domain(c["url"])
        if domain not in url_sources:
            url_sources[domain] = []
        if c["source"] not in url_sources[domain]:
            url_sources[domain].append(c["source"])
    
    # Score each candidate
    scored = []
    for c in candidates:
        domain = extract_domain(c["url"])
        score = 0
        
        # Multi-source bonus
        sources = url_sources.get(domain, [])
        if len(sources) > 1:
            score += 2
            c["source"] = "both"
        
        # Category term overlap
        name_lower = c.get("name", "").lower()
        for term in category_terms:
            if term in name_lower:
                score += 1
                break
        
        # Product-like URL signals
        url_lower = c["url"].lower()
        if any(sig in url_lower for sig in PRODUCT_SIGNALS):
            score += 1
        
        c["_score"] = score
        scored.append(c)
    
    # Sort by score descending, dedupe by domain
    scored.sort(key=lambda x: x.get("_score", 0), reverse=True)
    
    seen = set()
    ranked = []
    for c in scored:
        domain = extract_domain(c["url"])
        if domain in seen:
            continue
        seen.add(domain)
        
        # Clean up internal fields
        c.pop("_score", None)
        c.pop("g2_slug", None)
        
        # Assign confidence based on source
        c["confidence"] = "medium" if c["source"] == "both" else "low"
        
        ranked.append(c)
    
    return ranked


# ---------------------------------------------------------------------------
# Main Discovery Function
# ---------------------------------------------------------------------------

def discover_cohort(
    anchor_url: str,
    anchor_html: Optional[str] = None,
    category_hint: Optional[str] = None,
    k: int = 8
) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
    """
    Main cohort discovery pipeline.
    
    Args:
        anchor_url: Primary target URL
        anchor_html: Pre-fetched HTML (optional)
        category_hint: User-provided category hint
        k: Number of candidates to return
    
    Returns:
        (candidates, category_terms, discovery_sources)
    """
    anchor_domain = extract_domain(anchor_url)
    discovery_sources = []
    
    # 1. Fetch anchor HTML if not provided
    if not anchor_html:
        anchor_html = fetch_url_with_retry(anchor_url, timeout=15, max_attempts=2) or ""
    
    # 2. Extract category terms
    category_terms = extract_category_terms(anchor_html, anchor_url)
    if category_hint and category_hint.lower() not in [t.lower() for t in category_terms]:
        category_terms.insert(0, category_hint.lower())
    
    # 3. Extract anchor name from title
    anchor_name = anchor_domain
    title_match = re.search(r"<title>([^<]+)</title>", anchor_html, re.IGNORECASE)
    if title_match:
        # Take first part before | or -
        title_parts = re.split(r"[|\-–]", title_match.group(1))
        anchor_name = title_parts[0].strip()[:30]
    
    # 4. Web search
    search_candidates = search_alternatives(anchor_name, category_hint or (category_terms[0] if category_terms else None))
    if search_candidates:
        discovery_sources.append("web_search")
    
    # 5. G2 directory
    g2_category = category_hint or (category_terms[0] if category_terms else anchor_name)
    g2_candidates = scrape_g2_category(g2_category)
    
    # Resolve G2 URLs to actual websites
    resolved_g2 = []
    for c in g2_candidates:
        if "g2.com" in c["url"]:
            actual_url = resolve_g2_to_website(c["url"])
            if actual_url:
                c["url"] = actual_url
                resolved_g2.append(c)
        else:
            resolved_g2.append(c)
    
    if resolved_g2:
        discovery_sources.append("g2_directory")
    
    # 6. Merge candidates
    all_candidates = search_candidates + resolved_g2
    
    # 7. Filter
    filtered = filter_candidates(all_candidates, anchor_domain)
    
    # 8. Rank and select top k
    ranked = rank_candidates(filtered, category_terms)
    
    return ranked[:k], category_terms, discovery_sources
