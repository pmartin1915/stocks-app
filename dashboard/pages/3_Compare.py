"""
Compare Page - Side-by-side stock comparison with AI analysis.

Compare 2-3 stocks with F-Score and Z-Score breakdowns, winner highlighting,
and optional AI-powered analysis via Gemini.
Enhanced with price data and improved AI content display.
"""

import streamlit as st

from dashboard.components.ai_content import render_ai_section
from dashboard.components.comparison import (
    render_best_candidate,
    render_comparison_table,
    render_detailed_tabs,
    render_error_summary,
)
from dashboard.utils.ai_analysis import (
    build_comparison_context,
    estimate_analysis_cost,
    get_gemini_client_cached,
    run_comparison_analysis,
)
from dashboard.utils.scoring import get_scores_for_ticker
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.validators import validate_ticker
from dashboard.utils.watchlist import get_cached_scores, get_stocks, add_stock

st.set_page_config(page_title="Compare | Asymmetric", layout="wide")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Compare")
st.caption("Compare 2-3 stocks side-by-side with AI-powered analysis")

# Initialize session state
if "compare_tickers" not in st.session_state:
    st.session_state.compare_tickers = []
if "compare_results" not in st.session_state:
    st.session_state.compare_results = {}
if "compare_ai_result" not in st.session_state:
    st.session_state.compare_ai_result = None


def _fetch_scores(tickers: list[str]) -> dict[str, dict]:
    """Fetch scores for multiple tickers with progress display."""
    results = {}

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        status_text.text(f"Fetching {ticker}... ({i + 1}/{len(tickers)})")
        progress_bar.progress((i + 1) / len(tickers))

        # Try cached scores first
        cached = get_cached_scores(ticker)
        if cached and "piotroski" in cached:
            results[ticker] = cached
        else:
            # Fetch fresh
            results[ticker] = get_scores_for_ticker(ticker)

    progress_bar.empty()
    status_text.empty()

    return results


# Stock Selection Section
st.subheader("Select Stocks to Compare")

# Get watchlist for selection
watchlist_stocks = get_stocks()

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("**Option 1: Select from Watchlist**")

    if watchlist_stocks:
        selected_from_watchlist = st.multiselect(
            "Choose up to 3 stocks",
            options=sorted(watchlist_stocks),
            default=st.session_state.compare_tickers[:3] if st.session_state.compare_tickers else [],
            max_selections=3,
            key="watchlist_select",
            label_visibility="collapsed",
        )
    else:
        st.info("Your watchlist is empty. Add stocks or enter tickers manually.")
        selected_from_watchlist = []

with col2:
    st.markdown("**Option 2: Enter Tickers Manually**")

    manual_cols = st.columns(3)
    manual_tickers = []

    for i, mcol in enumerate(manual_cols):
        with mcol:
            ticker = st.text_input(
                f"Ticker {i + 1}",
                placeholder="AAPL" if i == 0 else "",
                key=f"manual_ticker_{i}",
                label_visibility="collapsed",
            ).upper().strip()
            if ticker:
                manual_tickers.append(ticker)

# Determine which tickers to use
if selected_from_watchlist:
    tickers_to_compare = selected_from_watchlist
elif manual_tickers:
    tickers_to_compare = manual_tickers
else:
    tickers_to_compare = []

# Validate manual tickers
validation_errors = []
for ticker in manual_tickers:
    is_valid, error = validate_ticker(ticker, allow_empty=True)
    if not is_valid:
        validation_errors.append(error)

# Compare button
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    compare_clicked = st.button(
        "Compare",
        type="primary",
        disabled=len(tickers_to_compare) < 2 or bool(validation_errors),
        use_container_width=True,
    )

with col2:
    if st.button("Clear", use_container_width=True):
        st.session_state.compare_tickers = []
        st.session_state.compare_results = {}
        st.session_state.compare_ai_result = None
        st.rerun()

# Show validation errors
for error in validation_errors:
    st.error(error)

# Show ticker count hint
if len(tickers_to_compare) < 2:
    st.info("Select at least 2 stocks to compare (maximum 3).")
elif len(tickers_to_compare) > 3:
    st.warning("Maximum 3 stocks for comparison. Please deselect some.")

# Fetch scores on compare click
if compare_clicked and len(tickers_to_compare) >= 2:
    st.session_state.compare_tickers = tickers_to_compare[:3]
    st.session_state.compare_ai_result = None  # Clear previous AI result

    with st.spinner("Fetching financial data from SEC EDGAR..."):
        st.session_state.compare_results = _fetch_scores(tickers_to_compare[:3])

# Display Comparison Results
if st.session_state.compare_results:
    st.divider()

    results = st.session_state.compare_results

    # Show any errors
    render_error_summary(results)

    # Check if we have enough valid results
    valid_count = len([t for t in results if "error" not in results[t]])

    if valid_count >= 2:
        # Comparison Table
        st.subheader("Score Comparison")
        render_comparison_table(results)

        st.divider()

        # Best Candidate
        render_best_candidate(results)

        st.divider()

        # Detailed Breakdown Tabs
        st.subheader("Detailed Breakdown")
        render_detailed_tabs(results)

        st.divider()

        # AI Analysis Section
        with st.expander("AI-Powered Analysis", expanded=False):
            st.markdown("Get AI insights on your stock comparison using Gemini.")

            # Check if Gemini is configured
            client = get_gemini_client_cached()

            if client is None:
                st.warning(
                    "Gemini API not configured. Set GEMINI_API_KEY in your .env file "
                    "to enable AI analysis."
                )
            else:
                # Build context for cost estimation
                context = build_comparison_context(results)

                col1, col2 = st.columns(2)

                with col1:
                    flash_estimate = estimate_analysis_cost(context, "flash")
                    st.markdown("**Quick Compare** (Flash model)")
                    st.caption(f"~{flash_estimate['input_tokens']:,} tokens, ~${flash_estimate['estimated_cost_usd']:.3f}")

                    if st.button("Run Quick Analysis", key="quick_analysis"):
                        with st.spinner("Analyzing with Gemini Flash..."):
                            st.session_state.compare_ai_result = run_comparison_analysis(
                                results, model="flash"
                            )
                        st.rerun()

                with col2:
                    pro_estimate = estimate_analysis_cost(context, "pro")
                    st.markdown("**Deep Analysis** (Pro model)")
                    st.caption(f"~{pro_estimate['input_tokens']:,} tokens, ~${pro_estimate['estimated_cost_usd']:.3f}")

                    if st.button("Run Deep Analysis", key="deep_analysis"):
                        with st.spinner("Analyzing with Gemini Pro..."):
                            st.session_state.compare_ai_result = run_comparison_analysis(
                                results, model="pro"
                            )
                        st.rerun()

                # Display AI result
                if st.session_state.compare_ai_result:
                    ai_result = st.session_state.compare_ai_result

                    st.divider()

                    if "error" in ai_result:
                        st.error(ai_result.get("message", "Analysis failed"))
                    else:
                        # Use enhanced AI content display with feedback
                        render_ai_section(
                            content=ai_result.get("content", ""),
                            model=ai_result.get("model", "unknown"),
                            cost=ai_result.get("cost_usd"),
                            timestamp=ai_result.get("timestamp"),
                            content_type="comparison",
                            ticker=",".join(st.session_state.compare_tickers),
                        )

                        # Create Thesis from Analysis
                        st.divider()
                        st.markdown("**Save as Thesis**")
                        thesis_col1, thesis_col2 = st.columns([2, 1])

                        with thesis_col1:
                            ticker_for_thesis = st.selectbox(
                                "Create thesis for:",
                                options=st.session_state.compare_tickers,
                                key="thesis_ticker_select",
                                label_visibility="collapsed",
                            )

                        with thesis_col2:
                            if st.button("Create Thesis", type="secondary", use_container_width=True):
                                from dashboard.utils.decisions import create_thesis_from_comparison

                                try:
                                    thesis_id = create_thesis_from_comparison(
                                        ticker=ticker_for_thesis,
                                        comparison_result=ai_result,
                                    )
                                    st.success(f"Thesis created! ID: {thesis_id}")
                                    st.caption("View it in the Decisions page.")
                                except Exception as e:
                                    st.error(f"Failed to create thesis: {e}")

        st.divider()

        # Quick Actions
        st.caption("**Quick Actions**")
        action_cols = st.columns(3)

        # Find stocks not in watchlist
        stocks_not_in_watchlist = [
            t for t in st.session_state.compare_tickers
            if t not in watchlist_stocks and t in results and "error" not in results[t]
        ]

        with action_cols[0]:
            if stocks_not_in_watchlist:
                ticker_to_add = st.selectbox(
                    "Add to Watchlist",
                    options=stocks_not_in_watchlist,
                    key="add_to_watchlist_select",
                    label_visibility="collapsed",
                )
                if st.button(f"Add {ticker_to_add} to Watchlist", use_container_width=True):
                    if add_stock(ticker_to_add):
                        st.success(f"Added {ticker_to_add} to watchlist!")
                        st.rerun()
            else:
                st.button("All stocks on watchlist", disabled=True, use_container_width=True)

        with action_cols[1]:
            if st.button("View Screener", use_container_width=True):
                st.switch_page("pages/2_Screener.py")

        with action_cols[2]:
            if st.button("Back to Watchlist", use_container_width=True):
                st.switch_page("pages/1_Watchlist.py")

    elif valid_count == 1:
        st.warning("Only one stock has valid data. Add another stock to compare.")
    else:
        st.error("No valid data for any selected stocks.")

# Footer with tips
if not st.session_state.compare_results:
    st.divider()
    st.markdown("""
    ### Tips for Stock Comparison

    - **F-Score (0-9)**: Higher is better. 7+ indicates strong financial health.
    - **Z-Score**: Higher is better. >2.99 is Safe zone, 1.81-2.99 is Grey zone.
    - **Winner highlighting**: Stars indicate the best value in each metric.
    - **AI Analysis**: Use Quick Compare for fast insights, Deep Analysis for detailed evaluation.
    """)
