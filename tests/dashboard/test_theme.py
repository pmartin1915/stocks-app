"""Test theme system functions.

Tests for dashboard/theme.py - dark theme colors, semantic colors, and Plotly theme.
"""

from dashboard.theme import (
    SEMANTIC_COLORS,
    THEME,
    get_color,
    get_plotly_theme,
    get_semantic_color,
    get_theme,
    get_theme_name,
    is_dark_mode,
)


class TestThemeConstants:
    """Tests for theme color constants."""

    def test_theme_has_all_keys(self):
        """THEME should have all required color keys."""
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
            assert key in THEME, f"Missing key: {key}"

    def test_semantic_colors_have_all_keys(self):
        """Semantic colors should have all required keys."""
        expected_keys = ["green", "yellow", "red", "gray", "blue"]
        for key in expected_keys:
            assert key in SEMANTIC_COLORS, f"Missing {key}"


class TestDarkThemeColors:
    """Tests for dark theme color values."""

    def test_bg_primary(self):
        """bg_primary should be slate-900."""
        assert THEME["bg_primary"] == "#0f172a"

    def test_text_primary(self):
        """text_primary should be light."""
        assert THEME["text_primary"] == "#f1f5f9"

    def test_border(self):
        """border should be slate-600."""
        assert THEME["border"] == "#475569"

    def test_text_on_yellow_is_dark(self):
        """text_on_yellow should be dark for contrast."""
        assert THEME["text_on_yellow"] == "#1a1a1a"

    def test_text_on_accent_is_white(self):
        """text_on_accent should be white for colored badges."""
        assert THEME["text_on_accent"] == "#ffffff"


class TestSemanticColorValues:
    """Tests for semantic color values."""

    def test_green(self):
        assert SEMANTIC_COLORS["green"] == "#10b981"

    def test_red(self):
        assert SEMANTIC_COLORS["red"] == "#f87171"

    def test_yellow(self):
        assert SEMANTIC_COLORS["yellow"] == "#f59e0b"

    def test_blue(self):
        assert SEMANTIC_COLORS["blue"] == "#60a5fa"

    def test_gray(self):
        assert SEMANTIC_COLORS["gray"] == "#9ca3af"


class TestGetThemeName:
    """Tests for get_theme_name() function."""

    def test_returns_dark(self):
        """get_theme_name should always return 'dark'."""
        assert get_theme_name() == "dark"

    def test_returns_string(self):
        assert isinstance(get_theme_name(), str)


class TestGetTheme:
    """Tests for get_theme() function."""

    def test_returns_dict(self):
        result = get_theme()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = get_theme()
        for key in ["bg_primary", "text_primary", "border"]:
            assert key in result


class TestGetColor:
    """Tests for get_color() function."""

    def test_returns_hex_string(self):
        result = get_color("bg_primary")
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_bg_primary(self):
        assert get_color("bg_primary") == "#0f172a"

    def test_text_primary(self):
        assert get_color("text_primary") == "#f1f5f9"


class TestGetSemanticColor:
    """Tests for get_semantic_color() function."""

    def test_returns_hex_string(self):
        result = get_semantic_color("green")
        assert isinstance(result, str)
        assert result.startswith("#")

    def test_green(self):
        assert get_semantic_color("green") == "#10b981"

    def test_red(self):
        assert get_semantic_color("red") == "#f87171"

    def test_unknown_returns_gray(self):
        result = get_semantic_color("unknown_color")
        assert result == "#9ca3af"


class TestIsDarkMode:
    """Tests for is_dark_mode() function."""

    def test_always_true(self):
        assert is_dark_mode() is True


class TestGetPlotlyTheme:
    """Tests for get_plotly_theme() function."""

    def test_returns_dict(self):
        result = get_plotly_theme()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = get_plotly_theme()
        assert "paper_bgcolor" in result
        assert "plot_bgcolor" in result
        assert "font" in result

    def test_font_has_color(self):
        result = get_plotly_theme()
        assert "color" in result["font"]

    def test_colors_are_hex(self):
        result = get_plotly_theme()
        assert result["paper_bgcolor"].startswith("#")
        assert result["plot_bgcolor"].startswith("#")
        assert result["font"]["color"].startswith("#")

    def test_uses_dark_colors(self):
        result = get_plotly_theme()
        assert result["paper_bgcolor"] == "#0f172a"
        assert result["plot_bgcolor"] == "#1e293b"
        assert result["font"]["color"] == "#f1f5f9"


class TestColorContrast:
    """Tests to verify colors have appropriate contrast."""

    def test_dark_text_on_dark_bg(self):
        """Dark theme text should be light on dark background."""
        assert THEME["bg_primary"] == "#0f172a"
        assert THEME["text_primary"] == "#f1f5f9"
