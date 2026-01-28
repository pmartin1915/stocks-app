"""
Alerts Page - Configure and monitor watchlist alerts.

Set up F-Score and Z-Score threshold alerts for your watchlist stocks.
View alert history and acknowledge triggered alerts.
"""

from datetime import datetime

import streamlit as st

from asymmetric.core.alerts import AlertChecker
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock

st.title("Alerts")
st.caption("Monitor score changes and threshold breaches")

# Initialize checker
checker = AlertChecker()

# Tabs for different views
tab_config, tab_history, tab_check = st.tabs([
    "Configure Alerts",
    "Alert History",
    "Check Now"
])

with tab_config:
    st.subheader("Configure Alerts")

    # Add new alert form
    with st.form("add_alert_form"):
        st.markdown("**Create New Alert**")

        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Stock Ticker", placeholder="AAPL").upper()
        with col2:
            alert_type = st.selectbox(
                "Alert Type",
                ["fscore_above", "fscore_below", "zscore_above", "zscore_below", "zscore_zone"],
                format_func=lambda x: {
                    "fscore_above": "F-Score rises above",
                    "fscore_below": "F-Score falls below",
                    "zscore_above": "Z-Score rises above",
                    "zscore_below": "Z-Score falls below",
                    "zscore_zone": "Z-Score enters zone"
                }.get(x, x)
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            if alert_type == "zscore_zone":
                threshold_zone = st.selectbox("Zone", ["Safe", "Grey", "Distress"])
                threshold_value = None
            else:
                threshold_value = st.number_input(
                    "Threshold",
                    min_value=0.0,
                    max_value=9.0 if "fscore" in alert_type else 10.0,
                    value=5.0 if "fscore" in alert_type else 2.0,
                    step=0.5
                )
                threshold_zone = None
        with col4:
            severity = st.selectbox("Severity", ["info", "warning", "critical"])
        with col5:
            is_active = st.checkbox("Active", value=True)

        submitted = st.form_submit_button("Create Alert", type="primary")

        if submitted and ticker:
            try:
                alert = checker.create_alert(
                    ticker=ticker,
                    alert_type=alert_type,
                    threshold_value=threshold_value,
                    threshold_zone=threshold_zone,
                    severity=severity,
                    is_active=is_active
                )
                if alert:
                    st.success(f"Alert created for {ticker}")
                    st.rerun()
                else:
                    st.error(f"Failed to create alert. Make sure {ticker} exists in the database.")
            except Exception as e:
                st.error(f"Error creating alert: {e}")

    st.divider()

    # List existing alerts
    st.markdown("**Existing Alerts**")

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        filter_ticker = st.text_input("Filter by Ticker", key="filter_ticker").upper()
    with col2:
        filter_active = st.selectbox("Status", ["All", "Active Only", "Inactive Only"])

    active_only = filter_active == "Active Only" if filter_active != "All" else None
    if filter_active == "Inactive Only":
        active_only = False

    alerts = checker.get_alerts(
        ticker=filter_ticker if filter_ticker else None,
        active_only=active_only
    )

    if alerts:
        for alert in alerts:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

                with col1:
                    status_icon = "" if alert.is_active else " (inactive)"
                    triggered_icon = " [TRIGGERED]" if alert.is_triggered else ""
                    st.markdown(f"**{alert.ticker}**{status_icon}{triggered_icon}")

                with col2:
                    # Format alert condition
                    type_labels = {
                        "fscore_above": f"F-Score > {alert.threshold_value}",
                        "fscore_below": f"F-Score < {alert.threshold_value}",
                        "zscore_above": f"Z-Score > {alert.threshold_value}",
                        "zscore_below": f"Z-Score < {alert.threshold_value}",
                        "zscore_zone": f"Zone = {alert.threshold_zone}"
                    }
                    st.caption(type_labels.get(alert.alert_type, alert.alert_type))

                with col3:
                    severity_colors = {"info": "blue", "warning": "orange", "critical": "red"}
                    st.markdown(f":{severity_colors.get(alert.severity, 'grey')}[{alert.severity}]")

                with col4:
                    if st.button("Remove", key=f"remove_{alert.id}"):
                        checker.remove_alert(alert.id)
                        st.rerun()

                st.divider()
    else:
        st.info("No alerts configured. Create one above to get started.")

with tab_history:
    st.subheader("Alert History")
    st.caption("Record of triggered alerts")

    col1, col2 = st.columns(2)
    with col1:
        show_unack = st.checkbox("Show unacknowledged only", value=False)
    with col2:
        history_limit = st.selectbox("Show last", [10, 25, 50, 100], index=1)

    history = checker.get_alert_history(
        unacknowledged_only=show_unack,
        limit=history_limit
    )

    if history:
        for h in history:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    st.markdown(f"**{h.ticker}**")
                    st.caption(h.triggered_at.strftime("%Y-%m-%d %H:%M") if h.triggered_at else "Unknown")

                with col2:
                    st.caption(h.message or "Alert triggered")

                with col3:
                    if h.previous_value is not None and h.current_value is not None:
                        st.caption(f"Value: {h.previous_value:.2f} -> {h.current_value:.2f}")
                    elif h.previous_zone and h.current_zone:
                        st.caption(f"Zone: {h.previous_zone} -> {h.current_zone}")

                with col4:
                    if h.acknowledged:
                        st.caption("Acknowledged")
                        if h.acknowledged_by:
                            st.caption(f"by {h.acknowledged_by}")
                    else:
                        if st.button("Ack", key=f"ack_{h.id}"):
                            checker.acknowledge_alert(h.id, acknowledged_by="dashboard")
                            st.rerun()

                st.divider()
    else:
        st.info("No alert history yet. Alerts will appear here when triggered.")

with tab_check:
    st.subheader("Check Alerts Now")
    st.caption("Manually check all active alerts against current scores")

    col1, col2 = st.columns([3, 1])
    with col1:
        check_ticker = st.text_input(
            "Specific Ticker (optional)",
            placeholder="Leave blank to check all",
            key="check_specific_ticker"
        ).upper()
    with col2:
        st.write("")  # Spacer
        st.write("")
        check_button = st.button("Check Now", type="primary", use_container_width=True)

    if check_button:
        with st.spinner("Checking alerts..."):
            try:
                if check_ticker:
                    triggers = checker.check_ticker(check_ticker)
                else:
                    triggers = checker.check_all()

                if triggers:
                    st.warning(f"{len(triggers)} alert(s) triggered!")
                    for trigger in triggers:
                        with st.container():
                            st.markdown(f"**{trigger.ticker}**: {trigger.message}")
                            if trigger.previous_value is not None:
                                st.caption(f"Value changed: {trigger.previous_value:.2f} -> {trigger.current_value:.2f}")
                            st.divider()
                else:
                    st.success("No alerts triggered. All scores are within thresholds.")
            except Exception as e:
                st.error(f"Error checking alerts: {e}")

    st.divider()
    st.markdown("""
    **How Alert Checking Works**

    1. Fetches the latest score for each stock with active alerts
    2. Compares against configured thresholds
    3. Records any triggered alerts in history
    4. Updates the alert's triggered status

    *Tip: Schedule regular checks using the CLI: `asymmetric alerts check`*
    """)

# Sidebar summary
st.sidebar.markdown("---")
st.sidebar.markdown("**Alert Summary**")

try:
    all_alerts = checker.get_alerts()
    active_count = sum(1 for a in all_alerts if a.is_active)
    triggered_count = sum(1 for a in all_alerts if a.is_triggered)
    unack_history = checker.get_alert_history(unacknowledged_only=True, limit=100)

    st.sidebar.metric("Active Alerts", active_count)
    st.sidebar.metric("Currently Triggered", triggered_count)
    st.sidebar.metric("Unacknowledged", len(unack_history))
except Exception:
    st.sidebar.caption("Unable to load alert summary")
