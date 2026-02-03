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
from dashboard.theme import get_semantic_color, get_plotly_theme
from dashboard.utils.formatters import format_date_friendly
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.scoring import get_scores_for_ticker
from dashboard.utils.validators import sanitize_html
from dashboard.utils.watchlist import get_cached_scores, get_stocks, add_stock

st.set_page_config(page_title="Research | Asymmetric", layout="wide")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

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
    from dashboard.theme import get_color

    steps = ["1. Research", "2. Thesis", "3. Decision"]

    green = get_semantic_color('green')
    blue = get_semantic_color('blue')
    gray = get_semantic_color('gray')
    text_on_accent = get_color('text_on_accent')
    bg_subtle = get_color('bg_tertiary')

    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if i < current_step:
                # Completed step
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:8px;background:{green};
                                color:{text_on_accent};border-radius:8px;font-weight:600">
                        ✓ {step}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif i == current_step:
                # Current step
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:8px;background:{blue};
                                color:{text_on_accent};border-radius:8px;font-weight:600">
                        ● {step}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                # Future step
                st.markdown(
                    f"""
                    <div style="text-align:center;padding:8px;background:{bg_subtle};
                                color:{gray};border-radius:8px">
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
        # Validate ticker format
        if not selected_ticker.isalnum() or len(selected_ticker) > 5:
            st.error("Invalid ticker format. Ticker must be 1-5 alphanumeric characters (e.g., AAPL, MSFT).")
            return

        st.session_state.research_ticker = selected_ticker

        # Fetch scores button
        if st.button("Analyze Stock", type="primary"):
            with st.spinner(f"Fetching data for {selected_ticker}..."):
                try:
                    # Try cached first
                    cached = get_cached_scores(selected_ticker)
                    if cached and "piotroski" in cached:
                        st.session_state.research_scores = cached
                    else:
                        st.session_state.research_scores = get_scores_for_ticker(selected_ticker)
                except Exception as e:
                    st.error(f"Failed to fetch data for {selected_ticker}: {str(e)}")
                    st.session_state.research_scores = {"error": True, "message": str(e)}

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
                                from dashboard.utils.ai_analysis import (
                                    run_single_stock_analysis,
                                    handle_ai_analysis_error,
                                )
                                st.session_state.research_ai_analysis = run_single_stock_analysis(
                                    selected_ticker, scores, model="flash"
                                )
                            except ImportError:
                                st.error("❌ AI analysis not available. Please check your Gemini API key configuration.")
                            except Exception as e:
                                handle_ai_analysis_error(e)

                with ai_col2:
                    if st.button("Deep Analysis (Pro)", use_container_width=True):
                        with st.spinner("Analyzing with Gemini Pro..."):
                            try:
                                from dashboard.utils.ai_analysis import (
                                    run_single_stock_analysis,
                                    handle_ai_analysis_error,
                                )
                                st.session_state.research_ai_analysis = run_single_stock_analysis(
                                    selected_ticker, scores, model="pro"
                                )
                            except ImportError:
                                st.error("❌ AI analysis not available. Please check your Gemini API key configuration.")
                            except Exception as e:
                                handle_ai_analysis_error(e)

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
        # Validation: Require summary with minimum length
        can_proceed = summary and len(summary.strip()) >= 20
        button_disabled = not can_proceed

        if st.button("Next: Decision →", type="primary", use_container_width=True, disabled=button_disabled):
            st.session_state.research_step = 2
            st.rerun()

        if not can_proceed and summary:
            st.caption("⚠️ Summary must be at least 20 characters")


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
    from dashboard.theme import get_color

    gray = get_semantic_color('gray')
    green = get_semantic_color('green')
    red = get_semantic_color('red')
    bg_card = get_color('bg_secondary')

    st.markdown(f"**Thesis for {ticker}**")
    # Escape user-provided content to prevent XSS
    summary_safe = sanitize_html(thesis_draft.get('summary', ''))
    bull_safe = sanitize_html(thesis_draft.get('bull_case', 'N/A')[:50])
    bear_safe = sanitize_html(thesis_draft.get('bear_case', 'N/A')[:50])
    st.markdown(
        f"""
        <div style="background:{bg_card};padding:12px;border-radius:8px;margin-bottom:16px">
            <div style="color:{gray};font-size:0.9rem">{summary_safe}</div>
            <div style="margin-top:8px">
                <span style="color:{green}">Bull:</span> {bull_safe}...
                <span style="margin-left:16px;color:{red}">Bear:</span> {bear_safe}...
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

    # Fetch decisions
    all_decisions = get_decisions(limit=100)
    pending_decisions = [d for d in all_decisions if not d.get("actual_outcome")]
    completed_decisions = get_decisions_with_outcomes(limit=50)

    # Section toggle
    view_mode = st.radio(
        "View",
        options=["Pending Review", "Completed Reviews"],
        horizontal=True,
    )

    if view_mode == "Pending Review":
        if not pending_decisions:
            st.info("✅ No decisions pending outcome review. All your decisions have been reviewed!")
            return

        st.markdown(f"**{len(pending_decisions)} decision(s) awaiting outcome review**")

        # Display pending decisions in expandable cards
        for decision in pending_decisions:
            ticker = decision.get("ticker", "N/A")
            action = decision.get("action", "N/A").upper()
            confidence = decision.get("confidence", 3)
            decided_at = decision.get("decided_at", "N/A")

            # Parse date for display
            date_str = format_date_friendly(decided_at)

            with st.expander(f"📊 {ticker} - {action} ({date_str}) - Conviction: {confidence}/5"):
                # Fetch full decision details including thesis
                full_decision = get_decision_by_id(decision["id"])

                # Before/After Comparison Section
                st.markdown("### Original Thesis vs. Outcome")

                comp_col1, comp_col2 = st.columns(2)

                with comp_col1:
                    st.markdown("#### 📋 Original Thesis")
                    st.markdown(f"**Summary**: {full_decision.get('thesis_summary', 'N/A')[:200]}...")
                    st.markdown(f"**Action**: {action}")
                    st.markdown(f"**Conviction**: {confidence}/5")
                    if decision.get('target_price'):
                        st.markdown(f"**Target Price**: ${decision['target_price']:.2f}")
                    st.markdown(f"**Date**: {date_str}")
                    st.markdown(f"**Rationale**: {decision.get('rationale', 'N/A')[:150]}...")

                with comp_col2:
                    st.markdown("#### 📊 Record Actual Outcome")
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

                    # Calculate return if both prices exist
                    if actual_price > 0 and decision.get('target_price', 0) > 0:
                        pct_return = ((actual_price - decision['target_price']) / decision['target_price']) * 100
                        color = get_semantic_color('green') if pct_return > 0 else get_semantic_color('red')
                        st.markdown(
                            f"<div style='color:{color};font-weight:600'>Return vs. Target: {pct_return:+.2f}%</div>",
                            unsafe_allow_html=True,
                        )

                    hit = st.checkbox(
                        "✓ Thesis proved correct",
                        help="Check if your original thesis was validated",
                        key=f"hit_{decision['id']}",
                    )

                st.divider()

                # Lessons learned (full width)
                lessons = st.text_area(
                    "📝 Lessons Learned",
                    placeholder="What did you learn from this decision? What would you do differently next time?",
                    height=100,
                    key=f"lessons_{decision['id']}",
                )

                # Save button
                if st.button("💾 Save Outcome", key=f"save_{decision['id']}", type="primary", use_container_width=True):
                    success = update_decision_outcome(
                        decision_id=decision["id"],
                        actual_outcome=outcome,
                        actual_price=actual_price if actual_price > 0 else None,
                        lessons_learned=lessons if lessons else None,
                        hit=hit,
                    )
                    if success:
                        st.success(f"✅ Outcome recorded for {ticker}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to save outcome. Please try again.")

    else:  # view_mode == "Completed Reviews"
        if not completed_decisions:
            st.info("No completed reviews yet. Record outcomes in 'Pending Review' to see them here.")
            return

        st.markdown(f"**{len(completed_decisions)} decision(s) with recorded outcomes**")

        # Display completed decisions with before/after comparison
        for decision in completed_decisions:
            ticker = decision.get("ticker", "N/A")
            action = decision.get("action", "N/A").upper()
            confidence = decision.get("confidence", 3)
            actual_outcome = decision.get("actual_outcome", "unknown").capitalize()
            hit = decision.get("hit")

            # Date formatting
            decided_at = decision.get("decided_at", "N/A")
            outcome_date = decision.get("outcome_date", "N/A")

            decided_str = format_date_friendly(decided_at, default="Unknown")
            outcome_str = format_date_friendly(outcome_date, default="Unknown")

            # Color code based on hit
            if hit is True:
                badge_color = get_semantic_color('green')
                badge_text = "✓ Hit"
            elif hit is False:
                badge_color = get_semantic_color('red')
                badge_text = "✗ Miss"
            else:
                badge_color = get_semantic_color('gray')
                badge_text = "? Unknown"

            with st.expander(f"📊 {ticker} - {action} - {actual_outcome} ({outcome_str})"):
                # Before/After Comparison
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### 📋 Original Thesis")
                    st.markdown(f"**Action**: {action}")
                    st.markdown(f"**Conviction**: {confidence}/5")
                    if decision.get('target_price'):
                        st.markdown(f"**Target Price**: ${decision['target_price']:.2f}")
                    st.markdown(f"**Date Decided**: {decided_str}")
                    st.markdown(f"**Rationale**: {decision.get('rationale', 'N/A')[:150]}...")
                    if decision.get('thesis_summary'):
                        st.markdown(f"**Thesis**: {decision['thesis_summary'][:150]}...")

                with col2:
                    st.markdown("#### 📊 Actual Outcome")
                    from dashboard.theme import get_color
                    text_on_accent = get_color('text_on_accent')
                    st.markdown(
                        f"<div style='background:{badge_color};color:{text_on_accent};padding:4px 12px;"
                        f"border-radius:4px;display:inline-block;font-weight:600'>{badge_text}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Outcome**: {actual_outcome}")
                    if decision.get('actual_price'):
                        st.markdown(f"**Actual Price**: ${decision['actual_price']:.2f}")

                        # Calculate return if both prices exist
                        if decision.get('target_price', 0) > 0:
                            pct_return = ((decision['actual_price'] - decision['target_price']) / decision['target_price']) * 100
                            return_color = get_semantic_color('green') if pct_return > 0 else get_semantic_color('red')
                            st.markdown(
                                f"<div style='color:{return_color};font-weight:600;font-size:1.2rem'>"
                                f"Return: {pct_return:+.2f}%</div>",
                                unsafe_allow_html=True,
                            )

                    st.markdown(f"**Reviewed On**: {outcome_str}")

                # Lessons learned (full width)
                if decision.get('lessons_learned'):
                    st.divider()
                    st.markdown("#### 📝 Lessons Learned")
                    st.markdown(decision['lessons_learned'])


def render_analytics_tab() -> None:
    """Render the Analytics tab with hit rate visualization."""
    st.subheader("Decision Analytics")
    st.caption("Analyze your prediction accuracy by conviction level")

    from dashboard.utils.decisions import (
        get_decisions_with_outcomes,
        analyze_by_conviction,
        calculate_portfolio_return,
    )

    # Fetch decisions with outcomes
    decisions_with_outcomes = get_decisions_with_outcomes(limit=100)

    if not decisions_with_outcomes:
        st.info("No outcome data yet. Record outcomes in the 'Review Outcomes' tab to see analytics.")
        return

    # Analyze by conviction
    conviction_stats = analyze_by_conviction(decisions_with_outcomes)

    st.markdown(f"### Hit Rate by Conviction Level")
    st.caption(f"Based on {len(decisions_with_outcomes)} decision(s) with recorded outcomes")

    # Create bar chart
    import plotly.graph_objects as go

    green = get_semantic_color('green')
    yellow = get_semantic_color('yellow')
    red = get_semantic_color('red')

    fig = go.Figure(data=[
        go.Bar(
            x=[f"Level {s['conviction_level']}" for s in conviction_stats],
            y=[s['hit_rate_pct'] for s in conviction_stats],
            text=[f"{s['hit_rate_pct']:.1f}%" for s in conviction_stats],
            textposition='auto',
            marker_color=[
                green if s['hit_rate_pct'] >= 60 else
                yellow if s['hit_rate_pct'] >= 40 else
                red
                for s in conviction_stats
            ],
        )
    ])

    fig.update_layout(
        xaxis_title="Conviction Level",
        yaxis_title="Hit Rate (%)",
        yaxis_range=[0, 100],
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        **get_plotly_theme()
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show stats table
    st.markdown("### Detailed Statistics")

    import pandas as pd
    df = pd.DataFrame(conviction_stats)
    df.columns = ["Conviction", "Hits", "Total", "Hit Rate (%)"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # What-If Calculator
    st.markdown("### What-If Analysis")
    st.caption("See how returns vary by conviction threshold")

    min_conviction = st.slider(
        "Minimum Conviction Level",
        min_value=1,
        max_value=5,
        value=3,
        help="Only include decisions with conviction ≥ this level",
    )

    avg_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=min_conviction)
    filtered_count = sum(1 for d in decisions_with_outcomes if (d.get('confidence') or 3) >= min_conviction)

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Avg Return",
            f"{avg_return:+.2f}%",
            delta=None,
        )
    with col2:
        st.metric(
            "Decisions Included",
            filtered_count,
        )

    if min_conviction > 1:
        all_return = calculate_portfolio_return(decisions_with_outcomes, conviction_min=1)
        improvement = avg_return - all_return
        if improvement > 0:
            st.success(f"✅ High-conviction filter improved returns by {improvement:+.2f}%")
        elif improvement < 0:
            st.warning(f"⚠️ High-conviction filter reduced returns by {improvement:.2f}%")
        else:
            st.info("No difference in returns")


# Tab selection
tab1, tab2, tab3 = st.tabs(["📝 New Research", "📊 Review Outcomes", "📈 Analytics"])

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

    # Only show confirmation if there's data to lose
    has_data = (
        st.session_state.research_ticker or
        st.session_state.research_scores or
        st.session_state.research_ai_analysis or
        st.session_state.research_thesis_draft
    )

    if has_data:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Reset Wizard", type="secondary", use_container_width=True):
                # Initialize reset confirmation state
                if "confirm_reset" not in st.session_state:
                    st.session_state.confirm_reset = False
                st.session_state.confirm_reset = True
                st.rerun()

        # Show confirmation dialog if reset was clicked
        if st.session_state.get("confirm_reset", False):
            st.warning("⚠️ This will clear all unsaved research data. Are you sure?")
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
