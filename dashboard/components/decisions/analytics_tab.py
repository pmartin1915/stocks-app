"""Analytics tab — decision-making track record analysis."""

import plotly.express as px
import streamlit as st

from dashboard.theme import get_plotly_theme, get_semantic_color
from dashboard.utils.decisions import (
    analyze_by_conviction,
    calculate_portfolio_return,
    get_decisions_with_outcomes,
)


def render_analytics_tab() -> None:
    """Render the Decision Analytics tab."""
    st.subheader("Decision Analytics")
    st.caption("Analyze your decision-making track record")

    decisions_with_outcomes = get_decisions_with_outcomes(limit=1000)

    if len(decisions_with_outcomes) < 5:
        st.info("""
**Not enough outcome data for analytics**

Record at least 5 decision outcomes in the "Review Outcomes" tab to see analytics.

Analytics will show:
- Hit rate by conviction level (1-5 stars)
- "What-If" analysis comparing all decisions vs. high-conviction only
- Common lessons learned across decisions
        """)
        return

    st.success(f"Analyzing {len(decisions_with_outcomes)} decisions with outcome data")

    conviction_analysis = analyze_by_conviction(decisions_with_outcomes)

    col1, col2 = st.columns(2)

    with col1:
        _render_conviction_chart(conviction_analysis)

    with col2:
        _render_what_if_analysis(decisions_with_outcomes)

    st.divider()
    _render_lessons_learned(decisions_with_outcomes)


def _render_conviction_chart(conviction_analysis) -> None:
    """Render hit rate by conviction level chart."""
    st.markdown("**Hit Rate by Conviction Level**")
    st.caption("Does higher conviction correlate with better outcomes?")

    red = get_semantic_color("red")
    yellow = get_semantic_color("yellow")
    green = get_semantic_color("green")

    fig = px.bar(
        conviction_analysis,
        x="conviction_level",
        y="hit_rate_pct",
        color="hit_rate_pct",
        color_continuous_scale=[red, yellow, green],
        range_color=[0, 100],
        labels={
            "conviction_level": "Conviction (1=Low, 5=High)",
            "hit_rate_pct": "Hit Rate %",
        },
        text="hit_rate_pct",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(showlegend=False, height=400, **get_plotly_theme())
    st.plotly_chart(fig, use_container_width=True)

    # Table with details
    st.dataframe(
        conviction_analysis,
        column_config={
            "conviction_level": st.column_config.NumberColumn("Conviction", format="%d"),
            "hit_count": st.column_config.NumberColumn("Hits"),
            "total_count": st.column_config.NumberColumn("Total"),
            "hit_rate_pct": st.column_config.NumberColumn("Hit Rate", format="%.1f%%"),
        },
        hide_index=True,
        use_container_width=True,
    )


def _render_what_if_analysis(decisions_with_outcomes: list) -> None:
    """Render what-if conviction analysis."""
    st.markdown("**What-If Analysis**")
    st.caption("How would returns differ if you only acted on high-conviction ideas?")

    all_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=1)
    high_conviction_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=4)
    very_high_conviction_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=5)

    all_count = sum(1 for d in decisions_with_outcomes if d.get("confidence", 3) >= 1)
    high_count = sum(1 for d in decisions_with_outcomes if d.get("confidence", 3) >= 4)
    very_high_count = sum(1 for d in decisions_with_outcomes if d.get("confidence", 3) >= 5)

    st.metric(
        "All Decisions (1-5)",
        f"{all_return:.1f}%",
        help=f"Average return across {all_count} decisions",
    )
    st.metric(
        "High Conviction Only (4-5)",
        f"{high_conviction_return:.1f}%",
        delta=f"{high_conviction_return - all_return:+.1f}%",
        help=f"Average return across {high_count} high-conviction decisions",
    )
    st.metric(
        "Very High Conviction Only (5)",
        f"{very_high_conviction_return:.1f}%",
        delta=f"{very_high_conviction_return - all_return:+.1f}%",
        help=f"Average return across {very_high_count} very-high-conviction decisions",
    )

    st.divider()

    if high_conviction_return > all_return:
        st.success(
            f"Your high-conviction decisions outperformed by "
            f"{high_conviction_return - all_return:.1f}%. "
            f"Focus on quality over quantity!"
        )
    elif high_conviction_return < all_return:
        st.warning(
            f"Your high-conviction decisions underperformed by "
            f"{all_return - high_conviction_return:.1f}%. "
            f"Review your conviction calibration."
        )
    else:
        st.info("Your conviction levels show no clear correlation with outcomes yet.")


def _render_lessons_learned(decisions_with_outcomes: list) -> None:
    """Render aggregated lessons learned section."""
    st.markdown("**Common Lessons Learned**")
    st.caption("Aggregated insights from your decision outcomes")

    lessons = [
        d.get("lessons_learned")
        for d in decisions_with_outcomes
        if d.get("lessons_learned")
    ]

    if lessons:
        with st.expander(f"View {len(lessons)} lesson(s)"):
            for i, lesson in enumerate(lessons[:10], 1):
                st.markdown(f"{i}. {lesson}")
            if len(lessons) > 10:
                st.caption(f"...and {len(lessons) - 10} more")
    else:
        st.info("No lessons recorded yet. Add lessons in the 'Review Outcomes' tab.")
