"""
Portfolio Page - Track holdings, transactions, and P&L.

Manage your investment portfolio with FIFO cost basis tracking,
realized/unrealized P&L, and portfolio-weighted score analysis.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from asymmetric.core.portfolio import PortfolioManager

st.title("Portfolio")
st.caption("Track holdings, transactions, and portfolio health")

# Initialize manager
manager = PortfolioManager()

# Get summary data
summary = manager.get_portfolio_summary()
holdings = manager.get_holdings()
weighted_scores = manager.get_weighted_scores()

# Top-level metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Cost Basis",
        f"${summary.total_cost_basis:,.2f}",
        help="Total amount invested"
    )

with col2:
    st.metric(
        "Positions",
        summary.position_count,
        help="Number of holdings"
    )

with col3:
    pnl_color = "normal" if summary.realized_pnl_total >= 0 else "inverse"
    st.metric(
        "Realized P&L (Total)",
        f"${summary.realized_pnl_total:,.2f}",
        help="Total realized gains/losses from sells"
    )

with col4:
    st.metric(
        "Realized P&L (YTD)",
        f"${summary.realized_pnl_ytd:,.2f}",
        help="Realized gains/losses this year"
    )

st.divider()

# Tabs for different views
tab_holdings, tab_add, tab_history, tab_health = st.tabs([
    "Holdings",
    "Add Transaction",
    "Transaction History",
    "Portfolio Health"
])

with tab_holdings:
    st.subheader("Current Holdings")

    if holdings:
        # Sort options
        col1, col2 = st.columns([3, 1])
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["value", "ticker", "fscore"],
                format_func=lambda x: {"value": "Value", "ticker": "Ticker", "fscore": "F-Score"}.get(x, x)
            )

        # Re-fetch with sort
        holdings = manager.get_holdings(sort_by=sort_by)

        # Holdings table
        holdings_data = []
        for h in holdings:
            holdings_data.append({
                "Ticker": h.ticker,
                "Company": h.company_name,
                "Shares": h.quantity,
                "Cost Basis": h.cost_basis_total,
                "Avg Cost": h.cost_basis_per_share,
                "Allocation %": h.allocation_percent,
                "F-Score": f"{h.fscore}/9" if h.fscore is not None else "N/A",
                "Z-Zone": h.zone or "N/A"
            })

        df = pd.DataFrame(holdings_data)
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Cost Basis": st.column_config.NumberColumn(format="$%.2f"),
                "Avg Cost": st.column_config.NumberColumn(format="$%.2f"),
                "Allocation %": st.column_config.NumberColumn(format="%.1f%%"),
            }
        )

        # Allocation pie chart
        st.subheader("Allocation")
        fig = px.pie(
            df,
            values="Cost Basis",
            names="Ticker",
            title="Portfolio Allocation by Cost Basis"
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No holdings yet. Add a buy transaction to get started.")

with tab_add:
    st.subheader("Record Transaction")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Buy Stock**")
        with st.form("buy_form"):
            buy_ticker = st.text_input("Ticker", key="buy_ticker").upper()
            buy_quantity = st.number_input("Quantity", min_value=0.001, value=1.0, key="buy_qty")
            buy_price = st.number_input("Price per Share", min_value=0.01, value=100.0, key="buy_price")
            buy_fees = st.number_input("Fees", min_value=0.0, value=0.0, key="buy_fees")
            buy_date = st.date_input("Date", value=datetime.now(), key="buy_date")
            buy_notes = st.text_input("Notes (optional)", key="buy_notes")

            if st.form_submit_button("Record Buy", type="primary"):
                if buy_ticker and buy_quantity > 0:
                    try:
                        transaction = manager.add_buy(
                            ticker=buy_ticker,
                            quantity=buy_quantity,
                            price_per_share=buy_price,
                            transaction_date=datetime.combine(buy_date, datetime.min.time()),
                            fees=buy_fees,
                            notes=buy_notes if buy_notes else None
                        )
                        st.success(f"Recorded purchase of {buy_quantity} shares of {buy_ticker}")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.error("Please enter ticker and quantity")

    with col2:
        st.markdown("**Sell Stock**")
        with st.form("sell_form"):
            sell_ticker = st.text_input("Ticker", key="sell_ticker").upper()
            sell_quantity = st.number_input("Quantity", min_value=0.001, value=1.0, key="sell_qty")
            sell_price = st.number_input("Price per Share", min_value=0.01, value=100.0, key="sell_price")
            sell_fees = st.number_input("Fees", min_value=0.0, value=0.0, key="sell_fees")
            sell_date = st.date_input("Date", value=datetime.now(), key="sell_date")
            sell_notes = st.text_input("Notes (optional)", key="sell_notes")

            if st.form_submit_button("Record Sell", type="secondary"):
                if sell_ticker and sell_quantity > 0:
                    try:
                        transaction = manager.add_sell(
                            ticker=sell_ticker,
                            quantity=sell_quantity,
                            price_per_share=sell_price,
                            transaction_date=datetime.combine(sell_date, datetime.min.time()),
                            fees=sell_fees,
                            notes=sell_notes if sell_notes else None
                        )
                        gain_text = f"${transaction.realized_gain:,.2f}" if transaction.realized_gain else "N/A"
                        st.success(f"Recorded sale of {sell_quantity} shares of {sell_ticker}. Realized gain: {gain_text}")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.error("Please enter ticker and quantity")

with tab_history:
    st.subheader("Transaction History")

    col1, col2 = st.columns([3, 1])
    with col1:
        hist_ticker = st.text_input("Filter by Ticker", key="hist_ticker").upper()
    with col2:
        hist_limit = st.selectbox("Show", [20, 50, 100], key="hist_limit")

    history = manager.get_transaction_history(
        ticker=hist_ticker if hist_ticker else None,
        limit=hist_limit
    )

    if history:
        history_data = []
        for t in history:
            history_data.append({
                "Date": t.transaction_date.strftime("%Y-%m-%d") if t.transaction_date else "",
                "Type": t.transaction_type.upper(),
                "Ticker": t.ticker,
                "Shares": t.quantity,
                "Price": t.price_per_share,
                "Fees": t.fees,
                "Total Cost": t.total_cost if t.transaction_type == "buy" else 0,
                "Proceeds": t.total_proceeds if t.transaction_type == "sell" else 0,
                "Realized Gain": t.realized_gain,
                "Notes": t.notes or ""
            })

        df = pd.DataFrame(history_data)
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Price": st.column_config.NumberColumn(format="$%.2f"),
                "Fees": st.column_config.NumberColumn(format="$%.2f"),
                "Total Cost": st.column_config.NumberColumn(format="$%.2f"),
                "Proceeds": st.column_config.NumberColumn(format="$%.2f"),
                "Realized Gain": st.column_config.NumberColumn(format="$%.2f"),
            }
        )

        # Export option
        csv = df.to_csv(index=False)
        st.download_button(
            "Export to CSV",
            csv,
            "transactions.csv",
            "text/csv"
        )
    else:
        st.info("No transactions recorded yet.")

with tab_health:
    st.subheader("Portfolio Health")
    st.caption("Portfolio-weighted scores and zone allocation")

    if holdings:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Weighted Scores**")
            st.metric(
                "Weighted F-Score",
                f"{weighted_scores.weighted_fscore:.1f}/9",
                help="Portfolio-weighted average F-Score based on cost basis allocation"
            )
            st.metric(
                "Weighted Z-Score",
                f"{weighted_scores.weighted_zscore:.2f}",
                help="Portfolio-weighted average Z-Score"
            )
            st.caption(f"Holdings with scores: {weighted_scores.holdings_with_scores}")
            if weighted_scores.holdings_without_scores > 0:
                st.warning(f"{weighted_scores.holdings_without_scores} holdings missing scores")

        with col2:
            st.markdown("**Zone Allocation**")

            # Zone allocation chart
            zone_data = {
                "Zone": ["Safe", "Grey", "Distress"],
                "Allocation %": [
                    weighted_scores.safe_allocation,
                    weighted_scores.grey_allocation,
                    weighted_scores.distress_allocation
                ]
            }
            zone_df = pd.DataFrame(zone_data)

            fig = px.bar(
                zone_df,
                x="Zone",
                y="Allocation %",
                color="Zone",
                color_discrete_map={"Safe": "green", "Grey": "orange", "Distress": "red"}
            )
            fig.update_layout(showlegend=False, title="Allocation by Z-Score Zone")
            st.plotly_chart(fig, use_container_width=True)

        # Health assessment
        st.divider()
        st.markdown("**Health Assessment**")

        assessments = []

        # F-Score assessment
        if weighted_scores.weighted_fscore >= 7:
            assessments.append(("F-Score", "Strong financial health across portfolio", "green"))
        elif weighted_scores.weighted_fscore >= 5:
            assessments.append(("F-Score", "Moderate financial health - some holdings may need review", "orange"))
        else:
            assessments.append(("F-Score", "Weak financial health - consider reviewing underperformers", "red"))

        # Zone assessment
        if weighted_scores.distress_allocation > 20:
            assessments.append(("Z-Score", f"{weighted_scores.distress_allocation:.1f}% in Distress zone - high bankruptcy risk exposure", "red"))
        elif weighted_scores.grey_allocation > 40:
            assessments.append(("Z-Score", f"{weighted_scores.grey_allocation:.1f}% in Grey zone - moderate uncertainty", "orange"))
        elif weighted_scores.safe_allocation > 60:
            assessments.append(("Z-Score", f"{weighted_scores.safe_allocation:.1f}% in Safe zone - low bankruptcy risk", "green"))

        for metric, assessment, color in assessments:
            st.markdown(f":{color}[**{metric}**]: {assessment}")

        # Take snapshot button
        st.divider()
        if st.button("Take Portfolio Snapshot"):
            snapshot = manager.take_snapshot()
            st.success(f"Snapshot saved at {snapshot.snapshot_date}")

    else:
        st.info("Add holdings to see portfolio health metrics.")

# Sidebar quick stats
st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Stats**")
st.sidebar.metric("Cost Basis", f"${summary.total_cost_basis:,.0f}")
st.sidebar.metric("Positions", summary.position_count)
st.sidebar.metric("Cash Invested", f"${summary.cash_invested:,.0f}")
st.sidebar.metric("Cash Received", f"${summary.cash_received:,.0f}")
