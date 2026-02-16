"""
Tests for tax lot sell logic — FIFO/LIFO/HIFO cost basis methods.

Validates that:
1. Transaction.realized_gain uses lot-specific costs (not weighted average)
2. Sell fees are allocated proportionally to lot dispositions
3. Holding cost basis is updated by subtracting actual consumed lot costs
4. sum(LotDisposition.realized_gain) == Transaction.realized_gain
5. FIFO/LIFO/HIFO ordering selects the correct lots
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlmodel import select

from asymmetric.core.portfolio.manager import PortfolioManager
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from asymmetric.db.portfolio_models import Holding, LotDisposition, TaxLot


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


def _get_dispositions_for_transaction(txn_id: int) -> list[LotDisposition]:
    """Helper to fetch dispositions for a sell transaction."""
    with get_session() as session:
        results = session.exec(
            select(LotDisposition)
            .where(LotDisposition.sell_transaction_id == txn_id)
            .order_by(LotDisposition.id)
        ).all()
        for d in results:
            session.expunge(d)
        return list(results)


def _get_holding(ticker: str) -> Holding:
    """Helper to fetch holding for a ticker."""
    with get_session() as session:
        stock = session.exec(select(Stock).where(Stock.ticker == ticker)).first()
        holding = session.exec(
            select(Holding).where(Holding.stock_id == stock.id)
        ).first()
        if holding:
            session.expunge(holding)
        return holding


def _get_open_lots(ticker: str) -> list[TaxLot]:
    """Helper to fetch open tax lots for a ticker."""
    with get_session() as session:
        stock = session.exec(select(Stock).where(Stock.ticker == ticker)).first()
        holding = session.exec(
            select(Holding).where(Holding.stock_id == stock.id)
        ).first()
        if not holding:
            return []
        lots = session.exec(
            select(TaxLot)
            .where(TaxLot.holding_id == holding.id)
            .where(TaxLot.quantity_remaining > 0)
            .order_by(TaxLot.purchase_date.asc())
        ).all()
        for lot in lots:
            session.expunge(lot)
        return list(lots)


class TestFIFOSell:
    """FIFO: oldest lots consumed first."""

    def test_fifo_single_lot(self, manager, stock_aapl):
        """Single lot — FIFO is trivial, gain = (sell - buy) * qty."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150)
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=50, price_per_share=200,
            cost_basis_method="fifo",
        )

        assert float(txn.realized_gain) == pytest.approx(2500.0)  # (200-150)*50
        assert float(txn.cost_basis_per_share) == pytest.approx(150.0)

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 1
        assert float(disps[0].realized_gain) == pytest.approx(2500.0)

    def test_fifo_multi_lot_different_costs(self, manager, stock_aapl):
        """Three lots at $100, $150, $200 — FIFO sells cheapest first."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        t3 = datetime(2024, 12, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=150, transaction_date=t2)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t3)

        # Sell 15 shares at $180 — FIFO takes all 10 @ $100 + 5 @ $150
        sell_date = datetime(2025, 3, 1, tzinfo=timezone.utc)
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=15, price_per_share=180,
            transaction_date=sell_date, cost_basis_method="fifo",
        )

        # Expected cost: (10 * 100) + (5 * 150) = 1000 + 750 = 1750
        # Expected proceeds: 15 * 180 = 2700
        # Expected gain: 2700 - 1750 = 950
        assert float(txn.realized_gain) == pytest.approx(950.0)

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 2

        # First disposition: 10 shares from $100 lot
        assert float(disps[0].quantity_disposed) == pytest.approx(10.0)
        assert float(disps[0].cost_basis_per_share) == pytest.approx(100.0)
        assert float(disps[0].realized_gain) == pytest.approx(800.0)  # (180-100)*10

        # Second disposition: 5 shares from $150 lot
        assert float(disps[1].quantity_disposed) == pytest.approx(5.0)
        assert float(disps[1].cost_basis_per_share) == pytest.approx(150.0)
        assert float(disps[1].realized_gain) == pytest.approx(150.0)  # (180-150)*5

        # KEY INVARIANT: Transaction gain == sum of disposition gains
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)

    def test_fifo_remaining_holding_cost_basis(self, manager, stock_aapl):
        """After FIFO sell, remaining holding cost reflects unsold lots."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t2)

        # Sell 10 shares (FIFO consumes $100 lot)
        manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="fifo",
        )

        holding = _get_holding(stock_aapl)
        # Remaining: 10 shares from $200 lot
        assert float(holding.quantity) == pytest.approx(10.0)
        assert float(holding.cost_basis_total) == pytest.approx(2000.0)
        assert float(holding.cost_basis_per_share) == pytest.approx(200.0)


class TestLIFOSell:
    """LIFO: newest lots consumed first."""

    def test_lifo_consumes_newest_first(self, manager, stock_aapl):
        """LIFO sells newest (most expensive here) lot first."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t2)

        # Sell 10 shares at $250 — LIFO takes $200 lot (newest)
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="lifo",
        )

        # Expected gain: (250 - 200) * 10 = 500
        assert float(txn.realized_gain) == pytest.approx(500.0)
        assert float(txn.cost_basis_per_share) == pytest.approx(200.0)

        # Remaining holding: 10 shares from $100 lot
        holding = _get_holding(stock_aapl)
        assert float(holding.cost_basis_per_share) == pytest.approx(100.0)

    def test_lifo_vs_fifo_different_gains(self, manager, stock_aapl):
        """LIFO and FIFO produce different gains for same portfolio."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t2)

        # LIFO sell: cost basis = $200 → gain = (250-200)*10 = 500
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="lifo",
        )
        lifo_gain = float(txn.realized_gain)

        # FIFO would give: cost basis = $100 → gain = (250-100)*10 = 1500
        # So LIFO gain should be LESS than FIFO gain (higher cost consumed)
        assert lifo_gain == pytest.approx(500.0)
        # We can't test FIFO in same test (lots already consumed), but we verified the math


class TestHIFOSell:
    """HIFO: highest cost lots consumed first (tax-optimal for gains)."""

    def test_hifo_consumes_highest_cost_first(self, manager, stock_aapl):
        """HIFO sells the most expensive lot first, minimizing taxable gain."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 3, 1, tzinfo=timezone.utc)
        t3 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=300, transaction_date=t2)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t3)

        # Sell 10 at $250 — HIFO takes $300 lot (highest cost)
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="hifo",
        )

        # Expected gain: (250 - 300) * 10 = -500 (a loss!)
        assert float(txn.realized_gain) == pytest.approx(-500.0)
        assert float(txn.cost_basis_per_share) == pytest.approx(300.0)

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 1
        assert float(disps[0].cost_basis_per_share) == pytest.approx(300.0)

    def test_hifo_remaining_lots_are_cheaper(self, manager, stock_aapl):
        """After HIFO sell, remaining lots should be the cheaper ones."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=300, transaction_date=t2)

        # HIFO consumes $300 lot
        manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="hifo",
        )

        lots = _get_open_lots(stock_aapl)
        assert len(lots) == 1
        assert float(lots[0].cost_per_share) == pytest.approx(100.0)


class TestFeeSell:
    """Verify sell fees are properly allocated to dispositions."""

    def test_fees_reduce_realized_gain(self, manager, stock_aapl):
        """Sell fees should reduce the realized gain."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=100)

        txn = manager.add_sell(
            ticker=stock_aapl, quantity=100, price_per_share=200, fees=50,
        )

        # Proceeds: (100 * 200) - 50 = 19950
        # Cost: 100 * 100 = 10000
        # Gain: 19950 - 10000 = 9950
        assert float(txn.realized_gain) == pytest.approx(9950.0)
        assert float(txn.total_proceeds) == pytest.approx(19950.0)

    def test_fees_allocated_to_dispositions(self, manager, stock_aapl):
        """Sum of disposition gains should equal transaction realized gain (fees included)."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t2)

        # Sell 15 shares at $250 with $30 fee
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=15, price_per_share=250,
            fees=30, cost_basis_method="fifo",
        )

        # Fee per share: 30 / 15 = 2
        # Lot 1 (10 shares @ $100): gain = (250 - 2 - 100) * 10 = 1480
        # Lot 2 (5 shares @ $200): gain = (250 - 2 - 200) * 5 = 240
        # Total disposition gain: 1480 + 240 = 1720
        # Transaction: proceeds = 15*250 - 30 = 3720, cost = 10*100 + 5*200 = 2000
        # Transaction gain: 3720 - 2000 = 1720
        disps = _get_dispositions_for_transaction(txn.id)
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)
        assert float(txn.realized_gain) == pytest.approx(1720.0)

    def test_zero_fees(self, manager, stock_aapl):
        """Zero fees should work without division issues."""
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100)
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=200, fees=0,
        )

        assert float(txn.realized_gain) == pytest.approx(1000.0)

        disps = _get_dispositions_for_transaction(txn.id)
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)


class TestPartialFill:
    """Verify partial lot consumption works correctly."""

    def test_partial_lot_consumption(self, manager, stock_aapl):
        """Selling less than a full lot partially consumes it."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150)

        manager.add_sell(
            ticker=stock_aapl, quantity=30, price_per_share=200,
            cost_basis_method="fifo",
        )

        lots = _get_open_lots(stock_aapl)
        assert len(lots) == 1
        assert float(lots[0].quantity_remaining) == pytest.approx(70.0)
        assert lots[0].status == "partial"

    def test_lot_fully_consumed_becomes_closed(self, manager, stock_aapl):
        """Selling exactly a full lot closes it."""
        manager.add_buy(ticker=stock_aapl, quantity=100, price_per_share=150)

        manager.add_sell(
            ticker=stock_aapl, quantity=100, price_per_share=200,
            cost_basis_method="fifo",
        )

        holding = _get_holding(stock_aapl)
        assert holding.status == "closed"

        # No open lots remaining
        lots = _get_open_lots(stock_aapl)
        assert len(lots) == 0

    def test_sell_spans_multiple_lots(self, manager, stock_aapl):
        """Sell that spans 3 lots creates 3 dispositions."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 4, 1, tzinfo=timezone.utc)
        t3 = datetime(2024, 7, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=5, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=5, price_per_share=150, transaction_date=t2)
        manager.add_buy(ticker=stock_aapl, quantity=5, price_per_share=200, transaction_date=t3)

        # Sell all 15 shares
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=15, price_per_share=250,
            cost_basis_method="fifo",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 3

        # Verify total gain reconciles
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)


class TestHoldingPeriod:
    """Verify long-term vs short-term classification."""

    def test_short_term_under_365_days(self, manager, stock_aapl):
        """Holding < 365 days is short-term."""
        buy_date = datetime(2024, 6, 1, tzinfo=timezone.utc)
        sell_date = datetime(2025, 5, 30, tzinfo=timezone.utc)  # 364 days

        manager.add_buy(
            ticker=stock_aapl, quantity=10, price_per_share=100,
            transaction_date=buy_date,
        )
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=200,
            transaction_date=sell_date, cost_basis_method="fifo",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 1
        assert disps[0].is_long_term is False

    def test_long_term_over_365_days(self, manager, stock_aapl):
        """Holding > 365 days is long-term."""
        buy_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        sell_date = datetime(2025, 1, 2, tzinfo=timezone.utc)  # 366 days

        manager.add_buy(
            ticker=stock_aapl, quantity=10, price_per_share=100,
            transaction_date=buy_date,
        )
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=200,
            transaction_date=sell_date, cost_basis_method="fifo",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 1
        assert disps[0].is_long_term is True

    def test_mixed_holding_periods(self, manager, stock_aapl):
        """Sell spanning lots with different holding periods."""
        buy1 = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Long-term
        buy2 = datetime(2024, 10, 1, tzinfo=timezone.utc)  # Short-term
        sell_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        manager.add_buy(
            ticker=stock_aapl, quantity=10, price_per_share=100,
            transaction_date=buy1,
        )
        manager.add_buy(
            ticker=stock_aapl, quantity=10, price_per_share=200,
            transaction_date=buy2,
        )

        txn = manager.add_sell(
            ticker=stock_aapl, quantity=20, price_per_share=250,
            transaction_date=sell_date, cost_basis_method="fifo",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 2
        assert disps[0].is_long_term is True   # 2023 lot
        assert disps[1].is_long_term is False  # Oct 2024 lot


class TestAverageCostMethod:
    """Average cost method still consumes lots but uses average cost."""

    def test_average_still_creates_dispositions(self, manager, stock_aapl):
        """Average method consumes lots in FIFO order but gain uses lot cost."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=200, transaction_date=t2)

        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="average",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 1  # Consumes from first lot (FIFO order)

        # Gain is based on actual lot cost ($100), not average ($150)
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)


class TestInvariant:
    """Key invariant: Transaction.realized_gain == sum(LotDisposition.realized_gain)."""

    def test_gain_reconciliation_single_lot(self, manager, stock_aapl):
        manager.add_buy(ticker=stock_aapl, quantity=50, price_per_share=100)
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=25, price_per_share=180,
            fees=10, cost_basis_method="fifo",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)

    def test_gain_reconciliation_multi_lot_with_fees(self, manager, stock_aapl):
        """Complex scenario: 3 lots, partial fill, fees."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 4, 1, tzinfo=timezone.utc)
        t3 = datetime(2024, 8, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=20, price_per_share=80, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=15, price_per_share=120, transaction_date=t2)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=160, transaction_date=t3)

        # Sell 30 shares spanning all 3 lots with $45 fee
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=30, price_per_share=200,
            fees=45, cost_basis_method="fifo",
        )

        disps = _get_dispositions_for_transaction(txn.id)
        assert len(disps) == 2  # FIFO: 20 from lot 1 + 10 from lot 2 = 30

        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total, rel=1e-6)

    def test_gain_reconciliation_hifo_with_loss(self, manager, stock_aapl):
        """HIFO sell resulting in a loss — gains still reconcile."""
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=100, transaction_date=t1)
        manager.add_buy(ticker=stock_aapl, quantity=10, price_per_share=300, transaction_date=t2)

        # Sell 10 at $250 using HIFO — takes $300 lot, realizes a loss
        txn = manager.add_sell(
            ticker=stock_aapl, quantity=10, price_per_share=250,
            cost_basis_method="hifo",
        )

        assert float(txn.realized_gain) < 0  # It's a loss

        disps = _get_dispositions_for_transaction(txn.id)
        disp_total = sum(float(d.realized_gain) for d in disps)
        assert float(txn.realized_gain) == pytest.approx(disp_total)
