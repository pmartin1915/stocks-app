"""Decisions tab — decision log with filters and create form."""

import streamlit as st

from dashboard.components.decisions.cards import render_decision_card, render_decision_form
from dashboard.config import DECISION_ACTIONS, DECISIONS_PAGE_LIMIT
from dashboard.utils.decisions import create_decision, get_decisions, get_theses


def render_decisions_tab(ticker_options: list[str]) -> None:
    """Render the My Decisions tab.

    Args:
        ticker_options: List of ticker symbols for filter dropdown.
    """
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
                st.info("Switch to the 'Theses Library' tab above")

        with action_cols[1]:
            if st.button("Go to Compare", use_container_width=True):
                st.switch_page("pages/5_Compare.py")

        with action_cols[2]:
            if st.button("Go to Watchlist", use_container_width=True):
                st.switch_page("pages/2_Watchlist.py")
