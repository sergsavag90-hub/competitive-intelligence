import numpy as np

from src.analyzers.anomaly_detector import AnomalyDetector
from src.analyzers.competitor_clustering import CompetitorClustering


def test_anomaly_detector():
    X = np.array([[1], [2], [2], [100]])
    det = AnomalyDetector(contamination=0.25)
    res = det.detect(X)
    assert len(res["labels"]) == 4


def test_clustering_basic():
    X = np.array([[1, 2], [2, 3], [10, 11]])
    cl = CompetitorClustering(n_clusters=2)
    clusters, score = cl.cluster(X)
    assert len(clusters) == 3
