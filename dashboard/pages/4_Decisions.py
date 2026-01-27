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
    create_decision,
    create_thesis,
    get_decision_by_id,
    get_decisions,
    get_theses,
    get_thesis_by_id,
    update_thesis,
)
from dashboard.utils.watchlist import get_stocks

st.set_page_config(page_title="Decisions | Asymmetric", layout="wide")

st.title("Decisions")
st.caption("Track investment theses and decision log")

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
tab1, tab2 = st.tabs(["My Decisions", "Theses Library"])

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


# Footer
st.divider()
st.caption(
    "**Tip:** Use the Compare page to run AI analysis on stocks, then create theses from the results. "
    "Link your decisions to theses to track your investment rationale over time."
)
