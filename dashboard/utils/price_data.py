"""Price data fetching with Streamlit caching.

Thin wrapper around asymmetric.core.data.market_data that adds
Streamlit-specific caching (@st.cache_data). All actual fetching
logic lives in the core module so CLI and MCP can use it too.
"""

from typing import Optional

import streamlit as st

# Re-export core functions that don't need caching
from asymmetric.core.data.market_data import (  # noqa: F401
    YFINANCE_AVAILABLE,
    calc_return as _calc_return,
    format_large_number,
    format_percentage,
)
from asymmetric.core.data.market_data import (
    fetch_batch_prices,
    fetch_price_data,
    fetch_price_history,
)


@st.cache_data(ttl=900)  # Cache 15 minutes
def get_price_data(ticker: str) -> dict:
    """Fetch current price data with Streamlit caching (15 min TTL)."""
    return fetch_price_data(ticker)


@st.cache_data(ttl=3600)  # Cache 1 hour
def get_price_history(ticker: str, period: str = "1y") -> dict:
    """Fetch price history with Streamlit caching (1 hour TTL)."""
    return fetch_price_history(ticker, period)


@st.cache_data(ttl=900)  # Cache 15 minutes
def get_batch_price_data(tickers: tuple[str, ...]) -> dict[str, dict]:
    """Fetch batch prices with Streamlit caching (15 min TTL)."""
    return fetch_batch_prices(tickers)


@st.cache_data(ttl=86400)  # Cache 24 hours (sectors rarely change)
def get_sector_data(tickers: tuple[str, ...]) -> dict[str, dict[str, Optional[str]]]:
    """Fetch sector and industry data for multiple tickers.

    Uses fetch_price_data() per ticker since yf.download() doesn't return
    sector info. Results cached for 24 hours since sectors rarely change.

    Args:
        tickers: Tuple of ticker symbols (tuple for hashability in cache).

    Returns:
        Dict mapping ticker -> {"sector": str|None, "industry": str|None}.
    """
    results = {}
    for ticker in tickers:
        data = fetch_price_data(ticker)
        results[ticker] = {
            "sector": data.get("sector"),
            "industry": data.get("industry"),
        }
    return results
