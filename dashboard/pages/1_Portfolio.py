"""
Portfolio Page - Track holdings, transactions, and P&L.

Manage your investment portfolio with lot-level cost basis tracking,
realized/unrealized P&L, and portfolio-weighted score analysis.
"""

import streamlit as st

from asymmetric.core.portfolio import PortfolioManager
from dashboard.components.page_header import render_page_header
from dashboard.components.portfolio import (
    render_holdings_tab,
    render_performance_tab,
    render_historical_tab,
    render_add_transaction_tab,
    render_transaction_history_tab,
    render_health_tab,
)
from dashboard.styles import inject_global_styles, metric_card, page_footer
from dashboard.theme import THEME
from dashboard.utils.portfolio_cache import get_cached_portfolio_data
from dashboard.utils.session_state import init_page_state
from dashboard.utils.sidebar import render_full_sidebar

# Initialize session state for this page
init_page_state("portfolio")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar(current_page="portfolio")
inject_global_styles()

render_page_header(
    title="Portfolio",
    subtitle="Track holdings, transactions, and portfolio health",
    breadcrumbs=[("Home", "app.py"), ("Portfolio", "")],
)

# Initialize manager
manager = PortfolioManager()

# Fetch portfolio data (cached 60s — avoids redundant DB + yfinance calls on tab switches)
try:
    with st.spinner("Loading portfolio data..."):
        summary, holdings, weighted_scores, _prices = get_cached_portfolio_data()
except Exception as e:
    st.error(f"Error loading portfolio data: {e}")
    st.info("Please check your database connection and try refreshing the page.")
    st.info("If the problem persists, try running: `asymmetric db init`")
    # Show navigation instead of halting the page entirely
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Go to Watchlist"):
            st.switch_page("pages/2_Watchlist.py")
    with col_b:
        if st.button("Retry"):
            st.rerun()
    st.stop()

# Warn if some prices were unavailable
if summary.missing_prices:
    st.warning(
        f"Live prices unavailable for: {', '.join(summary.missing_prices)}. "
        "Values shown use cost basis as fallback."
    )

# Top-level metrics — 3+2 layout for readability
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        metric_card("Total Market Value", f"${summary.total_market_value:,.2f}"),
        unsafe_allow_html=True,
    )

with col2:
    unrealized_pnl_pct = f"{summary.unrealized_pnl_percent:+.2f}%" if summary.unrealized_pnl_percent is not None else "N/A"
    delta_text = f"${summary.unrealized_pnl:+,.2f}" if summary.unrealized_pnl != 0 else ""
    delta_type = "positive" if summary.unrealized_pnl > 0 else "negative" if summary.unrealized_pnl < 0 else "neutral"
    st.markdown(
        metric_card("Unrealized P&L", unrealized_pnl_pct, delta=delta_text, delta_type=delta_type),
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        metric_card("Positions", str(summary.position_count)),
        unsafe_allow_html=True,
    )

col4, col5 = st.columns(2)

with col4:
    realized_text = f"${summary.realized_pnl_total:,.2f}"
    realized_delta = f"${summary.realized_pnl_total:+,.2f}" if summary.realized_pnl_total != 0 else ""
    realized_type = "positive" if summary.realized_pnl_total > 0 else "negative" if summary.realized_pnl_total < 0 else "neutral"
    st.markdown(
        metric_card("Realized P&L (Total)", realized_text, delta=realized_delta, delta_type=realized_type),
        unsafe_allow_html=True,
    )

with col5:
    total_return_pct = 0.0
    if summary.cash_invested > 0:
        total_return_pct = ((summary.realized_pnl_total + summary.unrealized_pnl) / summary.cash_invested) * 100
    return_delta = f"{total_return_pct:+.2f}%" if total_return_pct != 0 else ""
    return_type = "positive" if total_return_pct > 0 else "negative" if total_return_pct < 0 else "neutral"
    st.markdown(
        metric_card("Total Return", f"{total_return_pct:+.2f}%", delta=return_delta, delta_type=return_type),
        unsafe_allow_html=True,
    )

st.divider()

# 3-tab layout: Overview, Performance, Transactions
tab_overview, tab_performance, tab_transactions = st.tabs([
    "Overview",
    "Performance",
    "Transactions",
])

with tab_overview:
    # Holdings table + allocation charts
    render_holdings_tab(holdings, manager, _prices)

    # Portfolio Health (collapsed by default, below holdings)
    with st.expander("Portfolio Health", expanded=False):
        render_health_tab(holdings, weighted_scores, manager)

with tab_performance:
    # Performance analysis (winners/losers, metrics)
    render_performance_tab(holdings)

    st.divider()

    # Historical charts (snapshots, time-series)
    render_historical_tab()

with tab_transactions:
    # Add transaction form
    render_add_transaction_tab(manager)

    st.divider()

    # Transaction history table
    render_transaction_history_tab(manager)

# Sidebar quick stats
st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;'
    f'letter-spacing:0.05em;color:{THEME["text_secondary"]};padding:4px 0 8px">Quick Stats</div>',
    unsafe_allow_html=True,
)
st.sidebar.metric("Market Value", f"${summary.total_market_value:,.0f}")
st.sidebar.metric("Unrealized P&L", f"${summary.unrealized_pnl:+,.0f}")
st.sidebar.metric("Positions", summary.position_count)
st.sidebar.metric("Cash Invested", f"${summary.cash_invested:,.0f}")
st.sidebar.metric("Cash Received", f"${summary.cash_received:,.0f}")

page_footer()
