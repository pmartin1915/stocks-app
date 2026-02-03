"""Tests for dashboard/utils/price_data.py.

Tests price data fetching and formatting utilities.
Uses mocking to avoid network dependencies.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Check if yfinance is available for conditional test skipping
try:
    import yfinance as _yf  # noqa: F401
    YFINANCE_INSTALLED = True
    del _yf
except ImportError:
    YFINANCE_INSTALLED = False


class TestGetPriceData:
    """Tests for get_price_data()."""

    def test_returns_error_when_yfinance_unavailable(self, monkeypatch):
        """Should return error when yfinance not installed."""
        from dashboard.utils import price_data

        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", False)
        # Clear cache to get fresh result
        price_data.get_price_data.clear()

        result = price_data.get_price_data("AAPL")

        assert "error" in result
        assert "yfinance not installed" in result["error"]

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_returns_price_data_for_valid_ticker(self, monkeypatch):
        """Should return price data for valid ticker."""
        from dashboard.utils import price_data

        # Create a mock yfinance module
        mock_yf = MagicMock()
        mock_info = {
            "regularMarketPrice": 150.50,
            "currentPrice": 150.50,
            "regularMarketChange": 2.50,
            "regularMarketChangePercent": 1.69,
            "marketCap": 2500000000000,
            "trailingPE": 28.5,
            "forwardPE": 25.0,
            "fiftyTwoWeekHigh": 180.00,
            "fiftyTwoWeekLow": 120.00,
            "regularMarketVolume": 50000000,
            "averageVolume": 60000000,
            "dividendYield": 0.005,
            "beta": 1.2,
            "shortName": "Apple Inc.",
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }
        mock_ticker = MagicMock()
        mock_ticker.info = mock_info
        mock_yf.Ticker.return_value = mock_ticker

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_data.clear()

        result = price_data.get_price_data("AAPL")

        assert "error" not in result
        assert result["price"] == 150.50
        assert result["change"] == 2.50
        assert result["change_pct"] == 1.69
        assert result["market_cap"] == 2500000000000
        assert result["sector"] == "Technology"

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_returns_error_for_invalid_ticker(self, monkeypatch):
        """Should return error for ticker with no data."""
        from dashboard.utils import price_data

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": None}
        mock_yf.Ticker.return_value = mock_ticker

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_data.clear()

        result = price_data.get_price_data("INVALIDTICKER")

        assert "error" in result
        assert "No data found" in result["error"]

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_returns_error_on_exception(self, monkeypatch):
        """Should return error dict on exception."""
        from dashboard.utils import price_data

        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = Exception("Network error")

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_data.clear()

        result = price_data.get_price_data("AAPL")

        assert "error" in result
        assert "Network error" in result["error"]

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_includes_fetched_at_timestamp(self, monkeypatch):
        """Should include fetched_at timestamp in result."""
        from dashboard.utils import price_data

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 100.0}
        mock_yf.Ticker.return_value = mock_ticker

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_data.clear()

        result = price_data.get_price_data("TEST")

        assert "fetched_at" in result
        # Verify it's a valid ISO format
        datetime.fromisoformat(result["fetched_at"])


class TestGetPriceHistory:
    """Tests for get_price_history()."""

    def test_returns_error_when_yfinance_unavailable(self, monkeypatch):
        """Should return error when yfinance not installed."""
        from dashboard.utils import price_data

        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", False)
        price_data.get_price_history.clear()

        result = price_data.get_price_history("AAPL")

        assert "error" in result
        assert "yfinance not installed" in result["error"]

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_returns_history_for_valid_ticker(self, monkeypatch):
        """Should return historical data for valid ticker."""
        from dashboard.utils import price_data

        # Create mock DataFrame with price history
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        mock_hist = pd.DataFrame(
            {
                "Open": [100 + i for i in range(30)],
                "High": [105 + i for i in range(30)],
                "Low": [95 + i for i in range(30)],
                "Close": [102 + i for i in range(30)],
                "Volume": [1000000] * 30,
            },
            index=dates,
        )

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_hist
        mock_yf.Ticker.return_value = mock_ticker

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_history.clear()

        result = price_data.get_price_history("AAPL", period="1mo")

        assert "error" not in result
        assert "dates" in result
        assert "prices" in result
        assert "volumes" in result
        assert len(result["dates"]) == 30
        assert len(result["prices"]) == 30

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_returns_error_for_empty_history(self, monkeypatch):
        """Should return error when no history found."""
        from dashboard.utils import price_data

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_history.clear()

        result = price_data.get_price_history("INVALIDTICKER")

        assert "error" in result
        assert "No history found" in result["error"]

    @pytest.mark.skipif(not YFINANCE_INSTALLED, reason="yfinance not installed")
    def test_calculates_returns(self, monkeypatch):
        """Should calculate return values."""
        from dashboard.utils import price_data

        # Create mock with enough data for return calculations
        dates = pd.date_range(end=datetime.now(), periods=260, freq="D")
        mock_hist = pd.DataFrame(
            {
                "Open": [100] * 260,
                "High": [105] * 260,
                "Low": [95] * 260,
                "Close": [100 + i * 0.1 for i in range(260)],  # Steadily increasing
                "Volume": [1000000] * 260,
            },
            index=dates,
        )

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_hist
        mock_yf.Ticker.return_value = mock_ticker

        monkeypatch.setattr(price_data, "yf", mock_yf)
        monkeypatch.setattr(price_data, "YFINANCE_AVAILABLE", True)
        price_data.get_price_history.clear()

        result = price_data.get_price_history("AAPL")

        assert "returns_1d" in result
        assert "returns_1w" in result
        assert "returns_1m" in result
        assert "returns_3m" in result
        assert "returns_1y" in result


class TestCalcReturn:
    """Tests for _calc_return()."""

    def test_calculates_positive_return(self):
        """Should calculate positive return correctly."""
        from dashboard.utils.price_data import _calc_return

        dates = pd.date_range(end=datetime.now(), periods=10, freq="D")
        hist = pd.DataFrame({"Close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 110]}, index=dates)

        result = _calc_return(hist, 5)

        assert result is not None
        assert result > 0  # 110 vs 104 = positive return

    def test_calculates_negative_return(self):
        """Should calculate negative return correctly."""
        from dashboard.utils.price_data import _calc_return

        dates = pd.date_range(end=datetime.now(), periods=10, freq="D")
        hist = pd.DataFrame({"Close": [110, 108, 106, 104, 102, 100, 98, 96, 94, 90]}, index=dates)

        result = _calc_return(hist, 5)

        assert result is not None
        assert result < 0  # 90 vs 100 = negative return

    def test_returns_none_for_insufficient_data(self):
        """Should return None when not enough data points."""
        from dashboard.utils.price_data import _calc_return

        dates = pd.date_range(end=datetime.now(), periods=5, freq="D")
        hist = pd.DataFrame({"Close": [100, 101, 102, 103, 104]}, index=dates)

        result = _calc_return(hist, 10)  # Need 11 points, only have 5

        assert result is None


class TestFormatLargeNumber:
    """Tests for format_large_number()."""

    def test_formats_trillions(self):
        """Should format trillions correctly."""
        from dashboard.utils.price_data import format_large_number

        assert format_large_number(2.5e12) == "$2.5T"
        assert format_large_number(1.0e12) == "$1.0T"

    def test_formats_billions(self):
        """Should format billions correctly."""
        from dashboard.utils.price_data import format_large_number

        assert format_large_number(250e9) == "$250.0B"
        assert format_large_number(1.5e9) == "$1.5B"

    def test_formats_millions(self):
        """Should format millions correctly."""
        from dashboard.utils.price_data import format_large_number

        assert format_large_number(50e6) == "$50.0M"
        assert format_large_number(1.2e6) == "$1.2M"

    def test_formats_thousands(self):
        """Should format thousands correctly."""
        from dashboard.utils.price_data import format_large_number

        assert format_large_number(500e3) == "$500.0K"
        assert format_large_number(1.5e3) == "$1.5K"

    def test_formats_small_numbers(self):
        """Should format small numbers without suffix."""
        from dashboard.utils.price_data import format_large_number

        assert format_large_number(500) == "$500"
        assert format_large_number(99) == "$99"

    def test_returns_na_for_none(self):
        """Should return N/A for None."""
        from dashboard.utils.price_data import format_large_number

        assert format_large_number(None) == "N/A"


class TestFormatPercentage:
    """Tests for format_percentage()."""

    def test_formats_positive_with_sign(self):
        """Should format positive percentage with plus sign."""
        from dashboard.utils.price_data import format_percentage

        assert format_percentage(5.25) == "+5.25%"
        assert format_percentage(0.5) == "+0.50%"

    def test_formats_negative_with_sign(self):
        """Should format negative percentage with minus sign."""
        from dashboard.utils.price_data import format_percentage

        assert format_percentage(-3.5) == "-3.50%"
        assert format_percentage(-0.1) == "-0.10%"

    def test_formats_zero_with_sign(self):
        """Should format zero as positive."""
        from dashboard.utils.price_data import format_percentage

        assert format_percentage(0) == "+0.00%"

    def test_formats_without_sign(self):
        """Should format without sign when include_sign=False."""
        from dashboard.utils.price_data import format_percentage

        assert format_percentage(5.25, include_sign=False) == "5.25%"
        assert format_percentage(-3.5, include_sign=False) == "-3.50%"

    def test_returns_na_for_none(self):
        """Should return N/A for None."""
        from dashboard.utils.price_data import format_percentage

        assert format_percentage(None) == "N/A"
        assert format_percentage(None, include_sign=False) == "N/A"
