import logging
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Isolation Forest for price anomalies."""

    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42)

    def detect(self, X: np.ndarray) -> dict:
        if X.size == 0:
            return {"labels": [], "scores": []}
        labels = self.model.fit_predict(X)
        scores = self.model.score_samples(X)
        return {"labels": labels.tolist(), "scores": scores.tolist()}
