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
    """Get current theme name from session state.

    Returns 'light' if called outside a Streamlit context (e.g., during testing).
    """
    try:
        import streamlit as st

        return st.session_state.get("theme", "light")
    except (ImportError, RuntimeError):
        # ImportError: streamlit not installed
        # RuntimeError: called outside Streamlit context
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
    color = colors.get(key, "#6b7280")
    return color


def is_dark_mode() -> bool:
    """Check if dark mode is currently active."""
    return get_theme_name() == "dark"


def get_plotly_theme() -> dict:
    """Get Plotly layout settings for current theme.

    Returns a dict suitable for fig.update_layout(**get_plotly_theme()).
    Sets paper background, plot background, and font colors.
    """
    theme = get_theme()
    return {
        "paper_bgcolor": theme["bg_primary"],
        "plot_bgcolor": theme["bg_secondary"],
        "font": {"color": theme["text_primary"]},
    }


def apply_theme_css() -> None:
    """Inject CSS to style Streamlit's native elements based on current theme.

    This applies background colors, text colors, and other styles to Streamlit's
    root elements that can't be styled through normal means.
    """
    import streamlit as st

    theme = get_theme()
    bg_primary = theme["bg_primary"]
    bg_secondary = theme["bg_secondary"]
    text_primary = theme["text_primary"]
    text_secondary = theme["text_secondary"]
    border = theme["border"]

    css = f"""
    <style>
        /* Main app background */
        .stApp {{
            background-color: {bg_primary};
        }}

        /* Sidebar background */
        [data-testid="stSidebar"] {{
            background-color: {bg_secondary};
        }}

        /* Main content text */
        .stApp, .stApp p, .stApp span, .stApp li {{
            color: {text_primary};
        }}

        /* Headers */
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
            color: {text_primary};
        }}

        /* Captions and secondary text */
        .stApp .stCaption, [data-testid="stCaption"] {{
            color: {text_secondary};
        }}

        /* Metric labels */
        [data-testid="stMetricLabel"] {{
            color: {text_secondary};
        }}

        /* Metric values */
        [data-testid="stMetricValue"] {{
            color: {text_primary};
        }}

        /* Sidebar text */
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] li, [data-testid="stSidebar"] label {{
            color: {text_primary};
        }}

        /* Dividers */
        hr {{
            border-color: {border};
        }}

        /* Input fields */
        .stTextInput input, .stSelectbox select, .stTextArea textarea {{
            background-color: {bg_secondary};
            color: {text_primary};
            border-color: {border};
        }}

        /* Buttons - keep default styling for primary buttons */

        /* Expanders */
        .streamlit-expanderHeader {{
            background-color: {bg_secondary};
            color: {text_primary};
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: {bg_secondary};
        }}

        .stTabs [data-baseweb="tab"] {{
            color: {text_primary};
        }}

        /* Markdown content */
        .stMarkdown {{
            color: {text_primary};
        }}

        /* Code blocks */
        .stCode, pre, code {{
            background-color: {bg_secondary};
            color: {text_primary};
        }}

        /* Info/warning/error boxes */
        [data-testid="stAlert"] {{
            background-color: {bg_secondary};
        }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)
