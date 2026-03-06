"""Tests for cash flow tracking — deposits, withdrawals, and portfolio summary integration."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from asymmetric.core.portfolio.manager import PortfolioManager
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from asymmetric.db.portfolio_models import CashFlow


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


class TestAddCashFlow:
    def test_add_deposit(self, manager):
        cf = manager.add_cash_flow(amount=5000, flow_type="deposit")
        assert cf.id is not None
        assert cf.flow_type == "deposit"
        assert cf.amount == Decimal("5000")

    def test_add_withdrawal(self, manager):
        cf = manager.add_cash_flow(amount=1000, flow_type="withdrawal")
        assert cf.id is not None
        assert cf.flow_type == "withdrawal"
        assert cf.amount == Decimal("1000")

    def test_add_with_date(self, manager):
        date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        cf = manager.add_cash_flow(amount=3000, flow_type="deposit", flow_date=date)
        assert cf.flow_date.year == 2026
        assert cf.flow_date.month == 1
        assert cf.flow_date.day == 15

    def test_add_with_notes(self, manager):
        cf = manager.add_cash_flow(amount=2000, flow_type="deposit", notes="Initial funding")
        assert cf.notes == "Initial funding"

    def test_add_decimal_amount(self, manager):
        cf = manager.add_cash_flow(amount=Decimal("1234.56"), flow_type="deposit")
        assert cf.amount == Decimal("1234.56")

    def test_invalid_flow_type(self, manager):
        with pytest.raises(ValueError, match="Invalid flow_type"):
            manager.add_cash_flow(amount=100, flow_type="transfer")

    def test_invalid_amount_zero(self, manager):
        with pytest.raises(ValueError, match="Amount must be positive"):
            manager.add_cash_flow(amount=0, flow_type="deposit")

    def test_invalid_amount_negative(self, manager):
        with pytest.raises(ValueError, match="Amount must be positive"):
            manager.add_cash_flow(amount=-100, flow_type="deposit")


class TestGetCashFlows:
    def test_get_cash_flows_empty(self, manager):
        flows = manager.get_cash_flows()
        assert flows == []

    def test_get_cash_flows_ordered(self, manager):
        manager.add_cash_flow(amount=1000, flow_type="deposit",
                              flow_date=datetime(2026, 2, 1, tzinfo=timezone.utc))
        manager.add_cash_flow(amount=500, flow_type="withdrawal",
                              flow_date=datetime(2026, 1, 1, tzinfo=timezone.utc))
        manager.add_cash_flow(amount=2000, flow_type="deposit",
                              flow_date=datetime(2026, 3, 1, tzinfo=timezone.utc))

        flows = manager.get_cash_flows()
        assert len(flows) == 3
        # Should be ascending by date
        assert flows[0].flow_type == "withdrawal"
        assert flows[1].amount == Decimal("1000")
        assert flows[2].amount == Decimal("2000")

    def test_get_cash_flows_date_filter(self, manager):
        manager.add_cash_flow(amount=1000, flow_type="deposit",
                              flow_date=datetime(2026, 1, 1, tzinfo=timezone.utc))
        manager.add_cash_flow(amount=2000, flow_type="deposit",
                              flow_date=datetime(2026, 6, 1, tzinfo=timezone.utc))

        flows = manager.get_cash_flows(
            start_date=datetime(2026, 3, 1),
        )
        assert len(flows) == 1
        assert flows[0].amount == Decimal("2000")

    def test_get_cash_flows_end_date_filter(self, manager):
        manager.add_cash_flow(amount=1000, flow_type="deposit",
                              flow_date=datetime(2026, 1, 1, tzinfo=timezone.utc))
        manager.add_cash_flow(amount=2000, flow_type="deposit",
                              flow_date=datetime(2026, 6, 1, tzinfo=timezone.utc))

        flows = manager.get_cash_flows(
            end_date=datetime(2026, 3, 1),
        )
        assert len(flows) == 1
        assert flows[0].amount == Decimal("1000")


class TestGetTotalCashFlows:
    def test_empty(self, manager):
        totals = manager.get_total_cash_flows()
        assert totals["total_deposits"] == 0.0
        assert totals["total_withdrawals"] == 0.0
        assert totals["net_cash_flow"] == 0.0

    def test_deposits_only(self, manager):
        manager.add_cash_flow(amount=5000, flow_type="deposit")
        manager.add_cash_flow(amount=3000, flow_type="deposit")

        totals = manager.get_total_cash_flows()
        assert totals["total_deposits"] == pytest.approx(8000.0)
        assert totals["total_withdrawals"] == 0.0
        assert totals["net_cash_flow"] == pytest.approx(8000.0)

    def test_mixed_flows(self, manager):
        manager.add_cash_flow(amount=10000, flow_type="deposit")
        manager.add_cash_flow(amount=2000, flow_type="withdrawal")
        manager.add_cash_flow(amount=500, flow_type="withdrawal")

        totals = manager.get_total_cash_flows()
        assert totals["total_deposits"] == pytest.approx(10000.0)
        assert totals["total_withdrawals"] == pytest.approx(2500.0)
        assert totals["net_cash_flow"] == pytest.approx(7500.0)


class TestPortfolioSummaryCashFlows:
    def test_summary_includes_cash_flow_fields(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=10, price_per_share=150)
        manager.add_cash_flow(amount=5000, flow_type="deposit")
        manager.add_cash_flow(amount=1000, flow_type="withdrawal")

        summary = manager.get_portfolio_summary(include_market_data=False)
        assert summary.total_deposits == pytest.approx(5000.0)
        assert summary.total_withdrawals == pytest.approx(1000.0)
        assert summary.net_cash_flow == pytest.approx(4000.0)

    def test_summary_zero_cash_flows(self, manager, stock_aapl):
        manager.add_buy(ticker="AAPL", quantity=10, price_per_share=150)

        summary = manager.get_portfolio_summary(include_market_data=False)
        assert summary.total_deposits == 0.0
        assert summary.total_withdrawals == 0.0
        assert summary.net_cash_flow == 0.0


class TestSnapshotCashFlowOnDate:
    def test_snapshot_no_cash_flow(self, manager, stock_aapl):
        """Snapshot should have cash_flow_on_date = 0 when no flows exist."""
        manager.add_buy(ticker="AAPL", quantity=10, price_per_share=150)
        snapshot = manager.take_snapshot()
        assert float(snapshot.cash_flow_on_date) == pytest.approx(0.0)

    def test_snapshot_with_deposit_today(self, manager, stock_aapl):
        """Snapshot should capture today's cash flow."""
        manager.add_buy(ticker="AAPL", quantity=10, price_per_share=150)
        manager.add_cash_flow(amount=5000, flow_type="deposit")
        snapshot = manager.take_snapshot()
        assert float(snapshot.cash_flow_on_date) == pytest.approx(5000.0)

    def test_snapshot_with_withdrawal_today(self, manager, stock_aapl):
        """Withdrawal should appear as negative cash_flow_on_date."""
        manager.add_buy(ticker="AAPL", quantity=10, price_per_share=150)
        manager.add_cash_flow(amount=1000, flow_type="withdrawal")
        snapshot = manager.take_snapshot()
        assert float(snapshot.cash_flow_on_date) == pytest.approx(-1000.0)

    def test_snapshot_mixed_flows_today(self, manager, stock_aapl):
        """Net of deposits and withdrawals on same day."""
        manager.add_buy(ticker="AAPL", quantity=10, price_per_share=150)
        manager.add_cash_flow(amount=5000, flow_type="deposit")
        manager.add_cash_flow(amount=2000, flow_type="withdrawal")
        snapshot = manager.take_snapshot()
        assert float(snapshot.cash_flow_on_date) == pytest.approx(3000.0)
