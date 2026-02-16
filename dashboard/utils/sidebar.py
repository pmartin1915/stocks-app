"""Shared sidebar components for all pages.

This module contains sidebar elements that should appear consistently
across all pages in the multi-page app.
"""

import streamlit as st


def render_branding():
    """Render sidebar branding and navigation hints."""
    st.sidebar.title("Asymmetric")
    st.sidebar.caption("Long-term value investing research")


def render_navigation():
    """Render navigation hints in sidebar."""
    st.sidebar.divider()
    st.sidebar.markdown("""
**Navigate using the pages above:**
- **Portfolio** — Holdings & P&L
- **Watchlist** — Your tracked stocks
- **Screener** — Find opportunities
- **Research** — Guided stock analysis
- **Compare** — Side-by-side analysis
- **Decisions** — Investment theses
- **Trends** — Score trajectories
- **Alerts** — Threshold monitoring
""")


def render_full_sidebar():
    """Render complete sidebar with all components.

    Call this from every page to ensure consistent sidebar.
    """
    render_branding()
    render_navigation()
