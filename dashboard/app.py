"""
Asymmetric Dashboard - Main Entry Point

A Streamlit-based web interface for the Asymmetric investment research workstation.

Run with: streamlit run dashboard/app.py
Or use: python run_dashboard.py
"""

import streamlit as st
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.theme import get_semantic_color, get_color, is_dark_mode

st.set_page_config(
    page_title="Asymmetric",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Render shared sidebar (theme toggle, branding, navigation)
render_full_sidebar()

# DIAGNOSTIC: Test if colors are actually changing
st.info(f"🧪 Dark Mode: {'ON' if is_dark_mode() else 'OFF'}")

# Test color swatches
green = get_semantic_color("green")
red = get_semantic_color("red")
blue = get_semantic_color("blue")
bg = get_color("bg_primary")
text = get_color("text_primary")

st.markdown(f"""
### Color Test (Should Change with Theme Toggle)
<div style="display:flex; gap:20px; padding:20px; background:{bg};">
    <div style="background:{green}; padding:20px; border-radius:8px; color:white; font-weight:bold;">
        GREEN<br/>{green}
    </div>
    <div style="background:{red}; padding:20px; border-radius:8px; color:white; font-weight:bold;">
        RED<br/>{red}
    </div>
    <div style="background:{blue}; padding:20px; border-radius:8px; color:white; font-weight:bold;">
        BLUE<br/>{blue}
    </div>
    <div style="background:{bg}; border:2px solid {text}; padding:20px; border-radius:8px; color:{text}; font-weight:bold;">
        TEXT<br/>{text}
    </div>
</div>
""", unsafe_allow_html=True)

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
