"""Unified stock card component with layered information hierarchy.

Displays stock information in a consistent format across all pages:
- Primary: Ticker, name, price, scores, conviction
- Secondary: Thesis summary, key risk
- Actions: View, Update, Record Decision
"""

from typing import Optional

import streamlit as st

from dashboard.components import icons
from dashboard.theme import get_color, get_semantic_color
from dashboard.utils.price_data import (
    get_price_data,
    get_price_history,
    format_large_number,
)


def render_price_badge(ticker: str) -> None:
    """Render price with change indicator.

    Args:
        ticker: Stock ticker symbol.
    """
    data = get_price_data(ticker)

    if "error" in data:
        st.caption("Price unavailable")
        return

    price = data.get("price")
    change = data.get("change") or 0
    change_pct = data.get("change_pct") or 0

    if price is None:
        st.caption("Price unavailable")
        return

    # Color and arrow based on change direction
    if change >= 0:
        color = get_semantic_color("green")
        arrow = "↑"
    else:
        color = get_semantic_color("red")
        arrow = "↓"

    # Price display with change
    st.markdown(
        f"""
    <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap">
        <span style="font-size:1.25rem;font-weight:700">${price:.2f}</span>
        <span style="color:{color};font-weight:600;font-size:0.9rem">
            {arrow} {abs(change):.2f} ({abs(change_pct):.2f}%)
        </span>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_price_with_range(ticker: str) -> None:
    """Render price with 52-week range context.

    Args:
        ticker: Stock ticker symbol.
    """
    data = get_price_data(ticker)

    if "error" in data:
        st.caption("Price unavailable")
        return

    price = data.get("price")
    high_52w = data.get("52w_high")
    low_52w = data.get("52w_low")

    if price is None:
        st.caption("Price unavailable")
        return

    render_price_badge(ticker)

    # 52-week range indicator
    if high_52w and low_52w and high_52w != low_52w:
        pct_of_range = (price - low_52w) / (high_52w - low_52w) * 100
        pct_of_range = max(0, min(100, pct_of_range))

        text_secondary = get_color("text_secondary")
        border_color = get_color("border")

        st.markdown(
            f"""
        <div style="margin-top:4px">
            <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:{text_secondary}">
                <span>${low_52w:.0f}</span>
                <span>52W Range</span>
                <span>${high_52w:.0f}</span>
            </div>
            <div style="position:relative;height:6px;background:{border_color};border-radius:3px;margin-top:2px">
                <div style="position:absolute;left:{pct_of_range}%;top:-2px;width:10px;height:10px;
                            background:{get_semantic_color('blue')};border-radius:50%;transform:translateX(-50%)"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_sparkline(ticker: str, width: int = 120, height: int = 32) -> str:
    """Generate SVG sparkline for inline display.

    Args:
        ticker: Stock ticker symbol.
        width: SVG width in pixels.
        height: SVG height in pixels.

    Returns:
        HTML string with SVG sparkline.
    """
    history = get_price_history(ticker, period="3mo")

    if "error" in history or not history.get("prices"):
        return ""

    prices = history["prices"]
    if len(prices) < 2:
        return ""

    min_p, max_p = min(prices), max(prices)
    range_p = max_p - min_p or 1

    # Normalize to SVG coordinates with padding
    padding = 2
    effective_width = width - 2 * padding
    effective_height = height - 2 * padding

    points = []
    for i, p in enumerate(prices):
        x = padding + (i / (len(prices) - 1)) * effective_width
        y = padding + effective_height - ((p - min_p) / range_p) * effective_height
        points.append(f"{x:.1f},{y:.1f}")

    # Color based on overall trend
    color = get_semantic_color("green") if prices[-1] >= prices[0] else get_semantic_color("red")

    return f"""
    <svg width="{width}" height="{height}" style="display:inline-block;vertical-align:middle">
        <polyline points="{' '.join(points)}"
                  fill="none" stroke="{color}" stroke-width="1.5"
                  stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """


def render_key_metrics_row(ticker: str) -> None:
    """Render key valuation metrics in a row.

    Args:
        ticker: Stock ticker symbol.
    """
    data = get_price_data(ticker)

    if "error" in data:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pe = data.get("pe_ratio")
        st.metric("P/E", f"{pe:.1f}" if pe else "N/A")

    with col2:
        mcap = data.get("market_cap")
        st.metric("Mkt Cap", format_large_number(mcap))

    with col3:
        div_yield = data.get("dividend_yield")
        if div_yield:
            st.metric("Div Yield", f"{div_yield * 100:.2f}%")
        else:
            st.metric("Div Yield", "N/A")

    with col4:
        beta = data.get("beta")
        st.metric("Beta", f"{beta:.2f}" if beta else "N/A")


def render_stock_card_header(
    ticker: str,
    company_name: Optional[str] = None,
    conviction: Optional[int] = None,
    decision_status: Optional[str] = None,
) -> None:
    """Render stock card header with ticker, name, and conviction.

    Args:
        ticker: Stock ticker symbol.
        company_name: Company name (fetched from yfinance if not provided).
        conviction: Conviction level 1-5.
        decision_status: Current decision status (watching/holding/passed).
    """
    # Try to get company name from price data if not provided
    if not company_name:
        data = get_price_data(ticker)
        company_name = data.get("short_name") or data.get("long_name") or ""

    # Build header HTML
    header_parts = [f'<span style="font-size:1.25rem;font-weight:700">{ticker}</span>']

    if company_name:
        text_secondary = get_color("text_secondary")
        header_parts.append(
            f'<span style="color:{text_secondary};font-size:0.9rem;margin-left:8px">{company_name}</span>'
        )

    # Right-aligned section
    right_parts = []

    if conviction is not None:
        stars = icons.stars_rating(conviction, max_stars=5, size=14)
        right_parts.append(f'<span style="margin-right:8px">{stars}</span>')

    if decision_status:
        status_badge = _decision_status_badge(decision_status)
        right_parts.append(status_badge)

    # Combine header
    left_html = "".join(header_parts)
    right_html = "".join(right_parts)

    st.markdown(
        f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div>{left_html}</div>
        <div style="display:flex;align-items:center">{right_html}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def _decision_status_badge(status: str) -> str:
    """Create decision status badge.

    Args:
        status: Decision status (watching/holding/passed/none).

    Returns:
        HTML badge string.
    """
    text_on_accent = get_color("text_on_accent")
    text_on_yellow = get_color("text_on_yellow")
    blue = get_semantic_color("blue")
    green = get_semantic_color("green")
    gray = get_semantic_color("gray")
    yellow = get_semantic_color("yellow")

    status_styles = {
        "watching": (blue, text_on_accent, "WATCHING"),
        "holding": (green, text_on_accent, "HOLDING"),
        "passed": (gray, text_on_accent, "PASSED"),
        "sold": (yellow, text_on_yellow, "SOLD"),
    }

    bg, fg, label = status_styles.get(
        status.lower(), (gray, text_on_accent, status.upper())
    )
    return icons.badge(label, bg, fg, "small")


def render_stock_card(
    ticker: str,
    piotroski: Optional[dict] = None,
    altman: Optional[dict] = None,
    thesis: Optional[dict] = None,
    conviction: Optional[int] = None,
    decision_status: Optional[str] = None,
    show_price: bool = True,
    show_sparkline: bool = True,
    show_thesis: bool = True,
    key_prefix: str = "",
) -> dict:
    """Render complete stock card with all layers.

    Args:
        ticker: Stock ticker symbol.
        piotroski: Piotroski F-Score data dict.
        altman: Altman Z-Score data dict.
        thesis: Thesis data dict.
        conviction: Conviction level 1-5.
        decision_status: Current decision status.
        show_price: Whether to show price section.
        show_sparkline: Whether to show price sparkline.
        show_thesis: Whether to show thesis section.
        key_prefix: Prefix for button keys to ensure uniqueness.

    Returns:
        Dictionary with button click states.
    """
    actions = {"view_details": False, "update_thesis": False, "record_decision": False}

    # Header row
    render_stock_card_header(ticker, conviction=conviction, decision_status=decision_status)

    border_color = get_color("border")
    st.markdown(
        f'<hr style="margin:8px 0;border:none;border-top:1px solid {border_color}">',
        unsafe_allow_html=True,
    )

    # Price and scores row
    col1, col2 = st.columns([1.2, 1])

    with col1:
        if show_price:
            price_col, spark_col = st.columns([2, 1])
            with price_col:
                render_price_badge(ticker)
            with spark_col:
                sparkline = render_sparkline(ticker) if show_sparkline else ""
                if sparkline:
                    st.markdown(sparkline, unsafe_allow_html=True)
        else:
            st.caption("Price: Not available")

    with col2:
        # Score badges
        score_parts = []

        if piotroski:
            fscore = piotroski.get("score")
            score_parts.append(icons.fscore_badge(fscore, size="normal"))

        if altman:
            zscore = altman.get("z_score")
            zone = altman.get("zone")
            score_parts.append(icons.zscore_badge(zscore, zone, size="normal"))
            score_parts.append(icons.status_badge(zone or "neutral", size="normal"))

        if score_parts:
            st.markdown(" ".join(score_parts), unsafe_allow_html=True)
        else:
            st.caption("Scores: Not calculated")

    # Thesis section
    if show_thesis and thesis:
        border_color = get_color("border")
        text_secondary = get_color("text_secondary")
        text_on_accent = get_color("text_on_accent")

        st.markdown(
            f'<hr style="margin:8px 0;border:none;border-top:1px solid {border_color}">',
            unsafe_allow_html=True,
        )

        thesis_status = thesis.get("status", "draft")
        thesis_summary = thesis.get("summary", "")[:100]
        bear_case = thesis.get("bear_case", "")

        # Thesis icon based on AI vs human
        if thesis.get("ai_generated"):
            source_icon = icons.badge("AI", get_semantic_color("blue"), text_on_accent, "small")
        else:
            source_icon = ""

        status_badge = icons.thesis_status_badge(thesis_status, size="small")

        st.markdown(
            f"""
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px">
            <span>{status_badge}</span>
            {source_icon}
        </div>
        <div style="font-size:0.9rem;color:{text_secondary};margin-bottom:4px">
            {thesis_summary}{'...' if len(thesis.get('summary', '')) > 100 else ''}
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Key risk if available
        if bear_case:
            first_risk = bear_case.split("\n")[0][:80] if bear_case else ""
            if first_risk:
                yellow_color = get_semantic_color('yellow')
                st.markdown(
                    f"""
                <div style="display:flex;align-items:center;gap:4px;font-size:0.85rem">
                    <span style="color:{yellow_color}">⚠</span>
                    <span style="color:{text_secondary}">{first_risk}</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    # Action buttons
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        if st.button("View Details", key=f"{key_prefix}view_{ticker}", use_container_width=True):
            actions["view_details"] = True

    with btn_col2:
        if st.button(
            "Update Thesis", key=f"{key_prefix}thesis_{ticker}", use_container_width=True
        ):
            actions["update_thesis"] = True

    with btn_col3:
        if st.button(
            "Record Decision", key=f"{key_prefix}decision_{ticker}", use_container_width=True
        ):
            actions["record_decision"] = True

    return actions


def render_compact_stock_row(
    ticker: str,
    piotroski: Optional[dict] = None,
    altman: Optional[dict] = None,
    thesis_status: Optional[str] = None,
    show_price: bool = True,
) -> None:
    """Render compact stock row for tables/lists.

    Args:
        ticker: Stock ticker symbol.
        piotroski: Piotroski F-Score data dict.
        altman: Altman Z-Score data dict.
        thesis_status: Thesis status string.
        show_price: Whether to show price.
    """
    cols = st.columns([1, 1.5, 1, 1, 1, 0.8])

    with cols[0]:
        st.markdown(f"**{ticker}**")

    with cols[1]:
        if show_price:
            data = get_price_data(ticker)
            if "error" not in data and data.get("price"):
                price = data["price"]
                change_pct = data.get("change_pct") or 0
                color = get_semantic_color("green") if change_pct >= 0 else get_semantic_color("red")
                st.markdown(
                    f'${price:.2f} <span style="color:{color}">{change_pct:+.1f}%</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("N/A")
        else:
            st.caption("—")

    with cols[2]:
        if piotroski:
            st.markdown(
                icons.fscore_badge(piotroski.get("score"), size="small"),
                unsafe_allow_html=True,
            )
        else:
            st.caption("—")

    with cols[3]:
        if altman:
            st.markdown(
                icons.zscore_badge(
                    altman.get("z_score"), altman.get("zone"), size="small"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.caption("—")

    with cols[4]:
        if altman and altman.get("zone"):
            st.markdown(
                icons.status_badge(altman.get("zone"), size="small"),
                unsafe_allow_html=True,
            )
        else:
            st.caption("—")

    with cols[5]:
        if thesis_status:
            st.markdown(
                icons.thesis_status_badge(thesis_status, size="small"),
                unsafe_allow_html=True,
            )
        else:
            st.caption("—")
