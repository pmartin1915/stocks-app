"""Reusable score visualization components for the dashboard.

Provides multiple visualization styles:
- Basic progress bars (original)
- Segmented gauges (enhanced)
- Zone gradient indicators
"""

from typing import Any

import streamlit as st

from dashboard.components import icons
from dashboard.theme import get_color, get_semantic_color


def render_fscore(score: int | None, show_label: bool = True) -> None:
    """
    Render F-Score as a progress bar with icon indicator.

    Args:
        score: Piotroski F-Score (0-9), or None for N/A display.
        show_label: Whether to show "F-Score: X/9" label.
    """
    if score is None:
        if show_label:
            st.caption("F-Score: N/A")
        st.progress(0, text="No data")
        return

    if show_label:
        st.caption(f"F-Score: {score}/9")

    # Show progress bar (text can't contain HTML, so just show score)
    st.progress(score / 9, text=f"{score}/9")


def render_fscore_gauge(score: int | None, show_label: bool = True) -> None:
    """
    Render F-Score as a segmented gauge with 9 discrete segments.

    Args:
        score: Piotroski F-Score (0-9), or None for N/A display.
        show_label: Whether to show label with interpretation.
    """
    if score is None:
        if show_label:
            gray = get_semantic_color("gray")
            st.markdown(
                f'<span style="color:{gray}">F-Score: N/A</span>',
                unsafe_allow_html=True,
            )
        return

    # Determine color and interpretation
    if score >= 7:
        color = get_semantic_color("green")
        interp = "Strong"
    elif score >= 4:
        color = get_semantic_color("yellow")
        interp = "Moderate"
    else:
        color = get_semantic_color("red")
        interp = "Weak"

    if show_label:
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <span style="font-weight:600">F-Score: {score}/9</span>
                <span style="color:{color};font-weight:600">{interp}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Build 9-segment bar
    border_color = get_color("border")
    segments = []
    for i in range(9):
        if i < score:
            seg_color = color
        else:
            seg_color = border_color
        segments.append(
            f'<div style="flex:1;height:14px;background:{seg_color};'
            f'border-radius:2px"></div>'
        )

    bar_html = f'<div style="display:flex;gap:3px">{" ".join(segments)}</div>'
    st.markdown(bar_html, unsafe_allow_html=True)


def render_zscore_gauge(z_score: float | None, zone: str | None) -> None:
    """
    Render Z-Score with visual zone gradient indicator.

    Shows position on a gradient bar with Distress/Grey/Safe zones.

    Args:
        z_score: Altman Z-Score value.
        zone: Zone classification.
    """
    if z_score is None or zone is None:
        gray = get_semantic_color("gray")
        st.markdown(
            f'<span style="color:{gray}">Z-Score: N/A</span>',
            unsafe_allow_html=True,
        )
        return

    # Zone thresholds
    distress_threshold = 1.81
    safe_threshold = 2.99
    max_display = 5.0  # Cap display at 5.0 for visualization

    # Normalize to percentage (0-100)
    normalized = min(z_score, max_display) / max_display * 100
    normalized = max(0, min(100, normalized))

    # Zone percentages for gradient
    distress_pct = (distress_threshold / max_display) * 100
    safe_pct = (safe_threshold / max_display) * 100

    # Determine zone color for badge
    zone_lower = zone.lower()
    if zone_lower == "safe":
        zone_color = get_semantic_color("green")
    elif zone_lower in ("grey", "gray"):
        zone_color = get_semantic_color("yellow")
    else:
        zone_color = get_semantic_color("red")

    # Header with value and zone
    text_on_accent = get_color("text_on_accent")
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-weight:600">Z-Score: {z_score:.2f}</span>
            <span style="background:{zone_color};color:{text_on_accent};padding:2px 8px;
                        border-radius:12px;font-size:0.8rem;font-weight:600">{zone}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Zone labels
    text_secondary = get_color("text_secondary")
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:{text_secondary};margin-bottom:2px">
            <span>Distress</span>
            <span>Grey Zone</span>
            <span>Safe</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Gradient bar with position marker
    bg_primary = get_color("bg_primary")
    text_primary = get_color("text_primary")
    # Use semantic colors for the gradient
    red = get_semantic_color("red")
    yellow = get_semantic_color("yellow")
    green = get_semantic_color("green")
    st.markdown(
        f"""
        <div style="position:relative;height:20px;border-radius:4px;
                    background:linear-gradient(to right,
                        {red} 0%,
                        {red} {distress_pct}%,
                        {yellow} {distress_pct}%,
                        {yellow} {safe_pct}%,
                        {green} {safe_pct}%,
                        {green} 100%)">
            <div style="position:absolute;left:{normalized}%;top:50%;
                        transform:translate(-50%, -50%);
                        width:12px;height:12px;background:{bg_primary};
                        border:2px solid {text_primary};border-radius:50%;
                        box-shadow:0 1px 3px rgba(0,0,0,0.3)"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Threshold labels
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:{text_secondary};margin-top:2px">
            <span>&lt;1.81</span>
            <span>1.81-2.99</span>
            <span>&gt;2.99</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_conviction_gauge(conviction: int | None, max_level: int = 5) -> None:
    """
    Render conviction level with stars and progress bar.

    Args:
        conviction: Conviction level (1-5).
        max_level: Maximum conviction level.
    """
    if conviction is None:
        gray = get_semantic_color("gray")
        st.markdown(
            f'<span style="color:{gray}">Conviction: N/A</span>',
            unsafe_allow_html=True,
        )
        return

    conviction = max(1, min(conviction, max_level))

    # Conviction labels
    green = get_semantic_color("green")
    yellow = get_semantic_color("yellow")
    red = get_semantic_color("red")
    gray = get_semantic_color("gray")

    labels = {
        1: ("Very Low", red),
        2: ("Low", yellow),
        3: ("Medium", yellow),
        4: ("High", green),
        5: ("Very High", green),
    }
    label, color = labels.get(conviction, ("Unknown", gray))

    # Stars
    stars = icons.stars_rating(conviction, max_stars=max_level, size=16)

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <span style="font-weight:600">Conviction</span>
            <span>{stars}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Progress bar segments
    border_color = get_color("border")
    segments = []
    for i in range(max_level):
        if i < conviction:
            seg_color = color
        else:
            seg_color = border_color
        segments.append(
            f'<div style="flex:1;height:8px;background:{seg_color};border-radius:2px"></div>'
        )

    st.markdown(
        f"""
        <div style="display:flex;gap:3px">{" ".join(segments)}</div>
        <div style="text-align:right;font-size:0.8rem;color:{color};margin-top:2px">{label}</div>
        """,
        unsafe_allow_html=True,
    )


def render_score_panel(
    piotroski: dict[str, Any] | None,
    altman: dict[str, Any] | None,
    use_gauges: bool = True,
) -> None:
    """
    Render score panel with both F-Score and Z-Score gauges.

    Args:
        piotroski: Dict with piotroski score data.
        altman: Dict with altman score data.
        use_gauges: Use enhanced gauge display (True) or basic progress bars (False).
    """
    if use_gauges:
        # F-Score gauge
        if piotroski:
            render_fscore_gauge(piotroski.get("score"), show_label=True)
        else:
            render_fscore_gauge(None, show_label=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Z-Score gauge
        if altman:
            render_zscore_gauge(altman.get("z_score"), altman.get("zone"))
        else:
            render_zscore_gauge(None, None)
    else:
        # Original progress bar style
        render_score_summary(piotroski, altman)


def render_fscore_badge(score: int | None) -> str:
    """
    Return a styled badge string for F-Score.

    Args:
        score: Piotroski F-Score (0-9), or None.

    Returns:
        HTML string with colored badge.
    """
    return icons.fscore_badge(score, size="normal")


def render_zscore(
    z_score: float | None,
    zone: str | None,
    show_label: bool = True,
) -> None:
    """
    Render Z-Score with zone badge.

    Args:
        z_score: Altman Z-Score value.
        zone: Zone classification ("Safe", "Grey", "Distress").
        show_label: Whether to show the metric label.
    """
    if z_score is None or zone is None:
        st.metric(
            label="Z-Score" if show_label else "",
            value="N/A",
            delta="No data",
        )
        return

    st.metric(
        label="Z-Score" if show_label else "",
        value=f"{z_score:.2f}",
        delta=zone,
        delta_color="off",
    )


def render_zscore_badge(z_score: float | None, zone: str | None) -> str:
    """
    Return a styled badge string for Z-Score.

    Args:
        z_score: Altman Z-Score value.
        zone: Zone classification ("Safe", "Grey", "Distress").

    Returns:
        HTML string with colored badge and zone label.
    """
    if z_score is None or zone is None:
        return icons.zscore_badge(None, None, size="normal")

    # Show Z-Score badge + zone badge side by side
    z_badge = icons.zscore_badge(z_score, zone, size="normal")
    zone_badge = icons.status_badge(zone, size="normal")
    return f'{z_badge} {zone_badge}'


def render_fscore_breakdown(signals: dict[str, bool | None] | None) -> None:
    """
    Render full Piotroski 9-component breakdown.

    Args:
        signals: Dict with keys for each Piotroski criterion.
    """
    if signals is None:
        st.info("No F-Score breakdown available")
        return

    # Define the criteria with their labels
    profitability = [
        ("Positive ROA", "positive_roa"),
        ("Positive Operating CF", "positive_cfo"),
        ("ROA Improvement", "roa_improving"),
        ("CFO > Net Income", "accruals_quality"),
    ]

    leverage = [
        ("Lower Leverage", "leverage_decreasing"),
        ("Higher Liquidity", "current_ratio_improving"),
        ("No Share Dilution", "no_dilution"),
    ]

    efficiency = [
        ("Higher Gross Margin", "gross_margin_improving"),
        ("Higher Asset Turnover", "asset_turnover_improving"),
    ]

    st.markdown("**Profitability** (4 pts)")
    for label, key in profitability:
        _render_signal(label, signals.get(key))

    st.markdown("**Leverage/Liquidity** (3 pts)")
    for label, key in leverage:
        _render_signal(label, signals.get(key))

    st.markdown("**Operating Efficiency** (2 pts)")
    for label, key in efficiency:
        _render_signal(label, signals.get(key))


def _render_signal(label: str, passed: bool | None) -> None:
    """Render a single signal with pass/fail icon."""
    icon = icons.signal_icon(passed)
    st.markdown(f"{icon} {label}", unsafe_allow_html=True)


def render_score_summary(
    piotroski: dict[str, Any] | None,
    altman: dict[str, Any] | None,
) -> None:
    """
    Render a compact score summary for a stock.

    Args:
        piotroski: Dict with piotroski score data.
        altman: Dict with altman score data.
    """
    col1, col2 = st.columns(2)

    with col1:
        if piotroski:
            render_fscore(piotroski.get("score"), show_label=True)
        else:
            render_fscore(None, show_label=True)

    with col2:
        if altman:
            render_zscore(
                altman.get("z_score"),
                altman.get("zone"),
                show_label=True,
            )
        else:
            render_zscore(None, None, show_label=True)


def render_score_detail(
    piotroski: dict[str, Any] | None,
    altman: dict[str, Any] | None,
) -> None:
    """
    Render detailed score breakdown in tabs.

    Args:
        piotroski: Dict with piotroski score data including signals.
        altman: Dict with altman score data.
    """
    tab1, tab2 = st.tabs(["F-Score Breakdown", "Z-Score Details"])

    with tab1:
        if piotroski:
            render_fscore_breakdown(piotroski.get("signals"))

            # Show component scores
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Profitability", f"{piotroski.get('profitability', 0)}/4")
            with col2:
                st.metric("Leverage", f"{piotroski.get('leverage', 0)}/3")
            with col3:
                st.metric("Efficiency", f"{piotroski.get('efficiency', 0)}/2")

            st.caption(f"Interpretation: {piotroski.get('interpretation', 'N/A')}")
        else:
            st.info("F-Score data not available for this stock.")

    with tab2:
        if altman:
            zone = altman.get('zone', 'N/A')
            st.metric(
                "Z-Score",
                f"{altman.get('z_score', 0):.2f}",
                delta=zone,
                delta_color="off",
            )
            st.caption(f"Formula: {altman.get('formula_used', 'N/A')}")
            st.caption(f"Interpretation: {altman.get('interpretation', 'N/A')}")
        else:
            st.info("Z-Score data not available for this stock.")
