"""Performance tab — winners/losers, P&L chart, metrics, and price history."""

import plotly.graph_objects as go
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.theme import get_plotly_theme, get_semantic_color
from dashboard.utils.portfolio_cache import get_cached_realized_pnl
from dashboard.utils.price_data import get_batch_price_history


def _render_insights(holdings_with_prices: list) -> None:
    """Show up to 3 actionable insights based on current holdings."""
    if not holdings_with_prices:
        return

    insights: list[str] = []

    # Best/worst performer callout
    best = max(holdings_with_prices, key=lambda h: h.unrealized_pnl_percent or -999)
    worst = min(holdings_with_prices, key=lambda h: h.unrealized_pnl_percent or 999)

    best_pct = best.unrealized_pnl_percent or 0
    worst_pct = worst.unrealized_pnl_percent or 0

    if best_pct > 20:
        insights.append(
            f"**{best.ticker}** is up **{best_pct:+.1f}%** -- consider whether it's still undervalued or time to take some profits"
        )
    if worst_pct < -15:
        insights.append(
            f"**{worst.ticker}** is down **{worst_pct:+.1f}%** -- review your original thesis to see if it still holds"
        )

    # Concentration warning
    total_value = sum(h.market_value for h in holdings_with_prices if h.market_value)
    if total_value > 0:
        for h in holdings_with_prices:
            weight = (h.market_value / total_value * 100) if h.market_value else 0
            if weight > 30:
                insights.append(
                    f"**{h.ticker}** is **{weight:.0f}%** of your portfolio -- high concentration increases risk"
                )
                break

    # Win rate context
    winners = [h for h in holdings_with_prices if h.unrealized_pnl and h.unrealized_pnl > 0]
    win_rate = (len(winners) / len(holdings_with_prices) * 100) if holdings_with_prices else 0

    if win_rate < 40 and len(holdings_with_prices) >= 3:
        insights.append(
            f"Win rate is **{win_rate:.0f}%** -- normal for value investing, but worth reviewing your losers"
        )
    elif win_rate > 70 and len(holdings_with_prices) >= 3:
        insights.append(
            f"Win rate is **{win_rate:.0f}%** -- your stock selection process is working well"
        )

    # Display max 3 insights
    for insight in insights[:3]:
        st.info(insight)


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

        # Actionable insights
        _render_insights(holdings_with_prices)

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
                    "P&L ($)": f"▲ ${h.unrealized_pnl:,.2f}" if h.unrealized_pnl > 0 else f"▼ ${h.unrealized_pnl:,.2f}" if h.unrealized_pnl < 0 else "— $0.00",
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
                    "P&L ($)": f"▲ ${h.unrealized_pnl:,.2f}" if h.unrealized_pnl > 0 else f"▼ ${h.unrealized_pnl:,.2f}" if h.unrealized_pnl < 0 else "— $0.00",
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
            color_discrete_map={
                "Realized": get_semantic_color("green"),
                "Unrealized": get_semantic_color("blue"),
            },
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
            st.caption("% of your picks currently in profit")
        with col2:
            st.metric(
                "Avg Winning Position",
                f"${avg_gain:,.2f}",
                delta=f"+${avg_gain:,.2f}" if avg_gain > 0 else None,
                help="Average unrealized gain per winning position",
            )
        with col3:
            st.metric(
                "Avg Losing Position",
                f"${avg_loss:,.2f}",
                delta=f"${avg_loss:,.2f}" if avg_loss < 0 else None,
                help="Average unrealized loss per losing position",
            )
        with col4:
            best_pct = best.unrealized_pnl_percent or 0
            worst_pct = worst.unrealized_pnl_percent or 0
            st.metric(
                "Best / Worst",
                f"{best.ticker} / {worst.ticker}",
                delta=f"{best_pct:+.1f}% / {worst_pct:+.1f}%",
                delta_color="off",
                help=f"Best: {best_pct:+.1f}% | Worst: {worst_pct:+.1f}%",
            )

        # Price History Charts
        st.divider()
        _render_price_history_section(holdings_with_prices)

    except Exception as e:
        st.error(f"Error calculating performance metrics: {e}")
        st.info("Some market data may be unavailable. Try refreshing the page.")


# --- Price History helpers ---

MONEY_MARKET_TICKERS = {"SPAXX"}


def _render_price_history_section(holdings: list) -> None:
    """Render price history charts with cost basis overlay."""
    st.subheader("Price History")

    chart_holdings = [h for h in holdings if h.ticker not in MONEY_MARKET_TICKERS]
    excluded = [h.ticker for h in holdings if h.ticker in MONEY_MARKET_TICKERS]

    if excluded:
        st.caption(f"{', '.join(excluded)} (money market) excluded")

    if not chart_holdings:
        st.info("No equity holdings to chart.")
        return

    # Controls
    col1, col2 = st.columns([3, 1])

    ticker_options = ["All Holdings (Normalized)"] + [h.ticker for h in chart_holdings]

    with col1:
        selected = st.selectbox(
            "Select Holding",
            options=ticker_options,
            key="price_history_ticker",
        )

    with col2:
        period = st.selectbox(
            "Period",
            options=["Since Purchase", "3M", "6M", "1Y", "YTD"],
            index=0,
            key="price_history_period",
        )

    yf_period_map = {
        "Since Purchase": "2y",
        "3M": "3mo",
        "6M": "6mo",
        "1Y": "1y",
        "YTD": "ytd",
    }

    tickers_to_fetch = tuple(h.ticker for h in chart_holdings)

    with st.spinner("Loading price history..."):
        all_histories = get_batch_price_history(tickers_to_fetch, yf_period_map[period])

    if selected == "All Holdings (Normalized)":
        fig = _create_normalized_chart(chart_holdings, all_histories, period)
    else:
        holding = next(h for h in chart_holdings if h.ticker == selected)
        history = all_histories.get(selected, {})
        fig = _create_single_chart(holding, history, period)

    if fig:
        st.plotly_chart(fig, use_container_width=True)


def _create_single_chart(holding, history: dict, period: str):
    """Create price chart for one holding with cost basis overlay."""
    if "error" in history or not history.get("prices"):
        st.warning(f"Price history unavailable for {holding.ticker}")
        return None

    dates = list(history["dates"])
    prices = list(history["prices"])

    # Trim to purchase date for "Since Purchase"
    if period == "Since Purchase" and holding.first_purchase_date:
        cutoff = holding.first_purchase_date.strftime("%Y-%m-%d")
        filtered = [(d, p) for d, p in zip(dates, prices) if d >= cutoff]
        if filtered:
            dates, prices = zip(*filtered)
            dates, prices = list(dates), list(prices)

    cost_basis = holding.cost_basis_per_share
    current_price = prices[-1] if prices else 0
    green = get_semantic_color("green")
    red = get_semantic_color("red")
    blue = get_semantic_color("blue")
    gray = get_semantic_color("gray")
    fill_color = green if current_price >= cost_basis else red

    fig = go.Figure()

    # Invisible cost basis trace (fill target)
    fig.add_trace(go.Scatter(
        x=dates,
        y=[cost_basis] * len(dates),
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Price line with fill to cost basis
    fig.add_trace(go.Scatter(
        x=dates,
        y=prices,
        mode="lines",
        name=f"{holding.ticker} Price",
        line=dict(color=blue, width=2.5),
        fill="tonexty",
        fillcolor=f"rgba({_hex_to_rgb(fill_color)}, 0.15)",
        hovertemplate=(
            "<b>%{x}</b><br>"
            f"{holding.ticker}: $%{{y:.2f}}<br>"
            f"Cost Basis: ${cost_basis:.2f}<br>"
            "<extra></extra>"
        ),
    ))

    # Cost basis dashed line
    fig.add_hline(
        y=cost_basis,
        line_dash="dash",
        line_color=gray,
        line_width=1.5,
        annotation_text=f"Cost Basis: ${cost_basis:.2f}",
        annotation_position="top left",
        annotation_font_color=gray,
    )

    # P&L annotation
    pnl_pct = holding.unrealized_pnl_percent or 0
    pnl_color = green if pnl_pct >= 0 else red

    fig.add_annotation(
        text=f"P&L: {pnl_pct:+.1f}%",
        xref="paper", yref="paper",
        x=0.98, y=0.95,
        showarrow=False,
        font=dict(size=16, color=pnl_color, family="monospace"),
        bgcolor="rgba(0,0,0,0.5)",
        borderpad=4,
    )

    company = getattr(holding, "company_name", holding.ticker)
    fig.update_layout(
        title=f"{holding.ticker} — {company}",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=450,
        margin=dict(t=60, l=25, r=25, b=25),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        **get_plotly_theme(),
    )

    return fig


def _create_normalized_chart(holdings: list, all_histories: dict, period: str):
    """Create normalized % return chart for all holdings overlaid."""
    colors = ["#60a5fa", "#10b981", "#f59e0b", "#f87171", "#a78bfa", "#fb923c", "#38bdf8"]
    gray = get_semantic_color("gray")

    fig = go.Figure()
    has_data = False

    for i, holding in enumerate(holdings):
        history = all_histories.get(holding.ticker, {})
        if "error" in history or not history.get("prices"):
            continue

        dates = list(history["dates"])
        prices = list(history["prices"])

        if period == "Since Purchase" and holding.first_purchase_date:
            cutoff = holding.first_purchase_date.strftime("%Y-%m-%d")
            filtered = [(d, p) for d, p in zip(dates, prices) if d >= cutoff]
            if filtered:
                dates, prices = zip(*filtered)
                dates, prices = list(dates), list(prices)

        if not prices:
            continue

        cost_basis = holding.cost_basis_per_share
        if cost_basis <= 0:
            continue

        returns = [((p - cost_basis) / cost_basis) * 100 for p in prices]
        pnl_pct = holding.unrealized_pnl_percent or 0

        fig.add_trace(go.Scatter(
            x=dates,
            y=returns,
            mode="lines",
            name=f"{holding.ticker} ({pnl_pct:+.1f}%)",
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate=(
                f"<b>{holding.ticker}</b><br>"
                "%{x}<br>"
                "Return: %{y:.1f}%<br>"
                "<extra></extra>"
            ),
        ))
        has_data = True

    if not has_data:
        st.warning("No price history available for any holdings.")
        return None

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color=gray,
        line_width=1.5,
        annotation_text="Break Even (Cost Basis)",
        annotation_position="right",
        annotation_font_color=gray,
    )

    fig.update_layout(
        title="All Holdings — Return From Cost Basis",
        xaxis_title="Date",
        yaxis_title="Return (%)",
        height=500,
        margin=dict(t=60, l=25, r=25, b=25),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        **get_plotly_theme(),
    )

    return fig


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to 'r, g, b' string for rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
