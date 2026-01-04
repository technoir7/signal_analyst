from typing import Optional
import random

import requests
from loguru import logger


# Rotate user agents to reduce bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]


def fetch_url_with_retry(url: str, timeout: int = 5, max_attempts: int = 3) -> Optional[str]:
    """Fetch a URL with user agent rotation and retry budget."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            ua = random.choice(USER_AGENTS)
            logger.debug("HTTP fetch attempt {} for {} with UA: {}", attempt, url, ua[:50])
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }
            # Increased timeout to 10s for slower sites / WAFs
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                continue
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.warning("HTTP fetch error on attempt {} for {}: {}", attempt, url, exc)
    logger.error("Failed to fetch {} after {} attempts. Last error: {}", url, max_attempts, last_error)
    return None
