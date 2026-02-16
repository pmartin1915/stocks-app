"""Caching layer for portfolio data.

Avoids redundant DB queries and yfinance API calls on Streamlit page reruns
(every tab switch, button click, etc. triggers a full page rerun).

TTLs:
- 60s  for price-dependent data (summary, holdings, scores, realized P&L)
- 600s for historical snapshots (change infrequently intraday)
- 3600s for performance stats (expensive math, stable over short periods)
"""

from datetime import datetime, timedelta

import streamlit as st

from asymmetric.core.portfolio import PortfolioManager


@st.cache_data(ttl=60)
def get_cached_portfolio_data():
    """Fetch summary, holdings, weighted scores, and prices in one cached call.

    Returns:
        Tuple of (PortfolioSummary, list[HoldingDetail], WeightedScores, dict)
    """
    manager = PortfolioManager()
    holdings_basic = manager.get_holdings(include_market_data=False)
    tickers = [h.ticker for h in holdings_basic]
    try:
        prices = manager.refresh_market_prices(tickers) if tickers else {}
    except Exception:
        prices = {}
    if prices is None:
        prices = {}

    summary = manager.get_portfolio_summary(market_prices=prices)
    holdings = manager.get_holdings(market_prices=prices)
    weighted_scores = manager.get_weighted_scores(holdings=holdings)

    return summary, holdings, weighted_scores, prices


@st.cache_data(ttl=600)
def get_cached_snapshots(time_range: str):
    """Fetch snapshots for a given time range.

    Args:
        time_range: One of "7D", "30D", "90D", "YTD", "1Y", "All Time"

    Returns:
        List of PortfolioSnapshot objects.
    """
    now = datetime.now()
    start_date = None

    if time_range == "7D":
        start_date = (now - timedelta(days=7)).replace(tzinfo=None)
    elif time_range == "30D":
        start_date = (now - timedelta(days=30)).replace(tzinfo=None)
    elif time_range == "90D":
        start_date = (now - timedelta(days=90)).replace(tzinfo=None)
    elif time_range == "YTD":
        start_date = datetime(now.year, 1, 1)
    elif time_range == "1Y":
        start_date = (now - timedelta(days=365)).replace(tzinfo=None)

    manager = PortfolioManager()
    return manager.get_snapshots(start_date=start_date)


@st.cache_data(ttl=3600)
def get_cached_performance_stats(time_range: str):
    """Calculate performance stats for a given time range.

    Returns:
        Dict with performance metrics, or None if insufficient data.
    """
    snapshots = get_cached_snapshots(time_range)
    if not snapshots or len(snapshots) < 2:
        return None
    manager = PortfolioManager()
    return manager.get_performance_stats(snapshots)


@st.cache_data(ttl=60)
def get_cached_realized_pnl():
    """Fetch realized P&L grouped by ticker.

    Returns:
        Dict mapping ticker -> realized gain (float).
    """
    manager = PortfolioManager()
    return manager.get_realized_pnl_by_ticker()


def clear_portfolio_cache():
    """Clear all portfolio caches. Call after buy/sell transactions."""
    get_cached_portfolio_data.clear()
    get_cached_snapshots.clear()
    get_cached_performance_stats.clear()
    get_cached_realized_pnl.clear()
