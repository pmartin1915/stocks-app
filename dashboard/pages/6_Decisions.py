"""
Decisions Page - Track investment theses and decision log.

Four tabs: My Decisions, Theses Library, Review Outcomes, Analytics.
Tab logic lives in dashboard/components/decisions/ for maintainability.
"""

import streamlit as st

from dashboard.components.decisions import (
    render_analytics_tab,
    render_decision_detail,
    render_decisions_tab,
    render_outcomes_tab,
    render_thesis_detail,
    render_theses_tab,
)
from dashboard.components.page_header import render_page_header
from dashboard.styles import inject_global_styles, page_footer
from dashboard.utils.decisions import get_decision_by_id, get_thesis_by_id
from dashboard.utils.session_state import init_page_state
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.watchlist import get_stocks

st.set_page_config(page_title="Decisions | Asymmetric", layout="wide")

# Initialize session state for this page
init_page_state("decisions")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar(current_page="decisions")
inject_global_styles()

render_page_header(
    title="Decisions",
    subtitle="Track investment theses and decision log",
    breadcrumbs=[("Home", "app.py"), ("Decisions", "")],
)

# Research Wizard quick access
with st.container():
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Research Wizard", type="secondary", use_container_width=True):
            st.switch_page("pages/4_Research.py")

# Get watchlist for ticker filters
watchlist_stocks = get_stocks()
ticker_options = [""] + sorted(watchlist_stocks)


# --- Detail view handlers (shown in sidebar) ---

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


# Handle detail views (show in sidebar) — mutually exclusive
# If both are set (e.g., user clicked decision then thesis), prefer the most recent
if st.session_state.selected_decision_id and st.session_state.selected_thesis_id:
    # Both set — clear the decision (thesis was selected more recently via "View Thesis")
    st.session_state.selected_decision_id = None

if not _handle_decision_detail():
    _handle_thesis_detail()

# Tab layout
tab1, tab2, tab3, tab4 = st.tabs(["My Decisions", "Theses Library", "Review Outcomes", "Analytics"])

with tab1:
    render_decisions_tab(ticker_options)

with tab2:
    render_theses_tab(ticker_options)

with tab3:
    render_outcomes_tab()

with tab4:
    render_analytics_tab()

# Footer
st.divider()
st.caption(
    "**Tip:** Use the [Research Wizard](pages/4_Research.py) for a guided workflow from research to decision. "
    "Or use the Compare page to run AI analysis on stocks and create theses from the results."
)

page_footer()
