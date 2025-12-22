"""
Utility helpers to auto-detect product card selectors for adaptive scraping.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

PRICE_PATTERN = re.compile(r"[\d\s]+[,.]?\d*\s?(usd|uah|eur|€|\$|грн)", re.IGNORECASE)


def _selector_for_tag(tag) -> str:
    """Build a CSS selector based on tag name and classes/ids."""
    if not tag:
        return ""
    if tag.get("id"):
        return f"{tag.name}#{tag.get('id')}"
    classes = tag.get("class", [])
    if classes:
        return f"{tag.name}." + ".".join(sorted(set(classes))[:3])
    return tag.name


def detect_product_selectors(html: str, max_candidates: int = 5) -> List[Dict[str, str]]:
    """
    Detect likely product card containers by looking for repeated structures that contain prices.
    Returns a list of selector descriptors.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    candidates: List[Tuple[str, int]] = []

    for tag in soup.find_all(["div", "li", "article", "section"]):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        if PRICE_PATTERN.search(text):
            selector = _selector_for_tag(tag)
            if selector:
                candidates.append((selector, len(tag.find_all())))

    counter = Counter(selector for selector, _ in candidates)
    scored = counter.most_common(max_candidates)

    result: List[Dict[str, str]] = []
    for selector, count in scored:
        result.append({"selector": selector, "score": count})
    return result


def detect_title_price_fields(card_html: str) -> Dict[str, str]:
    """
    Best-effort extraction of title/price selectors within a product card fragment.
    """
    soup = BeautifulSoup(card_html or "", "html.parser")
    title = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    price = soup.find(text=PRICE_PATTERN)
    return {
        "title_selector": _selector_for_tag(title.parent if title else None),
        "price_selector": _selector_for_tag(price.parent if price else None) if price else "",
    }
