"""Performance tab — winners/losers, P&L chart, and metrics."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.theme import get_plotly_theme
from dashboard.utils.portfolio_cache import get_cached_realized_pnl


def render_performance_tab(holdings: list) -> None:
    """Render the Performance Analysis tab.

    Args:
        holdings: List of HoldingDetail objects with market data.
    """
    st.subheader("Performance Analysis")
    st.caption("Winners, losers, and performance metrics")

    if not holdings:
        st.info("Add holdings to see performance analysis.")
        return

    try:
        holdings_with_prices = [h for h in holdings if h.unrealized_pnl is not None]

        if not holdings_with_prices:
            st.warning("Market prices unavailable. Cannot calculate performance metrics.")
            return

        # Winners & Losers
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top 5 Performers**")
            winners = sorted(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or -999, reverse=True)[:5]
            winners_data = [
                {
                    "Ticker": h.ticker,
                    "Cost Basis": f"${h.cost_basis_total:,.2f}",
                    "Market Value": f"${h.market_value:,.2f}",
                    "P&L ($)": f"${h.unrealized_pnl:,.2f}",
                    "P&L (%)": f"{h.unrealized_pnl_percent:+.1f}%",
                    "Days Held": h.days_held,
                }
                for h in winners
            ]
            st.dataframe(pd.DataFrame(winners_data), use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Bottom 5 Performers**")
            losers = sorted(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or 999)[:5]
            losers_data = [
                {
                    "Ticker": h.ticker,
                    "Cost Basis": f"${h.cost_basis_total:,.2f}",
                    "Market Value": f"${h.market_value:,.2f}",
                    "P&L ($)": f"${h.unrealized_pnl:,.2f}",
                    "P&L (%)": f"{h.unrealized_pnl_percent:+.1f}%",
                    "Days Held": h.days_held,
                }
                for h in losers
            ]
            st.dataframe(pd.DataFrame(losers_data), use_container_width=True, hide_index=True)

        # Realized vs Unrealized P&L Chart
        st.divider()
        st.markdown("**Realized vs Unrealized P&L**")

        chart_data = [{"Ticker": h.ticker, "P&L": h.unrealized_pnl, "Type": "Unrealized"} for h in holdings_with_prices]

        realized_by_ticker = get_cached_realized_pnl()
        for h in holdings_with_prices:
            realized_for_ticker = realized_by_ticker.get(h.ticker, 0.0)
            if realized_for_ticker != 0:
                chart_data.append({"Ticker": h.ticker, "P&L": realized_for_ticker, "Type": "Realized"})

        chart_df = pd.DataFrame(chart_data)
        fig = px.bar(
            chart_df,
            x="Ticker",
            y="P&L",
            color="Type",
            barmode="group",
            color_discrete_map={"Realized": "green", "Unrealized": "blue"},
            title="Realized vs Unrealized P&L by Position",
        )
        fig.update_layout(**get_plotly_theme())
        fig.update_yaxis(title="P&L ($)")
        st.plotly_chart(fig, use_container_width=True)

        # Performance Summary
        st.divider()
        st.markdown("**Performance Summary**")

        winning_positions = [h for h in holdings_with_prices if h.unrealized_pnl and h.unrealized_pnl > 0]
        losing_positions = [h for h in holdings_with_prices if h.unrealized_pnl and h.unrealized_pnl < 0]

        avg_gain = sum(h.unrealized_pnl for h in winning_positions) / len(winning_positions) if winning_positions else 0
        avg_loss = sum(h.unrealized_pnl for h in losing_positions) / len(losing_positions) if losing_positions else 0
        win_rate = (len(winning_positions) / len(holdings_with_prices) * 100) if holdings_with_prices else 0

        best = max(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or -999)
        worst = min(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or 999)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Win Rate", f"{win_rate:.1f}%", help=f"{len(winning_positions)} winners / {len(holdings_with_prices)} total")
        with col2:
            st.metric("Avg Winning Position", f"${avg_gain:,.2f}", help="Average unrealized gain per winning position")
        with col3:
            st.metric("Avg Losing Position", f"${avg_loss:,.2f}", help="Average unrealized loss per losing position")
        with col4:
            st.metric(
                "Best / Worst",
                f"{best.ticker} / {worst.ticker}",
                help=f"Best: {best.unrealized_pnl_percent:+.1f}% | Worst: {worst.unrealized_pnl_percent:+.1f}%",
            )

    except Exception as e:
        st.error(f"Error calculating performance metrics: {e}")
        st.info("Some market data may be unavailable. Try refreshing the page.")
