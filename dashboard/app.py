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

# Sidebar branding
st.sidebar.title("Asymmetric")
st.sidebar.caption("Long-term value investing research")
st.sidebar.divider()

# Navigation hints in sidebar
st.sidebar.markdown("""
**Navigate using the pages above:**
- **Watchlist** — Your tracked stocks
- **Screener** — Find opportunities
- **Compare** — Side-by-side analysis
- **Decisions** — Investment theses
""")

# Main page content
st.title("Welcome to Asymmetric")

st.markdown("""
Asymmetric is a CLI-first investment research workstation built for long-term
value investors. This dashboard provides a visual interface for:

### Watchlist
View your tracked stocks with current **Piotroski F-Score** (financial health)
and **Altman Z-Score** (bankruptcy risk) at a glance.

### Screener
Filter the universe of stocks by quantitative criteria to find new opportunities.
Uses precomputed scores from bulk SEC data for instant results.

### Compare
Side-by-side comparison of 2-3 stocks with detailed score breakdowns and
AI-powered analysis via Gemini.

### Decisions
Track your investment theses and decision log over time.

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
