"""
Test snapshot automation functionality.

Tests the automated daily snapshot service including timing checks,
snapshot creation, and data retention policies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from asymmetric.core.portfolio import PortfolioManager
from asymmetric.core.portfolio.snapshot_service import (
    should_take_snapshot,
    take_daily_snapshot,
    cleanup_old_snapshots,
    get_last_snapshot_date,
)
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from asymmetric.db.portfolio_models import PortfolioSnapshot


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):  # noqa: ARG001
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def manager():
    """Create PortfolioManager instance."""
    return PortfolioManager()


@pytest.fixture
def stock_test():
    """Create test stock."""
    with get_session() as session:
        stock = Stock(ticker="TEST", cik="0001234567", company_name="Test Company")
        session.add(stock)
        session.commit()
        return stock.ticker


@pytest.fixture
def portfolio_with_holding(manager, stock_test):
    """Create portfolio with one holding."""
    manager.add_buy(stock_test, 100, 50.0, fees=5.0)
    return manager


class TestShouldTakeSnapshot:
    """Test snapshot timing and condition checks."""

    def test_should_take_snapshot_first_of_day(self, portfolio_with_holding):
        """Test snapshot is allowed on first run of the day."""
        # Mock time to be after market close (9 PM UTC)
        with patch("asymmetric.core.portfolio.snapshot_service.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 15, 21, 30, tzinfo=timezone.utc)  # 9:30 PM UTC
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine  # Pass through
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = should_take_snapshot()

            # Should allow snapshot (no snapshot exists yet, after market close, has holdings)
            assert result is True

    def test_should_take_snapshot_before_market_close(self, portfolio_with_holding):
        """Test snapshot blocked before market close."""
        # Mock time to be before market close (8 PM UTC / 3 PM ET)
        with patch("asymmetric.core.portfolio.snapshot_service.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc)  # 8 PM UTC
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = should_take_snapshot()

            # Should block (before market close)
            assert result is False

    def test_should_take_snapshot_empty_portfolio(self):
        """Test snapshot blocked when portfolio is empty."""
        # Mock time to be after market close
        with patch("asymmetric.core.portfolio.snapshot_service.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 15, 21, 30, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = should_take_snapshot()

            # Should block (no holdings)
            assert result is False

    def test_should_take_snapshot_already_exists_today(self, portfolio_with_holding):
        """Test snapshot blocked when one already exists today."""
        manager = portfolio_with_holding

        # Create a snapshot for today
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_prices:
            mock_prices.return_value = {"TEST": {"price": 60.0, "change_percent": 20.0}}
            manager.take_snapshot()

        # Mock time to be after market close
        with patch("asymmetric.core.portfolio.snapshot_service.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 15, 21, 30, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Check that snapshot is blocked (already exists)
            result = should_take_snapshot()

            # Should block (snapshot already exists today)
            assert result is False


class TestTakeDailySnapshot:
    """Test snapshot creation functionality."""

    def test_take_daily_snapshot_creates_record(self, portfolio_with_holding):
        """Test that take_daily_snapshot creates a database record."""
        # Mock time to be after market close
        with patch("asymmetric.core.portfolio.snapshot_service.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 15, 21, 30, tzinfo=timezone.utc)  # After 9 PM UTC
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock price data
            with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_prices:
                mock_prices.return_value = {"TEST": {"price": 60.0, "change_percent": 20.0}}

                # Take snapshot
                snapshot = take_daily_snapshot()

                # Verify snapshot was created
                assert snapshot is not None
                assert snapshot.id is not None

                # Verify snapshot data
                assert snapshot.position_count == 1
                assert snapshot.total_cost_basis == pytest.approx(5005.0)  # 100 * 50 + 5 fees
                assert snapshot.total_value == pytest.approx(6000.0)  # 100 * 60
                assert snapshot.unrealized_pnl == pytest.approx(995.0)  # 6000 - 5005

    def test_take_daily_snapshot_empty_portfolio(self):
        """Test snapshot creation with empty portfolio."""
        snapshot = take_daily_snapshot()

        # Should return None (no holdings)
        assert snapshot is None

    def test_take_daily_snapshot_error_handling(self, portfolio_with_holding):
        """Test error handling in snapshot creation."""
        # Mock get_portfolio_summary to raise exception
        with patch("asymmetric.core.portfolio.manager.PortfolioManager.get_portfolio_summary") as mock_summary:
            mock_summary.side_effect = Exception("Database error")

            # Should return None on error (not raise exception)
            snapshot = take_daily_snapshot()
            assert snapshot is None


class TestCleanupOldSnapshots:
    """Test snapshot retention and cleanup."""

    def test_cleanup_old_snapshots_keeps_recent(self, portfolio_with_holding):
        """Test that cleanup keeps recent snapshots."""
        manager = portfolio_with_holding

        # Create 3 snapshots with different dates
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_prices:
            mock_prices.return_value = {"TEST": {"price": 60.0, "change_percent": 20.0}}

            # Create snapshots at different times
            with get_session() as session:
                # Recent snapshot (5 days ago)
                snapshot1 = PortfolioSnapshot(
                    snapshot_date=datetime.now(timezone.utc) - timedelta(days=5),
                    total_value=6000.0,
                    total_cost_basis=5005.0,
                    unrealized_pnl=995.0,
                    unrealized_pnl_percent=19.88,
                    position_count=1,
                )
                # Old snapshot (400 days ago)
                snapshot2 = PortfolioSnapshot(
                    snapshot_date=datetime.now(timezone.utc) - timedelta(days=400),
                    total_value=5500.0,
                    total_cost_basis=5005.0,
                    unrealized_pnl=495.0,
                    unrealized_pnl_percent=9.89,
                    position_count=1,
                )
                # Very old snapshot (500 days ago)
                snapshot3 = PortfolioSnapshot(
                    snapshot_date=datetime.now(timezone.utc) - timedelta(days=500),
                    total_value=5200.0,
                    total_cost_basis=5005.0,
                    unrealized_pnl=195.0,
                    unrealized_pnl_percent=3.90,
                    position_count=1,
                )
                session.add_all([snapshot1, snapshot2, snapshot3])
                session.commit()

        # Cleanup with 365-day retention
        deleted = cleanup_old_snapshots(keep_days=365)

        # Should delete 2 old snapshots (400 and 500 days old)
        assert deleted == 2

        # Verify only recent snapshot remains
        with get_session() as session:
            from sqlmodel import select
            remaining = session.exec(select(PortfolioSnapshot)).all()
            assert len(remaining) == 1
            # Compare timezone-naive datetimes
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            snapshot_date_naive = remaining[0].snapshot_date.replace(tzinfo=None) if remaining[0].snapshot_date.tzinfo else remaining[0].snapshot_date
            assert (now_naive - snapshot_date_naive).days <= 10

    def test_cleanup_old_snapshots_empty_database(self):
        """Test cleanup with no snapshots."""
        deleted = cleanup_old_snapshots(keep_days=365)

        # Should delete nothing
        assert deleted == 0


class TestGetLastSnapshotDate:
    """Test last snapshot date retrieval."""

    def test_get_last_snapshot_date_exists(self, portfolio_with_holding):
        """Test retrieving last snapshot date."""
        manager = portfolio_with_holding

        # Create a snapshot
        with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_prices:
            mock_prices.return_value = {"TEST": {"price": 60.0, "change_percent": 20.0}}
            snapshot = manager.take_snapshot()

        # Get last snapshot date
        last_date = get_last_snapshot_date()

        # Should return snapshot date
        assert last_date is not None
        assert isinstance(last_date, datetime)
        # Should be very recent (within last minute)
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        last_date_naive = last_date.replace(tzinfo=None) if last_date.tzinfo else last_date
        assert (now_naive - last_date_naive).seconds < 60

    def test_get_last_snapshot_date_none(self):
        """Test when no snapshots exist."""
        last_date = get_last_snapshot_date()

        # Should return None
        assert last_date is None


class TestSnapshotIntegration:
    """Integration tests for full snapshot workflow."""

    def test_full_snapshot_workflow(self, portfolio_with_holding):
        """Test complete snapshot automation workflow."""
        manager = portfolio_with_holding

        # Mock time to be after market close
        with patch("asymmetric.core.portfolio.snapshot_service.datetime") as mock_dt:
            mock_now = datetime(2024, 1, 15, 21, 30, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock price data
            with patch("asymmetric.core.portfolio.manager.fetch_batch_prices") as mock_prices:
                mock_prices.return_value = {"TEST": {"price": 60.0, "change_percent": 20.0}}

                # 1. Check if snapshot should be taken
                should_take = should_take_snapshot()
                assert should_take is True

                # 2. Take snapshot
                snapshot = take_daily_snapshot()
                assert snapshot is not None
                assert snapshot.position_count == 1

                # 3. Verify snapshot in database
                last_date = get_last_snapshot_date()
                assert last_date is not None

                # 4. Check that second snapshot is blocked
                should_take_again = should_take_snapshot()
                assert should_take_again is False
