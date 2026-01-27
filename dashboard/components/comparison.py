"""Comparison-specific display components for the dashboard."""

from typing import Any, Callable

import streamlit as st

from dashboard.components import icons
from dashboard.components.score_display import (
    render_fscore_badge,
    render_score_detail,
    render_zscore_badge,
)


def find_winner_index(
    values: list[Any | None],
    higher_is_better: bool = True,
) -> int | None:
    """
    Find the index of the winning value.

    Args:
        values: List of numeric values (or None for missing).
        higher_is_better: If True, highest value wins; if False, lowest wins.

    Returns:
        Index of winner, or None if no valid values.
    """
    # Filter to valid numeric values with their indices
    valid = [(i, v) for i, v in enumerate(values) if v is not None]

    if not valid:
        return None

    if higher_is_better:
        return max(valid, key=lambda x: x[1])[0]
    else:
        return min(valid, key=lambda x: x[1])[0]


def render_comparison_header(tickers: list[str]) -> None:
    """
    Render the comparison table header row.

    Args:
        tickers: List of ticker symbols.
    """
    cols = st.columns([1.5] + [1] * len(tickers))

    with cols[0]:
        st.markdown("**Metric**")

    for i, ticker in enumerate(tickers, 1):
        with cols[i]:
            st.markdown(f"**{ticker}**")


def render_metric_row(
    label: str,
    values: dict[str, Any],
    format_func: Callable[[Any], str],
    higher_is_better: bool = True,
    show_winner: bool = True,
) -> None:
    """
    Render a single metric row with winner highlighting.

    Args:
        label: Metric label.
        values: Dict mapping ticker to value.
        format_func: Function to format value for display.
        higher_is_better: If True, highest value wins.
        show_winner: Whether to show winner star.
    """
    tickers = list(values.keys())
    value_list = [values[t] for t in tickers]
    winner_idx = find_winner_index(value_list, higher_is_better) if show_winner else None

    cols = st.columns([1.5] + [1] * len(tickers))

    with cols[0]:
        st.caption(label)

    for i, ticker in enumerate(tickers):
        with cols[i + 1]:
            value = values[ticker]
            formatted = format_func(value) if value is not None else "N/A"

            if i == winner_idx:
                trophy = icons.trophy(size=16)
                st.markdown(f"**{formatted}** {trophy}", unsafe_allow_html=True)
            else:
                st.write(formatted)


def render_comparison_table(results: dict[str, dict]) -> None:
    """
    Render the full side-by-side comparison table.

    Args:
        results: Dict mapping ticker to score data.
    """
    # Filter to valid results only
    valid_results = {t: d for t, d in results.items() if "error" not in d}

    if len(valid_results) < 2:
        st.warning("Need at least 2 stocks with valid data for comparison.")
        return

    tickers = list(valid_results.keys())

    # Header
    render_comparison_header(tickers)
    st.divider()

    # F-Score row
    fscore_values = {
        t: valid_results[t].get("piotroski", {}).get("score")
        for t in tickers
    }
    render_metric_row(
        "F-Score",
        fscore_values,
        lambda v: f"{v}/9",
        higher_is_better=True,
    )

    # Z-Score row
    zscore_values = {
        t: valid_results[t].get("altman", {}).get("z_score")
        for t in tickers
    }
    render_metric_row(
        "Z-Score",
        zscore_values,
        lambda v: f"{v:.2f}",
        higher_is_better=True,
    )

    # Zone row (no winner highlighting for categorical)
    zone_values = {
        t: valid_results[t].get("altman", {}).get("zone")
        for t in tickers
    }
    render_metric_row(
        "Zone",
        zone_values,
        lambda v: v if v else "N/A",
        show_winner=False,
    )

    st.divider()
    st.caption("**Component Breakdown**")

    # Profitability row
    prof_values = {
        t: valid_results[t].get("piotroski", {}).get("profitability")
        for t in tickers
    }
    render_metric_row(
        "Profitability",
        prof_values,
        lambda v: f"{v}/4",
        higher_is_better=True,
    )

    # Leverage row
    lev_values = {
        t: valid_results[t].get("piotroski", {}).get("leverage")
        for t in tickers
    }
    render_metric_row(
        "Leverage/Liquidity",
        lev_values,
        lambda v: f"{v}/3",
        higher_is_better=True,
    )

    # Efficiency row
    eff_values = {
        t: valid_results[t].get("piotroski", {}).get("efficiency")
        for t in tickers
    }
    render_metric_row(
        "Efficiency",
        eff_values,
        lambda v: f"{v}/2",
        higher_is_better=True,
    )


def calculate_combined_score(data: dict) -> float | None:
    """
    Calculate a combined score for ranking candidates.

    Uses F-Score as base, with Z-Score zone bonus.

    Args:
        data: Stock data dict with piotroski and altman scores.

    Returns:
        Combined score, or None if insufficient data.
    """
    piotroski = data.get("piotroski", {})
    altman = data.get("altman", {})

    fscore = piotroski.get("score")
    zone = altman.get("zone")

    if fscore is None:
        return None

    # Base score is F-Score (0-9)
    combined = fscore

    # Zone bonus
    if zone == "Safe":
        combined += 2
    elif zone == "Grey":
        combined += 1
    # Distress gets no bonus

    return combined


def render_best_candidate(results: dict[str, dict]) -> None:
    """
    Display the suggested best candidate with reasoning.

    Args:
        results: Dict mapping ticker to score data.
    """
    # Filter to valid results
    valid_results = {t: d for t, d in results.items() if "error" not in d}

    if len(valid_results) < 2:
        return

    # Calculate combined scores
    scores = {}
    for ticker, data in valid_results.items():
        combined = calculate_combined_score(data)
        if combined is not None:
            scores[ticker] = combined

    if not scores:
        return

    # Find best
    best_ticker = max(scores, key=scores.get)
    best_data = valid_results[best_ticker]

    piotroski = best_data.get("piotroski", {})
    altman = best_data.get("altman", {})

    fscore = piotroski.get("score", "N/A")
    zone = altman.get("zone", "N/A")

    st.success(
        f"**Best Candidate: {best_ticker}** "
        f"(F-Score: {fscore}/9, Zone: {zone})"
    )


def render_detailed_tabs(results: dict[str, dict]) -> None:
    """
    Render detailed breakdown tabs for each stock.

    Args:
        results: Dict mapping ticker to score data.
    """
    # Filter to valid results
    valid_results = {t: d for t, d in results.items() if "error" not in d}

    if not valid_results:
        return

    tickers = list(valid_results.keys())
    tabs = st.tabs(tickers)

    for i, ticker in enumerate(tickers):
        with tabs[i]:
            data = valid_results[ticker]
            piotroski = data.get("piotroski")
            altman = data.get("altman")

            # Show badges at top
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    render_fscore_badge(piotroski.get("score") if piotroski else None),
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    render_zscore_badge(
                        altman.get("z_score") if altman else None,
                        altman.get("zone") if altman else None,
                    ),
                    unsafe_allow_html=True,
                )

            st.divider()

            # Render detailed breakdown
            render_score_detail(piotroski, altman)


def render_error_summary(results: dict[str, dict]) -> None:
    """
    Display errors for any stocks that failed to load.

    Args:
        results: Dict mapping ticker to score data.
    """
    errors = {t: d for t, d in results.items() if "error" in d}

    if not errors:
        return

    with st.expander(f"Failed to load {len(errors)} stock(s)", expanded=False):
        for ticker, data in errors.items():
            error_type = data.get("error", "unknown")
            message = data.get("message", "Unknown error")

            if error_type == "rate_limited":
                st.caption(f"{ticker}: Rate limited by SEC. Try again later.")
            elif error_type == "graylisted":
                st.caption(f"{ticker}: SEC throttling. Wait a few minutes.")
            elif error_type == "no_data":
                st.caption(f"{ticker}: No SEC data found for this ticker.")
            else:
                st.caption(f"{ticker}: {message}")
