"""
Tests for portfolio performance analytics and historical queries.

Tests snapshot retrieval, performance calculations, and edge cases
for the historical performance charting feature.
"""

import pytest
from datetime import datetime, timedelta, timezone

from asymmetric.core.portfolio import PortfolioManager
from asymmetric.db.portfolio_models import PortfolioSnapshot
from asymmetric.db.database import get_session


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def manager():
    """Create PortfolioManager instance."""
    return PortfolioManager()


@pytest.fixture
def manager_with_snapshots(manager):
    """
    Create test snapshots spanning 30 days.

    Simulates portfolio growth from $10,000 to $12,000 with realistic volatility.
    """
    with get_session() as session:
        # Use timezone-naive datetime since SQLite stores without timezone (implicit UTC)
        base_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        base_value = 10000.0
        base_cost = 10000.0

        snapshots = []
        for day in range(30):
            snapshot_date = base_date + timedelta(days=day)

            # Simulate growth with volatility
            # Overall trend: +20% over 30 days
            # Daily volatility: ±2%
            trend_factor = 1 + (0.20 * day / 30)  # Linear growth to +20%
            volatility_factor = 1 + (0.02 * ((-1) ** day))  # Alternating ±2%
            total_value = base_value * trend_factor * volatility_factor

            # Simulate some realized P&L events
            realized_pnl_total = 0.0
            if day == 10:  # Sell on day 10
                realized_pnl_total = 500.0
            elif day == 20:  # Sell on day 20
                realized_pnl_total = 800.0
            elif day > 20:
                realized_pnl_total = 800.0  # Cumulative after day 20

            unrealized_pnl = total_value - base_cost
            unrealized_pnl_percent = (unrealized_pnl / base_cost) * 100 if base_cost > 0 else 0.0

            # Simulate weighted scores (F-Score: 6-8, Z-Score: 2-4)
            weighted_fscore = 7.0 + (0.5 * (day % 3))  # Oscillate 7-8
            weighted_zscore = 3.0 + (0.3 * (day % 4))  # Oscillate 3-3.9

            snapshot = PortfolioSnapshot(
                snapshot_date=snapshot_date,
                total_value=total_value,
                total_cost_basis=base_cost,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                realized_pnl_ytd=realized_pnl_total,  # Simplified: YTD = total for test
                realized_pnl_total=realized_pnl_total,
                position_count=3 + (day % 2),  # Oscillate 3-4 positions
                weighted_fscore=weighted_fscore,
                weighted_zscore=weighted_zscore,
            )
            session.add(snapshot)
            snapshots.append(snapshot)

        session.commit()

        # Detach from session
        for snapshot in snapshots:
            session.refresh(snapshot)
            session.expunge(snapshot)

    return manager


def test_get_snapshots_all(manager_with_snapshots):
    """Test retrieving all snapshots without filters."""
    snapshots = manager_with_snapshots.get_snapshots()

    assert len(snapshots) == 30
    # Verify ascending order (oldest to newest)
    for i in range(1, len(snapshots)):
        assert snapshots[i].snapshot_date > snapshots[i - 1].snapshot_date


def test_get_snapshots_date_range(manager_with_snapshots):
    """Test retrieving snapshots with date filters."""
    # Query last 7 days
    # Note: Use timezone-naive datetime since SQLite stores without timezone
    end_date = datetime.now(timezone.utc).replace(tzinfo=None)
    start_date = end_date - timedelta(days=7)

    snapshots = manager_with_snapshots.get_snapshots(start_date=start_date, end_date=end_date)

    # Should have ~7 snapshots (might be 7 or 8 depending on exact timing)
    assert 6 <= len(snapshots) <= 8
    # Verify all snapshots are within range
    for snapshot in snapshots:
        assert snapshot.snapshot_date >= start_date
        assert snapshot.snapshot_date <= end_date
    # Verify ascending order
    for i in range(1, len(snapshots)):
        assert snapshots[i].snapshot_date > snapshots[i - 1].snapshot_date


def test_get_snapshots_limit(manager_with_snapshots):
    """Test limit parameter returns oldest N snapshots."""
    snapshots = manager_with_snapshots.get_snapshots(limit=5)

    assert len(snapshots) == 5
    # Verify these are the oldest 5 (ascending order)
    all_snapshots = manager_with_snapshots.get_snapshots()
    for i in range(5):
        assert snapshots[i].snapshot_date == all_snapshots[i].snapshot_date


def test_get_snapshots_empty_portfolio(manager):
    """Test behavior with no snapshots."""
    snapshots = manager.get_snapshots()

    assert snapshots == []
    assert isinstance(snapshots, list)


def test_get_performance_stats_returns(manager_with_snapshots):
    """Test return calculations match expected formulas."""
    snapshots = manager_with_snapshots.get_snapshots()
    stats = manager_with_snapshots.get_performance_stats(snapshots)

    assert stats is not None

    first_value = snapshots[0].total_value
    latest_value = snapshots[-1].total_value

    # Verify total return calculation
    expected_return = ((latest_value - first_value) / first_value) * 100
    assert abs(stats["total_return"] - expected_return) < 0.01

    # Verify dollar return
    expected_dollars = latest_value - first_value
    assert abs(stats["total_return_dollars"] - expected_dollars) < 0.01

    # Verify days tracked
    assert stats["days_tracked"] == 30


def test_get_performance_stats_drawdown(manager_with_snapshots):
    """Test drawdown calculations."""
    snapshots = manager_with_snapshots.get_snapshots()
    stats = manager_with_snapshots.get_performance_stats(snapshots)

    assert stats is not None

    # Peak value should be highest value in snapshots
    max_value = max(s.total_value for s in snapshots)
    assert stats["peak_value"] == max_value

    # Current drawdown should be negative or zero
    assert stats["current_drawdown"] <= 0.0

    # Max drawdown should be negative or zero (worst decline from any peak)
    assert stats["max_drawdown"] <= 0.0


def test_get_performance_stats_volatility(manager_with_snapshots):
    """Test volatility (standard deviation) calculation."""
    snapshots = manager_with_snapshots.get_snapshots()
    stats = manager_with_snapshots.get_performance_stats(snapshots)

    assert stats is not None

    # Volatility should be positive (we have oscillating values)
    assert stats["volatility"] > 0.0

    # Average daily return should be positive (growing portfolio)
    assert stats["avg_daily_return"] > 0.0


def test_get_performance_stats_best_worst_days(manager_with_snapshots):
    """Test best/worst day identification."""
    snapshots = manager_with_snapshots.get_snapshots()
    stats = manager_with_snapshots.get_performance_stats(snapshots)

    assert stats is not None
    assert stats["best_day"] is not None
    assert stats["worst_day"] is not None

    # Best day should have positive return
    assert stats["best_day"]["return"] > 0.0

    # Worst day should have negative return (due to volatility)
    assert stats["worst_day"]["return"] < 0.0

    # Best day return should be greater than worst day return
    assert stats["best_day"]["return"] > stats["worst_day"]["return"]

    # Dates should be within snapshot range
    assert stats["best_day"]["date"] >= snapshots[0].snapshot_date
    assert stats["best_day"]["date"] <= snapshots[-1].snapshot_date
    assert stats["worst_day"]["date"] >= snapshots[0].snapshot_date
    assert stats["worst_day"]["date"] <= snapshots[-1].snapshot_date


def test_get_performance_stats_single_snapshot(manager):
    """Test stats with only one snapshot returns None."""
    # Create single snapshot
    with get_session() as session:
        snapshot = PortfolioSnapshot(
            snapshot_date=datetime.now(timezone.utc).replace(tzinfo=None),
            total_value=10000.0,
            total_cost_basis=10000.0,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            position_count=1,
        )
        session.add(snapshot)
        session.commit()

    snapshots = manager.get_snapshots()
    assert len(snapshots) == 1

    stats = manager.get_performance_stats(snapshots)

    # Should return None (cannot calculate returns with single data point)
    assert stats is None


def test_get_performance_stats_empty_list(manager):
    """Test stats with empty snapshot list returns None."""
    stats = manager.get_performance_stats([])

    assert stats is None


def test_get_performance_stats_default_fetch(manager_with_snapshots):
    """Test stats without providing snapshots fetches last 365 days."""
    # Call without snapshots parameter
    stats = manager_with_snapshots.get_performance_stats()

    assert stats is not None
    # Should have fetched our 30 test snapshots
    assert stats["days_tracked"] == 30


def test_snapshot_datetime_consistency(manager_with_snapshots):
    """Verify all snapshots use consistent timezone (UTC stored as naive)."""
    snapshots = manager_with_snapshots.get_snapshots()

    for snapshot in snapshots:
        # SQLite stores datetimes as strings without timezone info
        # They come back as timezone-naive, but are implicitly UTC
        assert snapshot.snapshot_date.tzinfo is None
        # Verify it's a valid datetime
        assert isinstance(snapshot.snapshot_date, datetime)


def test_get_snapshots_start_date_only(manager_with_snapshots):
    """Test filtering with only start_date (no end_date)."""
    # Get snapshots from 15 days ago onwards
    # Note: Use timezone-naive datetime since SQLite stores without timezone
    start_date = (datetime.now(timezone.utc) - timedelta(days=15)).replace(tzinfo=None)
    snapshots = manager_with_snapshots.get_snapshots(start_date=start_date)

    # Should have ~15 snapshots
    assert 14 <= len(snapshots) <= 16

    # All should be after start_date
    for snapshot in snapshots:
        assert snapshot.snapshot_date >= start_date


def test_get_snapshots_end_date_only(manager_with_snapshots):
    """Test filtering with only end_date (no start_date)."""
    # Get snapshots up to 10 days ago
    # Note: Use timezone-naive datetime since SQLite stores without timezone
    end_date = (datetime.now(timezone.utc) - timedelta(days=10)).replace(tzinfo=None)
    snapshots = manager_with_snapshots.get_snapshots(end_date=end_date)

    # Should have ~20 snapshots (30 total - 10 excluded)
    assert 19 <= len(snapshots) <= 21

    # All should be before end_date
    for snapshot in snapshots:
        assert snapshot.snapshot_date <= end_date


def test_performance_stats_zero_cost_basis(manager):
    """Test handling of zero cost basis (edge case)."""
    with get_session() as session:
        # Create snapshots with zero cost basis
        base_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
        for day in range(2):
            snapshot = PortfolioSnapshot(
                snapshot_date=base_date + timedelta(days=day),
                total_value=1000.0 + (day * 100),
                total_cost_basis=0.0,  # Zero cost basis
                unrealized_pnl=1000.0 + (day * 100),
                unrealized_pnl_percent=0.0,
                position_count=1,
            )
            session.add(snapshot)
        session.commit()

    stats = manager.get_performance_stats()

    # Should not crash, should return stats with zero/invalid returns
    assert stats is not None
    assert stats["days_tracked"] == 2
