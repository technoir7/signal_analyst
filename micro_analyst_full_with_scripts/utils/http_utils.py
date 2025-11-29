from typing import Optional

import requests
from loguru import logger


def fetch_url_with_retry(url: str, timeout: int = 5, max_attempts: int = 2) -> Optional[str]:
    """Fetch a URL with a small, deterministic number of attempts."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug("HTTP fetch attempt {} for {}", attempt, url)
            resp = requests.get(url, timeout=timeout, headers={
                "User-Agent": "MicroAnalystBot/1.0 (+https://example.com)"
            })
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                continue
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.warning("HTTP fetch error on attempt {} for {}: {}", attempt, url, exc)
    logger.error("Failed to fetch {} after {} attempts. Last error: {}", url, max_attempts, last_error)
    return None
