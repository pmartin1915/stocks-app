"""Health tab — weighted scores, zone allocation, and health assessment."""

import pandas as pd
import plotly.express as px
import streamlit as st

from asymmetric.core.portfolio import PortfolioManager
from dashboard.theme import get_plotly_theme


def render_health_tab(
    holdings: list,
    weighted_scores,
    manager: PortfolioManager,
) -> None:
    """Render the Portfolio Health tab.

    Args:
        holdings: List of HoldingDetail objects.
        weighted_scores: WeightedScores result from manager.
        manager: PortfolioManager instance.
    """
    st.subheader("Portfolio Health")
    st.caption("Portfolio-weighted scores and zone allocation")

    if not holdings:
        st.info("Add holdings to see portfolio health metrics.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Weighted Scores**")
        st.metric(
            "Weighted F-Score",
            f"{weighted_scores.weighted_fscore:.1f}/9",
            help="Portfolio-weighted average F-Score based on cost basis allocation",
        )
        st.metric(
            "Weighted Z-Score",
            f"{weighted_scores.weighted_zscore:.2f}",
            help="Portfolio-weighted average Z-Score",
        )
        st.caption(f"Holdings with scores: {weighted_scores.holdings_with_scores}")
        if weighted_scores.holdings_without_scores > 0:
            st.warning(f"{weighted_scores.holdings_without_scores} holdings missing scores")

    with col2:
        st.markdown("**Zone Allocation**")
        zone_data = {
            "Zone": ["Safe", "Grey", "Distress"],
            "Allocation %": [
                weighted_scores.safe_allocation,
                weighted_scores.grey_allocation,
                weighted_scores.distress_allocation,
            ],
        }
        zone_df = pd.DataFrame(zone_data)

        fig = px.bar(
            zone_df,
            x="Zone",
            y="Allocation %",
            color="Zone",
            color_discrete_map={"Safe": "green", "Grey": "orange", "Distress": "red"},
        )
        fig.update_layout(showlegend=False, title="Allocation by Z-Score Zone", **get_plotly_theme())
        st.plotly_chart(fig, use_container_width=True)

    # Health assessment
    st.divider()
    st.markdown("**Health Assessment**")

    assessments = []

    if weighted_scores.weighted_fscore >= 7:
        assessments.append(("F-Score", "Strong financial health across portfolio", "green"))
    elif weighted_scores.weighted_fscore >= 5:
        assessments.append(("F-Score", "Moderate financial health - some holdings may need review", "orange"))
    else:
        assessments.append(("F-Score", "Weak financial health - consider reviewing underperformers", "red"))

    if weighted_scores.distress_allocation > 20:
        assessments.append(("Z-Score", f"{weighted_scores.distress_allocation:.1f}% in Distress zone - high bankruptcy risk exposure", "red"))
    elif weighted_scores.grey_allocation > 40:
        assessments.append(("Z-Score", f"{weighted_scores.grey_allocation:.1f}% in Grey zone - moderate uncertainty", "orange"))
    elif weighted_scores.safe_allocation > 60:
        assessments.append(("Z-Score", f"{weighted_scores.safe_allocation:.1f}% in Safe zone - low bankruptcy risk", "green"))

    for metric, assessment, color in assessments:
        st.markdown(f":{color}[**{metric}**]: {assessment}")

    # Take snapshot button
    st.divider()
    if st.button("Take Portfolio Snapshot"):
        from asymmetric.core.portfolio.snapshot_service import get_last_snapshot_date
        from datetime import date

        last_date = get_last_snapshot_date()
        if last_date and last_date.date() == date.today():
            st.warning(f"Snapshot already exists for today ({last_date.strftime('%Y-%m-%d %H:%M')}). Only one snapshot per day is recommended.")
        else:
            snapshot = manager.take_snapshot()
            st.success(f"Snapshot saved at {snapshot.snapshot_date}")
