"""Tests for PortfolioManager business logic."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from asymmetric.core.portfolio.manager import PortfolioManager
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock, StockScore
from asymmetric.db.portfolio_models import Holding, Transaction


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def manager():
    """Create PortfolioManager instance."""
    return PortfolioManager()


@pytest.fixture
def stock_aapl():
    """Create AAPL stock for testing."""
    with get_session() as session:
        stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
        session.add(stock)
        session.commit()
        return stock.ticker


@pytest.fixture
def stock_msft():
    """Create MSFT stock for testing."""
    with get_session() as session:
        stock = Stock(ticker="MSFT", cik="0000789019", company_name="Microsoft Corp")
        session.add(stock)
        session.commit()
        return stock.ticker


@pytest.fixture
def stock_with_score():
    """Create a stock with an F-Score and Z-Score."""
    with get_session() as session:
        stock = Stock(ticker="GOOG", cik="0001652044", company_name="Alphabet Inc.")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        score = StockScore(
            stock_id=stock.id,
            piotroski_score=8,
            altman_z_score=4.5,
            altman_zone="Safe",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score)
        session.commit()

        return stock.ticker


class TestAddBuy:
    """Tests for buy transaction recording."""

    def test_add_buy_creates_holding(self, manager, stock_aapl):
        """Test that adding a buy creates a new holding."""
        transaction = manager.add_buy(
            ticker=stock_aapl,
            quantity=100,
            price_per_share=150.00,
        )

        assert transaction.id is not None
        assert transaction.transaction_type == "buy"
        assert transaction.quantity == 100
        assert transaction.price_per_share == 150.00
        assert transaction.total_cost == 15000.00

        # Check holding was created
        holding = manager.get_holding(stock_aapl)
        assert holding is not None
        assert holding.quantity == 100
        assert holding.cost_basis_total == 15000.00

    def test_add_buy_with_fees(self, manager, stock_aapl):
        """Test that fees are included in cost basis."""
        manager.add_buy(
            ticker=stock_aapl,
            quantity=100,
            price_per_share=150.00,
            fees=10.00,
        )

        holding = manager.get_holding(stock_aapl)
        assert holding.cost_basis_total == 15010.00
        assert holding.cost_basis_per_share == pytest.approx(150.10, rel=0.01)

    def test_add_buy_updates_existing_holding(self, manager, stock_aapl):
        """Test that buying more shares updates existing holding."""
        # First buy
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)

        # Second buy at different price
        manager.add_buy(ticker=stock_aapl, quantity=50, price_per_share=160.00)

        holding = manager.get_holding(stock_aapl)
        assert holding.quantity == 150
        assert holding.cost_basis_total == 23000.00  # 15000 + 8000
        assert holding.cost_basis_per_share == pytest.approx(153.33, rel=0.01)

    def test_add_buy_stock_not_found(self, manager):
        """Test buying non-existent stock raises error."""
        with pytest.raises(ValueError, match="Stock .* not found"):
            manager.add_buy(ticker="NOTEXIST", quantity=100, price_per_share=100.00)

    def test_add_buy_invalid_quantity(self, manager, stock_aapl):
        """Test buying zero or negative quantity raises error."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            manager.add_buy(ticker=stock_aapl, quantity=0, price_per_share=100.00)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            manager.add_buy(ticker=stock_aapl, quantity=-10, price_per_share=100.00)

    def test_add_buy_invalid_price(self, manager, stock_aapl):
        """Test buying at zero or negative price raises error."""
        with pytest.raises(ValueError, match="Price must be positive"):
            manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=0)

        with pytest.raises(ValueError, match="Price must be positive"):
            manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=-50)

    def test_add_buy_with_date(self, manager, stock_aapl):
        """Test buying with specific date."""
        specific_date = datetime(2023, 6, 15, tzinfo=timezone.utc)
        transaction = manager.add_buy(
            ticker=stock_aapl,
            quantity=100,
            price_per_share=150.00,
            transaction_date=specific_date,
        )

        # SQLite doesn't preserve timezone info, so compare datetime parts only
        assert transaction.transaction_date.year == specific_date.year
        assert transaction.transaction_date.month == specific_date.month
        assert transaction.transaction_date.day == specific_date.day


class TestAddSell:
    """Tests for sell transaction recording."""

    def test_add_sell_reduces_holding(self, manager, stock_aapl):
        """Test that selling reduces holding quantity."""
        # Buy first
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)

        # Sell some
        transaction = manager.add_sell(
            ticker=stock_aapl,
            quantity=30,
            price_per_share=180.00,
        )

        assert transaction.transaction_type == "sell"
        assert transaction.quantity == -30  # Negative for sells

        holding = manager.get_holding(stock_aapl)
        assert holding.quantity == 70

    def test_add_sell_fifo_cost_basis(self, manager, stock_aapl):
        """Test FIFO cost basis calculation on sale."""
        # Buy at $150
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)

        # Sell at $180
        transaction = manager.add_sell(
            ticker=stock_aapl,
            quantity=50,
            price_per_share=180.00,
        )

        # Cost basis should be $150 per share (FIFO)
        assert transaction.cost_basis_per_share == 150.00
        # Realized gain = (180 - 150) * 50 = 1500
        assert transaction.realized_gain == pytest.approx(1500.00, rel=0.01)

    def test_add_sell_closes_position(self, manager, stock_aapl):
        """Test selling all shares closes the position."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)

        manager.add_sell(ticker=stock_aapl, quantity=100, price_per_share=180.00)

        holding = manager.get_holding(stock_aapl)
        assert holding is None

    def test_add_sell_insufficient_shares(self, manager, stock_aapl):
        """Test selling more than owned raises error."""
        manager.add_buy(ticker=stock_aapl, quantity=50, price_per_share=150.00)

        with pytest.raises(ValueError, match="Insufficient shares"):
            manager.add_sell(ticker=stock_aapl, quantity=100, price_per_share=180.00)

    def test_add_sell_no_position(self, manager, stock_aapl):
        """Test selling without position raises error."""
        with pytest.raises(ValueError, match="Insufficient shares"):
            manager.add_sell(ticker=stock_aapl, quantity=10, price_per_share=180.00)

    def test_add_sell_with_fees(self, manager, stock_aapl):
        """Test that fees are deducted from proceeds."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)

        transaction = manager.add_sell(
            ticker=stock_aapl,
            quantity=50,
            price_per_share=180.00,
            fees=10.00,
        )

        # Proceeds = (50 * 180) - 10 = 8990
        assert transaction.total_proceeds == 8990.00


class TestGetHoldings:
    """Tests for holdings retrieval."""

    def test_get_holdings_empty(self, manager):
        """Test getting holdings when none exist."""
        holdings = manager.get_holdings()
        assert holdings == []

    def test_get_holdings_sorted_by_value(self, manager, stock_aapl, stock_msft):
        """Test holdings are sorted by value by default."""
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=150.00)  # $1500
        manager.add_buy(ticker=stock_msft, quantity=100, price_per_share=300.00)  # $30000

        holdings = manager.get_holdings(sort_by="value")

        assert len(holdings) == 2
        assert holdings[0].ticker == "MSFT"  # Higher value first
        assert holdings[1].ticker == "AAPL"

    def test_get_holdings_sorted_by_ticker(self, manager, stock_aapl, stock_msft):
        """Test holdings sorted alphabetically by ticker."""
        manager.add_buy(ticker=stock_msft, quantity=100, price_per_share=300.00)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=150.00)

        holdings = manager.get_holdings(sort_by="ticker")

        assert holdings[0].ticker == "AAPL"
        assert holdings[1].ticker == "MSFT"

    def test_get_holdings_includes_scores(self, manager, stock_with_score):
        """Test holdings include score data when available."""
        manager.add_buy(ticker=stock_with_score, quantity=50, price_per_share=100.00)

        holdings = manager.get_holdings()

        assert len(holdings) == 1
        assert holdings[0].fscore == 8
        assert holdings[0].zscore == 4.5
        assert holdings[0].zone == "Safe"

    def test_get_holdings_allocation_percent(self, manager, stock_aapl, stock_msft):
        """Test allocation percentages are calculated."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=100.00)  # $10000
        manager.add_buy(ticker=stock_msft, quantity=100, price_per_share=100.00)  # $10000

        holdings = manager.get_holdings()

        # Each should be 50%
        for h in holdings:
            assert h.allocation_percent == pytest.approx(50.0, rel=0.01)


class TestPortfolioSummary:
    """Tests for portfolio summary."""

    def test_get_portfolio_summary_empty(self, manager):
        """Test summary when portfolio is empty."""
        summary = manager.get_portfolio_summary()

        assert summary.position_count == 0
        assert summary.total_cost_basis == 0.0

    def test_get_portfolio_summary_with_positions(self, manager, stock_aapl, stock_msft):
        """Test summary with multiple positions."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)
        manager.add_buy(ticker=stock_msft, quantity=50, price_per_share=300.00)

        summary = manager.get_portfolio_summary()

        assert summary.position_count == 2
        assert summary.total_cost_basis == 30000.00  # 15000 + 15000
        assert summary.cash_invested == 30000.00

    def test_get_portfolio_summary_realized_pnl(self, manager, stock_aapl):
        """Test realized P&L in summary."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)
        manager.add_sell(ticker=stock_aapl, quantity=50, price_per_share=200.00)

        summary = manager.get_portfolio_summary()

        # Realized gain = (200 - 150) * 50 = 2500
        assert summary.realized_pnl_total == pytest.approx(2500.00, rel=0.01)


class TestTransactionHistory:
    """Tests for transaction history."""

    def test_get_transaction_history(self, manager, stock_aapl):
        """Test getting transaction history."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)
        manager.add_sell(ticker=stock_aapl, quantity=50, price_per_share=180.00)

        history = manager.get_transaction_history()

        assert len(history) == 2
        # Most recent first
        assert history[0].transaction_type == "sell"
        assert history[1].transaction_type == "buy"

    def test_get_transaction_history_filter_ticker(self, manager, stock_aapl, stock_msft):
        """Test filtering transaction history by ticker."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)
        manager.add_buy(ticker=stock_msft, quantity=50, price_per_share=300.00)

        history = manager.get_transaction_history(ticker=stock_aapl)

        assert len(history) == 1
        assert history[0].ticker == "AAPL"


class TestWeightedScores:
    """Tests for portfolio-weighted scores."""

    def test_get_weighted_scores_empty(self, manager):
        """Test weighted scores with empty portfolio."""
        scores = manager.get_weighted_scores()

        assert scores.holdings_with_scores == 0
        assert scores.holdings_without_scores == 0

    def test_get_weighted_scores_single_holding(self, manager, stock_with_score):
        """Test weighted scores with single holding."""
        manager.add_buy(ticker=stock_with_score, quantity=100, price_per_share=100.00)

        scores = manager.get_weighted_scores()

        assert scores.holdings_with_scores == 1
        assert scores.weighted_fscore == 8.0
        assert scores.weighted_zscore == 4.5
        assert scores.safe_allocation == 100.0

    def test_get_weighted_scores_no_scores(self, manager, stock_aapl):
        """Test weighted scores when holdings have no scores."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150.00)

        scores = manager.get_weighted_scores()

        assert scores.holdings_with_scores == 0
        assert scores.holdings_without_scores == 1
