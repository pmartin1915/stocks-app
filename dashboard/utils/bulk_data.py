"""Bulk data utilities for the dashboard.

Provides cached wrappers around BulkDataManager for use in
Streamlit pages, particularly the Screener.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


@st.cache_resource
def get_bulk_manager() -> "BulkDataManager":
    """
    Get a cached BulkDataManager instance.

    Uses st.cache_resource to maintain the DuckDB connection
    across Streamlit reruns for better performance.

    Returns:
        Initialized BulkDataManager with schema ready.
    """
    from asymmetric.core.data.bulk_manager import BulkDataManager

    bulk = BulkDataManager()
    bulk.initialize_schema()  # Ensure tables exist
    return bulk


def get_bulk_stats() -> dict[str, Any]:
    """
    Get bulk data statistics for display.

    Returns:
        Dict with:
        - ticker_count: Number of companies in database
        - fact_count: Number of financial facts
        - last_refresh: ISO timestamp of last data refresh
    """
    try:
        bulk = get_bulk_manager()
        return bulk.get_stats()
    except Exception as e:
        logger.error("Error getting bulk stats: %s", e)
        return {
            "ticker_count": 0,
            "fact_count": 0,
            "last_refresh": None,
        }


def get_scores_stats() -> dict[str, Any]:
    """
    Get precomputed scores statistics.

    Returns:
        Dict with:
        - scores_count: Number of precomputed scores
        - last_computed: ISO timestamp of last computation
    """
    try:
        bulk = get_bulk_manager()
        conn = bulk.conn

        # Get count of precomputed scores
        result = conn.execute(
            "SELECT COUNT(*) FROM precomputed_scores"
        ).fetchone()
        scores_count = result[0] if result else 0

        # Get last computation time
        result = conn.execute(
            "SELECT MAX(computed_at) FROM precomputed_scores"
        ).fetchone()
        last_computed = result[0] if result and result[0] else None

        return {
            "scores_count": scores_count,
            "last_computed": last_computed,
        }
    except Exception as e:
        logger.debug("Error getting scores stats (table may not exist): %s", e)
        return {
            "scores_count": 0,
            "last_computed": None,
        }


def has_precomputed_scores() -> bool:
    """
    Check if precomputed scores are available.

    Returns:
        True if precomputed_scores table has data.
    """
    try:
        bulk = get_bulk_manager()
        return bulk.has_precomputed_scores()
    except Exception as e:
        logger.debug("Error checking precomputed scores: %s", e)
        return False


@st.cache_data(ttl=60)
def get_screener_results(
    piotroski_min: int | None = None,
    altman_min: float | None = None,
    altman_zone: str | None = None,
    limit: int = 50,
    sort_by: str = "piotroski_score",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    """
    Get screener results from precomputed scores.

    Uses caching to avoid repeated queries when filter values
    haven't changed (cached for 60 seconds).

    Args:
        piotroski_min: Minimum F-Score (0-9), None for no filter
        altman_min: Minimum Z-Score, None for no filter
        altman_zone: Required zone ('Safe', 'Grey', 'Distress'), None for any
        limit: Maximum results to return
        sort_by: Sort field ('piotroski_score', 'altman_z_score', 'ticker')
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        List of score records matching criteria.
    """
    try:
        bulk = get_bulk_manager()
        return bulk.get_precomputed_scores(
            piotroski_min=piotroski_min,
            altman_min=altman_min,
            altman_zone=altman_zone,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        logger.error("Error getting screener results: %s", e)
        return []


def format_last_refresh(iso_str: str | None) -> str:
    """
    Format ISO timestamp to human-readable relative time.

    Args:
        iso_str: ISO format timestamp string, or None.

    Returns:
        Human-readable string like "2 hours ago", "Yesterday", "Jan 25, 2026"
    """
    if not iso_str:
        return "Never"
    try:
        # Handle both ISO format and DuckDB timestamp format
        if isinstance(iso_str, str):
            dt = datetime.fromisoformat(iso_str)
        else:
            dt = iso_str  # Already a datetime

        # Ensure timezone-aware for comparison
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        delta = now - dt

        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                if minutes <= 1:
                    return "Just now"
                return f"{minutes} minutes ago"
            if hours == 1:
                return "1 hour ago"
            return f"{hours} hours ago"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug("Error formatting timestamp %s: %s", iso_str, e)
        return "Unknown"


def get_sector_heatmap_data(results: list[dict[str, Any]]) -> Any:
    """
    Enrich screener results with sector and market cap data for treemap visualization.

    Args:
        results: List of dicts from get_screener_results with ticker, piotroski_score, etc.

    Returns:
        pandas DataFrame with: ticker, sector, market_cap, piotroski_score, altman_zone, company_name
    """
    import pandas as pd

    from dashboard.utils.price_data import get_price_data

    # Enrich each result with sector and market cap
    enriched = []

    for result in results[:50]:  # Limit to first 50 for performance
        ticker = result.get("ticker")
        if not ticker:
            continue

        # Fetch price data (which includes sector info from yfinance)
        price_info = get_price_data(ticker)

        # Default sector if not available
        sector = price_info.get("sector", "Unknown")
        if not sector or sector == "N/A":
            sector = "Unknown"

        # Get market cap
        market_cap = price_info.get("market_cap", 1_000_000)  # Default 1M if not available
        if not market_cap or market_cap == 0:
            market_cap = 1_000_000

        enriched.append({
            "ticker": ticker,
            "company_name": result.get("company_name", ticker),
            "sector": sector,
            "market_cap": market_cap,
            "piotroski_score": result.get("piotroski_score", 0),
            "altman_zone": result.get("altman_zone", "Unknown"),
        })

    return pd.DataFrame(enriched)
