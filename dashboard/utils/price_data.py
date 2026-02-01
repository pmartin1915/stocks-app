"""Price data fetching via Yahoo Finance.

Provides real-time and historical price data for stock cards
and sparkline visualizations.
"""

from datetime import datetime
from typing import Optional

import streamlit as st

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@st.cache_data(ttl=300)  # Cache 5 minutes
def get_price_data(ticker: str) -> dict:
    """Fetch current price and key metrics.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL").

    Returns:
        Dictionary with price data or error key if failed.
    """
    if not YFINANCE_AVAILABLE:
        return {"error": "yfinance not installed. Run: pip install yfinance"}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Handle case where ticker doesn't exist
        if not info or info.get("regularMarketPrice") is None:
            return {"error": f"No data found for ticker: {ticker}"}

        return {
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "change": info.get("regularMarketChange"),
            "change_pct": info.get("regularMarketChangePercent"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("regularMarketVolume"),
            "avg_volume": info.get("averageVolume"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "short_name": info.get("shortName"),
            "long_name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "fetched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600)  # Cache 1 hour
def get_price_history(ticker: str, period: str = "1y") -> dict:
    """Fetch historical prices for sparkline/chart.

    Args:
        ticker: Stock ticker symbol.
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).

    Returns:
        Dictionary with dates, prices, and calculated returns.
    """
    if not YFINANCE_AVAILABLE:
        return {"error": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return {"error": f"No history found for ticker: {ticker}"}

        return {
            "dates": hist.index.strftime("%Y-%m-%d").tolist(),
            "prices": hist["Close"].tolist(),
            "volumes": hist["Volume"].tolist(),
            "returns_1d": _calc_return(hist, 1),
            "returns_1w": _calc_return(hist, 5),
            "returns_1m": _calc_return(hist, 21),
            "returns_3m": _calc_return(hist, 63),
            "returns_1y": _calc_return(hist, 252),
        }
    except Exception as e:
        return {"error": str(e)}


def _calc_return(hist, days: int) -> Optional[float]:
    """Calculate return over N trading days.

    Args:
        hist: DataFrame with price history.
        days: Number of trading days.

    Returns:
        Percentage return or None if insufficient data.
    """
    if len(hist) < days + 1:
        return None
    try:
        return ((hist["Close"].iloc[-1] / hist["Close"].iloc[-days - 1]) - 1) * 100
    except (ZeroDivisionError, IndexError):
        return None


def format_large_number(n: Optional[float]) -> str:
    """Format large numbers in B/M/K notation.

    Args:
        n: Number to format (e.g., market cap).

    Returns:
        Formatted string (e.g., "$1.5T", "$250B", "$50M").
    """
    if n is None:
        return "N/A"
    if n >= 1e12:
        return f"${n / 1e12:.1f}T"
    elif n >= 1e9:
        return f"${n / 1e9:.1f}B"
    elif n >= 1e6:
        return f"${n / 1e6:.1f}M"
    elif n >= 1e3:
        return f"${n / 1e3:.1f}K"
    return f"${n:,.0f}"


def format_percentage(pct: Optional[float], include_sign: bool = True) -> str:
    """Format percentage with optional sign.

    Args:
        pct: Percentage value.
        include_sign: Whether to include +/- sign.

    Returns:
        Formatted percentage string.
    """
    if pct is None:
        return "N/A"
    if include_sign:
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.2f}%"
    return f"{pct:.2f}%"
