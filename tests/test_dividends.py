"""Tests for dividend recording and sync functionality."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from asymmetric.core.portfolio.manager import PortfolioManager
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from asymmetric.db.portfolio_models import Holding, Transaction


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def manager():
    return PortfolioManager()


@pytest.fixture
def stock_aapl():
    with get_session() as session:
        stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
        session.add(stock)
    return "AAPL"


@pytest.fixture
def stock_msft():
    with get_session() as session:
        stock = Stock(ticker="MSFT", cik="0000789019", company_name="Microsoft Corporation")
        session.add(stock)
    return "MSFT"


class TestAddDividend:
    def test_add_dividend_creates_transaction(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        txn = manager.add_dividend(ticker="AAPL", total_amount=25.50)

        assert txn.id is not None
        assert txn.transaction_type == "dividend"
        assert txn.total_proceeds == Decimal("25.50")
        assert txn.quantity == Decimal("0")
        assert txn.price_per_share == Decimal("0")

    def test_add_dividend_with_date(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        pay_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        txn = manager.add_dividend(ticker="AAPL", total_amount=50, pay_date=pay_date)

        assert txn.transaction_date.month == 1
        assert txn.transaction_date.day == 15

    def test_add_dividend_with_notes(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        txn = manager.add_dividend(ticker="AAPL", total_amount=25, notes="Q4 2025 dividend")

        assert txn.notes == "Q4 2025 dividend"

    def test_add_dividend_nonexistent_ticker(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.add_dividend(ticker="FAKE", total_amount=25)

    def test_add_dividend_invalid_amount(self, manager, stock_aapl):
        with pytest.raises(ValueError, match="must be positive"):
            manager.add_dividend(ticker="AAPL", total_amount=0)

    def test_add_dividend_negative_amount(self, manager, stock_aapl):
        with pytest.raises(ValueError, match="must be positive"):
            manager.add_dividend(ticker="AAPL", total_amount=-10)

    def test_dividend_does_not_change_holding(self, manager, stock_aapl):
        """Dividends should not affect holding quantity or cost basis."""
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)

        holding_before = manager.get_holding("AAPL")
        manager.add_dividend(ticker="AAPL", total_amount=25)
        holding_after = manager.get_holding("AAPL")

        assert holding_after.quantity == holding_before.quantity
        assert holding_after.cost_basis_total == holding_before.cost_basis_total


class TestDividendInHistory:
    def test_dividend_appears_in_transaction_history(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        manager.add_dividend(ticker="AAPL", total_amount=25)

        history = manager.get_transaction_history()
        div_txns = [t for t in history if t.transaction_type == "dividend"]
        assert len(div_txns) == 1
        assert div_txns[0].total_proceeds == pytest.approx(25.0)

    def test_dividend_in_ticker_filtered_history(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        manager.add_dividend(ticker="AAPL", total_amount=25)

        history = manager.get_transaction_history(ticker="AAPL")
        assert any(t.transaction_type == "dividend" for t in history)


class TestPortfolioSummaryDividends:
    def test_summary_total_dividends(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        manager.add_dividend(ticker="AAPL", total_amount=25)
        manager.add_dividend(ticker="AAPL", total_amount=30)

        summary = manager.get_portfolio_summary(include_market_data=False)
        assert summary.total_dividends == pytest.approx(55.0)

    def test_summary_no_dividends(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)

        summary = manager.get_portfolio_summary(include_market_data=False)
        assert summary.total_dividends == 0.0


class TestSyncDividends:
    def test_sync_dividends_mock(self, manager, stock_aapl):
        """Sync should create transactions from yfinance dividend data."""
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)

        mock_divs = [
            {"date": "2026-01-15", "amount_per_share": 0.25},
            {"date": "2026-02-15", "amount_per_share": 0.25},
        ]

        with patch("asymmetric.core.portfolio.manager.fetch_dividend_history", return_value=mock_divs):
            result = manager.sync_dividends(ticker="AAPL")

        assert result["synced"] == 2
        assert "AAPL" in result["tickers"]

        # Verify transactions created
        history = manager.get_transaction_history(ticker="AAPL")
        div_txns = [t for t in history if t.transaction_type == "dividend"]
        assert len(div_txns) == 2
        # 100 shares * $0.25 = $25.00 each
        assert all(t.total_proceeds == pytest.approx(25.0) for t in div_txns)

    def test_sync_dividends_no_duplicates(self, manager, stock_aapl):
        """Re-syncing should not duplicate existing dividends."""
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)

        mock_divs = [{"date": "2026-01-15", "amount_per_share": 0.25}]

        with patch("asymmetric.core.portfolio.manager.fetch_dividend_history", return_value=mock_divs):
            result1 = manager.sync_dividends(ticker="AAPL")
            assert result1["synced"] == 1

        # Second sync — the start_date filter should exclude already-synced dates
        with patch("asymmetric.core.portfolio.manager.fetch_dividend_history", return_value=[]):
            result2 = manager.sync_dividends(ticker="AAPL")
            assert result2["synced"] == 0

    def test_sync_dividends_no_holding(self, manager, stock_aapl):
        """Sync should report error for ticker without open holding."""
        # Stock exists but no holding
        result = manager.sync_dividends(ticker="AAPL")
        assert result["synced"] == 0
        assert any("no open holding" in err for err in result["errors"])

    def test_sync_dividends_nonexistent_ticker(self, manager):
        """Sync should report error for non-existent ticker."""
        result = manager.sync_dividends(ticker="FAKE")
        assert result["synced"] == 0
        assert len(result["errors"]) > 0

    def test_sync_all_holdings(self, manager, stock_aapl, stock_msft):
        """Sync with no ticker should sync all open holdings."""
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)
        manager.add_buy(ticker="MSFT", quantity=50, price_per_share=300)

        mock_divs = [{"date": "2026-01-15", "amount_per_share": 0.50}]

        with patch("asymmetric.core.portfolio.manager.fetch_dividend_history", return_value=mock_divs):
            result = manager.sync_dividends()

        assert result["synced"] == 2
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]

    def test_sync_dividends_yfinance_unavailable(self, manager, stock_aapl):
        """Should handle yfinance being unavailable gracefully."""
        manager.add_buy(ticker="AAPL", quantity=100, price_per_share=150)

        with patch("asymmetric.core.portfolio.manager.PRICE_DATA_AVAILABLE", False):
            result = manager.sync_dividends(ticker="AAPL")

        assert result["synced"] == 0
        assert "yfinance not available" in result["errors"]
