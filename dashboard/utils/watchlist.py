"""Watchlist management utilities.

Mirrors the CLI watchlist functionality to maintain consistency.
Stores watchlist in ~/.asymmetric/watchlist.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard.config import WATCHLIST_FILE


def _ensure_watchlist_dir() -> None:
    """Ensure the watchlist directory exists."""
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_watchlist() -> dict[str, Any]:
    """Load watchlist from JSON file.

    Returns:
        Dict with 'stocks' key containing ticker data.
    """
    if not WATCHLIST_FILE.exists():
        return {"stocks": {}}

    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"stocks": {}}


def save_watchlist(watchlist: dict[str, Any]) -> None:
    """Save watchlist to JSON file.

    Args:
        watchlist: Dict with 'stocks' key containing ticker data.
    """
    _ensure_watchlist_dir()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


def get_stocks() -> list[str]:
    """Get list of ticker symbols in watchlist.

    Returns:
        List of ticker symbols (uppercase).
    """
    wl = load_watchlist()
    return list(wl.get("stocks", {}).keys())


def get_stock_data(ticker: str) -> dict[str, Any] | None:
    """Get data for a specific ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dict with added date, note, cached scores, or None if not found.
    """
    wl = load_watchlist()
    return wl.get("stocks", {}).get(ticker.upper())


def add_stock(ticker: str, note: str = "") -> bool:
    """Add a stock to the watchlist.

    Args:
        ticker: Stock ticker symbol.
        note: Optional note about the stock.

    Returns:
        True if added, False if already exists.
    """
    ticker = ticker.upper()
    wl = load_watchlist()

    if ticker in wl.get("stocks", {}):
        # Update note if provided
        if note:
            wl["stocks"][ticker]["note"] = note
            wl["stocks"][ticker]["updated"] = datetime.now().isoformat()
            save_watchlist(wl)
        return False

    if "stocks" not in wl:
        wl["stocks"] = {}

    wl["stocks"][ticker] = {
        "added": datetime.now().isoformat(),
        "note": note,
    }
    save_watchlist(wl)
    return True


def remove_stock(ticker: str) -> bool:
    """Remove a stock from the watchlist.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        True if removed, False if not found.
    """
    ticker = ticker.upper()
    wl = load_watchlist()

    if ticker not in wl.get("stocks", {}):
        return False

    del wl["stocks"][ticker]
    save_watchlist(wl)
    return True


def update_cached_scores(ticker: str, scores: dict[str, Any]) -> None:
    """Update cached scores for a ticker.

    Args:
        ticker: Stock ticker symbol.
        scores: Dict with piotroski and altman score data.
    """
    ticker = ticker.upper()
    wl = load_watchlist()

    if ticker not in wl.get("stocks", {}):
        return

    wl["stocks"][ticker]["cached_scores"] = scores
    wl["stocks"][ticker]["cached_at"] = datetime.now().isoformat()
    save_watchlist(wl)


def get_cached_scores(ticker: str) -> dict[str, Any] | None:
    """Get cached scores for a ticker if not expired.

    Returns cached scores only if they are fresher than SCORE_CACHE_TTL.
    Returns None if no cache exists or if cache has expired.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dict with cached score data, or None if no cache or expired.
    """
    from dashboard.config import SCORE_CACHE_TTL

    data = get_stock_data(ticker)
    if data and "cached_scores" in data and "cached_at" in data:
        try:
            cached_at = datetime.fromisoformat(data["cached_at"])
            age_seconds = (datetime.now() - cached_at).total_seconds()
            if age_seconds < SCORE_CACHE_TTL:
                return data["cached_scores"]
        except (ValueError, TypeError):
            pass
    return None


def is_cache_expired(ticker: str) -> bool:
    """Check if cached scores for a ticker have expired.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        True if cache exists but is expired, False otherwise.
    """
    from dashboard.config import SCORE_CACHE_TTL

    data = get_stock_data(ticker)
    if data and "cached_scores" in data and "cached_at" in data:
        try:
            cached_at = datetime.fromisoformat(data["cached_at"])
            age_seconds = (datetime.now() - cached_at).total_seconds()
            return age_seconds >= SCORE_CACHE_TTL
        except (ValueError, TypeError):
            pass
    return False


def clear_watchlist() -> int:
    """Clear all stocks from watchlist.

    Returns:
        Number of stocks removed.
    """
    wl = load_watchlist()
    count = len(wl.get("stocks", {}))
    wl["stocks"] = {}
    save_watchlist(wl)
    return count
