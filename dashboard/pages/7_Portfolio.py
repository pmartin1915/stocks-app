"""
Portfolio Page - Track holdings, transactions, and P&L.

Manage your investment portfolio with average cost basis tracking,
realized/unrealized P&L, and portfolio-weighted score analysis.
"""

import streamlit as st

from asymmetric.core.portfolio import PortfolioManager
from dashboard.components.portfolio import (
    render_holdings_tab,
    render_performance_tab,
    render_historical_tab,
    render_add_transaction_tab,
    render_transaction_history_tab,
    render_health_tab,
)
from dashboard.utils.portfolio_cache import get_cached_portfolio_data
from dashboard.utils.session_state import init_page_state
from dashboard.utils.sidebar import render_full_sidebar

# Initialize session state for this page
init_page_state("portfolio")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Portfolio")
st.caption("Track holdings, transactions, and portfolio health")

# Initialize manager
manager = PortfolioManager()

# Fetch portfolio data (cached 60s — avoids redundant DB + yfinance calls on tab switches)
try:
    summary, holdings, weighted_scores, _prices = get_cached_portfolio_data()
except Exception as e:
    st.error(f"Error loading portfolio data: {e}")
    st.info("Please check your database connection and try refreshing the page.")
    st.info("If the problem persists, try running: `asymmetric db init`")
    st.stop()

# Top-level metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Market Value", f"${summary.total_market_value:,.2f}", help="Current market value of all holdings")

with col2:
    unrealized_delta = f"${summary.unrealized_pnl:,.2f}" if summary.unrealized_pnl != 0 else None
    st.metric("Unrealized P&L", f"{summary.unrealized_pnl_percent:+.2f}%", delta=unrealized_delta, help="Unrealized gains/losses on current holdings")

with col3:
    st.metric("Positions", summary.position_count, help="Number of holdings")

with col4:
    st.metric("Realized P&L (Total)", f"${summary.realized_pnl_total:,.2f}", help="Total realized gains/losses from sells")

with col5:
    total_return_pct = 0.0
    if summary.cash_invested > 0:
        total_return_pct = ((summary.realized_pnl_total + summary.unrealized_pnl) / summary.cash_invested) * 100
    st.metric("Total Return", f"{total_return_pct:+.2f}%", help="Combined realized + unrealized return")

st.divider()

# Tabs — delegate rendering to component modules
tab_holdings, tab_performance, tab_historical, tab_add, tab_history, tab_health = st.tabs([
    "Holdings",
    "Performance",
    "Historical",
    "Add Transaction",
    "Transaction History",
    "Portfolio Health",
])

with tab_holdings:
    render_holdings_tab(holdings, manager, _prices)

with tab_performance:
    render_performance_tab(holdings)

with tab_historical:
    render_historical_tab()

with tab_add:
    render_add_transaction_tab(manager)

with tab_history:
    render_transaction_history_tab(manager)

with tab_health:
    render_health_tab(holdings, weighted_scores, manager)

# Sidebar quick stats
st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Stats**")
st.sidebar.metric("Market Value", f"${summary.total_market_value:,.0f}")
st.sidebar.metric("Unrealized P&L", f"${summary.unrealized_pnl:+,.0f}")
st.sidebar.metric("Positions", summary.position_count)
st.sidebar.metric("Cash Invested", f"${summary.cash_invested:,.0f}")
st.sidebar.metric("Cash Received", f"${summary.cash_received:,.0f}")
