"""
Screener Page - Find investment opportunities by quantitative criteria.

Filters stocks using precomputed Piotroski F-Score and Altman Z-Score
from DuckDB bulk data (zero API calls during screening).
"""

import pandas as pd
import streamlit as st

from dashboard.utils.bulk_data import (
    format_last_refresh,
    get_bulk_stats,
    get_scores_stats,
    get_screener_results,
    has_precomputed_scores,
)
from dashboard.utils.watchlist import add_stock, get_stocks

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

with col1:
    piotroski_min = st.slider(
        "Minimum F-Score",
        min_value=0,
        max_value=9,
        value=5,
        help="Piotroski F-Score measures financial health (0-9). Higher is better.",
    )

with col2:
    altman_min = st.number_input(
        "Minimum Z-Score",
        min_value=-10.0,
        max_value=50.0,
        value=1.81,
        step=0.1,
        format="%.2f",
        help="Altman Z-Score measures bankruptcy risk. >2.99 is Safe, <1.81 is Distress.",
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
    limit = st.selectbox(
        "Results Limit",
        options=[25, 50, 100, 250, 500],
        index=1,
    )

st.divider()

# Fetch results
try:
    results = get_screener_results(
        piotroski_min=piotroski_min if piotroski_min > 0 else None,
        altman_min=altman_min if altman_min > -10 else None,
        altman_zone=altman_zone_filter,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
except Exception as e:
    st.error(f"Error fetching results: {e}")
    st.info("Try running `asymmetric db refresh` to ensure data is available.")
    results = []

# Results header with count
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"Results ({len(results)} stocks)")
with col2:
    # Export button
    if results:
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False)
        st.download_button(
            "Export CSV",
            csv,
            file_name="screener_results.csv",
            mime="text/csv",
        )

if not results:
    st.info("No stocks match the current filters. Try adjusting the criteria.")
else:
    # Convert to DataFrame for display
    df = pd.DataFrame(results)

    # Get current watchlist for comparison
    watchlist = set(get_stocks())
    df["on_watchlist"] = df["ticker"].apply(lambda x: "Yes" if x in watchlist else "")

    # Select and reorder columns for display
    display_columns = [
        "ticker",
        "company_name",
        "piotroski_score",
        "piotroski_interpretation",
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
        "piotroski_score": "F-Score",
        "piotroski_interpretation": "Interpretation",
        "altman_z_score": "Z-Score",
        "altman_zone": "Zone",
        "fiscal_year": "FY",
        "on_watchlist": "Watching",
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
            "F-Score": st.column_config.ProgressColumn(
                "F-Score",
                format="%d/9",
                min_value=0,
                max_value=9,
            ),
            "Interpretation": st.column_config.TextColumn(
                "Interpretation", width="medium"
            ),
            "Z-Score": st.column_config.NumberColumn("Z-Score", format="%.2f"),
            "Zone": st.column_config.TextColumn("Zone", width="small"),
            "FY": st.column_config.NumberColumn("FY", format="%d"),
            "Watching": st.column_config.TextColumn("Watching", width="small"),
        },
    )

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
