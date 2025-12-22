import logging
from datetime import timedelta
from typing import Optional

import pandas as pd

try:
    from prophet import Prophet  # type: ignore
except Exception:  # pragma: no cover
    Prophet = None

logger = logging.getLogger(__name__)


class ProphetForecaster:
    """Forecast price history using Prophet."""

    def __init__(self, contamination: float = 0.05):
        if not Prophet:
            logger.warning("Prophet not installed; forecasting disabled.")
        self.model = Prophet(yearly_seasonality=True, daily_seasonality=False) if Prophet else None

    async def forecast(self, df: pd.DataFrame, days: int = 30) -> Optional[pd.DataFrame]:
        """
        df expects columns: ds (datetime), y (price)
        """
        if not self.model:
            return None
        model = Prophet(yearly_seasonality=True, daily_seasonality=False)
        model.fit(df)
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)
        return forecast
