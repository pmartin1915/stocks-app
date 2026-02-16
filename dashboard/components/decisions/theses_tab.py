"""Theses tab — thesis library with filters, create/edit forms."""

import streamlit as st

from dashboard.components.decisions.cards import (
    render_thesis_card,
    render_thesis_edit_form,
    render_thesis_form,
)
from dashboard.config import THESIS_STATUS, THESES_PAGE_LIMIT
from dashboard.utils.decisions import (
    create_thesis,
    get_theses,
    get_thesis_by_id,
    update_thesis,
)


def render_theses_tab(ticker_options: list[str]) -> None:
    """Render the Theses Library tab.

    Args:
        ticker_options: List of ticker symbols for filter dropdown.
    """
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
                st.switch_page("pages/5_Compare.py")

        with action_cols[2]:
            if st.button("View Watchlist", use_container_width=True):
                st.switch_page("pages/2_Watchlist.py")
