"""
Decisions Page - Track investment theses and decision log.

Two tabs: My Decisions (decision log) and Theses Library (thesis management).
"""

import streamlit as st

from dashboard.components.decisions import (
    render_decision_card,
    render_decision_detail,
    render_decision_form,
    render_thesis_card,
    render_thesis_detail,
    render_thesis_edit_form,
    render_thesis_form,
)
from dashboard.config import DECISION_ACTIONS, DECISIONS_PAGE_LIMIT, THESIS_STATUS, THESES_PAGE_LIMIT
from dashboard.utils.decisions import (
    analyze_by_conviction,
    calculate_portfolio_return,
    create_decision,
    create_thesis,
    get_decision_by_id,
    get_decisions,
    get_decisions_with_outcomes,
    get_theses,
    get_thesis_by_id,
    update_decision_outcome,
    update_thesis,
)
from dashboard.utils.watchlist import get_stocks

st.set_page_config(page_title="Decisions | Asymmetric", layout="wide")

st.title("Decisions")
st.caption("Track investment theses and decision log")

# Research Wizard quick access
with st.container():
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🧪 Research Wizard", type="secondary", use_container_width=True):
            st.switch_page("pages/8_Research.py")

# Initialize session state
if "selected_decision_id" not in st.session_state:
    st.session_state.selected_decision_id = None
if "selected_thesis_id" not in st.session_state:
    st.session_state.selected_thesis_id = None
if "show_decision_form" not in st.session_state:
    st.session_state.show_decision_form = False
if "show_thesis_form" not in st.session_state:
    st.session_state.show_thesis_form = False
if "decision_action_filter" not in st.session_state:
    st.session_state.decision_action_filter = "all"
if "decision_ticker_filter" not in st.session_state:
    st.session_state.decision_ticker_filter = ""
if "thesis_status_filter" not in st.session_state:
    st.session_state.thesis_status_filter = "all"
if "thesis_ticker_filter" not in st.session_state:
    st.session_state.thesis_ticker_filter = ""
if "editing_thesis_id" not in st.session_state:
    st.session_state.editing_thesis_id = None

# Get watchlist for ticker filters
watchlist_stocks = get_stocks()
ticker_options = [""] + sorted(watchlist_stocks)


def _handle_decision_detail() -> bool:
    """Handle decision detail view in sidebar. Returns True if showing."""
    if not st.session_state.selected_decision_id:
        return False

    decision = get_decision_by_id(st.session_state.selected_decision_id)
    if not decision:
        st.session_state.selected_decision_id = None
        return False

    with st.sidebar:
        st.markdown("---")
        render_decision_detail(decision)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Close", use_container_width=True):
                st.session_state.selected_decision_id = None
                st.rerun()
        with col2:
            thesis_id = decision.get("thesis_id")
            if thesis_id and st.button("View Thesis", use_container_width=True):
                st.session_state.selected_thesis_id = thesis_id
                st.session_state.selected_decision_id = None
                st.rerun()

    return True


def _handle_thesis_detail() -> bool:
    """Handle thesis detail view in sidebar. Returns True if showing."""
    if not st.session_state.selected_thesis_id:
        return False

    thesis = get_thesis_by_id(st.session_state.selected_thesis_id)
    if not thesis:
        st.session_state.selected_thesis_id = None
        return False

    with st.sidebar:
        st.markdown("---")
        render_thesis_detail(thesis)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Close", use_container_width=True):
                st.session_state.selected_thesis_id = None
                st.rerun()
        with col2:
            if st.button("Edit", use_container_width=True):
                st.session_state.editing_thesis_id = thesis["id"]
                st.session_state.selected_thesis_id = None
                st.rerun()

    return True


# Handle detail views (show in sidebar)
_handle_decision_detail()
_handle_thesis_detail()

# Tab layout
tab1, tab2, tab3, tab4 = st.tabs(["My Decisions", "Theses Library", "Review Outcomes", "Analytics"])

# TAB 1: My Decisions
with tab1:
    # Filters row
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        action_filter = st.selectbox(
            "Filter by Action",
            options=["all", "buy", "hold", "sell", "pass"],
            format_func=lambda x: "All Actions" if x == "all" else DECISION_ACTIONS[x]["label"],
            key="filter_action",
        )
        st.session_state.decision_action_filter = action_filter

    with col2:
        ticker_filter = st.selectbox(
            "Filter by Ticker",
            options=ticker_options,
            format_func=lambda x: "All Tickers" if x == "" else x,
            key="filter_ticker",
        )
        st.session_state.decision_ticker_filter = ticker_filter

    with col3:
        if st.button("Refresh", use_container_width=True, key="refresh_decisions"):
            st.rerun()

    with col4:
        if st.button("New Decision", type="primary", use_container_width=True):
            st.session_state.show_decision_form = True
            st.session_state.show_thesis_form = False
            st.rerun()

    st.divider()

    # Show create form if requested
    if st.session_state.show_decision_form:
        # Get available theses for form
        available_theses = get_theses(status="active", limit=50)

        form_data = render_decision_form(available_theses=available_theses)

        if form_data:
            try:
                decision_id = create_decision(**form_data)
                st.success(f"Decision recorded! ID: {decision_id}")
                st.session_state.show_decision_form = False
                st.rerun()
            except ValueError as e:
                st.error(f"Error: {e}")
            except Exception as e:
                st.error(f"Failed to create decision: {e}")

        if st.button("Cancel", key="cancel_decision_form"):
            st.session_state.show_decision_form = False
            st.rerun()

        st.divider()

    # Fetch and display decisions
    decisions = get_decisions(
        action=action_filter if action_filter != "all" else None,
        ticker=ticker_filter if ticker_filter else None,
        limit=DECISIONS_PAGE_LIMIT,
    )

    if not decisions:
        st.info("No decisions recorded yet. Click 'New Decision' to create one.")
    else:
        st.caption(f"Showing {len(decisions)} decision(s)")
        for decision in decisions:
            render_decision_card(decision)

    # Quick actions
    if decisions:
        st.divider()
        st.caption("**Quick Actions**")
        action_cols = st.columns(3)

        with action_cols[0]:
            if st.button("View Theses", use_container_width=True):
                # Switch to theses tab (workaround: can't programmatically switch tabs)
                st.info("Switch to the 'Theses Library' tab above")

        with action_cols[1]:
            if st.button("Go to Compare", use_container_width=True):
                st.switch_page("pages/3_Compare.py")

        with action_cols[2]:
            if st.button("Go to Watchlist", use_container_width=True):
                st.switch_page("pages/1_Watchlist.py")


# TAB 2: Theses Library
with tab2:
    # Filters row
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["all", "draft", "active", "archived"],
            format_func=lambda x: "All Statuses" if x == "all" else THESIS_STATUS[x]["label"],
            key="filter_thesis_status",
        )
        st.session_state.thesis_status_filter = status_filter

    with col2:
        thesis_ticker_filter = st.selectbox(
            "Filter by Ticker",
            options=ticker_options,
            format_func=lambda x: "All Tickers" if x == "" else x,
            key="filter_thesis_ticker",
        )
        st.session_state.thesis_ticker_filter = thesis_ticker_filter

    with col3:
        if st.button("Refresh", use_container_width=True, key="refresh_theses"):
            st.rerun()

    with col4:
        if st.button("New Thesis", type="primary", use_container_width=True):
            st.session_state.show_thesis_form = True
            st.session_state.show_decision_form = False
            st.rerun()

    st.divider()

    # Show create form if requested
    if st.session_state.show_thesis_form:
        form_data = render_thesis_form()

        if form_data:
            try:
                thesis_id = create_thesis(**form_data)
                st.success(f"Thesis created! ID: {thesis_id}")
                st.session_state.show_thesis_form = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create thesis: {e}")

        if st.button("Cancel", key="cancel_thesis_form"):
            st.session_state.show_thesis_form = False
            st.rerun()

        st.divider()

    # Show edit form if requested
    if st.session_state.editing_thesis_id:
        thesis_to_edit = get_thesis_by_id(st.session_state.editing_thesis_id)
        if thesis_to_edit:
            form_data = render_thesis_edit_form(thesis_to_edit)

            if form_data:
                try:
                    thesis_id = form_data.pop("thesis_id")
                    success = update_thesis(thesis_id, **form_data)
                    if success:
                        st.success("Thesis updated!")
                        st.session_state.editing_thesis_id = None
                        st.rerun()
                    else:
                        st.error("Failed to update thesis - it may have been deleted")
                        st.session_state.editing_thesis_id = None
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to update thesis: {e}")
                    st.session_state.editing_thesis_id = None
                    st.rerun()

            if st.button("Cancel Edit", key="cancel_thesis_edit"):
                st.session_state.editing_thesis_id = None
                st.rerun()

            st.divider()
        else:
            st.session_state.editing_thesis_id = None

    # Fetch and display theses
    theses = get_theses(
        status=status_filter if status_filter != "all" else None,
        ticker=thesis_ticker_filter if thesis_ticker_filter else None,
        limit=THESES_PAGE_LIMIT,
    )

    if not theses:
        st.info("No theses created yet. Click 'New Thesis' or generate one from the Compare page.")
    else:
        st.caption(f"Showing {len(theses)} thesis/theses")
        for thesis in theses:
            render_thesis_card(thesis)

    # Quick actions
    if not theses:
        st.divider()
        st.markdown("""
        ### Tips for Creating Theses

        - **Manual Thesis**: Click 'New Thesis' to document your investment analysis
        - **AI-Generated**: Go to Compare page, run AI analysis, then click 'Create Thesis from Analysis'
        - **Bull/Bear Cases**: Document both sides of the investment argument
        - **Key Metrics**: Track what numbers you'll monitor to validate your thesis
        """)
    else:
        st.divider()
        st.caption("**Quick Actions**")
        action_cols = st.columns(3)

        with action_cols[0]:
            if st.button("Record Decision", use_container_width=True):
                st.session_state.show_decision_form = True
                st.rerun()

        with action_cols[1]:
            if st.button("Generate AI Thesis", use_container_width=True):
                st.switch_page("pages/3_Compare.py")

        with action_cols[2]:
            if st.button("View Watchlist", use_container_width=True):
                st.switch_page("pages/1_Watchlist.py")


# TAB 3: Review Outcomes
with tab3:
    st.subheader("Review Decision Outcomes")
    st.caption("Record what actually happened for retrospective analysis")

    # Get all decisions (can filter later)
    all_decisions = get_decisions(limit=100)

    if not all_decisions:
        st.info("No decisions recorded yet. Create decisions first, then return here to review outcomes.")
    else:
        # Filter: show decisions without outcomes
        ticker_filter_outcomes = st.selectbox(
            "Filter by Ticker",
            options=[""] + sorted(set(d["ticker"] for d in all_decisions)),
            format_func=lambda x: "All Tickers" if x == "" else x,
            key="outcome_ticker_filter",
        )

        show_all = st.checkbox("Show all decisions (including those with outcomes)", value=False)

        # Filter decisions
        decisions_to_review = [
            d for d in all_decisions
            if (not ticker_filter_outcomes or d["ticker"] == ticker_filter_outcomes)
        ]

        # If not showing all, filter out those with outcomes
        if not show_all:
            # Need to check which have outcomes by fetching decisions_with_outcomes
            decisions_with_outcome_ids = {d["id"] for d in get_decisions_with_outcomes(limit=1000)}
            decisions_to_review = [
                d for d in decisions_to_review
                if d["id"] not in decisions_with_outcome_ids
            ]

        if not decisions_to_review:
            if show_all:
                st.info("No decisions match the current filter.")
            else:
                st.success("All decisions have outcome data recorded! Switch to 'Show all decisions' to review.")
        else:
            st.caption(f"Showing {len(decisions_to_review)} decision(s)")

            for decision in decisions_to_review:
                with st.expander(
                    f"**{decision['ticker']}** — {decision['action'].upper()} "
                    f"({decision.get('decided_at', 'N/A')[:10]})"
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Company:** {decision.get('company_name', 'N/A')}")
                        st.markdown(f"**Action:** {decision['action'].upper()}")
                        st.markdown(f"**Confidence:** {decision.get('confidence', 'N/A')}/5")
                        if decision.get("target_price"):
                            st.markdown(f"**Target Price:** ${decision['target_price']:.2f}")
                        st.markdown(f"**Rationale:** {decision.get('rationale', 'N/A')[:200]}...")

                    with col2:
                        st.markdown(f"**Decision ID:** {decision['id']}")
                        st.markdown(f"**Decided:** {decision.get('decided_at', 'N/A')[:10]}")

                    st.divider()

                    # Outcome entry form
                    with st.form(f"outcome_form_{decision['id']}"):
                        st.markdown("**Record Outcome**")

                        outcome_col1, outcome_col2 = st.columns(2)

                        with outcome_col1:
                            actual_outcome = st.selectbox(
                                "Outcome",
                                options=["success", "partial", "failure", "ongoing"],
                                format_func=lambda x: x.title(),
                                key=f"outcome_{decision['id']}",
                            )

                        with outcome_col2:
                            actual_price = st.number_input(
                                "Actual Price ($)",
                                min_value=0.0,
                                value=decision.get("target_price", 100.0) or 100.0,
                                step=1.0,
                                format="%.2f",
                                key=f"price_{decision['id']}",
                            )

                        lessons_learned = st.text_area(
                            "Lessons Learned",
                            placeholder="What did you learn from this decision? What would you do differently?",
                            height=100,
                            key=f"lessons_{decision['id']}",
                        )

                        hit = st.checkbox(
                            "Thesis proved correct (hit)",
                            value=actual_outcome == "success",
                            key=f"hit_{decision['id']}",
                        )

                        if st.form_submit_button("Save Outcome", type="primary"):
                            success = update_decision_outcome(
                                decision_id=decision["id"],
                                actual_outcome=actual_outcome,
                                actual_price=actual_price if actual_price > 0 else None,
                                lessons_learned=lessons_learned if lessons_learned else None,
                                hit=hit,
                            )

                            if success:
                                st.success("Outcome recorded!")
                                st.rerun()
                            else:
                                st.error("Failed to save outcome")


# TAB 4: Analytics
with tab4:
    st.subheader("Decision Analytics")
    st.caption("Analyze your decision-making track record")

    # Import plotly for charts
    import plotly.express as px
    import plotly.graph_objects as go

    # Get all decisions with outcomes
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
    else:
        st.success(f"Analyzing {len(decisions_with_outcomes)} decisions with outcome data")

        # Conviction analysis
        conviction_analysis = analyze_by_conviction(decisions_with_outcomes)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Hit Rate by Conviction Level**")
            st.caption("Does higher conviction correlate with better outcomes?")

            # Get theme-aware colors for heatmap
            red = get_semantic_color('red')
            yellow = get_semantic_color('yellow')
            green = get_semantic_color('green')

            # Bar chart
            fig = px.bar(
                conviction_analysis,
                x="conviction_level",
                y="hit_rate_pct",
                color="hit_rate_pct",
                color_continuous_scale=[red, yellow, green],
                range_color=[0, 100],
                labels={
                    "conviction_level": "Conviction (1=Low, 5=High)",
                    "hit_rate_pct": "Hit Rate %"
                },
                text="hit_rate_pct",
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(showlegend=False, height=400)
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

        with col2:
            st.markdown("**What-If Analysis**")
            st.caption("How would returns differ if you only acted on high-conviction ideas?")

            # Calculate returns
            all_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=1)
            high_conviction_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=4)
            very_high_conviction_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=5)

            # Count decisions in each category
            all_count = sum(1 for d in decisions_with_outcomes if d.get("confidence", 3) >= 1)
            high_count = sum(1 for d in decisions_with_outcomes if d.get("confidence", 3) >= 4)
            very_high_count = sum(1 for d in decisions_with_outcomes if d.get("confidence", 3) >= 5)

            # Metrics
            st.metric(
                "All Decisions (1-5)",
                f"{all_return:.1f}%",
                help=f"Average return across {all_count} decisions"
            )
            st.metric(
                "High Conviction Only (4-5)",
                f"{high_conviction_return:.1f}%",
                delta=f"{high_conviction_return - all_return:+.1f}%",
                help=f"Average return across {high_count} high-conviction decisions"
            )
            st.metric(
                "Very High Conviction Only (5)",
                f"{very_high_conviction_return:.1f}%",
                delta=f"{very_high_conviction_return - all_return:+.1f}%",
                help=f"Average return across {very_high_count} very-high-conviction decisions"
            )

            st.divider()

            # Insight
            if high_conviction_return > all_return:
                st.success(
                    f"✓ Your high-conviction decisions outperformed by "
                    f"{high_conviction_return - all_return:.1f}%. "
                    f"Focus on quality over quantity!"
                )
            elif high_conviction_return < all_return:
                st.warning(
                    f"⚠ Your high-conviction decisions underperformed by "
                    f"{all_return - high_conviction_return:.1f}%. "
                    f"Review your conviction calibration."
                )
            else:
                st.info("Your conviction levels show no clear correlation with outcomes yet.")

        st.divider()

        # Lessons learned summary
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


# Footer
st.divider()
st.caption(
    "**Tip:** Use the [Research Wizard](pages/8_Research.py) for a guided workflow from research to decision. "
    "Or use the Compare page to run AI analysis on stocks and create theses from the results."
)
