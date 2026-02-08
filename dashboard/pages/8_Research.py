"""
Research Page - Unified research -> thesis -> decision wizard.

Provides a step-by-step workflow for researching stocks,
creating investment theses, and recording decisions.
"""

import streamlit as st

from dashboard.components.research import (
    render_step_indicator,
    render_research_step,
    render_thesis_step,
    render_decision_step,
    render_review_outcomes_tab,
    render_analytics_tab,
)
from dashboard.utils.sidebar import render_full_sidebar

st.set_page_config(page_title="Research | Asymmetric", layout="wide")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Research Wizard")
st.caption("Research -> Thesis -> Decision workflow")

# Initialize session state for wizard
if "research_step" not in st.session_state:
    st.session_state.research_step = 0
if "research_ticker" not in st.session_state:
    st.session_state.research_ticker = None
if "research_scores" not in st.session_state:
    st.session_state.research_scores = None
if "research_ai_analysis" not in st.session_state:
    st.session_state.research_ai_analysis = None
if "research_thesis_draft" not in st.session_state:
    st.session_state.research_thesis_draft = {}

# Tab selection
tab1, tab2, tab3 = st.tabs(["New Research", "Review Outcomes", "Analytics"])

with tab1:
    # Main wizard flow
    render_step_indicator(st.session_state.research_step)
    st.divider()

    if st.session_state.research_step == 0:
        render_research_step()
    elif st.session_state.research_step == 1:
        render_thesis_step()
    elif st.session_state.research_step == 2:
        render_decision_step()

    # Reset button (always visible)
    st.divider()

    has_data = (
        st.session_state.research_ticker
        or st.session_state.research_scores
        or st.session_state.research_ai_analysis
        or st.session_state.research_thesis_draft
    )

    if has_data:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Reset Wizard", type="secondary", use_container_width=True):
                if "confirm_reset" not in st.session_state:
                    st.session_state.confirm_reset = False
                st.session_state.confirm_reset = True
                st.rerun()

        if st.session_state.get("confirm_reset", False):
            st.warning("This will clear all unsaved research data. Are you sure?")
            conf_col1, conf_col2, conf_col3 = st.columns([1, 1, 2])
            with conf_col1:
                if st.button("Yes, Reset", type="primary"):
                    st.session_state.research_step = 0
                    st.session_state.research_ticker = None
                    st.session_state.research_scores = None
                    st.session_state.research_ai_analysis = None
                    st.session_state.research_thesis_draft = {}
                    st.session_state.confirm_reset = False
                    st.rerun()
            with conf_col2:
                if st.button("Cancel"):
                    st.session_state.confirm_reset = False
                    st.rerun()
    else:
        st.caption("Start researching a stock to begin the workflow")

with tab2:
    render_review_outcomes_tab()

with tab3:
    render_analytics_tab()
