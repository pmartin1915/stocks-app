"""Score calculation utilities for the dashboard.

Provides functions to calculate Piotroski F-Score and Altman Z-Score
for stocks using the SEC EDGAR client.
"""

import logging
from typing import Any, Callable

import streamlit as st

from asymmetric.core.data.edgar_client import EdgarClient
from asymmetric.core.data.exceptions import (
    InsufficientDataError,
    SECEmptyResponseError,
    SECRateLimitError,
)
from asymmetric.core.scoring import AltmanScorer, PiotroskiScorer

logger = logging.getLogger(__name__)


@st.cache_resource
def get_edgar_client() -> EdgarClient:
    """Get a cached EdgarClient instance."""
    return EdgarClient()


def get_scores_for_ticker(ticker: str) -> dict[str, Any]:
    """
    Calculate F-Score and Z-Score for a ticker.

    Uses the SEC EDGAR API (rate limited to 5 req/s).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dict with piotroski and altman score data, or error info.
        On success:
        {
            "piotroski": {...},
            "altman": {...}
        }
        On error:
        {
            "error": "rate_limited" | "graylisted" | "no_data" | "unknown",
            "message": "Human-readable error description"
        }
    """
    client = get_edgar_client()
    ticker = ticker.upper()

    try:
        financials = client.get_financials(ticker, periods=2)

        if not financials.get("periods"):
            logger.warning("No financial periods found for %s", ticker)
            return {
                "error": "no_data",
                "message": f"No financial data found for {ticker}. Company may not file with SEC.",
            }

        periods = financials["periods"]
        if len(periods) < 1:
            return {
                "error": "no_data",
                "message": f"No financial periods available for {ticker}.",
            }

        current = periods[0]
        prior = periods[1] if len(periods) > 1 else {}

        result: dict[str, Any] = {"piotroski": None, "altman": None}

        # Calculate Piotroski F-Score
        try:
            scorer = PiotroskiScorer()
            f_result = scorer.calculate_from_dict(current, prior)
            result["piotroski"] = {
                "score": f_result.score,
                "interpretation": f_result.interpretation,
                "profitability": f_result.profitability_score,
                "leverage": f_result.leverage_score,
                "efficiency": f_result.efficiency_score,
                "signals_available": f_result.signals_available,
                "signals": {
                    "positive_roa": f_result.positive_roa,
                    "positive_cfo": f_result.positive_cfo,
                    "roa_improving": f_result.roa_improving,
                    "accruals_quality": f_result.accruals_quality,
                    "leverage_decreasing": f_result.leverage_decreasing,
                    "current_ratio_improving": f_result.current_ratio_improving,
                    "no_dilution": f_result.no_dilution,
                    "gross_margin_improving": f_result.gross_margin_improving,
                    "asset_turnover_improving": f_result.asset_turnover_improving,
                },
            }
        except InsufficientDataError as e:
            logger.warning("Insufficient data for Piotroski F-Score on %s: %s", ticker, e)

        # Calculate Altman Z-Score
        try:
            scorer = AltmanScorer()
            z_result = scorer.calculate_from_dict(current, require_all_components=False)
            result["altman"] = {
                "z_score": z_result.z_score,
                "zone": z_result.zone,
                "interpretation": z_result.interpretation,
                "formula_used": z_result.formula_used,
                "components_calculated": z_result.components_calculated,
                "components_required": z_result.components_required,
                "is_approximate": z_result.is_approximate,
            }
        except InsufficientDataError as e:
            logger.warning("Insufficient data for Altman Z-Score on %s: %s", ticker, e)

        return result

    except SECRateLimitError as e:
        logger.warning("SEC rate limit for %s: %s", ticker, e)
        return {
            "error": "rate_limited",
            "message": "SEC rate limit reached. Please wait a moment and try again.",
        }

    except SECEmptyResponseError as e:
        logger.error("SEC graylisting for %s: %s", ticker, e)
        return {
            "error": "graylisted",
            "message": "SEC is throttling requests. Please wait several minutes before retrying.",
        }

    except Exception as e:
        logger.error("Error calculating scores for %s: %s", ticker, e)
        return {
            "error": "unknown",
            "message": f"Unexpected error: {str(e)}",
        }


def refresh_scores(
    tickers: list[str],
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """
    Refresh scores for multiple tickers.

    Args:
        tickers: List of ticker symbols.
        progress_callback: Optional callback function(ticker, current, total)
                          called after each ticker is processed.

    Returns:
        Dict mapping ticker to score data (or None if error).
    """
    results: dict[str, dict[str, Any] | None] = {}
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(ticker, i + 1, total)

        results[ticker] = get_scores_for_ticker(ticker)

    return results


def get_fscore_color(score: int) -> str:
    """
    Get color for F-Score display.

    Args:
        score: Piotroski F-Score (0-9).

    Returns:
        Color name: "green", "orange", or "red".
    """
    if score >= 7:
        return "green"
    elif score >= 4:
        return "orange"
    else:
        return "red"


def get_zone_color(zone: str) -> str:
    """
    Get color for Z-Score zone display.

    Args:
        zone: Altman zone ("Safe", "Grey", "Distress").

    Returns:
        Color name: "green", "orange", or "red".
    """
    from dashboard.config import ZSCORE_ZONES

    zone_config = ZSCORE_ZONES.get(zone, {})
    return zone_config.get("color", "grey")


def get_zone_icon(zone: str) -> str:
    """
    Get SVG icon for Z-Score zone display.

    Args:
        zone: Altman zone ("Safe", "Grey", "Distress").

    Returns:
        SVG icon HTML string.
    """
    from dashboard.components import icons

    return icons.status_icon(zone.lower() if zone else "neutral")
