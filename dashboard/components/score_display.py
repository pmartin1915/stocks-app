"""Reusable score visualization components for the dashboard."""

from typing import Any

import streamlit as st

from dashboard.components import icons


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
