"""
Watchlist Page - View and manage your tracked stocks.

Displays all watchlist stocks with F-Score and Z-Score indicators,
price data from Yahoo Finance, and thesis/decision status.
Supports adding/removing stocks and refreshing scores from SEC EDGAR.
"""

from datetime import UTC, datetime

import streamlit as st

from dashboard.components.page_header import render_page_header
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
from dashboard.styles import inject_global_styles, section_header, empty_state, page_footer
from dashboard.utils.formatters import format_date
from dashboard.utils.scoring import get_scores_for_ticker, refresh_scores
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.validators import validate_ticker
from dashboard.utils.session_state import init_page_state
from dashboard.utils.watchlist import (
    add_stock,
    get_all_cached_scores,
    get_all_stock_data,
    load_watchlist,
    remove_stock,
    save_watchlist,
    update_cached_scores,
)

# Initialize session state for this page
init_page_state("watchlist")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar(current_page="watchlist")
inject_global_styles()

render_page_header(
    title="Watchlist",
    subtitle="Track stocks with Piotroski F-Score and Altman Z-Score",
    breadcrumbs=[("Home", "app.py"), ("Watchlist", "")],
)


def _get_top_stocks_for_compare(
    stocks: list[str],
    all_scores: dict[str, dict | None],
    max_count: int = 3,
) -> list[str]:
    """Get top stocks by F-Score for comparison."""
    scored = []
    for ticker in stocks:
        cached = all_scores.get(ticker)
        if cached and "piotroski" in cached:
            piotroski_data = cached["piotroski"]
            if isinstance(piotroski_data, dict):
                fscore = piotroski_data.get("score", 0)
            elif isinstance(piotroski_data, int):
                fscore = piotroski_data
            else:
                fscore = 0
            scored.append((ticker, fscore))
        else:
            scored.append((ticker, 0))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [ticker for ticker, _ in scored[:max_count]]


# Add stock section
with st.container(border=True):
    section_header("Add Stock")
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
            is_valid, error_msg = validate_ticker(new_ticker)
            if not is_valid:
                st.error(error_msg)
            elif add_stock(new_ticker, new_note):
                # Auto-fetch scores immediately after adding
                with st.spinner(f"Fetching scores for {new_ticker}..."):
                    try:
                        scores = get_scores_for_ticker(new_ticker)
                        if scores and "error" not in scores:
                            wl = load_watchlist()
                            if new_ticker in wl.get("stocks", {}):
                                wl["stocks"][new_ticker]["cached_scores"] = scores
                                wl["stocks"][new_ticker]["cached_at"] = datetime.now(UTC).isoformat()
                                save_watchlist(wl)
                            st.success(f"Added {new_ticker} with scores")
                        else:
                            st.success(f"Added {new_ticker} (scores will load on next refresh)")
                    except Exception:
                        st.success(f"Added {new_ticker} (score fetch failed — try Refresh Scores)")
                st.rerun()
            else:
                st.warning(f"{new_ticker} is already on your watchlist")

st.divider()

# Get watchlist — single JSON read for all data
all_stock_data = get_all_stock_data()
stocks = list(all_stock_data.keys())
all_scores = get_all_cached_scores(all_stock_data)

if not stocks:
    empty_state(
        icon_html=icons.eye(size=48),
        title="Your watchlist is empty",
        message="Add stocks using the form above to start tracking them. "
                "Example tickers: AAPL, MSFT, GOOGL, AMZN, BRK-B",
    )
else:
    # Refresh scores button
    col1, col2 = st.columns([3, 1])
    with col1:
        section_header("Tracked Stocks", count=len(stocks))
        st.caption("F-Score (0-9) measures financial strength. Z-Score predicts bankruptcy risk. Higher is better for both.")
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
                    remaining = len(error_messages) - 3
                    st.error(
                        f"All {error_count} requests failed"
                        + (f" (showing 3 of {error_count})" if remaining > 0 else "")
                    )
                    for msg in error_messages[:3]:
                        st.caption(msg)
                    if remaining > 0:
                        with st.expander(f"+{remaining} more errors"):
                            for msg in error_messages[3:]:
                                st.caption(msg)
                st.rerun()

    # Display stocks as styled container cards
    for ticker in sorted(stocks):
        data = all_stock_data.get(ticker)
        cached_scores = all_scores.get(ticker)

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

        # Determine zone for card border styling
        zone = (altman.get("zone") or "").lower() if altman else ""
        zone_class = zone if zone in ("safe", "grey", "distress") else ""

        with st.container(border=True):
            # Card header: ticker, scores, actions
            header_col1, header_col2, header_col3 = st.columns([2, 2, 1])

            with header_col1:
                st.markdown(f"**{ticker}**")
                if data and data.get("note"):
                    st.caption(f"*{data.get('note')}*")

            with header_col2:
                # Score badges
                score_parts = []
                if piotroski:
                    score_parts.append(icons.fscore_badge(piotroski.get("score"), size="normal"))
                if altman:
                    score_parts.append(icons.zscore_badge(altman.get("z_score"), altman.get("zone"), size="normal"))
                    score_parts.append(icons.status_badge(altman.get("zone") or "neutral", size="normal"))
                if score_parts:
                    st.markdown(
                        f'<div class="asym-badge-row">{" ".join(score_parts)}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("No scores")

            with header_col3:
                # Remove button with confirmation (per-ticker state)
                confirm_key = f"confirm_remove_{ticker}"
                if st.session_state.get(confirm_key, False):
                    st.warning("Confirm removal?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes", key=f"yes_{ticker}", use_container_width=True):
                            remove_stock(ticker)
                            st.session_state[confirm_key] = False
                            st.rerun()
                    with col_no:
                        if st.button("No", key=f"no_{ticker}", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
                else:
                    if st.button("Remove", key=f"remove_{ticker}", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()

            # Price and sparkline row
            price_col, spark_col = st.columns([1.5, 1])

            with price_col:
                render_price_with_range(ticker)

            with spark_col:
                sparkline = render_sparkline(ticker)
                if sparkline:
                    st.markdown(sparkline, unsafe_allow_html=True)

            # Score detail in nested expander
            if cached_scores:
                with st.expander("Score Details"):
                    render_score_panel(piotroski, altman, use_gauges=True)
                    st.divider()
                    render_score_detail(piotroski, altman)
            else:
                st.caption(f"Added: {format_date(data.get('added') if data else None)}")
                st.caption("Click 'Refresh Scores' to fetch data from SEC EDGAR.")

    # Quick actions
    st.divider()
    section_header("Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Compare Top 3", disabled=len(stocks) < 2):
            # Get top stocks by F-Score (or first stocks if no scores)
            top_stocks = _get_top_stocks_for_compare(stocks, all_scores, max_count=3)
            st.session_state["compare_tickers"] = top_stocks
            st.switch_page("pages/5_Compare.py")

    with col2:
        if st.button("Screen Universe"):
            st.switch_page("pages/3_Screener.py")

    with col3:
        if st.button("Create Thesis", disabled=len(stocks) == 0):
            st.switch_page("pages/6_Decisions.py")

page_footer()
