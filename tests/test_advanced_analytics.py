import numpy as np
import pandas as pd
import pytest

from src.analyzers.anomaly_detector import AnomalyDetector
from src.analyzers.competitor_clustering import CompetitorClustering
from src.analyzers.prophet_forecaster import ProphetForecaster


def test_anomaly_detector_basic():
    X = np.array([[1], [2], [2], [100]])
    det = AnomalyDetector(contamination=0.25)
    res = det.detect(X)
    assert len(res["labels"]) == 4


def test_clustering():
    X = np.array([[1, 2], [1, 3], [10, 11], [10, 12]])
    cl = CompetitorClustering(n_clusters=2)
    clusters, score = cl.cluster(X)
    assert len(clusters) == 4
    assert score is not None


@pytest.mark.asyncio
async def test_prophet_forecaster_no_model(monkeypatch):
    # if Prophet not installed, forecast returns None
    monkeypatch.setattr("src.analyzers.prophet_forecaster.Prophet", None, raising=False)
    df = pd.DataFrame({"ds": pd.date_range("2024-01-01", periods=5, freq="D"), "y": [1, 2, 3, 4, 5]})
    pf = ProphetForecaster()
    res = await pf.forecast(df)
    assert res is None
