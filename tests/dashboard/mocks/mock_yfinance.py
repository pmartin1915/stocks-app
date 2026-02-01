"""Mock yfinance data for testing.

Provides realistic mock data for AAPL and other tickers to avoid
real API calls during testing.
"""

from datetime import UTC, datetime

import pandas as pd

# Sample price data for AAPL
MOCK_AAPL_INFO = {
    "currentPrice": 185.42,
    "regularMarketPrice": 185.42,
    "regularMarketChange": 2.34,
    "regularMarketChangePercent": 1.28,
    "marketCap": 2_850_000_000_000,
    "trailingPE": 28.5,
    "forwardPE": 26.2,
    "fiftyTwoWeekHigh": 199.62,
    "fiftyTwoWeekLow": 142.00,
    "regularMarketVolume": 45_000_000,
    "averageVolume": 52_000_000,
    "dividendYield": 0.005,
    "beta": 1.25,
    "shortName": "Apple Inc.",
    "longName": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
}

# Sample for MSFT
MOCK_MSFT_INFO = {
    "currentPrice": 420.50,
    "regularMarketPrice": 420.50,
    "regularMarketChange": -5.20,
    "regularMarketChangePercent": -1.22,
    "marketCap": 3_100_000_000_000,
    "trailingPE": 35.2,
    "forwardPE": 30.5,
    "fiftyTwoWeekHigh": 450.00,
    "fiftyTwoWeekLow": 310.00,
    "regularMarketVolume": 25_000_000,
    "averageVolume": 28_000_000,
    "dividendYield": 0.007,
    "beta": 0.92,
    "shortName": "Microsoft Corporation",
    "longName": "Microsoft Corporation",
    "sector": "Technology",
    "industry": "Software - Infrastructure",
}

# Sample for invalid ticker (empty response)
MOCK_INVALID_TICKER_INFO = {}


def create_mock_history(
    start_price: float = 170.0,
    trend: str = "up",
    periods: int = 63,
) -> pd.DataFrame:
    """Create mock price history DataFrame.

    Args:
        start_price: Starting price for the series.
        trend: Price trend direction ("up", "down", "flat").
        periods: Number of days of data.

    Returns:
        DataFrame with OHLCV data.
    """
    dates = pd.date_range(end=datetime.now(UTC), periods=periods, freq="D")

    if trend == "up":
        prices = [start_price + (i * 0.25) for i in range(periods)]
    elif trend == "down":
        prices = [start_price - (i * 0.2) for i in range(periods)]
    else:  # flat
        prices = [start_price + (i % 5 - 2) for i in range(periods)]

    return pd.DataFrame(
        {
            "Open": prices,
            "High": [p + 1 for p in prices],
            "Low": [p - 1 for p in prices],
            "Close": prices,
            "Volume": [50_000_000] * periods,
        },
        index=dates,
    )


# Pre-built mock histories
MOCK_AAPL_HISTORY = create_mock_history(170.0, "up", 63)
MOCK_MSFT_HISTORY = create_mock_history(400.0, "down", 63)
MOCK_EMPTY_HISTORY = pd.DataFrame()
