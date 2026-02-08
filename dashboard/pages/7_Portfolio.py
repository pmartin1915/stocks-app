"""
Portfolio Page - Track holdings, transactions, and P&L.

Manage your investment portfolio with average cost basis tracking,
realized/unrealized P&L, and portfolio-weighted score analysis.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from asymmetric.core.portfolio import PortfolioManager
from dashboard.theme import get_plotly_theme
from dashboard.utils.session_state import init_page_state
from dashboard.utils.sidebar import render_full_sidebar
from dashboard.utils.performance_charts import (
    create_portfolio_value_chart,
    create_pnl_attribution_chart,
    create_return_percentage_chart,
    create_portfolio_health_chart,
    create_position_count_chart
)

# Initialize session state for this page
init_page_state("portfolio")

# Render sidebar (theme toggle, branding, navigation)
render_full_sidebar()

st.title("Portfolio")
st.caption("Track holdings, transactions, and portfolio health")

# Initialize manager
manager = PortfolioManager()

# Get summary data with error handling
# Fetch prices once and share across all calls to avoid redundant yfinance API requests
try:
    # Get tickers for price fetch
    _holdings_no_prices = manager.get_holdings(include_market_data=False)
    _tickers = [h.ticker for h in _holdings_no_prices]
    _prices = manager.refresh_market_prices(_tickers) if _tickers else {}

    # Pass pre-fetched prices to all methods (single API roundtrip)
    summary = manager.get_portfolio_summary(market_prices=_prices)
    holdings = manager.get_holdings(market_prices=_prices)
    weighted_scores = manager.get_weighted_scores(holdings=holdings)
except Exception as e:
    st.error(f"Error loading portfolio data: {e}")
    st.info("Please check your database connection and try refreshing the page.")
    st.info("If the problem persists, try running: `asymmetric db init`")
    st.stop()

# Top-level metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Total Market Value",
        f"${summary.total_market_value:,.2f}",
        help="Current market value of all holdings"
    )

with col2:
    # Show unrealized P&L with delta indicator
    unrealized_delta = f"${summary.unrealized_pnl:,.2f}" if summary.unrealized_pnl != 0 else None
    st.metric(
        "Unrealized P&L",
        f"{summary.unrealized_pnl_percent:+.2f}%",
        delta=unrealized_delta,
        help="Unrealized gains/losses on current holdings"
    )

with col3:
    st.metric(
        "Positions",
        summary.position_count,
        help="Number of holdings"
    )

with col4:
    st.metric(
        "Realized P&L (Total)",
        f"${summary.realized_pnl_total:,.2f}",
        help="Total realized gains/losses from sells"
    )

with col5:
    # Calculate total return %
    total_return_pct = 0.0
    if summary.cash_invested > 0:
        total_return_pct = ((summary.realized_pnl_total + summary.unrealized_pnl) / summary.cash_invested) * 100

    st.metric(
        "Total Return",
        f"{total_return_pct:+.2f}%",
        help="Combined realized + unrealized return"
    )

st.divider()

# Tabs for different views
tab_holdings, tab_performance, tab_historical, tab_add, tab_history, tab_health = st.tabs([
    "Holdings",
    "Performance",
    "Historical",
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
                ["value", "gainloss", "ticker", "fscore"],
                format_func=lambda x: {
                    "value": "Value",
                    "gainloss": "Gain/Loss %",
                    "ticker": "Ticker",
                    "fscore": "F-Score"
                }.get(x, x)
            )

        # Re-fetch with sort using cached prices (no redundant API call)
        try:
            holdings = manager.get_holdings(sort_by=sort_by, market_prices=_prices)
        except Exception as e:
            st.error(f"Error sorting holdings: {e}")
            # Fall back to original unsorted holdings
            pass

        # Holdings table
        holdings_data = []
        for h in holdings:
            # Format P&L with color
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
                "Z-Zone": h.zone or "N/A"
            })

        df = pd.DataFrame(holdings_data)

        # Style P&L coloring based on raw numeric value (not string parsing)
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
                "_pnl_pct": None,  # Hide helper column used for styling
            }
        )

        # Allocation pie chart (now using market value)
        st.subheader("Allocation")
        fig = px.pie(
            df,
            values="Market Value",
            names="Ticker",
            title="Portfolio Allocation by Market Value"
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(**get_plotly_theme())
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No holdings yet. Add a buy transaction to get started.")

with tab_performance:
    st.subheader("Performance Analysis")
    st.caption("Winners, losers, and performance metrics")

    if holdings:
        try:
            # Filter holdings with market data
            holdings_with_prices = [h for h in holdings if h.unrealized_pnl is not None]

            if holdings_with_prices:
                # Winners & Losers
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Top 5 Performers**")
                    winners = sorted(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or -999, reverse=True)[:5]

                    winners_data = []
                    for h in winners:
                        winners_data.append({
                            "Ticker": h.ticker,
                            "Cost Basis": f"${h.cost_basis_total:,.2f}",
                            "Market Value": f"${h.market_value:,.2f}",
                            "P&L ($)": f"${h.unrealized_pnl:,.2f}",
                            "P&L (%)": f"{h.unrealized_pnl_percent:+.1f}%",
                            "Days Held": h.days_held
                        })

                    winners_df = pd.DataFrame(winners_data)
                    st.dataframe(winners_df, use_container_width=True, hide_index=True)

                with col2:
                    st.markdown("**Bottom 5 Performers**")
                    losers = sorted(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or 999)[:5]

                    losers_data = []
                    for h in losers:
                        losers_data.append({
                            "Ticker": h.ticker,
                            "Cost Basis": f"${h.cost_basis_total:,.2f}",
                            "Market Value": f"${h.market_value:,.2f}",
                            "P&L ($)": f"${h.unrealized_pnl:,.2f}",
                            "P&L (%)": f"{h.unrealized_pnl_percent:+.1f}%",
                            "Days Held": h.days_held
                        })

                    losers_df = pd.DataFrame(losers_data)
                    st.dataframe(losers_df, use_container_width=True, hide_index=True)

                # Realized vs Unrealized P&L Chart
                st.divider()
                st.markdown("**Realized vs Unrealized P&L**")

                chart_data = []
                for h in holdings_with_prices:
                    chart_data.append({
                        "Ticker": h.ticker,
                        "P&L": h.unrealized_pnl,
                        "Type": "Unrealized"
                    })

                # Add realized P&L from transaction history (single query)
                realized_by_ticker = manager.get_realized_pnl_by_ticker()
                for h in holdings_with_prices:
                    realized_for_ticker = realized_by_ticker.get(h.ticker, 0.0)
                    if realized_for_ticker != 0:
                        chart_data.append({
                            "Ticker": h.ticker,
                            "P&L": realized_for_ticker,
                            "Type": "Realized"
                        })

                chart_df = pd.DataFrame(chart_data)

                fig = px.bar(
                    chart_df,
                    x="Ticker",
                    y="P&L",
                    color="Type",
                    barmode="group",
                    color_discrete_map={"Realized": "green", "Unrealized": "blue"},
                    title="Realized vs Unrealized P&L by Position"
                )
                fig.update_layout(**get_plotly_theme())
                fig.update_yaxis(title="P&L ($)")
                st.plotly_chart(fig, use_container_width=True)

                # Performance Summary
                st.divider()
                st.markdown("**Performance Summary**")

                # Calculate metrics
                winning_positions = [h for h in holdings_with_prices if h.unrealized_pnl and h.unrealized_pnl > 0]
                losing_positions = [h for h in holdings_with_prices if h.unrealized_pnl and h.unrealized_pnl < 0]

                avg_gain = sum(h.unrealized_pnl for h in winning_positions) / len(winning_positions) if winning_positions else 0
                avg_loss = sum(h.unrealized_pnl for h in losing_positions) / len(losing_positions) if losing_positions else 0
                win_rate = (len(winning_positions) / len(holdings_with_prices) * 100) if holdings_with_prices else 0

                best = max(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or -999)
                worst = min(holdings_with_prices, key=lambda x: x.unrealized_pnl_percent or 999)

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Win Rate",
                        f"{win_rate:.1f}%",
                        help=f"{len(winning_positions)} winners / {len(holdings_with_prices)} total"
                    )

                with col2:
                    st.metric(
                        "Avg Winning Position",
                        f"${avg_gain:,.2f}",
                        help="Average unrealized gain per winning position"
                    )

                with col3:
                    st.metric(
                        "Avg Losing Position",
                        f"${avg_loss:,.2f}",
                        help="Average unrealized loss per losing position"
                    )

                with col4:
                    st.metric(
                        "Best / Worst",
                        f"{best.ticker} / {worst.ticker}",
                        help=f"Best: {best.unrealized_pnl_percent:+.1f}% | Worst: {worst.unrealized_pnl_percent:+.1f}%"
                    )

            else:
                st.warning("Market prices unavailable. Cannot calculate performance metrics.")

        except Exception as e:
            st.error(f"Error calculating performance metrics: {e}")
            st.info("Some market data may be unavailable. Try refreshing the page.")

    else:
        st.info("Add holdings to see performance analysis.")

with tab_historical:
    st.subheader("Historical Performance")
    st.caption("Portfolio value, P&L, and health metrics over time")

    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        time_range = st.selectbox(
            "Time Range",
            options=["7D", "30D", "90D", "YTD", "1Y", "All Time"],
            index=2,  # Default to 90D
            key="historical_time_range"
        )

    with col3:
        if st.button("Refresh Data", key="refresh_snapshots"):
            st.rerun()

    # Calculate date range based on selection
    now = datetime.now()
    start_date = None

    if time_range == "7D":
        start_date = (now - timedelta(days=7)).replace(tzinfo=None)
    elif time_range == "30D":
        start_date = (now - timedelta(days=30)).replace(tzinfo=None)
    elif time_range == "90D":
        start_date = (now - timedelta(days=90)).replace(tzinfo=None)
    elif time_range == "YTD":
        start_date = datetime(now.year, 1, 1)
    elif time_range == "1Y":
        start_date = (now - timedelta(days=365)).replace(tzinfo=None)
    # "All Time" = no start_date filter

    # Fetch snapshots
    try:
        snapshots = manager.get_snapshots(start_date=start_date)

        # Show data availability info
        if snapshots:
            first_date = snapshots[0].snapshot_date
            last_date = snapshots[-1].snapshot_date
            with col2:
                st.info(f"Data: {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')} ({len(snapshots)} snapshots)")

        # Handle insufficient data case
        if not snapshots or len(snapshots) < 2:
            st.warning("Insufficient snapshot data for charting.")
            st.info("📸 Snapshots are created daily at 4:00 PM ET market close.")
            st.info("💡 Tip: You can manually trigger a snapshot in the 'Portfolio Health' tab.")

            if len(snapshots) == 1:
                st.info(f"You have 1 snapshot from {snapshots[0].snapshot_date.strftime('%Y-%m-%d')}. Come back tomorrow for historical charts!")
            else:
                st.info("Create your first snapshot to start tracking performance over time.")
        else:
            # Calculate performance statistics
            stats = manager.get_performance_stats(snapshots)

            if stats:
                # Performance Statistics Card
                st.divider()
                st.markdown("### Performance Summary")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Total Return",
                        f"{stats['total_return']:.2f}%",
                        delta=f"${stats['total_return_dollars']:,.2f}",
                        help="Percentage return from first to last snapshot"
                    )

                with col2:
                    st.metric(
                        "Current Drawdown",
                        f"{stats['current_drawdown']:.2f}%",
                        help="Distance from peak portfolio value"
                    )

                with col3:
                    st.metric(
                        "Max Drawdown",
                        f"{stats['max_drawdown']:.2f}%",
                        help="Worst historical decline from any peak"
                    )

                with col4:
                    st.metric(
                        "Days Tracked",
                        stats['days_tracked'],
                        help="Number of snapshots in selected range"
                    )

                # Second row: volatility, avg return, best/worst day
                col5, col6, col7, col8 = st.columns(4)

                with col5:
                    st.metric(
                        "Volatility",
                        f"{stats['volatility']:.2f}%",
                        help="Standard deviation of snapshot-to-snapshot returns"
                    )

                with col6:
                    st.metric(
                        "Avg Daily Return",
                        f"{stats['avg_daily_return']:+.3f}%",
                        help="Mean return between consecutive snapshots"
                    )

                with col7:
                    if stats.get('best_day'):
                        best_date = stats['best_day']['date']
                        best_label = best_date.strftime('%m/%d') if hasattr(best_date, 'strftime') else str(best_date)
                        st.metric(
                            "Best Day",
                            f"+{stats['best_day']['return']:.2f}%",
                            delta=best_label,
                            help="Largest single-snapshot gain"
                        )

                with col8:
                    if stats.get('worst_day'):
                        worst_date = stats['worst_day']['date']
                        worst_label = worst_date.strftime('%m/%d') if hasattr(worst_date, 'strftime') else str(worst_date)
                        st.metric(
                            "Worst Day",
                            f"{stats['worst_day']['return']:.2f}%",
                            delta=worst_label,
                            delta_color="inverse",
                            help="Largest single-snapshot loss"
                        )

                st.divider()

                # Convert snapshots to dicts for chart functions
                snapshot_dicts = [s.model_dump() for s in snapshots]

                # Chart 1: Portfolio Value Over Time
                st.markdown("### Portfolio Value Progression")
                try:
                    fig_value = create_portfolio_value_chart(snapshot_dicts)
                    st.plotly_chart(fig_value, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating value chart: {e}")

                # Chart 2: P&L Attribution
                st.markdown("### P&L Attribution")
                st.caption("Unrealized (current positions) vs Realized (closed positions)")
                try:
                    fig_pnl = create_pnl_attribution_chart(snapshot_dicts)
                    st.plotly_chart(fig_pnl, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating P&L chart: {e}")

                # Chart 3: Return Percentage
                st.markdown("### Cumulative Return %")
                try:
                    fig_return = create_return_percentage_chart(snapshot_dicts)
                    st.plotly_chart(fig_return, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating return chart: {e}")

                # Chart 4: Portfolio Health (Scores)
                st.markdown("### Portfolio Health Over Time")
                st.caption("Weighted F-Score and Z-Score based on position sizes")
                try:
                    fig_health = create_portfolio_health_chart(snapshot_dicts)
                    st.plotly_chart(fig_health, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating health chart: {e}")

                # Chart 5: Position Count
                st.markdown("### Diversification Trend")
                st.caption("Number of open positions over time")
                try:
                    fig_positions = create_position_count_chart(snapshot_dicts)
                    st.plotly_chart(fig_positions, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating position count chart: {e}")

    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        st.info("Try refreshing the page or check your database connection.")

with tab_add:
    st.subheader("Record Transaction")

    # Handle pending buy confirmation
    if st.session_state.pending_buy:
        pending = st.session_state.pending_buy
        total_cost = (pending["quantity"] * pending["price"]) + pending["fees"]

        st.info("Review and confirm your purchase:")
        with st.container():
            st.markdown("### Confirm Purchase")
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**Ticker:** {pending['ticker']}")
                st.markdown(f"**Quantity:** {pending['quantity']:,.3f} shares")
                st.markdown(f"**Price:** ${pending['price']:,.2f}/share")
            with col_info2:
                st.markdown(f"**Fees:** ${pending['fees']:,.2f}")
                st.markdown(f"**Date:** {pending['date']}")
                if pending["notes"]:
                    st.markdown(f"**Notes:** {pending['notes']}")

            st.divider()
            st.markdown(f"**Total Cost: ${total_cost:,.2f}**")

            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            with col_btn1:
                if st.button("Confirm Purchase", type="primary", use_container_width=True):
                    try:
                        transaction = manager.add_buy(
                            ticker=pending["ticker"],
                            quantity=pending["quantity"],
                            price_per_share=pending["price"],
                            transaction_date=datetime.combine(pending["date"], datetime.min.time(), tzinfo=UTC),
                            fees=pending["fees"],
                            notes=pending["notes"] if pending["notes"] else None
                        )
                        st.session_state.pending_buy = None
                        st.success(f"Recorded purchase of {pending['quantity']} shares of {pending['ticker']}")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            with col_btn2:
                if st.button("Cancel", type="secondary", use_container_width=True):
                    st.session_state.pending_buy = None
                    st.rerun()

    # Handle pending sell confirmation
    elif st.session_state.pending_sell:
        pending = st.session_state.pending_sell
        total_proceeds = (pending["quantity"] * pending["price"]) - pending["fees"]

        st.info("Review and confirm your sale:")
        with st.container():
            st.markdown("### Confirm Sale")
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**Ticker:** {pending['ticker']}")
                st.markdown(f"**Quantity:** {pending['quantity']:,.3f} shares")
                st.markdown(f"**Price:** ${pending['price']:,.2f}/share")
            with col_info2:
                st.markdown(f"**Fees:** ${pending['fees']:,.2f}")
                st.markdown(f"**Date:** {pending['date']}")
                if pending["notes"]:
                    st.markdown(f"**Notes:** {pending['notes']}")

            st.divider()
            st.markdown(f"**Total Proceeds: ${total_proceeds:,.2f}**")

            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            with col_btn1:
                if st.button("Confirm Sale", type="primary", use_container_width=True):
                    try:
                        transaction = manager.add_sell(
                            ticker=pending["ticker"],
                            quantity=pending["quantity"],
                            price_per_share=pending["price"],
                            transaction_date=datetime.combine(pending["date"], datetime.min.time(), tzinfo=UTC),
                            fees=pending["fees"],
                            notes=pending["notes"] if pending["notes"] else None
                        )
                        st.session_state.pending_sell = None
                        gain_text = f"${transaction.realized_gain:,.2f}" if transaction.realized_gain else "N/A"
                        st.success(f"Recorded sale of {pending['quantity']} shares of {pending['ticker']}. Realized gain: {gain_text}")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            with col_btn2:
                if st.button("Cancel", type="secondary", use_container_width=True, key="cancel_sell"):
                    st.session_state.pending_sell = None
                    st.rerun()

    # Show transaction forms (only when no pending confirmation)
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Buy Stock**")
            with st.form("buy_form"):
                buy_ticker = st.text_input("Ticker", key="buy_ticker").upper()
                buy_quantity = st.number_input("Quantity", min_value=0.001, value=1.0, key="buy_qty")
                buy_price = st.number_input("Price per Share", min_value=0.01, value=100.0, key="buy_price")
                buy_fees = st.number_input("Fees", min_value=0.0, value=0.0, key="buy_fees")
                buy_date = st.date_input("Date", value=datetime.now(UTC), key="buy_date")
                buy_notes = st.text_input("Notes (optional)", key="buy_notes")

                if st.form_submit_button("Review Buy", type="primary"):
                    if buy_ticker and buy_quantity > 0:
                        st.session_state.pending_buy = {
                            "ticker": buy_ticker,
                            "quantity": buy_quantity,
                            "price": buy_price,
                            "fees": buy_fees,
                            "date": buy_date,
                            "notes": buy_notes,
                        }
                        st.rerun()
                    else:
                        st.error("Please enter ticker and quantity")

        with col2:
            st.markdown("**Sell Stock**")
            with st.form("sell_form"):
                sell_ticker = st.text_input("Ticker", key="sell_ticker").upper()
                sell_quantity = st.number_input("Quantity", min_value=0.001, value=1.0, key="sell_qty")
                sell_price = st.number_input("Price per Share", min_value=0.01, value=100.0, key="sell_price")
                sell_fees = st.number_input("Fees", min_value=0.0, value=0.0, key="sell_fees")
                sell_date = st.date_input("Date", value=datetime.now(UTC), key="sell_date")
                sell_notes = st.text_input("Notes (optional)", key="sell_notes")

                if st.form_submit_button("Review Sell", type="secondary"):
                    if sell_ticker and sell_quantity > 0:
                        st.session_state.pending_sell = {
                            "ticker": sell_ticker,
                            "quantity": sell_quantity,
                            "price": sell_price,
                            "fees": sell_fees,
                            "date": sell_date,
                            "notes": sell_notes,
                        }
                        st.rerun()
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

        # Export option — sanitize text fields to prevent CSV formula injection
        export_df = df.copy()
        for col in ["Notes", "Ticker", "Type"]:
            if col in export_df.columns:
                export_df[col] = export_df[col].apply(
                    lambda v: "'" + str(v) if isinstance(v, str) and v and v[0] in "=+\-@" else v
                )
        csv = export_df.to_csv(index=False)
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
            fig.update_layout(showlegend=False, title="Allocation by Z-Score Zone", **get_plotly_theme())
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
            from asymmetric.core.portfolio.snapshot_service import get_last_snapshot_date
            from datetime import date

            last_date = get_last_snapshot_date()
            if last_date and last_date.date() == date.today():
                st.warning(f"Snapshot already exists for today ({last_date.strftime('%Y-%m-%d %H:%M')}). Only one snapshot per day is recommended.")
            else:
                snapshot = manager.take_snapshot()
                st.success(f"Snapshot saved at {snapshot.snapshot_date}")

    else:
        st.info("Add holdings to see portfolio health metrics.")

# Sidebar quick stats
st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Stats**")
st.sidebar.metric("Market Value", f"${summary.total_market_value:,.0f}")
st.sidebar.metric("Unrealized P&L", f"${summary.unrealized_pnl:+,.0f}")
st.sidebar.metric("Positions", summary.position_count)
st.sidebar.metric("Cash Invested", f"${summary.cash_invested:,.0f}")
st.sidebar.metric("Cash Received", f"${summary.cash_received:,.0f}")
