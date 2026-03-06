"""Theme system for dashboard — dark mode color management.

Provides centralized color lookups for icons, badges, and Plotly charts.
Base styling is handled by .streamlit/config.toml (dark theme).
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


# Dark theme colors (matches .streamlit/config.toml)
THEME: ThemeColors = {
    "bg_primary": "#0f172a",
    "bg_secondary": "#1e293b",
    "bg_tertiary": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_on_accent": "#ffffff",
    "text_on_yellow": "#1a1a1a",
    "border": "#475569",
}

# Semantic colors tuned for dark background visibility
SEMANTIC_COLORS = {
    "green": "#10b981",
    "yellow": "#f59e0b",
    "red": "#f87171",
    "gray": "#9ca3af",
    "blue": "#60a5fa",
}


def get_theme_name() -> str:
    """Get current theme name. Always 'dark'."""
    return "dark"


def get_theme() -> ThemeColors:
    """Get current theme colors."""
    return THEME


def get_color(key: str) -> str:
    """Get a specific theme color by key.

    Args:
        key: Color key (bg_primary, text_primary, border, etc.)

    Returns:
        Hex color string.
    """
    return THEME[key]


def get_semantic_color(key: str) -> str:
    """Get a semantic color for the dark theme.

    Args:
        key: Color key (green, yellow, red, gray, blue)

    Returns:
        Hex color string.
    """
    return SEMANTIC_COLORS.get(key, "#9ca3af")


def is_dark_mode() -> bool:
    """Check if dark mode is currently active. Always True."""
    return True


PLOTLY_COLORWAY = (
    "#60a5fa",  # blue
    "#10b981",  # green
    "#f59e0b",  # yellow
    "#f87171",  # red
    "#a78bfa",  # purple
    "#fb923c",  # orange
    "#38bdf8",  # light blue
    "#34d399",  # light green
)


def get_plotly_theme() -> dict:
    """Get Plotly layout settings for dark theme.

    Returns a dict suitable for fig.update_layout(**get_plotly_theme()).
    Includes background, font, gridlines, hover labels, legend, and colorway.
    """
    return {
        "paper_bgcolor": THEME["bg_primary"],
        "plot_bgcolor": THEME["bg_secondary"],
        "font": {
            "color": THEME["text_primary"],
            "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
        "colorway": PLOTLY_COLORWAY,
        "xaxis": {
            "gridcolor": "#334155",
            "gridwidth": 0.5,
            "zeroline": False,
            "title_font": {"size": 12, "color": THEME["text_secondary"]},
            "tickfont": {"size": 11, "color": THEME["text_secondary"]},
        },
        "yaxis": {
            "gridcolor": "#334155",
            "gridwidth": 0.5,
            "zeroline": False,
            "title_font": {"size": 12, "color": THEME["text_secondary"]},
            "tickfont": {"size": 11, "color": THEME["text_secondary"]},
        },
        "hoverlabel": {
            "bgcolor": "#1e293b",
            "bordercolor": "#475569",
            "font": {"color": "#ffffff", "size": 13},
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": THEME["text_secondary"], "size": 12},
        },
    }


def get_plotly_chart_config() -> dict:
    """Get Plotly config for mode bar cleanup.

    Returns a dict for fig.show(config=...) or st.plotly_chart(..., config=...).
    """
    return {
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "lasso2d",
            "select2d",
            "autoScale2d",
        ],
    }


def get_plotly_pie_theme() -> dict:
    """Get Plotly layout settings optimized for pie/donut charts.

    Returns a dict suitable for fig.update_layout(**get_plotly_pie_theme()).
    """
    base = get_plotly_theme()
    base["legend"] = {
        "bgcolor": "rgba(0,0,0,0)",
        "font": {"color": THEME["text_secondary"], "size": 12},
        "orientation": "h",
        "yanchor": "bottom",
        "y": -0.15,
        "xanchor": "center",
        "x": 0.5,
    }
    return base
