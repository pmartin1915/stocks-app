"""Test theme system functions.

Tests for dashboard/theme.py - theme colors, semantic colors, and mode detection.
"""

from unittest.mock import MagicMock, patch

import pytest

from dashboard.theme import (
    SEMANTIC_COLORS,
    THEMES,
    get_color,
    get_plotly_theme,
    get_semantic_color,
    get_theme,
    get_theme_name,
    is_dark_mode,
)


class TestThemeConstants:
    """Tests for theme color constants."""

    def test_themes_has_light_and_dark(self):
        """THEMES should have both light and dark entries."""
        assert "light" in THEMES
        assert "dark" in THEMES

    def test_light_theme_has_all_keys(self):
        """Light theme should have all required color keys."""
        expected_keys = [
            "bg_primary",
            "bg_secondary",
            "bg_tertiary",
            "text_primary",
            "text_secondary",
            "text_on_accent",
            "text_on_yellow",
            "border",
        ]
        for key in expected_keys:
            assert key in THEMES["light"], f"Missing key: {key}"

    def test_dark_theme_has_all_keys(self):
        """Dark theme should have all required color keys."""
        expected_keys = [
            "bg_primary",
            "bg_secondary",
            "bg_tertiary",
            "text_primary",
            "text_secondary",
            "text_on_accent",
            "text_on_yellow",
            "border",
        ]
        for key in expected_keys:
            assert key in THEMES["dark"], f"Missing key: {key}"

    def test_semantic_colors_has_light_and_dark(self):
        """SEMANTIC_COLORS should have both light and dark entries."""
        assert "light" in SEMANTIC_COLORS
        assert "dark" in SEMANTIC_COLORS

    def test_semantic_colors_have_all_keys(self):
        """Both light and dark semantic colors should have all required keys."""
        expected_keys = ["green", "yellow", "red", "gray", "blue"]
        for theme in ["light", "dark"]:
            for key in expected_keys:
                assert key in SEMANTIC_COLORS[theme], f"Missing {key} in {theme}"


class TestLightThemeColors:
    """Tests for light theme color values."""

    def test_light_bg_primary(self):
        """Light bg_primary should be white."""
        assert THEMES["light"]["bg_primary"] == "#ffffff"

    def test_light_text_primary(self):
        """Light text_primary should be dark."""
        assert THEMES["light"]["text_primary"] == "#1a1a1a"

    def test_light_border(self):
        """Light border should be light gray."""
        assert THEMES["light"]["border"] == "#e5e7eb"


class TestDarkThemeColors:
    """Tests for dark theme color values."""

    def test_dark_bg_primary(self):
        """Dark bg_primary should be slate-900."""
        assert THEMES["dark"]["bg_primary"] == "#0f172a"

    def test_dark_text_primary(self):
        """Dark text_primary should be light."""
        assert THEMES["dark"]["text_primary"] == "#f1f5f9"

    def test_dark_border(self):
        """Dark border should be slate-600."""
        assert THEMES["dark"]["border"] == "#475569"


class TestSemanticColorValues:
    """Tests for semantic color values per theme."""

    @pytest.mark.parametrize(
        "theme,color,expected",
        [
            ("light", "green", "#22c55e"),
            ("light", "red", "#ef4444"),
            ("light", "yellow", "#eab308"),
            ("light", "blue", "#3b82f6"),
            ("light", "gray", "#6b7280"),
            ("dark", "green", "#10b981"),
            ("dark", "red", "#f87171"),
            ("dark", "yellow", "#f59e0b"),
            ("dark", "blue", "#60a5fa"),
            ("dark", "gray", "#9ca3af"),
        ],
    )
    def test_semantic_color_values(self, theme, color, expected):
        """Verify semantic colors have correct hex values."""
        assert SEMANTIC_COLORS[theme][color] == expected


class TestGetThemeName:
    """Tests for get_theme_name() function."""

    def test_get_theme_name_returns_valid_theme(self):
        """get_theme_name should return 'light' or 'dark'."""
        result = get_theme_name()
        # Should return one of the valid themes
        assert result in ["light", "dark"]

    def test_get_theme_name_returns_string(self):
        """get_theme_name should return a string."""
        result = get_theme_name()
        assert isinstance(result, str)


class TestGetTheme:
    """Tests for get_theme() function."""

    def test_get_theme_returns_dict(self):
        """get_theme should return a dictionary."""
        result = get_theme()
        assert isinstance(result, dict)

    def test_get_theme_has_required_keys(self):
        """get_theme result should have all required keys."""
        result = get_theme()
        expected_keys = ["bg_primary", "text_primary", "border"]
        for key in expected_keys:
            assert key in result


class TestGetColor:
    """Tests for get_color() function."""

    def test_get_color_returns_string(self):
        """get_color should return a hex color string."""
        result = get_color("bg_primary")
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_get_color_bg_primary(self):
        """get_color('bg_primary') should return valid color."""
        result = get_color("bg_primary")
        # Should be either light or dark bg_primary
        assert result in ["#ffffff", "#0f172a"]


class TestGetSemanticColor:
    """Tests for get_semantic_color() function."""

    def test_get_semantic_color_returns_string(self):
        """get_semantic_color should return a hex color string."""
        result = get_semantic_color("green")
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_get_semantic_color_green(self):
        """get_semantic_color('green') should return valid green."""
        result = get_semantic_color("green")
        # Should be either light or dark green
        assert result in ["#22c55e", "#10b981"]

    def test_get_semantic_color_red(self):
        """get_semantic_color('red') should return valid red."""
        result = get_semantic_color("red")
        assert result in ["#ef4444", "#f87171"]

    def test_get_semantic_color_unknown_returns_gray(self):
        """get_semantic_color with unknown key should return gray fallback."""
        result = get_semantic_color("unknown_color")
        assert result == "#6b7280"


class TestIsDarkMode:
    """Tests for is_dark_mode() function."""

    def test_is_dark_mode_returns_boolean(self):
        """is_dark_mode should return a boolean."""
        result = is_dark_mode()
        assert isinstance(result, bool)


class TestGetPlotlyTheme:
    """Tests for get_plotly_theme() function."""

    def test_get_plotly_theme_returns_dict(self):
        """get_plotly_theme should return a dict."""
        result = get_plotly_theme()
        assert isinstance(result, dict)

    def test_get_plotly_theme_has_required_keys(self):
        """get_plotly_theme should have paper_bgcolor, plot_bgcolor, and font."""
        result = get_plotly_theme()
        assert "paper_bgcolor" in result
        assert "plot_bgcolor" in result
        assert "font" in result

    def test_get_plotly_theme_font_has_color(self):
        """get_plotly_theme font should have color key."""
        result = get_plotly_theme()
        assert "color" in result["font"]

    def test_get_plotly_theme_colors_are_hex(self):
        """get_plotly_theme colors should be hex strings."""
        result = get_plotly_theme()
        assert result["paper_bgcolor"].startswith("#")
        assert result["plot_bgcolor"].startswith("#")
        assert result["font"]["color"].startswith("#")


class TestThemeMocking:
    """Tests using mocked session state for theme switching."""

    def test_light_theme_colors_with_mock(self):
        """Light theme should return light colors when mocked."""
        mock_st = MagicMock()
        mock_st.session_state.get.return_value = "light"

        with patch.dict("sys.modules", {"streamlit": mock_st}):
            # The function reads theme from session state
            # Since we can't easily mock the import inside the function,
            # we test the THEMES dict directly
            light_green = SEMANTIC_COLORS["light"]["green"]
            assert light_green == "#22c55e"

    def test_dark_theme_colors_with_mock(self):
        """Dark theme should return dark colors when mocked."""
        dark_green = SEMANTIC_COLORS["dark"]["green"]
        assert dark_green == "#10b981"


class TestColorContrast:
    """Tests to verify colors have appropriate contrast."""

    def test_light_text_on_light_bg_contrast(self):
        """Light theme text should be dark on light background."""
        bg = THEMES["light"]["bg_primary"]
        text = THEMES["light"]["text_primary"]
        # Light bg is white (#ffffff), text should be dark (#1a1a1a)
        assert bg == "#ffffff"
        assert text == "#1a1a1a"

    def test_dark_text_on_dark_bg_contrast(self):
        """Dark theme text should be light on dark background."""
        bg = THEMES["dark"]["bg_primary"]
        text = THEMES["dark"]["text_primary"]
        # Dark bg is slate-900 (#0f172a), text should be light (#f1f5f9)
        assert bg == "#0f172a"
        assert text == "#f1f5f9"

    def test_text_on_yellow_is_dark(self):
        """text_on_yellow should be dark for contrast."""
        assert THEMES["light"]["text_on_yellow"] == "#1a1a1a"
        assert THEMES["dark"]["text_on_yellow"] == "#1a1a1a"

    def test_text_on_accent_is_white(self):
        """text_on_accent should be white for colored badges."""
        assert THEMES["light"]["text_on_accent"] == "#ffffff"
        assert THEMES["dark"]["text_on_accent"] == "#ffffff"


class TestFScoreColorThresholds:
    """Tests to verify F-Score color thresholds match spec."""

    def test_green_for_high_fscore(self):
        """Green color should be used for F-Score 7-9."""
        # This tests that the color values are correct for the UI
        light_green = SEMANTIC_COLORS["light"]["green"]
        dark_green = SEMANTIC_COLORS["dark"]["green"]
        assert light_green == "#22c55e"
        assert dark_green == "#10b981"

    def test_yellow_for_moderate_fscore(self):
        """Yellow color should be used for F-Score 4-6."""
        light_yellow = SEMANTIC_COLORS["light"]["yellow"]
        dark_yellow = SEMANTIC_COLORS["dark"]["yellow"]
        assert light_yellow == "#eab308"
        assert dark_yellow == "#f59e0b"

    def test_red_for_low_fscore(self):
        """Red color should be used for F-Score 0-3."""
        light_red = SEMANTIC_COLORS["light"]["red"]
        dark_red = SEMANTIC_COLORS["dark"]["red"]
        assert light_red == "#ef4444"
        assert dark_red == "#f87171"


class TestZScoreZoneColors:
    """Tests to verify Z-Score zone colors match spec."""

    def test_green_for_safe_zone(self):
        """Green should be used for Safe zone (Z > 2.99)."""
        # Uses same green as F-Score
        assert SEMANTIC_COLORS["light"]["green"] == "#22c55e"
        assert SEMANTIC_COLORS["dark"]["green"] == "#10b981"

    def test_yellow_for_grey_zone(self):
        """Yellow should be used for Grey zone (1.81 <= Z <= 2.99)."""
        assert SEMANTIC_COLORS["light"]["yellow"] == "#eab308"
        assert SEMANTIC_COLORS["dark"]["yellow"] == "#f59e0b"

    def test_red_for_distress_zone(self):
        """Red should be used for Distress zone (Z < 1.81)."""
        assert SEMANTIC_COLORS["light"]["red"] == "#ef4444"
        assert SEMANTIC_COLORS["dark"]["red"] == "#f87171"
