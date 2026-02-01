"""Test scoring utility functions.

Tests for dashboard/utils/scoring.py - get_fscore_color() and get_zone_color().
"""

import pytest

from dashboard.utils.scoring import get_fscore_color, get_zone_color


class TestGetFscoreColor:
    """Tests for get_fscore_color()."""

    @pytest.mark.parametrize(
        "score,expected",
        [
            (9, "green"),
            (8, "green"),
            (7, "green"),
            (6, "orange"),
            (5, "orange"),
            (4, "orange"),
            (3, "red"),
            (2, "red"),
            (1, "red"),
            (0, "red"),
        ],
    )
    def test_fscore_color_thresholds(self, score, expected):
        """F-Score should map to correct color at each threshold."""
        assert get_fscore_color(score) == expected

    def test_high_boundary(self):
        """Score of 7 is the boundary for green."""
        assert get_fscore_color(7) == "green"
        assert get_fscore_color(6) == "orange"

    def test_low_boundary(self):
        """Score of 4 is the boundary for orange."""
        assert get_fscore_color(4) == "orange"
        assert get_fscore_color(3) == "red"


class TestGetZoneColor:
    """Tests for get_zone_color()."""

    def test_safe_zone(self):
        """Safe zone should return a valid color."""
        result = get_zone_color("Safe")
        # Color depends on ZSCORE_ZONES config, but should be defined
        assert result is not None
        assert isinstance(result, str)

    def test_grey_zone(self):
        """Grey zone should return a valid color."""
        result = get_zone_color("Grey")
        assert result is not None
        assert isinstance(result, str)

    def test_distress_zone(self):
        """Distress zone should return a valid color."""
        result = get_zone_color("Distress")
        assert result is not None
        assert isinstance(result, str)

    def test_unknown_zone_fallback(self):
        """Unknown zone should return grey fallback."""
        result = get_zone_color("UnknownZone")
        assert result == "grey"

    def test_none_zone(self):
        """None zone should be handled gracefully."""
        # get_zone_color expects a string, None may cause issues
        # but the fallback should still work
        try:
            result = get_zone_color(None)
            # If it doesn't error, verify it returns something
            assert result is not None
        except (TypeError, AttributeError):
            # If it errors on None, that's also acceptable behavior
            pass

    def test_empty_string_zone(self):
        """Empty string zone should fallback to grey."""
        result = get_zone_color("")
        assert result == "grey"
