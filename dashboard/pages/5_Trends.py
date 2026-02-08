"""
Trends Page - Historical score trends and trajectory analysis.

Visualizes F-Score and Z-Score changes over time using Plotly charts.
Supports trend detection (improving, declining, consistent, turnaround).
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from asymmetric.core.trends import TrendAnalyzer
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from dashboard.theme import get_semantic_color, get_plotly_theme
from dashboard.utils.sidebar import render_full_sidebar

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Score Trends")
st.caption("Track F-Score and Z-Score trajectories over time")

# Initialize analyzer
analyzer = TrendAnalyzer()

# Tabs for different views
tab_history, tab_improving, tab_declining, tab_turnaround = st.tabs([
    "Stock History",
    "Improving",
    "Declining",
    "Turnarounds"
])

with tab_history:
    st.subheader("Score History")

    # Ticker input
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input(
            "Enter Ticker",
            placeholder="AAPL",
            key="trend_ticker"
        ).upper()
    with col2:
        years = st.selectbox("Years", [3, 5, 10], index=1)

    if ticker:
        history = analyzer.get_score_history(ticker, years=years)

        if not history:
            st.info(f"No score history found for {ticker}. Score the stock first using the CLI or Compare page.")
        else:
            # Filter out records with NULL fiscal data and convert to DataFrame
            valid_history = [
                h for h in history
                if h.fiscal_year is not None and h.fiscal_period is not None
            ]

            if not valid_history:
                st.info(f"No valid historical score data available for {ticker}.")
            else:
                # Convert to DataFrame for plotting
                df = pd.DataFrame([{
                    "Year": h.fiscal_year,
                    "Period": h.fiscal_period,
                    "F-Score": h.piotroski_score,
                    "Z-Score": h.altman_z_score,
                    "Zone": h.altman_zone,
                    "Profitability": h.piotroski_profitability,
                    "Leverage": h.piotroski_leverage,
                    "Efficiency": h.piotroski_efficiency,
                } for h in valid_history])

                # Sort by year
                df = df.sort_values("Year")

                # Create dual-axis chart
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Get theme-aware colors for chart lines
                blue = get_semantic_color('blue')
                gray = get_semantic_color('gray')

                # F-Score line (primary y-axis)
                fig.add_trace(
                    go.Scatter(
                        x=df["Year"],
                        y=df["F-Score"],
                        name="F-Score",
                        mode="lines+markers",
                        line=dict(color=blue, width=3),
                        marker=dict(size=10)
                    ),
                    secondary_y=False
                )

                # Z-Score line (secondary y-axis)
                fig.add_trace(
                    go.Scatter(
                        x=df["Year"],
                        y=df["Z-Score"],
                        name="Z-Score",
                        mode="lines+markers",
                        line=dict(color=gray, width=3),
                        marker=dict(size=10)
                    ),
                    secondary_y=True
                )

                # Add zone bands to Z-Score axis
                green = get_semantic_color('green')
                red = get_semantic_color('red')
                from asymmetric.core.scoring.constants import ZSCORE_MFG_GREY_LOW, ZSCORE_MFG_SAFE

                fig.add_hline(y=ZSCORE_MFG_SAFE, line_dash="dash", line_color=green,
                             annotation_text="Safe Zone", secondary_y=True)
                fig.add_hline(y=ZSCORE_MFG_GREY_LOW, line_dash="dash", line_color=red,
                             annotation_text="Distress Zone", secondary_y=True)

                fig.update_layout(
                    title=f"{ticker} Score History",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    **get_plotly_theme()
                )
                fig.update_yaxes(title_text="F-Score (0-9)", secondary_y=False, range=[0, 9])
                fig.update_yaxes(title_text="Z-Score", secondary_y=True)

                st.plotly_chart(fig, use_container_width=True)

                # Trend calculation
                trend = analyzer.calculate_trend(ticker, periods=min(4, len(valid_history)))
                if trend:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        direction_icon = {"improving": "+", "declining": "-", "stable": "="}
                        st.metric(
                            "F-Score Trend",
                            trend.trend_direction.title(),
                            f"{direction_icon.get(trend.trend_direction, '=')} {abs(trend.fscore_change):.1f} pts"
                        )
                    with col2:
                        zone_change_text = f"{trend.previous_zone} -> {trend.current_zone}" if trend.zone_changed else "No change"
                        st.metric(
                            "Z-Score Trend",
                            f"{trend.zscore_change:+.2f}",
                            zone_change_text
                        )
                    with col3:
                        st.metric("Periods Analyzed", trend.periods_analyzed)

                # F-Score component breakdown
                st.subheader("F-Score Component Breakdown")
                if "Profitability" in df.columns:
                    comp_fig = go.Figure()
                    comp_fig.add_trace(go.Bar(name="Profitability (0-4)", x=df["Year"], y=df["Profitability"]))
                    comp_fig.add_trace(go.Bar(name="Leverage (0-3)", x=df["Year"], y=df["Leverage"]))
                    comp_fig.add_trace(go.Bar(name="Efficiency (0-2)", x=df["Year"], y=df["Efficiency"]))
                    comp_fig.update_layout(barmode="stack", title="F-Score Components by Year", **get_plotly_theme())
                    st.plotly_chart(comp_fig, use_container_width=True)

            # Raw data table
            with st.expander("View Raw Data"):
                st.dataframe(df, use_container_width=True)

with tab_improving:
    st.subheader("Improving Stocks")
    st.caption("Stocks showing consistent F-Score improvement")

    col1, col2 = st.columns(2)
    with col1:
        min_improvement = st.slider("Min F-Score Improvement", 1, 5, 2)
    with col2:
        periods = st.slider("Over Periods", 2, 8, 4)

    if st.button("Find Improving Stocks", key="find_improving"):
        with st.spinner("Analyzing trends..."):
            improving = analyzer.find_improving(
                min_improvement=min_improvement,
                periods=periods,
                limit=20
            )

            if improving:
                for trend in improving:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.markdown(f"**{trend.ticker}**")
                        with col2:
                            st.metric("F-Score", f"{trend.current_fscore}/9", f"+{trend.fscore_change:.1f}")
                        with col3:
                            st.metric("Z-Score", f"{trend.current_zscore:.2f}" if trend.current_zscore else "N/A")
                        with col4:
                            st.caption(f"{trend.periods_analyzed} periods")
                        st.divider()
            else:
                st.info("No stocks found meeting the improvement criteria. Try adjusting the filters or score more stocks first.")

with tab_declining:
    st.subheader("Declining Stocks")
    st.caption("Stocks showing consistent F-Score decline - review for potential issues")

    col1, col2 = st.columns(2)
    with col1:
        min_decline = st.slider("Min F-Score Decline", 1, 5, 2)
    with col2:
        decline_periods = st.slider("Over Periods", 2, 8, 4, key="decline_periods")

    if st.button("Find Declining Stocks", key="find_declining"):
        with st.spinner("Analyzing trends..."):
            declining = analyzer.find_declining(
                min_decline=min_decline,
                periods=decline_periods,
                limit=20
            )

            if declining:
                for trend in declining:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.markdown(f"**{trend.ticker}**")
                        with col2:
                            st.metric("F-Score", f"{trend.current_fscore}/9", f"{trend.fscore_change:.1f}")
                        with col3:
                            zone_color = {"Safe": "green", "Grey": "orange", "Distress": "red"}.get(trend.current_zone, "grey")
                            st.metric("Zone", trend.current_zone or "N/A")
                        with col4:
                            st.caption(f"{trend.periods_analyzed} periods")
                        st.divider()
            else:
                st.info("No stocks found meeting the decline criteria.")

with tab_turnaround:
    st.subheader("Turnaround Candidates")
    st.caption("Stocks that moved from Distress to Grey/Safe zone - potential recovery plays")

    if st.button("Find Turnarounds", key="find_turnarounds"):
        with st.spinner("Scanning for turnarounds..."):
            turnarounds = analyzer.find_turnaround(limit=20)

            if turnarounds:
                for t in turnarounds:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**{t.ticker}**")
                            st.caption(f"Zone: {t.previous_zone} -> {t.current_zone}")
                        with col2:
                            st.metric(
                                "Z-Score Change",
                                f"{t.current_zscore:.2f}" if t.current_zscore else "N/A",
                                f"+{t.zscore_improvement:.2f}" if t.zscore_improvement else None
                            )
                        with col3:
                            st.metric("F-Score", f"{t.current_fscore}/9" if t.current_fscore else "N/A")
                        st.divider()
            else:
                st.info("No turnaround candidates found. These are stocks that transitioned from Distress zone to Grey or Safe.")

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("""
**About Trends**

The Trends page helps identify:

- **Improving**: Stocks with rising F-Scores
- **Declining**: Stocks with falling F-Scores
- **Turnarounds**: Moved out of Distress zone

*Note: Trends require multiple scored periods. Use the CLI or Compare page to score stocks and build history.*
""")
