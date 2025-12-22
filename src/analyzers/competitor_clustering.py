import logging
from typing import Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class CompetitorClustering:
    """KMeans clustering for competitors."""

    def __init__(self, n_clusters: int = 3):
        self.model = KMeans(n_clusters=n_clusters, random_state=42)

    def cluster(self, features: np.ndarray) -> Tuple[np.ndarray, Optional[float]]:
        if features.shape[0] == 0:
            return np.array([]), None
        clusters = self.model.fit_predict(features)
        score = None
        if len(set(clusters)) > 1:
            score = float(silhouette_score(features, clusters))
        return clusters, score
