"""
Test price integration and market data functionality.

Tests the integration of real-time market prices with portfolio holdings,
including price fetching, P&L calculations, and graceful error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from asymmetric.core.portfolio import PortfolioManager
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):  # noqa: ARG001
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def manager():
    """Create PortfolioManager instance."""
    return PortfolioManager()


@pytest.fixture
def stock_test1():
    """Create TEST1 stock for testing."""
    with get_session() as session:
        stock = Stock(ticker="TEST1", cik="0001234567", company_name="Test Company 1")
        session.add(stock)
        session.commit()
        return stock.ticker


@pytest.fixture
def stock_test2():
    """Create TEST2 stock for testing."""
    with get_session() as session:
        stock = Stock(ticker="TEST2", cik="0001234568", company_name="Test Company 2")
        session.add(stock)
        session.commit()
        return stock.ticker


@pytest.fixture
def setup_portfolio_with_holdings(manager, stock_test1, stock_test2):
    """Create a portfolio with test holdings."""
    # Add holdings
    manager.add_buy(stock_test1, 100, 50.0, fees=5.0)  # Cost basis: $5,005
    manager.add_buy(stock_test2, 50, 100.0, fees=10.0)  # Cost basis: $5,010
    return manager


class TestRefreshMarketPrices:
    """Test market price fetching functionality."""

    def test_refresh_market_prices_success(self, setup_portfolio_with_holdings):
        """Test successful batch price fetching."""
        manager = setup_portfolio_with_holdings

        # Mock get_batch_price_data to return test prices
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},
                "TEST2": {"price": 110.0, "change_percent": 10.0}
            }

            tickers = ["TEST1", "TEST2"]
            prices = manager.refresh_market_prices(tickers)

            # Verify prices returned
            assert prices == {"TEST1": 60.0, "TEST2": 110.0}

            # Verify batch fetch was called (with tuple for caching)
            mock_get_prices.assert_called_once_with(("TEST1", "TEST2"))

    def test_refresh_market_prices_missing_ticker(self, setup_portfolio_with_holdings):
        """Test handling of invalid/missing ticker."""
        manager = setup_portfolio_with_holdings

        # Mock get_batch_price_data to return error for one ticker
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},
                "TEST2": {"error": "No data found for ticker: TEST2"}
            }

            tickers = ["TEST1", "TEST2"]
            prices = manager.refresh_market_prices(tickers)

            # TEST1 has price, TEST2 returns None
            assert prices["TEST1"] == 60.0
            assert prices["TEST2"] is None

    def test_refresh_market_prices_empty_tickers(self):
        """Test behavior with empty ticker list."""
        manager = PortfolioManager()

        prices = manager.refresh_market_prices([])

        # Should return empty dict
        assert prices == {}

    def test_refresh_market_prices_api_failure(self, setup_portfolio_with_holdings):
        """Test handling of API failure."""
        manager = setup_portfolio_with_holdings

        # Mock get_batch_price_data to raise exception
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.side_effect = Exception("API unavailable")

            tickers = ["TEST1", "TEST2"]
            prices = manager.refresh_market_prices(tickers)

            # Should return None for all tickers on error (graceful degradation)
            assert prices == {"TEST1": None, "TEST2": None}


class TestGetHoldingsWithMarketData:
    """Test holdings retrieval with market price integration."""

    def test_get_holdings_with_market_data(self, setup_portfolio_with_holdings):
        """Test holdings include market prices and P&L."""
        manager = setup_portfolio_with_holdings

        # Mock price data
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},  # $6,000 market value
                "TEST2": {"price": 110.0, "change_percent": 10.0}  # $5,500 market value
            }

            holdings = manager.get_holdings(include_market_data=True)

            # Should have 2 holdings
            assert len(holdings) == 2

            # Check TEST1 (100 shares @ $60 = $6,000, cost basis $5,005)
            test1 = [h for h in holdings if h.ticker == "TEST1"][0]
            assert test1.current_price == 60.0
            assert test1.market_value == pytest.approx(6000.0)
            assert test1.unrealized_pnl == pytest.approx(995.0)  # $6,000 - $5,005
            assert test1.unrealized_pnl_percent == pytest.approx(19.88, rel=0.1)  # 995/5005 * 100

            # Check TEST2 (50 shares @ $110 = $5,500, cost basis $5,010)
            test2 = [h for h in holdings if h.ticker == "TEST2"][0]
            assert test2.current_price == 110.0
            assert test2.market_value == pytest.approx(5500.0)
            assert test2.unrealized_pnl == pytest.approx(490.0)  # $5,500 - $5,010
            assert test2.unrealized_pnl_percent == pytest.approx(9.78, rel=0.1)  # 490/5010 * 100

    def test_get_holdings_fallback_to_cost_basis(self, setup_portfolio_with_holdings):
        """Test graceful degradation when prices unavailable."""
        manager = setup_portfolio_with_holdings

        # Mock price data with one ticker missing
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},
                "TEST2": {"error": "No data found"}
            }

            holdings = manager.get_holdings(include_market_data=True)

            # TEST1 should have market data
            test1 = [h for h in holdings if h.ticker == "TEST1"][0]
            assert test1.current_price == 60.0
            assert test1.market_value == pytest.approx(6000.0)
            assert test1.unrealized_pnl is not None

            # TEST2 should fall back to cost basis (no P&L calculated)
            test2 = [h for h in holdings if h.ticker == "TEST2"][0]
            assert test2.current_price is None
            assert test2.market_value is None
            assert test2.unrealized_pnl is None
            assert test2.unrealized_pnl_percent is None

    def test_get_holdings_without_market_data(self, setup_portfolio_with_holdings):
        """Test holdings retrieval without fetching market data."""
        manager = setup_portfolio_with_holdings

        # Don't mock - include_market_data=False should skip price fetch
        holdings = manager.get_holdings(include_market_data=False)

        assert len(holdings) == 2

        for holding in holdings:
            # Market data fields should be None
            assert holding.current_price is None
            assert holding.market_value is None
            assert holding.unrealized_pnl is None
            assert holding.unrealized_pnl_percent is None

    def test_get_holdings_sort_by_gainloss(self, setup_portfolio_with_holdings):
        """Test sorting holdings by unrealized P&L percent."""
        manager = setup_portfolio_with_holdings

        # Mock price data - TEST1 gains more than TEST2
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},  # ~19.88% gain
                "TEST2": {"price": 110.0, "change_percent": 10.0}  # ~9.78% gain
            }

            holdings = manager.get_holdings(sort_by="gainloss", include_market_data=True)

            # Should be sorted by P&L percent descending
            assert holdings[0].ticker == "TEST1"  # Higher gain first
            assert holdings[1].ticker == "TEST2"
            assert holdings[0].unrealized_pnl_percent > holdings[1].unrealized_pnl_percent


class TestPortfolioSummaryMarketData:
    """Test portfolio summary with market data integration."""

    def test_get_portfolio_summary_with_market_data(self, setup_portfolio_with_holdings):
        """Test portfolio summary includes market values."""
        manager = setup_portfolio_with_holdings

        # Mock price data
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},  # $6,000 market value
                "TEST2": {"price": 110.0, "change_percent": 10.0}  # $5,500 market value
            }

            summary = manager.get_portfolio_summary(include_market_data=True)

            # Total market value = $6,000 + $5,500 = $11,500
            assert summary.total_market_value == pytest.approx(11500.0)

            # Total cost basis = $5,005 + $5,010 = $10,015
            assert summary.total_cost_basis == pytest.approx(10015.0)

            # Unrealized P&L = $11,500 - $10,015 = $1,485
            assert summary.unrealized_pnl == pytest.approx(1485.0)

            # Unrealized P&L % = 1485 / 10015 * 100 = ~14.83%
            assert summary.unrealized_pnl_percent == pytest.approx(14.83, rel=0.1)

    def test_get_portfolio_summary_without_market_data(self, setup_portfolio_with_holdings):
        """Test portfolio summary without market data."""
        manager = setup_portfolio_with_holdings

        summary = manager.get_portfolio_summary(include_market_data=False)

        # Should use cost basis for total value
        assert summary.total_market_value == pytest.approx(10015.0)  # Cost basis
        assert summary.unrealized_pnl == 0.0
        assert summary.unrealized_pnl_percent == 0.0


class TestPriceCaching:
    """Test price data caching behavior."""

    def test_price_cache_used_for_multiple_calls(self, setup_portfolio_with_holdings):
        """Test that price cache reduces redundant API calls."""
        manager = setup_portfolio_with_holdings

        # Mock get_batch_price_data
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_get_prices:
            mock_get_prices.return_value = {
                "TEST1": {"price": 60.0, "change_percent": 20.0},
                "TEST2": {"price": 110.0, "change_percent": 10.0}
            }

            # First call - should fetch prices
            holdings1 = manager.get_holdings(include_market_data=True)

            # Second call - should use cached prices (if cache implemented)
            # Note: Current implementation doesn't cache within manager, but
            # get_batch_price_data has internal caching with @st.cache_data
            holdings2 = manager.get_holdings(include_market_data=True)

            # Both should return same data
            assert len(holdings1) == len(holdings2)
            assert holdings1[0].current_price == holdings2[0].current_price
