"""Historical tab — snapshots, performance stats, and time-series charts."""

import streamlit as st

from dashboard.utils.performance_charts import (
    create_portfolio_value_chart,
    create_pnl_attribution_chart,
    create_return_percentage_chart,
    create_portfolio_health_chart,
    create_position_count_chart,
)
from dashboard.utils.portfolio_cache import get_cached_snapshots, get_cached_performance_stats


def render_historical_tab() -> None:
    """Render the Historical Performance tab."""
    st.subheader("Historical Performance")
    st.caption("Portfolio value, P&L, and health metrics over time")

    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        time_range = st.selectbox(
            "Time Range",
            options=["7D", "30D", "90D", "YTD", "1Y", "All Time"],
            index=2,
            key="historical_time_range",
        )

    with col3:
        if st.button("Refresh Data", key="refresh_snapshots"):
            get_cached_snapshots.clear()
            get_cached_performance_stats.clear()
            st.rerun()

    try:
        snapshots = get_cached_snapshots(time_range)

        if snapshots:
            first_date = snapshots[0].snapshot_date
            last_date = snapshots[-1].snapshot_date
            with col2:
                st.info(f"Data: {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')} ({len(snapshots)} snapshots)")

        if not snapshots or len(snapshots) < 2:
            st.warning("Insufficient snapshot data for charting.")
            st.info("Snapshots are created daily at 4:00 PM ET market close.")
            st.info("Tip: You can manually trigger a snapshot in the 'Portfolio Health' tab.")

            if len(snapshots) == 1:
                st.info(f"You have 1 snapshot from {snapshots[0].snapshot_date.strftime('%Y-%m-%d')}. Come back tomorrow for historical charts!")
            else:
                st.info("Create your first snapshot to start tracking performance over time.")
        else:
            _render_performance_stats(time_range)
            _render_charts(snapshots)

    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        st.info("Try refreshing the page or check your database connection.")


def _render_performance_stats(time_range: str) -> None:
    """Render performance statistics cards."""
    stats = get_cached_performance_stats(time_range)
    if not stats:
        return

    st.divider()
    st.markdown("### Performance Summary")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Return", f"{stats['total_return']:.2f}%", delta=f"${stats['total_return_dollars']:,.2f}", help="Percentage return from first to last snapshot")
    with col2:
        st.metric("Current Drawdown", f"{stats['current_drawdown']:.2f}%", help="Distance from peak portfolio value")
    with col3:
        st.metric("Max Drawdown", f"{stats['max_drawdown']:.2f}%", help="Worst historical decline from any peak")
    with col4:
        st.metric("Days Tracked", stats["days_tracked"], help="Number of snapshots in selected range")

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Volatility", f"{stats['volatility']:.2f}%", help="Standard deviation of snapshot-to-snapshot returns")
    with col6:
        st.metric("Avg Daily Return", f"{stats['avg_daily_return']:+.3f}%", help="Mean return between consecutive snapshots")
    with col7:
        if stats.get("best_day"):
            best_date = stats["best_day"]["date"]
            best_label = best_date.strftime("%m/%d") if hasattr(best_date, "strftime") else str(best_date)
            st.metric("Best Day", f"+{stats['best_day']['return']:.2f}%", delta=best_label, help="Largest single-snapshot gain")
    with col8:
        if stats.get("worst_day"):
            worst_date = stats["worst_day"]["date"]
            worst_label = worst_date.strftime("%m/%d") if hasattr(worst_date, "strftime") else str(worst_date)
            st.metric("Worst Day", f"{stats['worst_day']['return']:.2f}%", delta=worst_label, delta_color="inverse", help="Largest single-snapshot loss")

    st.divider()


def _render_charts(snapshots: list) -> None:
    """Render all historical charts."""
    snapshot_dicts = [s.model_dump() for s in snapshots]

    st.markdown("### Portfolio Value Progression")
    try:
        st.plotly_chart(create_portfolio_value_chart(snapshot_dicts), use_container_width=True)
    except Exception as e:
        st.error(f"Error creating value chart: {e}")

    st.markdown("### P&L Attribution")
    st.caption("Unrealized (current positions) vs Realized (closed positions)")
    try:
        st.plotly_chart(create_pnl_attribution_chart(snapshot_dicts), use_container_width=True)
    except Exception as e:
        st.error(f"Error creating P&L chart: {e}")

    st.markdown("### Cumulative Return %")
    try:
        st.plotly_chart(create_return_percentage_chart(snapshot_dicts), use_container_width=True)
    except Exception as e:
        st.error(f"Error creating return chart: {e}")

    st.markdown("### Portfolio Health Over Time")
    st.caption("Weighted F-Score and Z-Score based on position sizes")
    try:
        st.plotly_chart(create_portfolio_health_chart(snapshot_dicts), use_container_width=True)
    except Exception as e:
        st.error(f"Error creating health chart: {e}")

    st.markdown("### Diversification Trend")
    st.caption("Number of open positions over time")
    try:
        st.plotly_chart(create_position_count_chart(snapshot_dicts), use_container_width=True)
    except Exception as e:
        st.error(f"Error creating position count chart: {e}")
