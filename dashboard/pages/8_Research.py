"""
Research Page - Unified research → thesis → decision wizard.

Provides a step-by-step workflow for researching stocks,
creating investment theses, and recording decisions.
"""

import streamlit as st

from dashboard.components.ai_content import render_ai_section
from dashboard.components.score_display import render_score_panel
from dashboard.components.stock_card import (
    render_price_with_range,
    render_sparkline,
    render_key_metrics_row,
)
from dashboard.components import icons
from dashboard.components.icons import COLORS
from dashboard.utils.scoring import get_scores_for_ticker
from dashboard.utils.watchlist import get_cached_scores, get_stocks, add_stock

st.set_page_config(page_title="Research | Asymmetric", layout="wide")

st.title("Research Wizard")
st.caption("Research → Thesis → Decision workflow")

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


def render_step_indicator(current_step: int) -> None:
    """Render the wizard step indicator."""
    steps = ["1. Research", "2. Thesis", "3. Decision"]

    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if i < current_step:
                # Completed step
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:8px;background:{COLORS['green']};
                                color:#fff;border-radius:8px;font-weight:600">
                        ✓ {step}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif i == current_step:
                # Current step
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:8px;background:{COLORS['blue']};
                                color:#fff;border-radius:8px;font-weight:600">
                        ● {step}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                # Future step
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:8px;background:#e5e7eb;
                                color:{COLORS['gray']};border-radius:8px">
                        ○ {step}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_research_step() -> None:
    """Render Step 1: Research - stock selection and score analysis."""
    st.subheader("Step 1: Research Stock")

    # Stock selection
    watchlist = get_stocks()

    col1, col2 = st.columns([2, 1])

    with col1:
        if watchlist:
            ticker = st.selectbox(
                "Select from watchlist or enter ticker",
                options=[""] + sorted(watchlist),
                index=0 if not st.session_state.research_ticker else
                    (sorted(watchlist).index(st.session_state.research_ticker) + 1
                     if st.session_state.research_ticker in watchlist else 0),
                format_func=lambda x: "Choose a stock..." if x == "" else x,
            )
        else:
            ticker = ""

    with col2:
        manual_ticker = st.text_input(
            "Or enter ticker",
            value="" if ticker else (st.session_state.research_ticker or ""),
            placeholder="AAPL",
        ).upper().strip()

    # Use manual ticker if provided
    selected_ticker = manual_ticker if manual_ticker else ticker

    if selected_ticker:
        st.session_state.research_ticker = selected_ticker

        # Fetch scores button
        if st.button("Analyze Stock", type="primary"):
            with st.spinner(f"Fetching data for {selected_ticker}..."):
                # Try cached first
                cached = get_cached_scores(selected_ticker)
                if cached and "piotroski" in cached:
                    st.session_state.research_scores = cached
                else:
                    st.session_state.research_scores = get_scores_for_ticker(selected_ticker)

        # Display scores if available
        if st.session_state.research_scores:
            scores = st.session_state.research_scores

            if "error" in scores:
                st.error(f"Error: {scores.get('message', 'Failed to fetch data')}")
            else:
                st.divider()

                # Price and scores panel
                price_col, scores_col = st.columns([1, 1.5])

                with price_col:
                    st.markdown("**Price & Market Data**")
                    render_price_with_range(selected_ticker)
                    sparkline = render_sparkline(selected_ticker, width=200, height=50)
                    if sparkline:
                        st.markdown(sparkline, unsafe_allow_html=True)
                    st.divider()
                    render_key_metrics_row(selected_ticker)

                with scores_col:
                    st.markdown("**Financial Health Scores**")
                    render_score_panel(
                        scores.get("piotroski"),
                        scores.get("altman"),
                        use_gauges=True,
                    )

                st.divider()

                # AI Analysis section
                st.markdown("**AI Analysis (Optional)**")

                ai_col1, ai_col2 = st.columns(2)

                with ai_col1:
                    if st.button("Quick Analysis (Flash)", use_container_width=True):
                        with st.spinner("Analyzing with Gemini Flash..."):
                            try:
                                from dashboard.utils.ai_analysis import run_single_stock_analysis
                                st.session_state.research_ai_analysis = run_single_stock_analysis(
                                    selected_ticker, scores, model="flash"
                                )
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")

                with ai_col2:
                    if st.button("Deep Analysis (Pro)", use_container_width=True):
                        with st.spinner("Analyzing with Gemini Pro..."):
                            try:
                                from dashboard.utils.ai_analysis import run_single_stock_analysis
                                st.session_state.research_ai_analysis = run_single_stock_analysis(
                                    selected_ticker, scores, model="pro"
                                )
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")

                # Display AI analysis if available
                if st.session_state.research_ai_analysis:
                    ai_result = st.session_state.research_ai_analysis
                    if "error" not in ai_result:
                        render_ai_section(
                            content=ai_result.get("content", ""),
                            model=ai_result.get("model", "unknown"),
                            cost=ai_result.get("cost_usd"),
                            timestamp=ai_result.get("timestamp"),
                            content_type="research",
                            ticker=selected_ticker,
                        )

                st.divider()

                # Navigation
                nav_col1, nav_col2 = st.columns([3, 1])
                with nav_col2:
                    if st.button("Next: Create Thesis →", type="primary", use_container_width=True):
                        st.session_state.research_step = 1
                        st.rerun()
    else:
        st.info("Select or enter a stock ticker to begin research.")


def render_thesis_step() -> None:
    """Render Step 2: Thesis - create investment thesis."""
    st.subheader("Step 2: Create Thesis")

    ticker = st.session_state.research_ticker
    if not ticker:
        st.warning("No stock selected. Please go back to Step 1.")
        if st.button("← Back to Research"):
            st.session_state.research_step = 0
            st.rerun()
        return

    st.markdown(f"Creating thesis for **{ticker}**")

    # Pre-populate from AI analysis if available
    ai_summary = ""
    ai_bull = ""
    ai_bear = ""

    if st.session_state.research_ai_analysis:
        ai_content = st.session_state.research_ai_analysis.get("content", "")
        # Try to extract sections (simple heuristic)
        if ai_content:
            ai_summary = ai_content[:200] + "..." if len(ai_content) > 200 else ai_content

    # Thesis form
    draft = st.session_state.research_thesis_draft

    st.markdown("**Summary** (required)")
    summary = st.text_area(
        "Brief summary of your investment thesis",
        value=draft.get("summary", ai_summary),
        height=100,
        max_chars=500,
        label_visibility="collapsed",
        placeholder="e.g., Apple's ecosystem moat continues to expand with services growth...",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Bull Case**")
        bull_case = st.text_area(
            "Reasons to buy",
            value=draft.get("bull_case", ai_bull),
            height=150,
            label_visibility="collapsed",
            placeholder="• Strong free cash flow\n• Growing services revenue\n• Brand loyalty",
        )

    with col2:
        st.markdown("**Bear Case**")
        bear_case = st.text_area(
            "Risks and concerns",
            value=draft.get("bear_case", ai_bear),
            height=150,
            label_visibility="collapsed",
            placeholder="• iPhone revenue concentration\n• China geopolitical risk\n• Competition",
        )

    st.markdown("**Conviction Level**")
    conviction = st.slider(
        "How confident are you?",
        min_value=1,
        max_value=5,
        value=draft.get("conviction", 3),
        format="%d/5",
        help="1 = Very Low, 5 = Very High",
    )

    conviction_labels = {1: "Very Low", 2: "Low", 3: "Medium", 4: "High", 5: "Very High"}
    st.caption(f"Conviction: {conviction_labels[conviction]}")

    st.markdown("**Key Metrics to Monitor**")
    key_metrics = st.text_input(
        "Metrics to watch",
        value=draft.get("key_metrics", ""),
        placeholder="e.g., Services revenue growth, iPhone units, China revenue %",
        label_visibility="collapsed",
    )

    # Save draft
    st.session_state.research_thesis_draft = {
        "summary": summary,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "conviction": conviction,
        "key_metrics": key_metrics,
    }

    st.divider()

    # Navigation
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])

    with nav_col1:
        if st.button("← Back to Research", use_container_width=True):
            st.session_state.research_step = 0
            st.rerun()

    with nav_col2:
        if st.button("Save Draft", use_container_width=True):
            st.success("Draft saved!")

    with nav_col3:
        if st.button("Next: Decision →", type="primary", use_container_width=True, disabled=not summary):
            st.session_state.research_step = 2
            st.rerun()


def render_decision_step() -> None:
    """Render Step 3: Decision - record investment decision."""
    st.subheader("Step 3: Record Decision")

    ticker = st.session_state.research_ticker
    thesis_draft = st.session_state.research_thesis_draft

    if not ticker or not thesis_draft.get("summary"):
        st.warning("No thesis created. Please go back to Step 2.")
        if st.button("← Back to Thesis"):
            st.session_state.research_step = 1
            st.rerun()
        return

    # Show thesis summary
    st.markdown(f"**Thesis for {ticker}**")
    st.markdown(
        f"""
        <div style="background:#f8fafc;padding:12px;border-radius:8px;margin-bottom:16px">
            <div style="color:{COLORS['gray']};font-size:0.9rem">{thesis_draft.get('summary', '')}</div>
            <div style="margin-top:8px">
                <span style="color:{COLORS['green']}">Bull:</span> {thesis_draft.get('bull_case', 'N/A')[:50]}...
                <span style="margin-left:16px;color:{COLORS['red']}">Bear:</span> {thesis_draft.get('bear_case', 'N/A')[:50]}...
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Decision form
    st.markdown("**Your Decision**")

    col1, col2 = st.columns(2)

    with col1:
        action = st.selectbox(
            "Action",
            options=["buy", "hold", "sell", "pass"],
            format_func=lambda x: x.upper(),
        )

    with col2:
        confidence = st.slider(
            "Decision Confidence",
            min_value=1,
            max_value=5,
            value=thesis_draft.get("conviction", 3),
            format="%d/5",
        )

    # Price targets (optional)
    st.markdown("**Price Targets (Optional)**")
    target_col1, target_col2 = st.columns(2)

    with target_col1:
        target_price = st.number_input(
            "Target Price ($)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            format="%.2f",
        )

    with target_col2:
        stop_loss = st.number_input(
            "Stop Loss ($)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            format="%.2f",
        )

    st.markdown("**Rationale**")
    rationale = st.text_area(
        "Why this decision?",
        height=100,
        placeholder="e.g., Current valuation attractive given growth prospects...",
        label_visibility="collapsed",
    )

    st.divider()

    # Navigation and save
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])

    with nav_col1:
        if st.button("← Back to Thesis", use_container_width=True):
            st.session_state.research_step = 1
            st.rerun()

    with nav_col3:
        if st.button("Save & Complete", type="primary", use_container_width=True):
            # Save thesis and decision
            try:
                from dashboard.utils.decisions import create_thesis, create_decision

                # Create thesis first
                thesis_id = create_thesis(
                    ticker=ticker,
                    summary=thesis_draft.get("summary", ""),
                    bull_case=thesis_draft.get("bull_case"),
                    bear_case=thesis_draft.get("bear_case"),
                    conviction=thesis_draft.get("conviction"),
                    key_metrics=thesis_draft.get("key_metrics"),
                    ai_model=st.session_state.research_ai_analysis.get("model") if st.session_state.research_ai_analysis else None,
                    ai_cost=st.session_state.research_ai_analysis.get("cost_usd") if st.session_state.research_ai_analysis else None,
                )

                # Create decision linked to thesis
                decision_id = create_decision(
                    thesis_id=thesis_id,
                    action=action,
                    confidence=confidence,
                    rationale=rationale,
                    target_price=target_price if target_price > 0 else None,
                    stop_loss=stop_loss if stop_loss > 0 else None,
                )

                # Add to watchlist if not already there
                add_stock(ticker, f"Thesis created: {thesis_draft.get('summary', '')[:50]}...")

                st.success(f"Thesis and decision saved for {ticker}!")
                st.balloons()

                # Reset wizard
                st.session_state.research_step = 0
                st.session_state.research_ticker = None
                st.session_state.research_scores = None
                st.session_state.research_ai_analysis = None
                st.session_state.research_thesis_draft = {}

                st.info("View your thesis in the Decisions page.")

            except ImportError:
                st.error("Decision utilities not available. Please check your installation.")
            except Exception as e:
                st.error(f"Failed to save: {e}")


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
if st.button("Reset Wizard", type="secondary"):
    st.session_state.research_step = 0
    st.session_state.research_ticker = None
    st.session_state.research_scores = None
    st.session_state.research_ai_analysis = None
    st.session_state.research_thesis_draft = {}
    st.rerun()
