"""Decision and thesis display components.

Provides reusable UI rendering functions for decisions and theses,
following the same patterns as score_display.py and comparison.py.
"""

from datetime import datetime
from typing import Any, Optional

import streamlit as st

from dashboard.components import icons
from dashboard.config import CONFIDENCE_LEVELS, DECISION_ACTIONS, THESIS_STATUS


def render_action_badge(action: str) -> str:
    """
    Return styled badge string for decision action.

    Args:
        action: Decision action (buy/hold/sell/pass).

    Returns:
        HTML string with colored badge.
    """
    return icons.action_badge(action, size="normal")


def render_status_badge(status: str) -> str:
    """
    Return styled badge string for thesis status.

    Args:
        status: Thesis status (draft/active/archived).

    Returns:
        HTML string with colored badge.
    """
    return icons.thesis_status_badge(status, size="normal")


def render_confidence_indicator(confidence: Optional[int]) -> str:
    """
    Render confidence as star rating.

    Args:
        confidence: Confidence level 1-5 or None.

    Returns:
        HTML star rating string with label.
    """
    if confidence is None:
        return "N/A"
    config = CONFIDENCE_LEVELS.get(confidence, CONFIDENCE_LEVELS[3])
    stars = icons.stars_rating(config["rating"])
    return f"{stars} ({config['label']})"


def _format_date(iso_date: Optional[str]) -> str:
    """Format ISO date string for display."""
    if not iso_date:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return "N/A"


def _format_short_date(iso_date: Optional[str]) -> str:
    """Format ISO date string as short date."""
    if not iso_date:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return "N/A"


def render_decision_card(
    decision: dict[str, Any],
    expanded: bool = False,
    show_view_button: bool = True,
) -> None:
    """
    Render a decision as an expandable card.

    Args:
        decision: Decision dict from get_decisions().
        expanded: Whether to expand by default.
        show_view_button: Whether to show view details button.
    """
    ticker = decision.get("ticker", "?")
    action = decision.get("action", "pass")
    confidence = decision.get("confidence")
    decided_at = decision.get("decided_at", "")

    # Format expander label (plain text for expander title)
    date_str = _format_short_date(decided_at)
    action_label = DECISION_ACTIONS.get(action, DECISION_ACTIONS["pass"])["label"]
    label = f"**{ticker}** | {action_label} | {date_str}"

    with st.expander(label, expanded=expanded):
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown(
                f"**Confidence:** {render_confidence_indicator(confidence)}",
                unsafe_allow_html=True,
            )

            # Price targets
            if decision.get("target_price"):
                st.caption(f"Target: ${decision['target_price']:.2f}")
            if decision.get("stop_loss"):
                st.caption(f"Stop Loss: ${decision['stop_loss']:.2f}")

        with col2:
            thesis_id = decision.get("thesis_id")
            if thesis_id:
                st.caption(f"Thesis #{thesis_id}")
            thesis_summary = decision.get("thesis_summary", "")
            if thesis_summary:
                st.caption(thesis_summary[:80] + "..." if len(thesis_summary) > 80 else thesis_summary)

        # Rationale
        rationale = decision.get("rationale", "")
        if rationale:
            st.divider()
            st.markdown("**Rationale:**")
            st.write(rationale)

        # View button
        if show_view_button:
            if st.button("View Full Details", key=f"view_decision_{decision['id']}"):
                st.session_state.selected_decision_id = decision["id"]
                st.rerun()


def render_thesis_card(
    thesis: dict[str, Any],
    expanded: bool = False,
    show_view_button: bool = True,
) -> None:
    """
    Render a thesis as an expandable card.

    Args:
        thesis: Thesis dict from get_theses().
        expanded: Whether to expand by default.
        show_view_button: Whether to show view details button.
    """
    ticker = thesis.get("ticker", "?")
    status = thesis.get("status", "draft")
    ai_generated = thesis.get("ai_generated", False)
    decision_count = thesis.get("decision_count", 0)

    # Format expander label (plain text for expander title)
    status_label = THESIS_STATUS.get(status, THESIS_STATUS["draft"])["label"]
    ai_marker = " (AI)" if ai_generated else ""
    label = f"**{ticker}** | {status_label}{ai_marker} | {decision_count} decision(s)"

    with st.expander(label, expanded=expanded):
        # Summary
        st.markdown(thesis.get("summary", "No summary"))

        col1, col2 = st.columns([3, 2])

        with col1:
            if ai_generated:
                st.caption(f"Generated by: {thesis.get('ai_model', 'unknown')}")
                if thesis.get("ai_cost_usd"):
                    st.caption(f"Cost: ${thesis['ai_cost_usd']:.4f}")

            created = thesis.get("created_at")
            if created:
                st.caption(f"Created: {_format_short_date(created)}")

        with col2:
            st.metric("Decisions", decision_count)

        # View button
        if show_view_button:
            if st.button("View Full Thesis", key=f"view_thesis_{thesis['id']}"):
                st.session_state.selected_thesis_id = thesis["id"]
                st.rerun()


def render_thesis_detail(thesis: dict[str, Any]) -> None:
    """
    Render full thesis details.

    Args:
        thesis: Full thesis dict from get_thesis_by_id().
    """
    st.subheader(f"{thesis.get('ticker', '?')} - {thesis.get('company_name', 'Unknown')}")

    # Status and metadata row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"**Status:** {render_status_badge(thesis.get('status', 'draft'))}",
            unsafe_allow_html=True,
        )
    with col2:
        if thesis.get("ai_generated"):
            st.markdown(f"**AI Model:** {thesis.get('ai_model', 'unknown')}")
        else:
            st.markdown("**Source:** Manual")
    with col3:
        st.markdown(f"**Decisions:** {thesis.get('decision_count', 0)}")

    st.divider()

    # Summary
    st.markdown("### Summary")
    st.write(thesis.get("summary", "No summary"))

    # Bull/Bear cases
    if thesis.get("bull_case") or thesis.get("bear_case"):
        st.divider()
        render_bull_bear_columns(thesis.get("bull_case"), thesis.get("bear_case"))

    # Full analysis
    if thesis.get("analysis_text"):
        st.divider()
        st.markdown("### Full Analysis")
        st.write(thesis.get("analysis_text", ""))

    # Key metrics
    if thesis.get("key_metrics"):
        st.divider()
        st.markdown("### Key Metrics to Monitor")
        st.write(thesis.get("key_metrics", ""))

    # AI metadata
    if thesis.get("ai_generated"):
        st.divider()
        st.caption("**AI Generation Details:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"Input tokens: {thesis.get('ai_tokens_input', 'N/A')}")
        with col2:
            st.caption(f"Output tokens: {thesis.get('ai_tokens_output', 'N/A')}")
        with col3:
            cost = thesis.get("ai_cost_usd")
            st.caption(f"Cost: ${cost:.4f}" if cost else "Cost: N/A")
            cached = thesis.get("cached", False)
            st.caption(f"Cached: {'Yes' if cached else 'No'}")

    # Related decisions
    decisions = thesis.get("decisions", [])
    if decisions:
        st.divider()
        st.markdown("### Related Decisions")
        for d in decisions:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.markdown(
                    render_action_badge(d.get("action", "pass")),
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    render_confidence_indicator(d.get("confidence")),
                    unsafe_allow_html=True,
                )
            with col3:
                st.caption(_format_short_date(d.get("decided_at")))


def render_decision_detail(decision: dict[str, Any]) -> None:
    """
    Render full decision details.

    Args:
        decision: Full decision dict from get_decision_by_id().
    """
    st.subheader(f"{decision.get('ticker', '?')} - {decision.get('company_name', 'Unknown')}")

    # Action and confidence row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"**Action:** {render_action_badge(decision.get('action', 'pass'))}",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"**Confidence:** {render_confidence_indicator(decision.get('confidence'))}",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(f"**Date:** {_format_date(decision.get('decided_at'))}")

    st.divider()

    # Price targets
    target = decision.get("target_price")
    stop = decision.get("stop_loss")
    if target or stop:
        col1, col2 = st.columns(2)
        with col1:
            if target:
                st.metric("Target Price", f"${target:.2f}")
        with col2:
            if stop:
                st.metric("Stop Loss", f"${stop:.2f}")
        st.divider()

    # Rationale
    st.markdown("### Rationale")
    st.write(decision.get("rationale", "No rationale provided"))

    # Linked thesis
    thesis_id = decision.get("thesis_id")
    if thesis_id:
        st.divider()
        st.markdown(f"### Linked Thesis (#{thesis_id})")
        st.markdown(
            f"**Status:** {render_status_badge(decision.get('thesis_status', 'draft'))}",
            unsafe_allow_html=True,
        )
        st.write(decision.get("thesis_summary", "No summary"))


def render_bull_bear_columns(
    bull_case: Optional[str],
    bear_case: Optional[str],
) -> None:
    """
    Render bull and bear cases side by side.

    Args:
        bull_case: Bull case text.
        bear_case: Bear case text.
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Bull Case")
        st.write(bull_case or "*Not specified*")

    with col2:
        st.markdown("### Bear Case")
        st.write(bear_case or "*Not specified*")


def render_decision_form(
    ticker: Optional[str] = None,
    thesis_id: Optional[int] = None,
    available_theses: Optional[list[dict]] = None,
) -> Optional[dict[str, Any]]:
    """
    Render decision creation form.

    Args:
        ticker: Pre-filled ticker.
        thesis_id: Pre-selected thesis ID.
        available_theses: List of available theses for selection.

    Returns:
        Form data dict if submitted successfully, None otherwise.
    """
    with st.form("decision_form", clear_on_submit=True):
        st.subheader("Record New Decision")

        col1, col2 = st.columns(2)

        with col1:
            form_ticker = st.text_input(
                "Ticker *",
                value=ticker or "",
                placeholder="AAPL",
                max_chars=10,
            ).upper().strip()

            action = st.selectbox(
                "Action *",
                options=["buy", "hold", "sell", "pass"],
                format_func=lambda x: DECISION_ACTIONS[x]["label"],
            )

            confidence = st.slider(
                "Confidence",
                min_value=1,
                max_value=5,
                value=3,
                help="1=Very Low, 5=Very High",
            )

        with col2:
            # Thesis selection
            if available_theses:
                thesis_options = [("", "-- Create new thesis --")] + [
                    (str(t["id"]), f"#{t['id']}: {t['summary'][:40]}...")
                    for t in available_theses
                ]
                selected_thesis = st.selectbox(
                    "Link to Thesis",
                    options=[opt[0] for opt in thesis_options],
                    format_func=lambda x: next(
                        (opt[1] for opt in thesis_options if opt[0] == x), ""
                    ),
                )
            else:
                selected_thesis = ""
                st.caption("A default thesis will be created")

            target_price = st.number_input(
                "Target Price ($)",
                min_value=0.01,
                value=None,
                step=1.0,
                format="%.2f",
            )

            stop_loss = st.number_input(
                "Stop Loss ($)",
                min_value=0.01,
                value=None,
                step=1.0,
                format="%.2f",
            )

        rationale = st.text_area(
            "Rationale",
            placeholder="Why are you making this decision?",
            max_chars=1000,
        )

        submitted = st.form_submit_button("Record Decision", type="primary")

        if submitted:
            if not form_ticker:
                st.error("Please enter a ticker symbol")
                return None

            return {
                "ticker": form_ticker,
                "action": action,
                "confidence": confidence,
                "thesis_id": int(selected_thesis) if selected_thesis else thesis_id,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "rationale": rationale,
            }

    return None


def render_thesis_edit_form(
    thesis: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Render thesis edit form with pre-filled values.

    Args:
        thesis: Current thesis data from get_thesis_by_id().

    Returns:
        Form data dict if submitted successfully, None otherwise.
    """
    with st.form("thesis_edit_form", clear_on_submit=False):
        st.subheader(f"Edit Thesis: {thesis.get('ticker', '?')}")

        col1, col2 = st.columns(2)

        with col1:
            status = st.selectbox(
                "Status",
                options=["draft", "active", "archived"],
                format_func=lambda x: THESIS_STATUS[x]["label"],
                index=["draft", "active", "archived"].index(thesis.get("status", "draft")),
            )

        with col2:
            if thesis.get("ai_generated"):
                st.caption(f"AI-generated by {thesis.get('ai_model', 'unknown')}")

        summary = st.text_area(
            "Summary *",
            value=thesis.get("summary", ""),
            max_chars=500,
        )

        analysis_text = st.text_area(
            "Full Analysis",
            value=thesis.get("analysis_text", ""),
            height=150,
        )

        col1, col2 = st.columns(2)

        with col1:
            bull_case = st.text_area(
                "Bull Case",
                value=thesis.get("bull_case") or "",
                height=100,
            )

        with col2:
            bear_case = st.text_area(
                "Bear Case",
                value=thesis.get("bear_case") or "",
                height=100,
            )

        key_metrics = st.text_input(
            "Key Metrics to Monitor",
            value=thesis.get("key_metrics") or "",
        )

        submitted = st.form_submit_button("Save Changes", type="primary")

        if submitted:
            if not summary:
                st.error("Please enter a summary")
                return None

            return {
                "thesis_id": thesis["id"],
                "summary": summary,
                "analysis_text": analysis_text,
                "bull_case": bull_case or None,
                "bear_case": bear_case or None,
                "key_metrics": key_metrics or None,
                "status": status,
            }

    return None


def render_thesis_form(
    ticker: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Render thesis creation form.

    Args:
        ticker: Pre-filled ticker.

    Returns:
        Form data dict if submitted successfully, None otherwise.
    """
    with st.form("thesis_form", clear_on_submit=True):
        st.subheader("Create New Thesis")

        col1, col2 = st.columns(2)

        with col1:
            form_ticker = st.text_input(
                "Ticker *",
                value=ticker or "",
                placeholder="AAPL",
                max_chars=10,
            ).upper().strip()

            status = st.selectbox(
                "Status",
                options=["draft", "active", "archived"],
                format_func=lambda x: THESIS_STATUS[x]["label"],
            )

        with col2:
            st.caption("Use Compare page for AI-generated theses")

        summary = st.text_area(
            "Summary *",
            placeholder="Brief investment thesis (1-2 sentences)",
            max_chars=500,
        )

        analysis_text = st.text_area(
            "Full Analysis",
            placeholder="Detailed investment analysis...",
            height=150,
        )

        col1, col2 = st.columns(2)

        with col1:
            bull_case = st.text_area(
                "Bull Case",
                placeholder="Key reasons this investment could succeed...",
                height=100,
            )

        with col2:
            bear_case = st.text_area(
                "Bear Case",
                placeholder="Key risks and concerns...",
                height=100,
            )

        key_metrics = st.text_input(
            "Key Metrics to Monitor",
            placeholder="Revenue growth, FCF margin, etc.",
        )

        submitted = st.form_submit_button("Create Thesis", type="primary")

        if submitted:
            if not form_ticker:
                st.error("Please enter a ticker symbol")
                return None
            if not summary:
                st.error("Please enter a summary")
                return None

            return {
                "ticker": form_ticker,
                "summary": summary,
                "analysis_text": analysis_text,
                "bull_case": bull_case or None,
                "bear_case": bear_case or None,
                "key_metrics": key_metrics or None,
                "status": status,
            }

    return None
