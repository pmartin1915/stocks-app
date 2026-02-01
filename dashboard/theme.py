"""Theme system for dashboard dark/light mode support.

Provides centralized color management with theme switching via session state.
"""

from typing import TypedDict


class ThemeColors(TypedDict):
    """Color scheme for a theme."""

    bg_primary: str  # Main background
    bg_secondary: str  # Cards, containers
    bg_tertiary: str  # AI content, subtle areas
    text_primary: str  # Main text
    text_secondary: str  # Labels, captions
    text_on_accent: str  # White text on colored badges
    text_on_yellow: str  # Dark text for yellow badges (contrast)
    border: str  # Dividers, borders


# Theme color palettes
THEMES: dict[str, ThemeColors] = {
    "light": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8fafc",
        "bg_tertiary": "#f1f5f9",
        "text_primary": "#1a1a1a",
        "text_secondary": "#6b7280",
        "text_on_accent": "#ffffff",
        "text_on_yellow": "#1a1a1a",
        "border": "#e5e7eb",
    },
    "dark": {
        "bg_primary": "#0f172a",
        "bg_secondary": "#1e293b",
        "bg_tertiary": "#334155",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_on_accent": "#ffffff",
        "text_on_yellow": "#1a1a1a",  # Keep dark for yellow contrast
        "border": "#475569",
    },
}

# Semantic colors adjusted for dark mode visibility
SEMANTIC_COLORS = {
    "light": {
        "green": "#22c55e",
        "yellow": "#eab308",
        "red": "#ef4444",
        "gray": "#6b7280",
        "blue": "#3b82f6",
    },
    "dark": {
        "green": "#10b981",  # Brighter emerald
        "yellow": "#f59e0b",  # Amber for better contrast
        "red": "#f87171",  # Lighter red
        "gray": "#9ca3af",  # Brighter gray
        "blue": "#60a5fa",  # Lighter blue
    },
}


def get_theme_name() -> str:
    """Get current theme name from session state."""
    try:
        import streamlit as st

        return st.session_state.get("theme", "light")
    except Exception:
        return "light"


def get_theme() -> ThemeColors:
    """Get current theme colors from session state."""
    theme_name = get_theme_name()
    return THEMES.get(theme_name, THEMES["light"])


def get_color(key: str) -> str:
    """Get a specific theme color by key.

    Args:
        key: Color key (bg_primary, text_primary, border, etc.)

    Returns:
        Hex color string.
    """
    return get_theme()[key]


def get_semantic_color(key: str) -> str:
    """Get a semantic color adjusted for current theme.

    Args:
        key: Color key (green, yellow, red, gray, blue)

    Returns:
        Hex color string.
    """
    theme_name = get_theme_name()
    colors = SEMANTIC_COLORS.get(theme_name, SEMANTIC_COLORS["light"])
    return colors.get(key, "#6b7280")


def is_dark_mode() -> bool:
    """Check if dark mode is currently active."""
    return get_theme_name() == "dark"
