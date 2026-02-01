"""
Asymmetric Dashboard - Main Entry Point

A Streamlit-based web interface for the Asymmetric investment research workstation.

Run with: streamlit run dashboard/app.py
Or use: python run_dashboard.py
"""

import streamlit as st

st.set_page_config(
    page_title="Asymmetric",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize theme in session state (must be before any theme-dependent rendering)
if "theme" not in st.session_state:
    st.session_state.theme = "light"

# Sidebar branding
st.sidebar.title("Asymmetric")
st.sidebar.caption("Long-term value investing research")

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
    st.session_state.theme = "dark" if is_dark else "light"

st.sidebar.divider()

# Navigation hints in sidebar
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

# Main page content
st.title("Welcome to Asymmetric")

st.markdown("""
Asymmetric is a CLI-first investment research workstation built for long-term
value investors. This dashboard provides a visual interface for:

### Core Features
- **Watchlist** — Track stocks with F-Score and Z-Score indicators
- **Screener** — Filter by quantitative criteria using bulk SEC data
- **Compare** — Side-by-side analysis with AI-powered insights via Gemini
- **Decisions** — Track investment theses and decision logs

### New Features
- **Trends** — Visualize F-Score and Z-Score trajectories over time with interactive Plotly charts
- **Alerts** — Configure threshold alerts for score changes and zone transitions
- **Portfolio** — Track holdings with FIFO cost basis, P&L, and portfolio-weighted scores

---

**Quick Start:**
1. Navigate to **Watchlist** in the sidebar
2. Add stocks you want to track
3. Click **Refresh Scores** to fetch current data from SEC EDGAR

*Note: SEC data is rate-limited to 5 requests/second. Refreshing many stocks may take a moment.*
""")

# Show some stats if available
st.divider()
col1, col2, col3 = st.columns(3)

try:
    from dashboard.utils.watchlist import get_stocks

    stocks = get_stocks()
    with col1:
        st.metric("Watchlist Size", len(stocks))
    with col2:
        st.metric("F-Score Range", "0-9 pts")
    with col3:
        st.metric("Z-Score Zones", "Safe/Grey/Distress")
except Exception:
    pass
