"""
Lightweight page classifier used to adapt scraping strategy.

Tries to leverage scikit-learn DecisionTree if available; otherwise falls back
to deterministic heuristics so callers always get a label.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:  # Optional heavy dependency
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.feature_extraction import DictVectorizer
    import joblib
except Exception:  # pragma: no cover - optional dependency
    DecisionTreeClassifier = None
    DictVectorizer = None
    joblib = None


PageSample = Tuple[str, str]  # (html, label)


def _extract_features(html: str) -> Dict[str, float]:
    """Extract simple DOM features for classification."""
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    features: Dict[str, float] = {
        "len_html": len(html),
        "len_text": len(text),
        "count_img": len(soup.find_all("img")),
        "count_a": len(soup.find_all("a")),
        "count_button": len(soup.find_all("button")),
        "count_script": len(soup.find_all("script")),
        "count_meta": len(soup.find_all("meta")),
        "count_article": len(soup.find_all("article")),
        "count_li": len(soup.find_all("li")),
        "has_price_text": 1.0 if any(token in text for token in ["$", "€", "uah", "грн", "price"]) else 0.0,
        "has_cart": 1.0 if "add to cart" in text or "кошик" in text else 0.0,
        "has_category_words": 1.0 if any(word in text for word in ["category", "categories", "категорії"]) else 0.0,
        "has_blog_words": 1.0 if any(word in text for word in ["blog", "article", "post"]) else 0.0,
        "has_product_schema": 1.0 if '"@type":"Product"' in html else 0.0,
    }
    return features


class PageClassifier:
    """Adaptive classifier with optional ML model and heuristic fallback."""

    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path) if model_path else None
        self.vectorizer = DictVectorizer(sparse=False) if DictVectorizer else None
        self.model = DecisionTreeClassifier(max_depth=6, random_state=42) if DecisionTreeClassifier else None
        self.labels: List[str] = ["product", "category", "blog", "other"]

        if self.model_path and self.model_path.exists() and joblib and self.model:
            try:
                bundle = joblib.load(self.model_path)
                self.model = bundle["model"]
                self.vectorizer = bundle["vectorizer"]
                logger.info("Loaded page classifier model from %s", self.model_path)
            except Exception as exc:  # pragma: no cover - optional path
                logger.warning("Failed to load classifier model: %s", exc)

    def fit(self, samples: Sequence[PageSample]) -> None:
        """Train DecisionTree on provided samples."""
        if not (self.model and self.vectorizer):
            logger.info("sklearn not available; skipping ML training, heuristic mode only.")
            return

        if not samples:
            logger.warning("No samples provided for training.")
            return

        X = [_extract_features(html) for html, _ in samples]
        y = [label for _, label in samples]
        X_vec = self.vectorizer.fit_transform(X)
        self.model.fit(X_vec, y)
        if self.model_path and joblib:
            joblib.dump({"model": self.model, "vectorizer": self.vectorizer}, self.model_path)
            logger.info("Saved trained classifier to %s", self.model_path)

    def predict(self, html: str) -> str:
        """Predict page type; uses heuristics if model unavailable."""
        feats = _extract_features(html)

        if self.model and self.vectorizer:
            try:
                X_vec = self.vectorizer.transform([feats])
                return str(self.model.predict(X_vec)[0])
            except Exception as exc:  # pragma: no cover - runtime safety
                logger.debug("Model prediction failed, falling back to heuristics: %s", exc)

        return self._heuristic_predict(feats)

    def _heuristic_predict(self, feats: Dict[str, float]) -> str:
        """Simple rules for environments without sklearn."""
        if feats.get("has_cart") or feats.get("has_product_schema"):
            return "product"
        if feats.get("has_price_text") and feats.get("count_img", 0) > 5:
            return "product"
        if feats.get("has_category_words"):
            return "category"
        if feats.get("has_blog_words"):
            return "blog"
        return "other"
