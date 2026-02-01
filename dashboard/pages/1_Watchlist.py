"""
Watchlist Page - View and manage your tracked stocks.

Displays all watchlist stocks with F-Score and Z-Score indicators,
price data from Yahoo Finance, and thesis/decision status.
Supports adding/removing stocks and refreshing scores from SEC EDGAR.
"""

import re
from datetime import UTC, datetime

import streamlit as st

from dashboard.components.score_display import (
    render_score_detail,
    render_score_panel,
)
from dashboard.components.stock_card import (
    render_price_with_range,
    render_sparkline,
    render_stock_card_header,
)
from dashboard.components import icons
from dashboard.utils.scoring import get_scores_for_ticker, refresh_scores
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.watchlist import (
    add_stock,
    get_cached_scores,
    get_stock_data,
    get_stocks,
    load_watchlist,
    remove_stock,
    save_watchlist,
    update_cached_scores,
)

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Watchlist")
st.caption("Track stocks with Piotroski F-Score and Altman Z-Score")

# Initialize session state for confirmations
if "confirm_remove" not in st.session_state:
    st.session_state.confirm_remove = None


def _format_date(iso_str: str | None) -> str:
    """Format ISO date string to readable format."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return "N/A"


def _validate_ticker(ticker: str) -> tuple[bool, str]:
    """Validate ticker symbol format.

    Args:
        ticker: Stock ticker symbol to validate.

    Returns:
        Tuple of (is_valid, error_message). Error message is empty if valid.
    """
    if not ticker:
        return False, "Please enter a ticker symbol"

    # Ticker format: 1-5 uppercase letters, optionally followed by hyphen and letter
    # Examples: AAPL, MSFT, BRK-B, BRK-A (lowercase input is auto-uppercased)
    if not re.match(r"^[A-Z]{1,5}(?:-[A-Z])?$", ticker):
        return False, "Invalid ticker format (e.g., AAPL, BRK-B). Lowercase is OK."

    return True, ""


def _get_top_stocks_for_compare(stocks: list[str], max_count: int = 3) -> list[str]:
    """Get top stocks by F-Score for comparison.

    Args:
        stocks: List of ticker symbols from watchlist.
        max_count: Maximum number of stocks to return.

    Returns:
        List of up to max_count tickers, sorted by F-Score (highest first).
    """
    # Get scores for each stock
    scored = []
    for ticker in stocks:
        cached = get_cached_scores(ticker)
        if cached and "piotroski" in cached:
            fscore = cached["piotroski"].get("score", 0)
            scored.append((ticker, fscore))
        else:
            # No score, use 0
            scored.append((ticker, 0))

    # Sort by F-Score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top N tickers
    return [ticker for ticker, _ in scored[:max_count]]


# Add stock section
with st.container():
    st.subheader("Add Stock")
    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        new_ticker = st.text_input(
            "Ticker",
            placeholder="AAPL",
            label_visibility="collapsed",
            key="new_ticker",
        ).upper()

    with col2:
        new_note = st.text_input(
            "Note (optional)",
            placeholder="Why are you watching this stock?",
            label_visibility="collapsed",
            key="new_note",
        )

    with col3:
        if st.button("Add", type="primary", use_container_width=True):
            is_valid, error_msg = _validate_ticker(new_ticker)
            if not is_valid:
                st.error(error_msg)
            elif add_stock(new_ticker, new_note):
                st.success(f"Added {new_ticker} to watchlist")
                st.rerun()
            else:
                st.warning(f"{new_ticker} is already on your watchlist")

st.divider()

# Get watchlist
stocks = get_stocks()

if not stocks:
    st.info("""
    Your watchlist is empty.

    Add stocks using the form above to start tracking them.

    **Example tickers to try:** AAPL, MSFT, GOOGL, AMZN, BRK-B
    """)
else:
    # Refresh scores button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Tracked Stocks ({len(stocks)})")
    with col2:
        if st.button("Refresh Scores", use_container_width=True):
            with st.spinner("Fetching scores from SEC EDGAR..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(ticker: str, current: int, total: int) -> None:
                    progress_bar.progress(current / total)
                    status_text.text(f"Fetching {ticker}... ({current}/{total})")

                results = refresh_scores(stocks, update_progress)

                # Update cached scores and track errors
                wl = load_watchlist()
                success_count = 0
                error_count = 0
                error_messages = []

                for ticker, scores in results.items():
                    if ticker not in wl.get("stocks", {}):
                        continue

                    # Check if it's an error response
                    if "error" in scores:
                        error_count += 1
                        error_type = scores.get("error")
                        if error_type == "rate_limited":
                            error_messages.append(f"{ticker}: Rate limited")
                        elif error_type == "graylisted":
                            error_messages.append(f"{ticker}: SEC throttling")
                        elif error_type == "no_data":
                            error_messages.append(f"{ticker}: No SEC data found")
                        else:
                            error_messages.append(f"{ticker}: {scores.get('message', 'Unknown error')}")
                    else:
                        wl["stocks"][ticker]["cached_scores"] = scores
                        wl["stocks"][ticker]["cached_at"] = datetime.now(UTC).isoformat()
                        success_count += 1
                save_watchlist(wl)

                progress_bar.empty()
                status_text.empty()

                # Show appropriate message based on results
                if error_count == 0:
                    st.success(f"All {success_count} scores refreshed!")
                elif success_count > 0:
                    st.warning(f"Refreshed {success_count} scores, {error_count} failed")
                    with st.expander("View errors"):
                        for msg in error_messages:
                            st.caption(msg)
                else:
                    st.error(f"All {error_count} requests failed")
                    for msg in error_messages[:3]:
                        st.caption(msg)
                st.rerun()

    # Display stocks
    for ticker in sorted(stocks):
        data = get_stock_data(ticker)
        cached_scores = get_cached_scores(ticker)

        # Validate cached scores before accessing
        piotroski = None
        altman = None
        if cached_scores and isinstance(cached_scores, dict):
            piotroski_data = cached_scores.get("piotroski")
            if piotroski_data and isinstance(piotroski_data, dict):
                piotroski = piotroski_data

            altman_data = cached_scores.get("altman")
            if altman_data and isinstance(altman_data, dict):
                altman = altman_data

        # Build plain text label for expander
        fscore_text = f"F:{piotroski.get('score')}/9" if piotroski and piotroski.get('score') is not None else "F:N/A"
        zscore_text = f"Z:{altman.get('zone')}" if altman and altman.get('zone') else "Z:N/A"

        # Create expandable card for each stock
        with st.expander(
            f"**{ticker}** — {fscore_text} | {zscore_text}",
            expanded=False,
        ):
            # Header with price and scores
            render_stock_card_header(ticker)

            # Price and sparkline row
            price_col, spark_col, score_col = st.columns([1.5, 1, 1.5])

            with price_col:
                render_price_with_range(ticker)

            with spark_col:
                sparkline = render_sparkline(ticker)
                if sparkline:
                    st.markdown(sparkline, unsafe_allow_html=True)

            with score_col:
                # Score badges
                score_parts = []
                if piotroski:
                    score_parts.append(icons.fscore_badge(piotroski.get("score"), size="normal"))
                if altman:
                    score_parts.append(icons.zscore_badge(altman.get("z_score"), altman.get("zone"), size="normal"))
                    score_parts.append(icons.status_badge(altman.get("zone") or "neutral", size="normal"))
                if score_parts:
                    st.markdown(" ".join(score_parts), unsafe_allow_html=True)
                else:
                    st.caption("No scores")

            st.divider()

            # Stock info row
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.caption(f"Added: {_format_date(data.get('added') if data else None)}")
                if data and data.get("note"):
                    st.markdown(f"*{data.get('note')}*")

            with col2:
                if cached_scores:
                    cached_at = data.get("cached_at") if data else None
                    st.caption(f"Scores cached: {_format_date(cached_at)}")
                else:
                    st.caption("No cached scores. Click 'Refresh Scores' above.")

            with col3:
                # Remove button with confirmation
                if st.session_state.confirm_remove == ticker:
                    st.warning("Confirm removal?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes", key=f"yes_{ticker}", use_container_width=True):
                            remove_stock(ticker)
                            st.session_state.confirm_remove = None
                            st.rerun()
                    with col_no:
                        if st.button("No", key=f"no_{ticker}", use_container_width=True):
                            st.session_state.confirm_remove = None
                            st.rerun()
                else:
                    if st.button("Remove", key=f"remove_{ticker}", use_container_width=True):
                        st.session_state.confirm_remove = ticker
                        st.rerun()

            st.divider()

            # Enhanced score display with gauges
            if cached_scores:
                # Use new gauge display
                render_score_panel(piotroski, altman, use_gauges=True)
                st.divider()
                render_score_detail(piotroski, altman)
            else:
                st.info("Click 'Refresh Scores' to fetch data from SEC EDGAR.")

    # Quick actions
    st.divider()
    st.caption("**Quick Actions**")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Compare Top 3", disabled=len(stocks) < 2):
            # Get top stocks by F-Score (or first stocks if no scores)
            top_stocks = _get_top_stocks_for_compare(stocks, max_count=3)
            st.session_state["compare_tickers"] = top_stocks
            st.switch_page("pages/3_Compare.py")

    with col2:
        if st.button("Screen Universe"):
            st.switch_page("pages/2_Screener.py")

    with col3:
        if st.button("Create Thesis", disabled=len(stocks) == 0):
            st.switch_page("pages/4_Decisions.py")
