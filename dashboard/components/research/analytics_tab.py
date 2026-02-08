"""Analytics tab — conviction analysis and what-if calculator."""

import streamlit as st

from dashboard.theme import get_semantic_color, get_plotly_theme


def render_analytics_tab() -> None:
    """Render the Analytics tab with hit rate visualization."""
    st.subheader("Decision Analytics")
    st.caption("Analyze your prediction accuracy by conviction level")

    from dashboard.utils.decisions import (
        get_decisions_with_outcomes,
        analyze_by_conviction,
        calculate_portfolio_return,
    )

    decisions_with_outcomes = get_decisions_with_outcomes(limit=100)

    if not decisions_with_outcomes:
        st.info("No outcome data yet. Record outcomes in the 'Review Outcomes' tab to see analytics.")
        return

    conviction_stats = analyze_by_conviction(decisions_with_outcomes)

    st.markdown("### Hit Rate by Conviction Level")
    st.caption(f"Based on {len(decisions_with_outcomes)} decision(s) with recorded outcomes")

    _render_conviction_chart(conviction_stats)

    # Stats table
    st.markdown("### Detailed Statistics")
    import pandas as pd

    df = pd.DataFrame(conviction_stats)
    df.columns = ["Conviction", "Hits", "Total", "Hit Rate (%)"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # What-If Calculator
    _render_what_if_analysis(decisions_with_outcomes, calculate_portfolio_return)


def _render_conviction_chart(conviction_stats: list) -> None:
    """Render the conviction hit rate bar chart."""
    import plotly.graph_objects as go

    green = get_semantic_color("green")
    yellow = get_semantic_color("yellow")
    red = get_semantic_color("red")

    fig = go.Figure(
        data=[
            go.Bar(
                x=[f"Level {s['conviction_level']}" for s in conviction_stats],
                y=[s["hit_rate_pct"] for s in conviction_stats],
                text=[f"{s['hit_rate_pct']:.1f}%" for s in conviction_stats],
                textposition="auto",
                marker_color=[green if s["hit_rate_pct"] >= 60 else yellow if s["hit_rate_pct"] >= 40 else red for s in conviction_stats],
            )
        ]
    )

    fig.update_layout(
        xaxis_title="Conviction Level",
        yaxis_title="Hit Rate (%)",
        yaxis_range=[0, 100],
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        **get_plotly_theme(),
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_what_if_analysis(decisions_with_outcomes, calculate_portfolio_return):
    """Render the what-if analysis section."""
    st.markdown("### What-If Analysis")
    st.caption("See how returns vary by conviction threshold")

    min_conviction = st.slider("Minimum Conviction Level", min_value=1, max_value=5, value=3, help="Only include decisions with conviction >= this level")

    avg_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=min_conviction)
    filtered_count = sum(1 for d in decisions_with_outcomes if (d.get("confidence") or 3) >= min_conviction)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Avg Return", f"{avg_return:+.2f}%")
    with col2:
        st.metric("Decisions Included", filtered_count)

    if min_conviction > 1:
        all_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=1)
        improvement = avg_return - all_return
        if improvement > 0:
            st.success(f"High-conviction filter improved returns by {improvement:+.2f}%")
        elif improvement < 0:
            st.warning(f"High-conviction filter reduced returns by {improvement:.2f}%")
        else:
            st.info("No difference in returns")
