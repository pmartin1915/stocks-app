"""Outcomes tab — review and record decision outcomes."""

import streamlit as st

from dashboard.theme import get_semantic_color
from dashboard.utils.formatters import format_date_friendly


def render_review_outcomes_tab() -> None:
    """Render the Review Outcomes tab for tracking decision outcomes."""
    st.subheader("Review Outcomes")
    st.caption("Record what actually happened vs. your predictions")

    from dashboard.utils.decisions import (
        get_decisions,
        update_decision_outcome,
        get_decision_by_id,
        get_decisions_with_outcomes,
    )

    all_decisions = get_decisions(limit=100)
    pending_decisions = [d for d in all_decisions if not d.get("actual_outcome")]
    completed_decisions = get_decisions_with_outcomes(limit=50)

    view_mode = st.radio("View", options=["Pending Review", "Completed Reviews"], horizontal=True)

    if view_mode == "Pending Review":
        _render_pending_reviews(pending_decisions, get_decision_by_id, update_decision_outcome)
    else:
        _render_completed_reviews(completed_decisions)


def _render_pending_reviews(pending_decisions, get_decision_by_id, update_decision_outcome):
    """Render pending outcome reviews."""
    if not pending_decisions:
        st.info("No decisions pending outcome review. All your decisions have been reviewed!")
        return

    st.markdown(f"**{len(pending_decisions)} decision(s) awaiting outcome review**")

    for decision in pending_decisions:
        ticker = decision.get("ticker", "N/A")
        action = decision.get("action", "N/A").upper()
        confidence = decision.get("confidence", 3)
        decided_at = decision.get("decided_at", "N/A")
        date_str = format_date_friendly(decided_at)

        with st.expander(f"{ticker} - {action} ({date_str}) - Conviction: {confidence}/5"):
            full_decision = get_decision_by_id(decision["id"])

            st.markdown("### Original Thesis vs. Outcome")
            comp_col1, comp_col2 = st.columns(2)

            with comp_col1:
                st.markdown("#### Original Thesis")
                st.markdown(f"**Summary**: {full_decision.get('thesis_summary', 'N/A')[:200]}...")
                st.markdown(f"**Action**: {action}")
                st.markdown(f"**Conviction**: {confidence}/5")
                if decision.get("target_price"):
                    st.markdown(f"**Target Price**: ${decision['target_price']:.2f}")
                st.markdown(f"**Date**: {date_str}")
                st.markdown(f"**Rationale**: {decision.get('rationale', 'N/A')[:150]}...")

            with comp_col2:
                st.markdown("#### Record Actual Outcome")
                st.caption("Fill in what actually happened")

                outcome = st.selectbox(
                    "Actual Outcome",
                    options=["success", "partial", "failure", "unknown"],
                    format_func=lambda x: x.capitalize(),
                    key=f"outcome_{decision['id']}",
                )

                actual_price = st.number_input(
                    "Actual Price ($)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    help="Current stock price or exit price",
                    key=f"price_{decision['id']}",
                )

                if actual_price > 0 and decision.get("target_price", 0) > 0:
                    pct_return = ((actual_price - decision["target_price"]) / decision["target_price"]) * 100
                    color = get_semantic_color("green") if pct_return > 0 else get_semantic_color("red")
                    st.markdown(f"<div style='color:{color};font-weight:600'>Return vs. Target: {pct_return:+.2f}%</div>", unsafe_allow_html=True)

                hit = st.checkbox("Thesis proved correct", help="Check if your original thesis was validated", key=f"hit_{decision['id']}")

            st.divider()

            lessons = st.text_area("Lessons Learned", placeholder="What did you learn from this decision?", height=100, key=f"lessons_{decision['id']}")

            if st.button("Save Outcome", key=f"save_{decision['id']}", type="primary", use_container_width=True):
                success = update_decision_outcome(
                    decision_id=decision["id"],
                    actual_outcome=outcome,
                    actual_price=actual_price if actual_price > 0 else None,
                    lessons_learned=lessons if lessons else None,
                    hit=hit,
                )
                if success:
                    st.success(f"Outcome recorded for {ticker}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to save outcome. Please try again.")


def _render_completed_reviews(completed_decisions):
    """Render completed outcome reviews."""
    if not completed_decisions:
        st.info("No completed reviews yet. Record outcomes in 'Pending Review' to see them here.")
        return

    st.markdown(f"**{len(completed_decisions)} decision(s) with recorded outcomes**")

    for decision in completed_decisions:
        ticker = decision.get("ticker", "N/A")
        action = decision.get("action", "N/A").upper()
        confidence = decision.get("confidence", 3)
        actual_outcome = decision.get("actual_outcome", "unknown").capitalize()
        hit = decision.get("hit")

        decided_str = format_date_friendly(decision.get("decided_at", "N/A"), default="Unknown")
        outcome_str = format_date_friendly(decision.get("outcome_date", "N/A"), default="Unknown")

        if hit is True:
            badge_color = get_semantic_color("green")
            badge_text = "Hit"
        elif hit is False:
            badge_color = get_semantic_color("red")
            badge_text = "Miss"
        else:
            badge_color = get_semantic_color("gray")
            badge_text = "? Unknown"

        with st.expander(f"{ticker} - {action} - {actual_outcome} ({outcome_str})"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Original Thesis")
                st.markdown(f"**Action**: {action}")
                st.markdown(f"**Conviction**: {confidence}/5")
                if decision.get("target_price"):
                    st.markdown(f"**Target Price**: ${decision['target_price']:.2f}")
                st.markdown(f"**Date Decided**: {decided_str}")
                st.markdown(f"**Rationale**: {decision.get('rationale', 'N/A')[:150]}...")
                if decision.get("thesis_summary"):
                    st.markdown(f"**Thesis**: {decision['thesis_summary'][:150]}...")

            with col2:
                st.markdown("#### Actual Outcome")
                from dashboard.theme import get_color

                text_on_accent = get_color("text_on_accent")
                st.markdown(
                    f"<div style='background:{badge_color};color:{text_on_accent};padding:4px 12px;"
                    f"border-radius:4px;display:inline-block;font-weight:600'>{badge_text}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Outcome**: {actual_outcome}")
                if decision.get("actual_price"):
                    st.markdown(f"**Actual Price**: ${decision['actual_price']:.2f}")

                    if decision.get("target_price", 0) > 0:
                        pct_return = ((decision["actual_price"] - decision["target_price"]) / decision["target_price"]) * 100
                        return_color = get_semantic_color("green") if pct_return > 0 else get_semantic_color("red")
                        st.markdown(f"<div style='color:{return_color};font-weight:600;font-size:1.2rem'>Return: {pct_return:+.2f}%</div>", unsafe_allow_html=True)

                st.markdown(f"**Reviewed On**: {outcome_str}")

            if decision.get("lessons_learned"):
                st.divider()
                st.markdown("#### Lessons Learned")
                st.markdown(decision["lessons_learned"])
