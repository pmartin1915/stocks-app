"""
Portfolio snapshot automation service.

Provides functions for automated daily snapshots and cleanup of old data.
Designed to be called via CLI commands or cron jobs.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlmodel import select

from asymmetric.db.database import get_session
from asymmetric.db.portfolio_models import PortfolioSnapshot

from .manager import PortfolioManager

logger = logging.getLogger(__name__)


def should_take_snapshot() -> bool:
    """
    Check if a snapshot should be taken today.

    Returns True if:
    - No snapshot exists for today
    - Current time is after 4:00 PM ET (market close)
    - Portfolio has active holdings

    Returns:
        True if snapshot should be taken, False otherwise
    """
    now = datetime.now(UTC)

    # Check if after 4 PM ET (market close)
    # Convert to Eastern Time to properly handle DST transitions
    try:
        et_time = now.astimezone(ZoneInfo("America/New_York"))
        market_close_hour = 16  # 4 PM ET

        if et_time.hour < market_close_hour:
            logger.info(f"Current time {et_time.strftime('%I:%M %p %Z')} is before market close (4:00 PM ET)")
            return False
    except Exception as e:
        # Fallback to UTC check if timezone conversion fails
        logger.warning(f"Timezone conversion failed: {e}. Falling back to UTC check.")
        hour_utc = now.hour
        if hour_utc < 21:  # Before 9 PM UTC (approximately 4 PM ET)
            logger.info(f"Current hour {hour_utc} UTC is before market close (21:00 UTC)")
            return False

    # Check if snapshot already exists today
    with get_session() as session:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        existing_snapshot = session.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_date >= today_start)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
        ).first()

        if existing_snapshot:
            logger.info(f"Snapshot already exists for today: {existing_snapshot.snapshot_date}")
            return False

    # Check if portfolio has holdings
    manager = PortfolioManager()
    summary = manager.get_portfolio_summary(include_market_data=False)  # Quick check
    if summary.position_count == 0:
        logger.info("Portfolio is empty, skipping snapshot")
        return False

    return True


def take_daily_snapshot() -> Optional[PortfolioSnapshot]:
    """
    Take a daily portfolio snapshot with current market prices.

    Only creates snapshot if conditions are met (see should_take_snapshot()).

    Returns:
        Created PortfolioSnapshot or None if conditions not met
    """
    try:
        if not should_take_snapshot():
            return None

        manager = PortfolioManager()
        snapshot = manager.take_snapshot(auto=True)

        logger.info(
            f"Snapshot created: "
            f"Market Value=${snapshot.total_value:,.2f}, "
            f"Unrealized P&L=${snapshot.unrealized_pnl:,.2f}"
        )

        # Cleanup old snapshots after successful creation
        cleanup_old_snapshots()

        return snapshot

    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}", exc_info=True)
        return None


def cleanup_old_snapshots(keep_days: int = 365) -> int:
    """
    Delete portfolio snapshots older than keep_days.

    Args:
        keep_days: Number of days to retain (default 365 = 1 year)

    Returns:
        Number of snapshots deleted
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=keep_days)

    with get_session() as session:
        old_snapshots = session.exec(
            select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date < cutoff_date)
        ).all()

        count = len(old_snapshots)

        for snapshot in old_snapshots:
            session.delete(snapshot)

        session.commit()

        if count > 0:
            logger.info(f"Deleted {count} snapshots older than {keep_days} days")

        return count


def get_last_snapshot_date() -> Optional[datetime]:
    """
    Get the date of the most recent snapshot.

    Returns:
        Datetime of last snapshot or None if no snapshots exist
    """
    with get_session() as session:
        last_snapshot = session.exec(
            select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.desc())
        ).first()

        return last_snapshot.snapshot_date if last_snapshot else None
