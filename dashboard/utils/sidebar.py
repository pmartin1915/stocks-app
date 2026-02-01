"""Shared sidebar components for all pages.

This module contains the theme toggle and other sidebar elements that should
appear consistently across all pages in the multi-page app.
"""

import streamlit as st
from dashboard.theme import get_semantic_color


def render_theme_toggle():
    """Render the dark mode toggle in sidebar.

    CRITICAL: This must be called by EVERY page in the multi-page app.
    In Streamlit multi-page apps, app.py only runs on the home page.
    Child pages need to explicitly call this to show the toggle.
    """
    # Initialize theme in session state if not present
    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    # Theme selector
    theme_col1, theme_col2 = st.sidebar.columns([3, 1])
    with theme_col1:
        st.caption("Theme")
    with theme_col2:
        # Use a toggle for cleaner UX
        is_dark = st.toggle(
            "🌙",
            value=st.session_state.theme == "dark",
            key="theme_toggle",
            help="Toggle dark mode",
        )
        new_theme = "dark" if is_dark else "light"

        # DEBUG: Log toggle state changes
        if "debug_toggle_clicks" not in st.session_state:
            st.session_state.debug_toggle_clicks = 0

        # Only rerun if theme actually changed (prevents infinite loop)
        if st.session_state.theme != new_theme:
            st.session_state.debug_toggle_clicks += 1
            st.session_state.theme = new_theme
            st.write(f"🔄 Rerunning... (click #{st.session_state.debug_toggle_clicks})")
            st.rerun()


def render_branding():
    """Render sidebar branding and navigation hints."""
    st.sidebar.title("Asymmetric")
    st.sidebar.caption("Long-term value investing research")


def render_navigation():
    """Render navigation hints in sidebar."""
    st.sidebar.divider()
    st.sidebar.markdown("""
**Navigate using the pages above:**
- **Watchlist** — Your tracked stocks
- **Screener** — Find opportunities
- **Compare** — Side-by-side analysis
- **Decisions** — Investment theses
- **Trends** — Score trajectories
- **Alerts** — Threshold monitoring
- **Portfolio** — Holdings & P&L
""")


def render_debug_info():
    """Render debug info to verify theme propagation.

    TEMPORARY: Remove this once dark mode is confirmed working.
    """
    st.sidebar.divider()
    st.sidebar.caption("🔍 Debug Info")

    # Show current theme state
    current_theme = st.session_state.get('theme', 'unknown')
    st.sidebar.text(f"Theme: {current_theme}")

    # Show color values
    green = get_semantic_color('green')
    blue = get_semantic_color('blue')
    red = get_semantic_color('red')

    st.sidebar.text(f"Green: {green}")
    st.sidebar.text(f"Blue: {blue}")
    st.sidebar.text(f"Red: {red}")

    # Expected values for verification
    if current_theme == "light":
        st.sidebar.caption("Expected: #22c55e, #3b82f6, #ef4444")
    else:
        st.sidebar.caption("Expected: #10b981, #60a5fa, #f87171")

    # Visual color swatches
    st.sidebar.markdown(f"""
<div style="display:flex; gap:10px; margin-top:10px;">
    <div style="background:{green}; width:30px; height:30px; border-radius:4px;"></div>
    <div style="background:{blue}; width:30px; height:30px; border-radius:4px;"></div>
    <div style="background:{red}; width:30px; height:30px; border-radius:4px;"></div>
</div>
""", unsafe_allow_html=True)


def render_full_sidebar():
    """Render complete sidebar with all components.

    Call this from every page to ensure consistent sidebar.
    """
    render_branding()
    render_theme_toggle()
    render_navigation()
    render_debug_info()  # TODO: Remove after dark mode verification
