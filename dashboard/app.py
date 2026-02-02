"""
Asymmetric Dashboard - Main Entry Point

A Streamlit-based web interface for the Asymmetric investment research workstation.

Run with: streamlit run dashboard/app.py
Or use: python run_dashboard.py
"""

import streamlit as st
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.theme import get_semantic_color, is_dark_mode

st.set_page_config(
    page_title="Asymmetric",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Render shared sidebar (theme toggle, branding, navigation)
render_full_sidebar()

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
except Exception as e:
    # Show fallback metrics if watchlist unavailable
    with col1:
        st.metric("Watchlist Size", "—")
    with col2:
        st.metric("F-Score Range", "0-9 pts")
    with col3:
        st.metric("Z-Score Zones", "Safe/Grey/Distress")
    st.caption(f"Could not load watchlist stats: {e}")

# Debug: Dark mode indicator and color test boxes
import datetime
st.divider()
st.subheader("Dark Mode: " + ("ON" if is_dark_mode() else "OFF"))
st.caption(f"Rendered at: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

# Color test boxes
green = get_semantic_color('green')
red = get_semantic_color('red')
blue = get_semantic_color('blue')

test_col1, test_col2, test_col3 = st.columns(3)
with test_col1:
    st.markdown(f'''
    <div style="background:{green}; padding:20px; color:white; border-radius:8px;">
        <strong>GREEN</strong><br>{green}
    </div>
    ''', unsafe_allow_html=True)
with test_col2:
    st.markdown(f'''
    <div style="background:{red}; padding:20px; color:white; border-radius:8px;">
        <strong>RED</strong><br>{red}
    </div>
    ''', unsafe_allow_html=True)
with test_col3:
    st.markdown(f'''
    <div style="background:{blue}; padding:20px; color:white; border-radius:8px;">
        <strong>BLUE</strong><br>{blue}
    </div>
    ''', unsafe_allow_html=True)
