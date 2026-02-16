"""Outcomes tab — review and record decision outcomes."""

import streamlit as st

from dashboard.utils.decisions import (
    get_decisions,
    get_decisions_with_outcomes,
    update_decision_outcome,
)


def render_outcomes_tab() -> None:
    """Render the Review Outcomes tab."""
    st.subheader("Review Decision Outcomes")
    st.caption("Record what actually happened for retrospective analysis")

    all_decisions = get_decisions(limit=100)

    if not all_decisions:
        st.info("No decisions recorded yet. Create decisions first, then return here to review outcomes.")
        return

    # Filter controls
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

    if not show_all:
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
        return

    st.caption(f"Showing {len(decisions_to_review)} decision(s)")

    for decision in decisions_to_review:
        with st.expander(
            f"**{decision['ticker']}** \u2014 {decision['action'].upper()} "
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
