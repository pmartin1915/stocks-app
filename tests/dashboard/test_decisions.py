"""Test decision display utility functions.

Tests for dashboard/components/decisions.py - date formatting and confidence indicator.
"""

import pytest

from dashboard.components.decisions import (
    _format_date,
    _format_short_date,
    render_confidence_indicator,
)


class TestFormatDate:
    """Tests for _format_date()."""

    def test_valid_iso_date(self):
        """Valid ISO date should format as 'YYYY-MM-DD HH:MM'."""
        assert _format_date("2025-01-15T10:30:00") == "2025-01-15 10:30"

    def test_iso_with_timezone(self):
        """ISO date with timezone should still parse."""
        result = _format_date("2025-01-15T10:30:00+00:00")
        assert "2025-01-15" in result
        assert "10:30" in result

    def test_none_returns_na(self):
        """None input should return 'N/A'."""
        assert _format_date(None) == "N/A"

    def test_empty_string_returns_na(self):
        """Empty string should return 'N/A'."""
        assert _format_date("") == "N/A"

    def test_invalid_format_returns_na(self):
        """Invalid date format should return 'N/A'."""
        assert _format_date("not-a-date") == "N/A"
        assert _format_date("01/15/2025") == "N/A"

    def test_date_only_format(self):
        """Date-only ISO format should work."""
        result = _format_date("2025-01-15")
        assert "2025-01-15" in result

    def test_midnight(self):
        """Midnight should display as 00:00."""
        assert _format_date("2025-01-15T00:00:00") == "2025-01-15 00:00"

    def test_end_of_day(self):
        """End of day should display as 23:59."""
        assert _format_date("2025-01-15T23:59:00") == "2025-01-15 23:59"


class TestFormatShortDate:
    """Tests for _format_short_date()."""

    def test_valid_iso_date(self):
        """Valid ISO date should format as 'YYYY-MM-DD'."""
        assert _format_short_date("2025-01-15T10:30:00") == "2025-01-15"

    def test_none_returns_na(self):
        """None input should return 'N/A'."""
        assert _format_short_date(None) == "N/A"

    def test_empty_string_returns_na(self):
        """Empty string should return 'N/A'."""
        assert _format_short_date("") == "N/A"

    def test_invalid_format_returns_na(self):
        """Invalid date format should return 'N/A'."""
        assert _format_short_date("not-a-date") == "N/A"

    def test_date_only_input(self):
        """Date-only input should work."""
        result = _format_short_date("2025-01-15")
        assert "2025-01-15" in result

    def test_strips_time(self):
        """Time component should be stripped."""
        result = _format_short_date("2025-01-15T23:59:59")
        assert "23:59" not in result
        assert result == "2025-01-15"


class TestRenderConfidenceIndicator:
    """Tests for render_confidence_indicator()."""

    @pytest.mark.parametrize(
        "level,expected_label",
        [
            (1, "Very Low"),
            (2, "Low"),
            (3, "Medium"),
            (4, "High"),
            (5, "Very High"),
        ],
    )
    def test_confidence_labels(self, level, expected_label):
        """Each confidence level should have correct label."""
        html = render_confidence_indicator(level)
        assert expected_label in html

    def test_none_returns_na(self):
        """None confidence should return 'N/A'."""
        assert render_confidence_indicator(None) == "N/A"

    def test_contains_svg_stars(self):
        """Result should contain SVG star elements."""
        html = render_confidence_indicator(3)
        assert "<svg" in html

    def test_level_1_minimal_stars(self):
        """Level 1 should have minimal stars (1 filled)."""
        html = render_confidence_indicator(1)
        # Should contain stars but with low rating
        assert "<svg" in html
        assert "Very Low" in html

    def test_level_5_maximum_stars(self):
        """Level 5 should have maximum stars (5 filled)."""
        html = render_confidence_indicator(5)
        assert "<svg" in html
        assert "Very High" in html

    def test_invalid_level_uses_default(self):
        """Invalid level should use default (Medium) config."""
        # Level 10 is invalid, should fallback to level 3 (Medium)
        html = render_confidence_indicator(10)
        assert "Medium" in html

    def test_zero_level_uses_default(self):
        """Level 0 should use default config."""
        html = render_confidence_indicator(0)
        # 0 is not in CONFIDENCE_LEVELS, should fallback
        assert "Medium" in html
