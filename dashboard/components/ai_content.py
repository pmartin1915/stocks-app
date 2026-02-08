"""AI content display component with functional feedback.

Provides clear visual distinction for AI-generated content while
maintaining equal visual weight with human-authored content.
"""

import hashlib
from datetime import datetime
from typing import Optional

import streamlit as st

from dashboard.components import icons
from dashboard.theme import get_color, get_semantic_color


def render_ai_section(
    content: str,
    model: str,
    cost: Optional[float] = None,
    timestamp: Optional[str] = None,
    content_type: str = "analysis",
    ticker: Optional[str] = None,
    on_feedback: Optional[callable] = None,
) -> None:
    """Render AI-generated content with clear attribution and feedback.

    Args:
        content: The AI-generated text content.
        model: Model name used (e.g., "gemini-2.5-flash", "pro").
        cost: Estimated cost in dollars.
        timestamp: ISO timestamp when content was generated.
        content_type: Type of content for feedback tracking.
        ticker: Stock ticker for context.
        on_feedback: Optional callback for feedback (helpful: bool, text: str).
    """
    # Generate content hash for feedback tracking
    content_hash = _generate_content_hash(content, model, ticker or "")

    # Header with model badge and cost
    model_display = _format_model_name(model)
    text_on_accent = get_color("text_on_accent")
    blue = get_semantic_color("blue")
    gray = get_semantic_color("gray")
    model_badge = icons.badge(model_display, blue, text_on_accent, "small")

    header_parts = [
        '<span style="font-weight:600">AI Analysis</span>',
        model_badge,
    ]

    if cost is not None:
        cost_badge = icons.badge(f"${cost:.3f}", gray, text_on_accent, "small")
        header_parts.append(cost_badge)

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">
            {" ".join(header_parts)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Timestamp
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%b %d, %Y %H:%M")
        except (ValueError, AttributeError):
            formatted_time = timestamp
        text_secondary = get_color("text_secondary")
        st.markdown(
            f'<div style="font-size:0.8rem;color:{text_secondary};margin-bottom:8px">Generated: {formatted_time}</div>',
            unsafe_allow_html=True,
        )

    # Content with styled container
    bg_tertiary = get_color("bg_tertiary")
    st.markdown(
        f"""
        <div style="background:{bg_tertiary};border-left:3px solid {blue};
                    padding:12px 16px;margin:8px 0;border-radius:0 4px 4px 0;
                    font-size:0.95rem;line-height:1.6">
            {_format_content(content)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feedback buttons
    _render_feedback_buttons(content_hash, content_type, ticker, model, on_feedback)

    # Regulatory disclosure (FINRA Rule 2210, EU AI Act compliance)
    with st.expander("ℹ️ AI Limitations & Disclaimer"):
        st.caption("""
**Important Disclosures:**

This analysis was generated using artificial intelligence (Gemini 2.5) and is provided
for informational purposes only. It is not investment advice.

**Limitations:**
- AI analysis is based on historical financial data and may not reflect recent market events
- Generated content may not include information after the model's knowledge cutoff
- AI cannot predict future market conditions or guarantee investment outcomes
- You should verify all information independently before making investment decisions

**Data Sources:** SEC EDGAR filings (10-K, 10-Q), Yahoo Finance market data

**Regulatory Note:** This content is subject to the same standards as human-authored
communications under FINRA Rule 2210. The use of AI to generate this content has been
disclosed per EU AI Act requirements (effective August 2026).
        """)


def render_ai_inline_badge(model: str, is_ai: bool = True) -> str:
    """Return inline badge HTML for AI attribution.

    Args:
        model: Model name used.
        is_ai: Whether content is AI-generated.

    Returns:
        HTML string for inline badge.
    """
    if not is_ai:
        return ""

    model_display = _format_model_name(model)
    text_on_accent = get_color("text_on_accent")
    blue = get_semantic_color("blue")
    return icons.badge(f"AI: {model_display}", blue, text_on_accent, "small")


def render_human_section(
    content: str,
    author: str = "You",
    timestamp: Optional[str] = None,
) -> None:
    """Render human-authored content section.

    Args:
        content: The human-authored text content.
        author: Author name.
        timestamp: ISO timestamp when content was written.
    """
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <span style="font-weight:600">{author}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%b %d, %Y %H:%M")
        except (ValueError, AttributeError):
            formatted_time = timestamp
        text_secondary = get_color("text_secondary")
        st.markdown(
            f'<div style="font-size:0.8rem;color:{text_secondary};margin-bottom:8px">{formatted_time}</div>',
            unsafe_allow_html=True,
        )

    # Content with subtle styling (no colored border to distinguish from AI)
    bg_secondary = get_color("bg_secondary")
    border_color = get_color("border")
    st.markdown(
        f"""
        <div style="background:{bg_secondary};border:1px solid {border_color};
                    padding:12px 16px;margin:8px 0;border-radius:4px;
                    font-size:0.95rem;line-height:1.6">
            {_format_content(content)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_feedback_buttons(
    content_hash: str,
    content_type: str,
    ticker: Optional[str],
    model: str,
    on_feedback: Optional[callable],
) -> None:
    """Render feedback buttons with state tracking.

    Args:
        content_hash: Unique hash for this content.
        content_type: Type of content.
        ticker: Stock ticker.
        model: Model name.
        on_feedback: Callback function.
    """
    # Initialize session state for feedback tracking
    feedback_key = f"ai_feedback_{content_hash}"
    if feedback_key not in st.session_state:
        st.session_state[feedback_key] = None

    current_feedback = st.session_state[feedback_key]

    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 1.5])

    with col1:
        helpful_style = (
            "primary" if current_feedback == "helpful" else "secondary"
        )
        if st.button(
            "👍 Helpful",
            key=f"helpful_{content_hash}",
            type=helpful_style,
            use_container_width=True,
        ):
            st.session_state[feedback_key] = "helpful"
            _record_feedback(content_hash, True, content_type, ticker, model, on_feedback)

    with col2:
        not_helpful_style = (
            "primary" if current_feedback == "not_helpful" else "secondary"
        )
        if st.button(
            "👎 Not helpful",
            key=f"not_helpful_{content_hash}",
            type=not_helpful_style,
            use_container_width=True,
        ):
            st.session_state[feedback_key] = "not_helpful"
            _record_feedback(content_hash, False, content_type, ticker, model, on_feedback)

    # Show feedback confirmation
    if current_feedback:
        with col4:
            green = get_semantic_color("green")
            gray = get_semantic_color("gray")
            if current_feedback == "helpful":
                st.markdown(
                    f'<span style="color:{green};font-size:0.85rem">✓ Thanks for feedback!</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span style="color:{gray};font-size:0.85rem">✓ Feedback recorded</span>',
                    unsafe_allow_html=True,
                )


def _record_feedback(
    content_hash: str,
    helpful: bool,
    content_type: str,
    ticker: Optional[str],
    model: str,
    on_feedback: Optional[callable],
) -> None:
    """Record feedback to database.

    Args:
        content_hash: Unique content hash.
        helpful: Whether feedback is positive.
        content_type: Type of content.
        ticker: Stock ticker.
        model: Model name.
        on_feedback: Optional callback.
    """
    if on_feedback:
        on_feedback(helpful=helpful, content_hash=content_hash)
    else:
        # Try to use the database directly
        try:
            from dashboard.utils.ai_feedback import record_ai_feedback

            record_ai_feedback(
                content_hash=content_hash,
                content_type=content_type,
                ticker=ticker or "",
                model=model,
                helpful=helpful,
            )
        except ImportError:
            # Fallback: just log to session state
            pass


def _generate_content_hash(content: str, model: str, ticker: str) -> str:
    """Generate unique hash for content tracking.

    Args:
        content: AI content text.
        model: Model name.
        ticker: Stock ticker.

    Returns:
        Short hash string.
    """
    combined = f"{content[:500]}|{model}|{ticker}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def _format_model_name(model: str) -> str:
    """Format model name for display.

    Args:
        model: Raw model name.

    Returns:
        Formatted display name.
    """
    model_lower = model.lower()

    if "flash" in model_lower:
        return "Flash"
    elif "pro" in model_lower:
        return "Pro"
    elif "gemini-2.5" in model_lower:
        if "flash" in model_lower:
            return "Gemini Flash"
        return "Gemini Pro"
    elif "gemini-3" in model_lower:
        return "Gemini 3 Pro"

    # Return shortened version
    if len(model) > 15:
        return model[:12] + "..."
    return model


def _format_content(content: str) -> str:
    """Format content for HTML display.

    Args:
        content: Raw content text.

    Returns:
        HTML-safe formatted content.
    """
    import html
    content = html.escape(content)

    # Convert markdown-style bullets to HTML
    lines = content.split("\n")
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("• ") or stripped.startswith("- "):
            # Bullet point
            text = stripped[2:]
            formatted_lines.append(f"<div style='margin-left:16px'>• {text}</div>")
        elif stripped.startswith("* "):
            text = stripped[2:]
            formatted_lines.append(f"<div style='margin-left:16px'>• {text}</div>")
        elif stripped:
            formatted_lines.append(f"<div>{stripped}</div>")
        else:
            formatted_lines.append("<div style='height:8px'></div>")

    return "".join(formatted_lines)


def render_ai_comparison(
    ai_content: str,
    human_content: Optional[str],
    model: str,
    cost: Optional[float] = None,
) -> None:
    """Render side-by-side comparison of AI and human content.

    Args:
        ai_content: AI-generated content.
        human_content: Human-authored content (optional).
        model: Model name.
        cost: Estimated cost.
    """
    if human_content:
        col1, col2 = st.columns(2)

        with col1:
            render_human_section(human_content, author="Your Analysis")

        with col2:
            render_ai_section(ai_content, model=model, cost=cost)
    else:
        render_ai_section(ai_content, model=model, cost=cost)
