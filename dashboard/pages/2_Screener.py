"""
Screener Page - Find investment opportunities by quantitative criteria.

Filters stocks using precomputed Piotroski F-Score and Altman Z-Score
from DuckDB bulk data (zero API calls during screening).
Enhanced with price data from Yahoo Finance.
"""

import math

import pandas as pd
import streamlit as st

from dashboard.theme import get_semantic_color, get_plotly_theme
from dashboard.utils.bulk_data import (
    format_last_refresh,
    get_bulk_stats,
    get_scores_stats,
    get_screener_results,
    has_precomputed_scores,
)
from dashboard.utils.price_data import get_batch_price_data
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.watchlist import add_stock, get_stocks

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Screener")


def _format_score_note(result: dict) -> str:
    """Format score info for watchlist note, handling None values."""
    f_score = result.get("piotroski_score")
    z_score = result.get("altman_z_score")
    zone = result.get("altman_zone", "")

    f_part = f"F={f_score}" if f_score is not None else "F=N/A"
    if z_score is not None:
        z_part = f"Z={z_score:.2f} ({zone})" if zone else f"Z={z_score:.2f}"
    else:
        z_part = "Z=N/A"

    return f"Screen: {f_part}, {z_part}"


st.caption("Filter stocks by Piotroski F-Score and Altman Z-Score")

# Data freshness indicator in sidebar
with st.sidebar:
    st.subheader("Data Status")

    bulk_stats = get_bulk_stats()
    scores_stats = get_scores_stats()

    st.metric("Companies in DB", f"{bulk_stats.get('ticker_count', 0):,}")
    st.metric("Scores Computed", f"{scores_stats.get('scores_count', 0):,}")

    last_refresh = bulk_stats.get("last_refresh")
    st.caption(f"Bulk data: {format_last_refresh(last_refresh)}")

    last_computed = scores_stats.get("last_computed")
    st.caption(f"Scores: {format_last_refresh(last_computed)}")

    st.divider()
    st.caption("To refresh data, run:")
    st.code("asymmetric db refresh\nasymmetric db precompute", language="bash")

# Check if precomputed scores exist
if not has_precomputed_scores():
    st.warning("""
**No precomputed scores available.**

The screener requires precomputed scores for instant results.
Run the following commands in your terminal:

```bash
# Download bulk SEC data (~10-15 minutes first time)
asymmetric db refresh

# Precompute scores (~2-5 minutes)
asymmetric db precompute
```

Once complete, refresh this page.
""")
    st.stop()

# Filter controls
st.subheader("Filters")

col1, col2, col3 = st.columns(3)

from asymmetric.core.scoring.constants import FSCORE_MAX, ZSCORE_MFG_GREY_LOW, ZSCORE_MFG_SAFE

with col1:
    piotroski_min = st.slider(
        "Minimum F-Score",
        min_value=0,
        max_value=FSCORE_MAX,
        value=5,
        help=f"Piotroski F-Score measures financial health (0-{FSCORE_MAX}). Higher is better.",
    )

with col2:
    altman_min = st.number_input(
        "Minimum Z-Score",
        min_value=-10.0,
        max_value=50.0,
        value=ZSCORE_MFG_GREY_LOW,
        step=0.1,
        format="%.2f",
        help=f"Altman Z-Score measures bankruptcy risk. >{ZSCORE_MFG_SAFE} is Safe, <{ZSCORE_MFG_GREY_LOW} is Distress.",
    )

with col3:
    altman_zone = st.selectbox(
        "Z-Score Zone",
        options=["Any", "Safe", "Grey", "Distress"],
        index=0,
        help="Filter by Altman zone classification",
    )
    # Convert "Any" to None for the query
    altman_zone_filter = None if altman_zone == "Any" else altman_zone

# Additional controls row
col4, col5, col6 = st.columns(3)

with col4:
    sort_by = st.selectbox(
        "Sort By",
        options=["piotroski_score", "altman_z_score", "ticker"],
        format_func=lambda x: {
            "piotroski_score": "F-Score",
            "altman_z_score": "Z-Score",
            "ticker": "Ticker",
        }[x],
        index=0,
    )

with col5:
    sort_order = st.radio(
        "Sort Order",
        options=["desc", "asc"],
        format_func=lambda x: "Highest First" if x == "desc" else "Lowest First",
        horizontal=True,
    )

with col6:
    page_size = st.selectbox(
        "Per page",
        options=[25, 50, 100],
        index=1,
    )

st.divider()

# Pagination state
if "screener_page" not in st.session_state:
    st.session_state.screener_page = 0

# Reset page when filters change
filter_key = f"{piotroski_min}_{altman_min}_{altman_zone}_{sort_by}_{sort_order}_{page_size}"
if st.session_state.get("screener_filter_key") != filter_key:
    st.session_state.screener_filter_key = filter_key
    st.session_state.screener_page = 0

# Fetch all matching results
try:
    results = get_screener_results(
        piotroski_min=piotroski_min if piotroski_min > 0 else None,
        altman_min=altman_min if altman_min > -10 else None,
        altman_zone=altman_zone_filter,
        limit=500,
        sort_by=sort_by,
        sort_order=sort_order,
    )
except Exception as e:
    st.error(f"Error fetching results: {e}")
    st.info("Try running `asymmetric db refresh` to ensure data is available.")
    results = []

# Pagination math
total_results = len(results)
total_pages = max(1, math.ceil(total_results / page_size))
current_page = min(st.session_state.screener_page, total_pages - 1)
start_idx = current_page * page_size
end_idx = min(start_idx + page_size, total_results)
page_results = results[start_idx:end_idx]

# Results header with page info
col1, col2 = st.columns([3, 1])
with col1:
    if total_pages > 1:
        st.subheader(f"Results ({total_results} stocks, page {current_page + 1} of {total_pages})")
    else:
        st.subheader(f"Results ({total_results} stocks)")
with col2:
    # Export all results as CSV
    if results:
        df_export = pd.DataFrame(results)
        csv = df_export.to_csv(index=False)
        st.download_button(
            "Export CSV",
            csv,
            file_name="screener_results.csv",
            mime="text/csv",
        )

# Page navigation
if total_pages > 1:
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("Previous", disabled=current_page == 0, use_container_width=True):
            st.session_state.screener_page = current_page - 1
            st.rerun()
    with nav2:
        st.markdown(
            f"<div style='text-align:center;padding:0.5rem 0;'>Showing {start_idx + 1}–{end_idx} of {total_results}</div>",
            unsafe_allow_html=True,
        )
    with nav3:
        if st.button("Next", disabled=current_page >= total_pages - 1, use_container_width=True):
            st.session_state.screener_page = current_page + 1
            st.rerun()

if not results:
    st.info("No stocks match the current filters. Try adjusting the criteria.")
else:
    # Build DataFrame from current page only
    df = pd.DataFrame(page_results)

    # Get current watchlist for comparison
    watchlist = set(get_stocks())
    df["on_watchlist"] = df["ticker"].apply(lambda x: "✓" if x in watchlist else "")

    # Fetch prices for current page's tickers only
    tickers_to_fetch = tuple(df["ticker"].tolist())
    batch_prices = get_batch_price_data(tickers_to_fetch) if tickers_to_fetch else {}

    # Extract price data into columns
    prices = []
    changes = []
    market_caps = []

    for ticker in df["ticker"]:
        if ticker in batch_prices:
            price_data = batch_prices[ticker]
            if "error" not in price_data:
                prices.append(price_data.get("price"))
                changes.append(price_data.get("change_pct"))
                market_caps.append("—")
            else:
                prices.append(None)
                changes.append(None)
                market_caps.append("N/A")
        else:
            prices.append(None)
            changes.append(None)
            market_caps.append("—")

    df["price"] = prices
    df["change_pct"] = changes
    df["market_cap"] = market_caps

    # Select and reorder columns for display
    display_columns = [
        "ticker",
        "company_name",
        "price",
        "change_pct",
        "market_cap",
        "piotroski_score",
        "altman_z_score",
        "altman_zone",
        "fiscal_year",
        "on_watchlist",
    ]
    # Only include columns that exist
    available_columns = [c for c in display_columns if c in df.columns]
    df_display = df[available_columns].copy()

    # Rename columns for better display
    column_renames = {
        "ticker": "Ticker",
        "company_name": "Company",
        "price": "Price",
        "change_pct": "Change %",
        "market_cap": "Mkt Cap",
        "piotroski_score": "F-Score",
        "altman_z_score": "Z-Score",
        "altman_zone": "Zone",
        "fiscal_year": "FY",
        "on_watchlist": "Watch",
    }
    df_display = df_display.rename(columns=column_renames)

    # Display with column configuration
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Change %": st.column_config.NumberColumn(
                "Change %",
                format="%.2f%%",
                help="Daily price change percentage",
            ),
            "Mkt Cap": st.column_config.TextColumn("Mkt Cap", width="small"),
            "F-Score": st.column_config.ProgressColumn(
                "F-Score",
                format="%d/9",
                min_value=0,
                max_value=9,
            ),
            "Z-Score": st.column_config.NumberColumn("Z-Score", format="%.2f"),
            "Zone": st.column_config.TextColumn("Zone", width="small"),
            "FY": st.column_config.NumberColumn("FY", format="%d"),
            "Watch": st.column_config.TextColumn("Watch", width="small"),
        },
    )

    # Sector Heatmap visualization
    st.divider()
    st.subheader("Sector Heatmap")
    st.caption("Visual breakdown by sector, sized by market cap, colored by F-Score")

    if len(results) >= 10:
        with st.spinner("Loading sector data for heatmap..."):
            try:
                from dashboard.utils.bulk_data import get_sector_heatmap_data
                import plotly.express as px

                heatmap_data = get_sector_heatmap_data(results)

                if not heatmap_data.empty and len(heatmap_data) > 0:
                    # Get theme-aware colors for treemap
                    red = get_semantic_color('red')
                    yellow = get_semantic_color('yellow')
                    green = get_semantic_color('green')

                    # Treemap: size = market cap, color = F-Score
                    fig = px.treemap(
                        heatmap_data,
                        path=[px.Constant("Market"), "sector", "ticker"],
                        values="market_cap",
                        color="piotroski_score",
                        color_continuous_scale=[[0, red], [0.5, yellow], [1, green]],
                        range_color=[0, 9],
                        hover_data={
                            "company_name": True,
                            "piotroski_score": True,
                            "altman_zone": True,
                            "market_cap": ":,.0f",
                        },
                        labels={
                            "piotroski_score": "F-Score",
                            "market_cap": "Market Cap",
                        },
                    )
                    fig.update_traces(
                        textinfo="label+value",
                        hovertemplate="<b>%{label}</b><br>" +
                                      "F-Score: %{color}<br>" +
                                      "Market Cap: $%{value:,.0f}<br>" +
                                      "<extra></extra>",
                    )
                    fig.update_layout(
                        height=500,
                        margin=dict(t=50, l=25, r=25, b=25),
                        **get_plotly_theme()
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.caption(
                        "**How to read:** Box size = market capitalization. "
                        "Color = F-Score (green=strong, yellow=moderate, red=weak). "
                        "Grouped by sector."
                    )
                else:
                    st.info("Not enough sector data available for heatmap. Try broadening your filters.")
            except Exception as e:
                st.warning(f"Could not generate heatmap: {e}")
    else:
        st.info("Heatmap requires at least 10 results. Adjust your filters to see more stocks.")

st.divider()

# Add to Watchlist section
st.subheader("Add to Watchlist")

if results:
    # Get available tickers (not already on watchlist)
    available_tickers = [r["ticker"] for r in results if r["ticker"] not in watchlist]

    if not available_tickers:
        st.success("All matching stocks are already on your watchlist!")
    else:
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_tickers = st.multiselect(
                "Select stocks to add",
                options=available_tickers,
                default=[],
                placeholder="Choose stocks...",
                label_visibility="collapsed",
            )

        with col2:
            if st.button(
                "Add Selected",
                disabled=not selected_tickers,
                use_container_width=True,
            ):
                added_count = 0
                for ticker in selected_tickers:
                    # Find the result to get score info for the note
                    result = next((r for r in results if r["ticker"] == ticker), None)
                    if result:
                        note = _format_score_note(result)
                        if add_stock(ticker, note):
                            added_count += 1

                if added_count > 0:
                    st.success(f"Added {added_count} stock(s) to watchlist!")
                    st.rerun()
                else:
                    st.warning("Stocks were already on watchlist.")

        # Quick add single stock
        with st.expander("Quick Add Single Stock"):
            col1, col2 = st.columns([3, 1])
            with col1:
                quick_ticker = st.selectbox(
                    "Select stock",
                    options=available_tickers,
                    index=None,
                    placeholder="Choose a stock...",
                    label_visibility="collapsed",
                    key="quick_add_ticker",
                )
            with col2:
                if st.button(
                    "Add",
                    disabled=not quick_ticker,
                    use_container_width=True,
                    key="quick_add_btn",
                ):
                    result = next(
                        (r for r in results if r["ticker"] == quick_ticker), None
                    )
                    if result:
                        note = _format_score_note(result)
                        if add_stock(quick_ticker, note):
                            st.success(f"Added {quick_ticker} to watchlist!")
                            st.rerun()
else:
    st.info("No stocks available to add.")

# Help section at bottom
with st.expander("Score Reference"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
**Piotroski F-Score (0-9)**

Measures financial health based on 9 criteria:
- **7-9:** Strong - Financially healthy
- **4-6:** Moderate - Mixed signals
- **0-3:** Weak - Financial concerns

*Higher is better. Look for stocks scoring 7+.*
""")

    with col2:
        st.markdown("""
**Altman Z-Score**

Predicts bankruptcy probability:
- **>2.99:** Safe - Low bankruptcy risk
- **1.81-2.99:** Grey - Uncertain
- **<1.81:** Distress - High risk

*For non-manufacturing companies, use 2.60 as the Safe threshold.*
""")
