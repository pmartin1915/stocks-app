"""Dashboard-specific test fixtures.

Provides fixtures for mocking yfinance, Streamlit caching, and price data.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tests.dashboard.mocks.mock_yfinance import (
    MOCK_AAPL_HISTORY,
    MOCK_AAPL_INFO,
    MOCK_EMPTY_HISTORY,
    MOCK_INVALID_TICKER_INFO,
    MOCK_MSFT_HISTORY,
    MOCK_MSFT_INFO,
)


@pytest.fixture
def mock_yfinance():
    """Mock yfinance.Ticker for testing.

    Returns mock data for AAPL and MSFT, empty data for other tickers.
    """
    with patch("yfinance.Ticker") as mock_ticker:

        def create_mock(ticker: str):
            mock = MagicMock()
            ticker_upper = ticker.upper()

            if ticker_upper == "AAPL":
                mock.info = MOCK_AAPL_INFO
                mock.history.return_value = MOCK_AAPL_HISTORY
            elif ticker_upper == "MSFT":
                mock.info = MOCK_MSFT_INFO
                mock.history.return_value = MOCK_MSFT_HISTORY
            else:
                mock.info = MOCK_INVALID_TICKER_INFO
                mock.history.return_value = MOCK_EMPTY_HISTORY
            return mock

        mock_ticker.side_effect = create_mock
        yield mock_ticker


@pytest.fixture
def disable_streamlit_cache(monkeypatch):
    """Disable Streamlit caching for tests.

    Makes @st.cache_data a passthrough decorator.
    """

    def passthrough_decorator(*args, **kwargs):
        def decorator(func):
            return func

        # Handle both @cache_data and @cache_data() syntax
        if args and callable(args[0]):
            return args[0]
        return decorator

    monkeypatch.setattr("streamlit.cache_data", passthrough_decorator)


@pytest.fixture
def mock_price_data():
    """Pre-computed price data for testing without yfinance.

    Returns dict of ticker -> price data.
    """
    return {
        "AAPL": {
            "price": 185.42,
            "change": 2.34,
            "change_pct": 1.28,
            "market_cap": 2_850_000_000_000,
            "pe_ratio": 28.5,
            "52w_high": 199.62,
            "52w_low": 142.00,
            "dividend_yield": 0.005,
            "beta": 1.25,
            "short_name": "Apple Inc.",
        },
        "MSFT": {
            "price": 420.50,
            "change": -5.20,
            "change_pct": -1.22,
            "market_cap": 3_100_000_000_000,
            "pe_ratio": 35.2,
            "52w_high": 450.00,
            "52w_low": 310.00,
            "dividend_yield": 0.007,
            "beta": 0.92,
            "short_name": "Microsoft Corporation",
        },
    }


@pytest.fixture
def mock_price_history():
    """Pre-computed price history for sparkline tests.

    Returns dict matching get_price_history() output format.
    """
    return {
        "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "prices": [170.0, 175.0, 185.42],
        "volumes": [50_000_000, 52_000_000, 48_000_000],
        "returns_1d": 5.95,
        "returns_1w": None,
        "returns_1m": None,
        "returns_3m": 9.07,
        "returns_1y": None,
    }


@pytest.fixture
def sample_piotroski_scores():
    """Sample Piotroski F-Score data for component tests."""
    return {
        "score": 8,
        "signals": {
            "roa_positive": True,
            "cfo_positive": True,
            "delta_roa_positive": True,
            "accruals_quality": True,
            "leverage_decreased": True,
            "liquidity_improved": True,
            "no_dilution": True,
            "margin_improved": True,
            "turnover_improved": True,
        },
    }


@pytest.fixture
def sample_altman_scores():
    """Sample Altman Z-Score data for component tests."""
    return {
        "z_score": 3.45,
        "zone": "Safe",
        "components": {
            "working_capital_ratio": 0.35,
            "retained_earnings_ratio": 0.42,
            "ebit_ratio": 0.18,
            "equity_to_debt_ratio": 1.25,
            "asset_turnover_ratio": 0.85,
        },
    }
