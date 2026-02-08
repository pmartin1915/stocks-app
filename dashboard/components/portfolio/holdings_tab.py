"""Holdings tab — current positions table and allocation chart."""

from typing import Dict, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from asymmetric.core.portfolio import PortfolioManager
from dashboard.theme import get_plotly_theme


def render_holdings_tab(
    holdings: list,
    manager: PortfolioManager,
    prices: Dict[str, Optional[float]],
) -> None:
    """Render the Holdings tab content.

    Args:
        holdings: List of HoldingDetail objects.
        manager: PortfolioManager instance.
        prices: Pre-fetched market prices dict.
    """
    st.subheader("Current Holdings")

    if not holdings:
        st.info("No holdings yet. Add a buy transaction to get started.")
        return

    # Sort options
    col1, col2 = st.columns([3, 1])
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["value", "gainloss", "ticker", "fscore"],
            format_func=lambda x: {
                "value": "Value",
                "gainloss": "Gain/Loss %",
                "ticker": "Ticker",
                "fscore": "F-Score",
            }.get(x, x),
        )

    # Re-fetch with sort using cached prices (no redundant API call)
    try:
        holdings = manager.get_holdings(sort_by=sort_by, market_prices=prices)
    except Exception as e:
        st.error(f"Error sorting holdings: {e}")

    # Holdings table
    holdings_data = []
    for h in holdings:
        if h.unrealized_pnl is not None:
            pnl_text = f"${h.unrealized_pnl:,.2f} ({h.unrealized_pnl_percent:+.1f}%)"
        else:
            pnl_text = "N/A"

        holdings_data.append({
            "Ticker": h.ticker,
            "Company": h.company_name,
            "Shares": h.quantity,
            "Cost Basis": h.cost_basis_total,
            "Current Price": h.current_price if h.current_price else 0.0,
            "Market Value": h.market_value if h.market_value else h.cost_basis_total,
            "Unrealized P&L": pnl_text,
            "_pnl_pct": h.unrealized_pnl_percent if h.unrealized_pnl_percent is not None else 0.0,
            "Allocation %": h.allocation_percent,
            "Days Held": h.days_held,
            "F-Score": f"{h.fscore}/9" if h.fscore is not None else "N/A",
            "Z-Zone": h.zone or "N/A",
        })

    df = pd.DataFrame(holdings_data)

    # Style P&L coloring based on raw numeric value
    def style_pnl(row):
        pct = row["_pnl_pct"]
        color = "green" if pct > 0 else "red" if pct < 0 else ""
        return [f"color: {color}" if col == "Unrealized P&L" and color else "" for col in row.index]

    styled_df = df.style.apply(style_pnl, axis=1)

    st.dataframe(
        styled_df,
        use_container_width=True,
        column_config={
            "Cost Basis": st.column_config.NumberColumn(format="$%.2f"),
            "Current Price": st.column_config.NumberColumn(format="$%.2f"),
            "Market Value": st.column_config.NumberColumn(format="$%.2f"),
            "Allocation %": st.column_config.NumberColumn(format="%.1f%%"),
            "Unrealized P&L": st.column_config.TextColumn("Unrealized P&L"),
            "_pnl_pct": None,  # Hide helper column
        },
    )

    # Allocation pie chart
    st.subheader("Allocation")
    fig = px.pie(
        df,
        values="Market Value",
        names="Ticker",
        title="Portfolio Allocation by Market Value",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(**get_plotly_theme())
    st.plotly_chart(fig, use_container_width=True)
