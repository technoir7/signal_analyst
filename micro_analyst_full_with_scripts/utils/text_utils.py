from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup  # type: ignore


def clean_html_to_text(html: Optional[str]) -> str:
    """
    Convert raw HTML into cleaned plain text.

    - Strips <script> and <style> blocks.
    - Uses the built-in html.parser (no lxml dependency).
    - Normalizes whitespace.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Extract visible text
    text = soup.get_text(separator=" ", strip=True)

    # Collapse excessive whitespace
    return " ".join(text.split())


def truncate_text(text: Optional[str], max_length: int) -> Optional[str]:
    """
    Simple truncation helper aligned with tests.

    Behavior:
    - If text is None: return None.
    - If max_length <= 0: return "" (non-None, but empty).
    - If len(text) <= max_length: return text unchanged.
    - Else: return the first max_length characters (no ellipsis).
    """
    if text is None:
        return None

    if max_length <= 0:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length]
