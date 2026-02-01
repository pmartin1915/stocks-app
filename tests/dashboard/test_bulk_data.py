"""Test bulk data utility functions.

Tests for dashboard/utils/bulk_data.py - specifically the format_last_refresh() function.
"""

from datetime import UTC, datetime, timedelta

import pytest

from dashboard.utils.bulk_data import format_last_refresh


class TestFormatLastRefresh:
    """Tests for format_last_refresh()."""

    def test_just_now(self):
        """Timestamps within last minute should show 'Just now'."""
        now = datetime.now(UTC)
        iso = now.isoformat()
        assert format_last_refresh(iso) == "Just now"

    def test_minutes_ago_singular(self):
        """2 minutes ago should show '2 minutes ago'."""
        two_min_ago = datetime.now(UTC) - timedelta(minutes=2)
        iso = two_min_ago.isoformat()
        result = format_last_refresh(iso)
        assert "2 minutes ago" in result

    def test_minutes_ago_plural(self):
        """30 minutes ago should show '30 minutes ago'."""
        thirty_min_ago = datetime.now(UTC) - timedelta(minutes=30)
        iso = thirty_min_ago.isoformat()
        result = format_last_refresh(iso)
        assert "30 minutes ago" in result

    def test_one_hour_ago(self):
        """1 hour ago should show '1 hour ago'."""
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        iso = one_hour_ago.isoformat()
        assert format_last_refresh(iso) == "1 hour ago"

    def test_hours_ago_plural(self):
        """5 hours ago should show '5 hours ago'."""
        five_hours_ago = datetime.now(UTC) - timedelta(hours=5)
        iso = five_hours_ago.isoformat()
        assert format_last_refresh(iso) == "5 hours ago"

    def test_yesterday(self):
        """24-48 hours ago should show 'Yesterday'."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        iso = yesterday.isoformat()
        assert format_last_refresh(iso) == "Yesterday"

    def test_days_ago_plural(self):
        """3 days ago should show '3 days ago'."""
        three_days_ago = datetime.now(UTC) - timedelta(days=3)
        iso = three_days_ago.isoformat()
        assert format_last_refresh(iso) == "3 days ago"

    def test_week_shows_days(self):
        """6 days ago should still show days, not weeks."""
        six_days_ago = datetime.now(UTC) - timedelta(days=6)
        iso = six_days_ago.isoformat()
        assert format_last_refresh(iso) == "6 days ago"

    def test_older_shows_date(self):
        """More than a week should show formatted date."""
        two_weeks_ago = datetime.now(UTC) - timedelta(days=14)
        iso = two_weeks_ago.isoformat()
        result = format_last_refresh(iso)
        # Should be in format like "Jan 17, 2026"
        assert len(result) > 5
        assert "ago" not in result

    def test_none_returns_never(self):
        """None input should return 'Never'."""
        assert format_last_refresh(None) == "Never"

    def test_empty_string_returns_never(self):
        """Empty string should return 'Never'."""
        assert format_last_refresh("") == "Never"

    def test_invalid_format_returns_unknown(self):
        """Invalid ISO format should return 'Unknown'."""
        assert format_last_refresh("not-a-date") == "Unknown"

    def test_handles_microseconds(self):
        """Should handle ISO timestamps with microseconds."""
        now = datetime.now(UTC)
        iso_with_micro = now.isoformat()  # Includes microseconds
        result = format_last_refresh(iso_with_micro)
        assert result == "Just now"

    def test_handles_datetime_object(self):
        """Should handle datetime objects directly."""
        now = datetime.now(UTC)
        result = format_last_refresh(now)
        assert result == "Just now"

    def test_handles_old_datetime(self):
        """Should handle very old timestamps."""
        old_date = datetime(2020, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = format_last_refresh(old_date.isoformat())
        assert result == "Jan 15, 2020"
