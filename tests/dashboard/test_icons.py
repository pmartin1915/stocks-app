"""Test icon and badge generation functions.

Tests for dashboard/components/icons.py - all pure functions that return HTML strings.
"""

import pytest

from dashboard.components.icons import (
    COLORS,
    _svg,
    action_badge,
    badge,
    check,
    circle,
    circle_green,
    circle_red,
    circle_yellow,
    fscore_badge,
    signal_icon,
    stars_rating,
    status_badge,
    thesis_status_badge,
    x_mark,
    zscore_badge,
)


class TestSvgGeneration:
    """Tests for SVG generation helpers."""

    def test_svg_filled(self):
        """Filled SVGs should have fill attribute."""
        svg = _svg('<circle cx="12" cy="12" r="8"/>', "#ff0000", 18, filled=True)
        assert 'fill="#ff0000"' in svg
        assert 'width="18"' in svg
        assert 'height="18"' in svg
        assert '<circle cx="12" cy="12" r="8"/>' in svg

    def test_svg_stroked(self):
        """Stroked SVGs should have stroke and no fill."""
        svg = _svg('<line x1="0" y1="0" x2="10" y2="10"/>', "#00ff00", 24, filled=False)
        assert 'stroke="#00ff00"' in svg
        assert 'fill="none"' in svg
        assert 'stroke-width="2"' in svg

    def test_svg_contains_viewbox(self):
        """All SVGs should have viewBox for scaling."""
        svg = _svg('<path d="M0 0"/>', "#000", 16, filled=False)
        assert 'viewBox="0 0 24 24"' in svg


class TestCircleIcons:
    """Tests for status circle icons."""

    def test_circle_green(self):
        """Green circle should use green color."""
        icon = circle_green()
        assert COLORS["green"] in icon
        assert "<circle" in icon

    def test_circle_red(self):
        """Red circle should use red color."""
        icon = circle_red()
        assert COLORS["red"] in icon

    def test_circle_yellow(self):
        """Yellow circle should use yellow color."""
        icon = circle_yellow()
        assert COLORS["yellow"] in icon

    def test_circle_custom_color(self):
        """Circle with custom color should work."""
        icon = circle("#123456", 20)
        assert "#123456" in icon
        assert 'width="20"' in icon

    def test_circle_default_size(self):
        """Default size should be 18."""
        icon = circle_green()
        assert 'width="18"' in icon


class TestSignalIcons:
    """Tests for check/x/minus icons."""

    def test_check_icon(self):
        """Check icon should use green and polyline."""
        icon = check()
        assert COLORS["green"] in icon
        assert "polyline" in icon

    def test_x_mark_icon(self):
        """X mark should use red and line elements."""
        icon = x_mark()
        assert COLORS["red"] in icon
        assert "line" in icon

    def test_signal_icon_true(self):
        """signal_icon(True) should return check mark."""
        icon = signal_icon(True)
        assert "polyline" in icon
        assert COLORS["green"] in icon

    def test_signal_icon_false(self):
        """signal_icon(False) should return X mark."""
        icon = signal_icon(False)
        assert "line" in icon
        assert COLORS["red"] in icon

    def test_signal_icon_none(self):
        """signal_icon(None) should return minus/dash."""
        icon = signal_icon(None)
        assert "line" in icon
        assert COLORS["gray"] in icon


class TestBadges:
    """Tests for generic badge generation."""

    def test_badge_basic(self):
        """Badge should contain text and colors."""
        b = badge("Test", "#ff0000", "#ffffff", "small")
        assert "Test" in b
        assert "background:#ff0000" in b
        assert "color:#ffffff" in b

    def test_badge_small_size(self):
        """Small badges should have smaller padding."""
        small = badge("X", "#000", "#fff", "small")
        assert "padding:2px 8px" in small
        assert "font-size:0.75rem" in small

    def test_badge_normal_size(self):
        """Normal badges should have larger padding."""
        normal = badge("X", "#000", "#fff", "normal")
        assert "padding:4px 12px" in normal
        assert "font-size:0.875rem" in normal

    def test_badge_has_border_radius(self):
        """Badges should be pill-shaped."""
        b = badge("Test", "#000", "#fff", "small")
        assert "border-radius:12px" in b


class TestFScoreBadge:
    """Tests for F-Score badge coloring."""

    @pytest.mark.parametrize(
        "score,expected_color",
        [
            (9, COLORS["green"]),
            (8, COLORS["green"]),
            (7, COLORS["green"]),
            (6, COLORS["yellow"]),
            (5, COLORS["yellow"]),
            (4, COLORS["yellow"]),
            (3, COLORS["red"]),
            (2, COLORS["red"]),
            (1, COLORS["red"]),
            (0, COLORS["red"]),
        ],
    )
    def test_fscore_color_thresholds(self, score, expected_color):
        """F-Score should use correct color for each threshold."""
        b = fscore_badge(score)
        assert expected_color in b, f"Score {score} should use {expected_color}"
        assert f"F:{score}/9" in b

    def test_fscore_none(self):
        """None F-Score should show N/A in gray."""
        b = fscore_badge(None)
        assert COLORS["gray"] in b
        assert "N/A" in b

    def test_fscore_sizes(self):
        """F-Score badges should respect size parameter."""
        small = fscore_badge(8, size="small")
        normal = fscore_badge(8, size="normal")
        assert "padding:2px 8px" in small
        assert "padding:4px 12px" in normal

    def test_fscore_incomplete_signals(self):
        """F-Score with fewer than 9 signals should show signal count."""
        b = fscore_badge(7, signals_available=6)
        assert "6sig" in b
        assert "F:7/9" in b

    def test_fscore_full_signals_no_suffix(self):
        """F-Score with all 9 signals should NOT show signal count."""
        b = fscore_badge(7, signals_available=9)
        assert "sig" not in b


class TestZScoreBadge:
    """Tests for Z-Score badge coloring."""

    def test_zscore_safe(self):
        """Safe zone should be green."""
        b = zscore_badge(3.5, "Safe")
        assert COLORS["green"] in b
        assert "Z:3.5" in b

    def test_zscore_grey(self):
        """Grey zone should be yellow."""
        b = zscore_badge(2.5, "Grey")
        assert COLORS["yellow"] in b

    def test_zscore_gray_alternate_spelling(self):
        """Gray zone (alternate spelling) should be yellow."""
        b = zscore_badge(2.5, "Gray")
        assert COLORS["yellow"] in b

    def test_zscore_distress(self):
        """Distress zone should be red."""
        b = zscore_badge(1.2, "Distress")
        assert COLORS["red"] in b

    def test_zscore_none_value(self):
        """None Z-Score should show N/A in gray."""
        b = zscore_badge(None, None)
        assert COLORS["gray"] in b
        assert "N/A" in b

    def test_zscore_none_zone(self):
        """Z-Score with None zone should show N/A."""
        b = zscore_badge(2.5, None)
        assert "N/A" in b

    def test_zscore_decimal_formatting(self):
        """Z-Score should display with 1 decimal place."""
        b = zscore_badge(3.456, "Safe")
        assert "Z:3.5" in b  # Rounded to 1 decimal

    def test_zscore_approximate(self):
        """Approximate Z-Score should show ~ prefix."""
        b = zscore_badge(2.5, "Grey", is_approximate=True)
        assert "Z:~2.5" in b

    def test_zscore_not_approximate(self):
        """Non-approximate Z-Score should NOT show ~ prefix."""
        b = zscore_badge(3.5, "Safe", is_approximate=False)
        assert "Z:3.5" in b
        assert "~" not in b


class TestStatusBadge:
    """Tests for status zone badges."""

    def test_status_safe(self):
        """Safe status should be green."""
        b = status_badge("Safe")
        assert COLORS["green"] in b
        assert "Safe" in b

    def test_status_grey(self):
        """Grey status should be yellow with dark text."""
        b = status_badge("Grey")
        assert COLORS["yellow"] in b
        assert "#1a1a1a" in b  # Dark text for contrast

    def test_status_distress(self):
        """Distress status should be red."""
        b = status_badge("Distress")
        assert COLORS["red"] in b


class TestActionBadge:
    """Tests for decision action badges."""

    def test_action_buy(self):
        """Buy action should be green."""
        b = action_badge("buy")
        assert COLORS["green"] in b
        assert "BUY" in b

    def test_action_hold(self):
        """Hold action should be yellow."""
        b = action_badge("hold")
        assert COLORS["yellow"] in b
        assert "HOLD" in b

    def test_action_sell(self):
        """Sell action should be red."""
        b = action_badge("sell")
        assert COLORS["red"] in b
        assert "SELL" in b

    def test_action_pass(self):
        """Pass action should be gray."""
        b = action_badge("pass")
        assert COLORS["gray"] in b
        assert "PASS" in b

    def test_action_case_insensitive(self):
        """Action badges should be case-insensitive."""
        assert "BUY" in action_badge("BUY")
        assert "BUY" in action_badge("Buy")
        assert "BUY" in action_badge("buy")


class TestThesisStatusBadge:
    """Tests for thesis status badges."""

    def test_thesis_draft(self):
        """Draft thesis should be yellow."""
        b = thesis_status_badge("draft")
        assert COLORS["yellow"] in b
        assert "Draft" in b

    def test_thesis_active(self):
        """Active thesis should be green."""
        b = thesis_status_badge("active")
        assert COLORS["green"] in b
        assert "Active" in b

    def test_thesis_archived(self):
        """Archived thesis should be gray."""
        b = thesis_status_badge("archived")
        assert COLORS["gray"] in b
        assert "Archived" in b


class TestStarsRating:
    """Tests for star rating generation."""

    def test_full_stars(self):
        """5/5 stars should have 5 filled."""
        stars = stars_rating(5, max_stars=5)
        # Filled stars have fill="#f59e0b" (dark theme yellow/amber)
        assert stars.count('fill="#f59e0b"') == 5

    def test_no_stars(self):
        """0/5 stars should have none filled."""
        stars = stars_rating(0, max_stars=5)
        assert stars.count('fill="#f59e0b"') == 0

    def test_partial_stars(self):
        """3/5 stars should have 3 filled."""
        stars = stars_rating(3, max_stars=5)
        assert stars.count('fill="#f59e0b"') == 3

    def test_clamp_high(self):
        """Rating > max should clamp to max."""
        stars = stars_rating(10, max_stars=5)
        assert stars.count('fill="#f59e0b"') == 5

    def test_clamp_negative(self):
        """Negative rating should clamp to 0."""
        stars = stars_rating(-1, max_stars=5)
        assert stars.count('fill="#f59e0b"') == 0

    def test_custom_max_stars(self):
        """Custom max_stars should work."""
        stars = stars_rating(3, max_stars=10)
        # Should have 3 filled and 7 empty
        assert stars.count('fill="#f59e0b"') == 3
        # Count total SVG elements (10 stars)
        assert stars.count("<svg") == 10

    def test_custom_size(self):
        """Custom size parameter should be applied."""
        stars = stars_rating(1, max_stars=1, size=24)
        assert 'width="24"' in stars
        assert 'height="24"' in stars
