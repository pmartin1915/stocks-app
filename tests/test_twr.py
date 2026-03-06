"""Tests for Time-Weighted Return (TWR) calculation."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from asymmetric.core.portfolio.manager import PortfolioManager
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from asymmetric.db.portfolio_models import PortfolioSnapshot


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def manager():
    return PortfolioManager()


def _create_snapshot(date, total_value, cash_flow=0):
    """Helper to create a snapshot directly in the database."""
    with get_session() as session:
        snapshot = PortfolioSnapshot(
            snapshot_date=date,
            total_value=Decimal(str(total_value)),
            total_cost_basis=Decimal(str(total_value)),
            unrealized_pnl=Decimal("0"),
            unrealized_pnl_percent=Decimal("0"),
            realized_pnl_ytd=Decimal("0"),
            realized_pnl_total=Decimal("0"),
            cash_flow_on_date=Decimal(str(cash_flow)),
            position_count=1,
        )
        session.add(snapshot)
        session.flush()
        session.refresh(snapshot)
        session.expunge(snapshot)
        return snapshot


class TestCalculateTWR:
    def test_twr_insufficient_snapshots_none(self, manager):
        """Returns None with fewer than 2 snapshots."""
        result = manager.calculate_twr()
        assert result is None

    def test_twr_single_snapshot_none(self, manager):
        """Returns None with exactly 1 snapshot."""
        _create_snapshot(datetime(2026, 1, 1), 10000)
        result = manager.calculate_twr()
        assert result is None

    def test_twr_no_cash_flows_equals_simple_return(self, manager):
        """Without cash flows, TWR should equal simple return."""
        _create_snapshot(datetime(2026, 1, 1), 10000)
        _create_snapshot(datetime(2026, 1, 2), 10500)

        result = manager.calculate_twr()
        assert result is not None
        # Simple return: (10500 - 10000) / 10000 = 5%
        assert result["twr"] == pytest.approx(5.0)
        assert result["simple_return"] == pytest.approx(5.0)

    def test_twr_deposit_does_not_inflate_return(self, manager):
        """A deposit shouldn't look like investment gain."""
        # Day 1: $10,000 portfolio
        _create_snapshot(datetime(2026, 1, 1), 10000)
        # Day 2: $15,000 portfolio (deposited $5,000, no investment gain)
        _create_snapshot(datetime(2026, 1, 2), 15000, cash_flow=5000)

        result = manager.calculate_twr()
        assert result is not None
        # TWR: (15000 - 5000) / 10000 - 1 = 0% (no investment gain)
        assert result["twr"] == pytest.approx(0.0)
        # Simple return would incorrectly show 50%
        assert result["simple_return"] == pytest.approx(50.0)

    def test_twr_withdrawal_does_not_deflate_return(self, manager):
        """A withdrawal shouldn't look like investment loss."""
        # Day 1: $10,000 portfolio
        _create_snapshot(datetime(2026, 1, 1), 10000)
        # Day 2: $7,000 portfolio (withdrew $3,000, no investment loss)
        _create_snapshot(datetime(2026, 1, 2), 7000, cash_flow=-3000)

        result = manager.calculate_twr()
        assert result is not None
        # TWR: (7000 - (-3000)) / 10000 - 1 = 0%
        assert result["twr"] == pytest.approx(0.0)
        # Simple return would incorrectly show -30%
        assert result["simple_return"] == pytest.approx(-30.0)

    def test_twr_known_values(self, manager):
        """Hand-calculated TWR scenario with deposit mid-period."""
        # Day 1: Start with $100,000
        _create_snapshot(datetime(2026, 1, 1), 100000)
        # Day 2: Portfolio grows to $110,000 (10% gain)
        _create_snapshot(datetime(2026, 1, 2), 110000)
        # Day 3: Deposit $50,000, portfolio at $165,000 (includes $5,000 gain on $160,000)
        _create_snapshot(datetime(2026, 1, 3), 165000, cash_flow=50000)

        result = manager.calculate_twr()
        assert result is not None
        # Period 1: (110000 - 0) / 100000 - 1 = 10%
        # Period 2: (165000 - 50000) / 110000 - 1 = 4.545%
        # TWR: (1.10 * 1.04545) - 1 = 15.0%
        assert result["twr"] == pytest.approx(15.0, rel=0.01)
        assert result["periods"] == 2

    def test_twr_multiple_periods(self, manager):
        """Chain-linked returns across multiple periods."""
        base = datetime(2026, 1, 1)
        _create_snapshot(base, 10000)
        _create_snapshot(base + timedelta(days=1), 10500)   # +5%
        _create_snapshot(base + timedelta(days=2), 10290)   # 10290/10500 = -2%
        _create_snapshot(base + timedelta(days=3), 10496)   # 10496/10290 = +2%

        result = manager.calculate_twr()
        assert result is not None
        # Exact: (10500/10000) * (10290/10500) * (10496/10290) - 1 = 4.96%
        assert result["twr"] == pytest.approx(4.96, rel=0.01)
        assert result["periods"] == 3

    def test_twr_zero_start_value_skips_period(self, manager):
        """Period with zero start value (initial deposit) is skipped."""
        _create_snapshot(datetime(2026, 1, 1), 0)
        _create_snapshot(datetime(2026, 1, 2), 10000, cash_flow=10000)
        _create_snapshot(datetime(2026, 1, 3), 10500)

        result = manager.calculate_twr()
        assert result is not None
        # First period skipped (start=0), second period: (10500-0)/10000 = 5%
        assert result["twr"] == pytest.approx(5.0)
        assert result["periods"] == 1

    def test_twr_annualized_short_period(self, manager):
        """Annualized TWR should be None for periods < 365 days."""
        _create_snapshot(datetime(2026, 1, 1), 10000)
        _create_snapshot(datetime(2026, 3, 1), 10500)

        result = manager.calculate_twr()
        assert result is not None
        assert result["twr_annualized"] is None

    def test_twr_annualized_long_period(self, manager):
        """Annualized TWR should be calculated for periods > 365 days."""
        _create_snapshot(datetime(2024, 1, 1), 10000)
        _create_snapshot(datetime(2026, 1, 1), 12100)  # 2 years, 21% total

        result = manager.calculate_twr(start_date=datetime(2023, 1, 1))
        assert result is not None
        assert result["twr_annualized"] is not None
        # 21% over ~730 days -> ~10% annualized
        assert result["twr_annualized"] == pytest.approx(10.0, rel=0.1)

    def test_twr_result_fields(self, manager):
        """Verify all expected fields in TWR result."""
        _create_snapshot(datetime(2026, 1, 1), 10000)
        _create_snapshot(datetime(2026, 1, 2), 10500)

        result = manager.calculate_twr()
        assert "twr" in result
        assert "twr_annualized" in result
        assert "simple_return" in result
        assert "periods" in result
        assert "start_date" in result
        assert "end_date" in result


class TestPerformanceStatsIncludesTWR:
    def test_performance_stats_has_twr_keys(self, manager):
        """get_performance_stats should include twr and twr_annualized."""
        _create_snapshot(datetime(2026, 1, 1), 10000)
        _create_snapshot(datetime(2026, 1, 2), 10500)

        stats = manager.get_performance_stats()
        assert stats is not None
        assert "twr" in stats
        assert "twr_annualized" in stats

    def test_performance_stats_twr_value(self, manager):
        """TWR in performance stats matches calculate_twr."""
        _create_snapshot(datetime(2026, 1, 1), 10000)
        _create_snapshot(datetime(2026, 1, 2), 10500)

        stats = manager.get_performance_stats()
        twr_result = manager.calculate_twr()

        assert stats["twr"] == pytest.approx(twr_result["twr"])
