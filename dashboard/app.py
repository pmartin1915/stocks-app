"""
Asymmetric Dashboard - Main Entry Point

A Streamlit-based web interface for the Asymmetric investment research workstation.

Run with: streamlit run dashboard/app.py
Or use: python run_dashboard.py
"""

import streamlit as st

from dashboard.utils.sidebar import render_full_sidebar

st.set_page_config(
    page_title="Asymmetric",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Render shared sidebar (theme toggle, branding, navigation)
render_full_sidebar()

# --- Daily Dashboard ---
st.title("Asymmetric")
st.caption("Your portfolio at a glance")

# Try to load portfolio data
try:
    from dashboard.utils.portfolio_cache import get_cached_portfolio_data

    summary, holdings, _weighted_scores, _prices = get_cached_portfolio_data()
    has_portfolio = bool(holdings)
except ImportError:
    has_portfolio = False
    summary = None
    holdings = []
except Exception as e:
    import logging
    logging.getLogger(__name__).exception("Failed to load portfolio data")
    has_portfolio = False
    summary = None
    holdings = []
    st.error(f"Could not load portfolio: {type(e).__name__}. Try `asymmetric db init` to reset.")

if has_portfolio:
    # Warn if some prices were unavailable
    if summary.missing_prices:
        st.warning(
            f"Live prices unavailable for: {', '.join(summary.missing_prices)}. "
            "Values shown use cost basis as fallback."
        )

    # Portfolio summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Value",
            f"${summary.total_market_value:,.2f}",
            help="Current market value of all holdings",
        )

    with col2:
        pnl_pct = (
            f"{summary.unrealized_pnl_percent:+.2f}%"
            if summary.unrealized_pnl_percent is not None
            else "N/A"
        )
        delta = f"${summary.unrealized_pnl:,.2f}" if summary.unrealized_pnl != 0 else None
        st.metric("Unrealized P&L", pnl_pct, delta=delta, help="Gains/losses on current holdings")

    with col3:
        holdings_with_prices = [h for h in holdings if h.unrealized_pnl is not None]
        winners = [h for h in holdings_with_prices if h.unrealized_pnl and h.unrealized_pnl > 0]
        win_rate = (len(winners) / len(holdings_with_prices) * 100) if holdings_with_prices else 0
        st.metric(
            "Win Rate",
            f"{win_rate:.0f}%",
            help=f"{len(winners)} of {len(holdings_with_prices)} positions are profitable",
        )

    with col4:
        st.metric("Positions", summary.position_count, help="Number of holdings in your portfolio")

    # Top Movers
    st.divider()
    st.subheader("Top Movers")

    if holdings_with_prices:
        sorted_by_pnl = sorted(
            holdings_with_prices,
            key=lambda h: h.unrealized_pnl_percent or 0,
            reverse=True,
        )
        best = sorted_by_pnl[:3]
        worst = sorted_by_pnl[-3:]

        col_best, col_worst = st.columns(2)

        with col_best:
            st.markdown("**Best Performers**")
            for h in best:
                pct = h.unrealized_pnl_percent or 0
                arrow = "\u25b2" if pct > 0 else "\u25bc" if pct < 0 else "\u2014"
                color = "green" if pct > 0 else "red" if pct < 0 else "gray"
                st.markdown(
                    f":{color}[{arrow} **{h.ticker}** {pct:+.1f}%]"
                    f" &nbsp; ${h.market_value:,.0f}"
                )

        with col_worst:
            st.markdown("**Worst Performers**")
            for h in worst:
                pct = h.unrealized_pnl_percent or 0
                arrow = "\u25b2" if pct > 0 else "\u25bc" if pct < 0 else "\u2014"
                color = "green" if pct > 0 else "red" if pct < 0 else "gray"
                st.markdown(
                    f":{color}[{arrow} **{h.ticker}** {pct:+.1f}%]"
                    f" &nbsp; ${h.market_value:,.0f}"
                )
    else:
        st.info("Market prices unavailable. Check back shortly.")

    # Quick Actions
    st.divider()
    st.subheader("Quick Actions")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("View Portfolio", use_container_width=True):
            st.switch_page("pages/1_Portfolio.py")
    with col2:
        if st.button("Screen Stocks", use_container_width=True):
            st.switch_page("pages/3_Screener.py")
    with col3:
        if st.button("Research a Stock", use_container_width=True):
            st.switch_page("pages/4_Research.py")
    with col4:
        if st.button("Check Alerts", use_container_width=True):
            st.switch_page("pages/8_Alerts.py")

else:
    # Onboarding for empty portfolio
    st.info("No portfolio data yet. Get started by adding your holdings.")

    st.markdown("""
### Getting Started
1. Go to **Portfolio** in the sidebar and add your first transaction
2. Or use the CLI: `asymmetric portfolio add AAPL -q 10 -p 150.00`
3. Come back here to see your dashboard
""")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Portfolio", use_container_width=True):
            st.switch_page("pages/1_Portfolio.py")
    with col2:
        if st.button("Browse Screener", use_container_width=True):
            st.switch_page("pages/3_Screener.py")

# Workflow guide (always visible)
st.divider()
with st.expander("Your Workflow"):
    st.markdown("""
**Daily** (2 min) — Open this page, check your P&L and top movers, glance at alerts

**Weekly** (15-30 min) — Screen for new opportunities, research your top picks, compare candidates

**Monthly** — Review your theses and decision outcomes, check score trends, rebalance if needed

**CLI shortcuts:**
- `asymmetric portfolio snapshot --auto` — save daily portfolio state
- `asymmetric db refresh --limit 500` — update SEC bulk data
- `asymmetric db precompute` — refresh screener scores
""")

st.caption("Asymmetric v1.0 — Investment Research Workstation")
