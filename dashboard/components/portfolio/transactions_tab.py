"""Transaction tabs — add transaction form and transaction history."""

from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from asymmetric.core.portfolio import PortfolioManager
from dashboard.utils.portfolio_cache import clear_portfolio_cache


def render_add_transaction_tab(manager: PortfolioManager) -> None:
    """Render the Add Transaction tab with buy/sell forms and confirmations.

    Args:
        manager: PortfolioManager instance.
    """
    st.subheader("Record Transaction")

    # Handle pending buy confirmation
    if st.session_state.pending_buy:
        _render_buy_confirmation(manager)
    # Handle pending sell confirmation
    elif st.session_state.pending_sell:
        _render_sell_confirmation(manager)
    # Show transaction forms
    else:
        _render_transaction_forms()


def _render_buy_confirmation(manager: PortfolioManager) -> None:
    """Render buy confirmation dialog."""
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
                    manager.add_buy(
                        ticker=pending["ticker"],
                        quantity=pending["quantity"],
                        price_per_share=pending["price"],
                        transaction_date=datetime.combine(pending["date"], datetime.min.time(), tzinfo=UTC),
                        fees=pending["fees"],
                        notes=pending["notes"] if pending["notes"] else None,
                    )
                    st.session_state.pending_buy = None
                    clear_portfolio_cache()
                    st.success(f"Recorded purchase of {pending['quantity']} shares of {pending['ticker']}")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        with col_btn2:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.pending_buy = None
                st.rerun()


def _render_sell_confirmation(manager: PortfolioManager) -> None:
    """Render sell confirmation dialog."""
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
                        notes=pending["notes"] if pending["notes"] else None,
                    )
                    st.session_state.pending_sell = None
                    clear_portfolio_cache()
                    gain_text = f"${transaction.realized_gain:,.2f}" if transaction.realized_gain else "N/A"
                    st.success(f"Recorded sale of {pending['quantity']} shares of {pending['ticker']}. Realized gain: {gain_text}")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        with col_btn2:
            if st.button("Cancel", type="secondary", use_container_width=True, key="cancel_sell"):
                st.session_state.pending_sell = None
                st.rerun()


def _render_transaction_forms() -> None:
    """Render buy and sell forms side by side."""
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


def render_transaction_history_tab(manager: PortfolioManager) -> None:
    """Render the Transaction History tab.

    Args:
        manager: PortfolioManager instance.
    """
    st.subheader("Transaction History")

    col1, col2 = st.columns([3, 1])
    with col1:
        hist_ticker = st.text_input("Filter by Ticker", key="hist_ticker").upper()
    with col2:
        hist_limit = st.selectbox("Show", [20, 50, 100], key="hist_limit")

    history = manager.get_transaction_history(
        ticker=hist_ticker if hist_ticker else None,
        limit=hist_limit,
    )

    if not history:
        st.info("No transactions recorded yet.")
        return

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
            "Notes": t.notes or "",
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
        },
    )

    # Export with CSV injection protection
    from dashboard.utils.csv_export import sanitize_csv_dataframe
    export_df = sanitize_csv_dataframe(df)
    csv = export_df.to_csv(index=False)
    st.download_button("Export to CSV", csv, "transactions.csv", "text/csv")
