"""
Alert checking and notification system.

Monitors watchlist stocks for score threshold changes:
- F-Score improvements (entry signals)
- F-Score declines (warnings)
- Z-Score zone changes (risk alerts)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select

from asymmetric.db.alert_models import Alert, AlertHistory
from asymmetric.db.database import get_session, get_stock_by_ticker
from asymmetric.db.models import Stock, StockScore


@dataclass
class AlertTrigger:
    """Information about a triggered alert."""

    alert_id: int
    ticker: str
    alert_type: str
    severity: str
    message: str
    previous_value: Optional[float]
    current_value: Optional[float]
    previous_zone: Optional[str]
    current_zone: Optional[str]
    triggered_at: datetime


class AlertChecker:
    """
    Checks alerts against current scores and triggers notifications.

    Evaluates alert conditions and records trigger history.
    """

    def check_all(self, tickers: Optional[list[str]] = None) -> list[AlertTrigger]:
        """
        Check all active alerts and return triggers.

        Args:
            tickers: Optional list of tickers to check (all if None)

        Returns:
            List of AlertTrigger for triggered alerts
        """
        triggers = []

        with get_session() as session:
            # Get all active alerts
            stmt = select(Alert).where(Alert.is_active == True)

            if tickers:
                stock_ids = []
                for ticker in tickers:
                    stock = get_stock_by_ticker(session, ticker)
                    if stock:
                        stock_ids.append(stock.id)
                stmt = stmt.where(Alert.stock_id.in_(stock_ids))

            alerts = session.exec(stmt).all()

            for alert in alerts:
                trigger = self._check_alert(session, alert)
                if trigger:
                    triggers.append(trigger)

        return triggers

    def check_ticker(self, ticker: str) -> list[AlertTrigger]:
        """
        Check alerts for a specific ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of AlertTrigger for the ticker
        """
        return self.check_all(tickers=[ticker])

    def _check_alert(self, session, alert: Alert) -> Optional[AlertTrigger]:
        """
        Evaluate a single alert against current data.

        Args:
            session: Database session
            alert: Alert to check

        Returns:
            AlertTrigger if triggered, None otherwise
        """
        # Get stock and latest score
        stock = session.exec(select(Stock).where(Stock.id == alert.stock_id)).first()
        if not stock:
            return None

        latest_score = session.exec(
            select(StockScore)
            .where(StockScore.stock_id == stock.id)
            .order_by(StockScore.calculated_at.desc())
        ).first()
        if not latest_score:
            return None

        # Evaluate based on alert type
        triggered = False
        message = ""
        previous_value = alert.last_checked_value
        current_value = None
        previous_zone = alert.last_checked_zone
        current_zone = latest_score.altman_zone

        if alert.alert_type == "fscore_above":
            current_value = float(latest_score.piotroski_score)
            if current_value >= alert.threshold_value:
                # Only trigger if it crossed the threshold (wasn't already above)
                if previous_value is None or previous_value < alert.threshold_value:
                    triggered = True
                    message = (
                        f"{stock.ticker} F-Score reached {int(current_value)} "
                        f"(threshold: {int(alert.threshold_value)})"
                    )

        elif alert.alert_type == "fscore_below":
            current_value = float(latest_score.piotroski_score)
            if current_value <= alert.threshold_value:
                if previous_value is None or previous_value > alert.threshold_value:
                    triggered = True
                    message = (
                        f"{stock.ticker} F-Score dropped to {int(current_value)} "
                        f"(threshold: {int(alert.threshold_value)})"
                    )

        elif alert.alert_type == "zscore_zone":
            current_value = latest_score.altman_z_score
            # Trigger if zone changed to the target zone
            if current_zone == alert.threshold_zone:
                if previous_zone and previous_zone != alert.threshold_zone:
                    triggered = True
                    message = (
                        f"{stock.ticker} Z-Score zone changed from "
                        f"{previous_zone} to {current_zone}"
                    )

        elif alert.alert_type == "zscore_above":
            current_value = latest_score.altman_z_score
            if current_value >= alert.threshold_value:
                if previous_value is None or previous_value < alert.threshold_value:
                    triggered = True
                    message = (
                        f"{stock.ticker} Z-Score reached {current_value:.2f} "
                        f"(threshold: {alert.threshold_value:.2f})"
                    )

        elif alert.alert_type == "zscore_below":
            current_value = latest_score.altman_z_score
            if current_value <= alert.threshold_value:
                if previous_value is None or previous_value > alert.threshold_value:
                    triggered = True
                    message = (
                        f"{stock.ticker} Z-Score dropped to {current_value:.2f} "
                        f"(threshold: {alert.threshold_value:.2f})"
                    )

        # Update last checked values
        alert.last_checked_value = current_value
        alert.last_checked_zone = current_zone
        alert.last_checked_at = datetime.now(timezone.utc)

        if triggered:
            alert.is_triggered = True
            alert.last_triggered_at = datetime.now(timezone.utc)
            alert.trigger_count += 1

            # Record to history
            history = AlertHistory(
                alert_id=alert.id,
                previous_value=previous_value,
                current_value=current_value,
                previous_zone=previous_zone,
                current_zone=current_zone,
                message=message,
            )
            session.add(history)
            session.add(alert)

            return AlertTrigger(
                alert_id=alert.id,
                ticker=stock.ticker,
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=message,
                previous_value=previous_value,
                current_value=current_value,
                previous_zone=previous_zone,
                current_zone=current_zone,
                triggered_at=datetime.now(timezone.utc),
            )

        session.add(alert)
        return None

    def create_alert(
        self,
        ticker: str,
        alert_type: str,
        threshold_value: Optional[float] = None,
        threshold_zone: Optional[str] = None,
        severity: str = "warning",
        message_template: Optional[str] = None,
    ) -> Alert:
        """
        Create a new alert for a stock.

        Args:
            ticker: Stock ticker symbol
            alert_type: Type of alert (fscore_above, fscore_below, zscore_zone, etc.)
            threshold_value: Numeric threshold for score alerts
            threshold_zone: Zone for zone change alerts
            severity: Alert severity (info, warning, critical)
            message_template: Optional custom message template

        Returns:
            Created Alert object

        Raises:
            ValueError: If stock not found or invalid parameters
        """
        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                raise ValueError(f"Stock not found: {ticker}")

            # Validate alert type
            valid_types = [
                "fscore_above",
                "fscore_below",
                "zscore_zone",
                "zscore_above",
                "zscore_below",
            ]
            if alert_type not in valid_types:
                raise ValueError(f"Invalid alert type: {alert_type}. Must be one of {valid_types}")

            # Validate threshold
            if alert_type in ["fscore_above", "fscore_below"] and threshold_value is None:
                raise ValueError(f"threshold_value required for {alert_type}")
            if alert_type == "zscore_zone" and threshold_zone is None:
                raise ValueError("threshold_zone required for zscore_zone alert")
            if alert_type in ["zscore_above", "zscore_below"] and threshold_value is None:
                raise ValueError(f"threshold_value required for {alert_type}")

            # Get current values for baseline
            latest_score = session.exec(
                select(StockScore)
                .where(StockScore.stock_id == stock.id)
                .order_by(StockScore.calculated_at.desc())
            ).first()

            alert = Alert(
                stock_id=stock.id,
                alert_type=alert_type,
                threshold_value=threshold_value,
                threshold_zone=threshold_zone,
                severity=severity,
                message_template=message_template,
                last_checked_value=(
                    float(latest_score.piotroski_score)
                    if latest_score and alert_type.startswith("fscore")
                    else latest_score.altman_z_score if latest_score else None
                ),
                last_checked_zone=latest_score.altman_zone if latest_score else None,
                last_checked_at=datetime.now(timezone.utc) if latest_score else None,
            )

            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert

    def get_alerts(
        self,
        ticker: Optional[str] = None,
        active_only: bool = True,
        triggered_only: bool = False,
    ) -> list[tuple[Alert, str]]:
        """
        Get alerts with optional filtering.

        Args:
            ticker: Optional ticker to filter by
            active_only: Only return active alerts
            triggered_only: Only return triggered alerts

        Returns:
            List of (Alert, ticker) tuples
        """
        with get_session() as session:
            stmt = select(Alert, Stock.ticker).join(Stock, Alert.stock_id == Stock.id)

            if ticker:
                stmt = stmt.where(Stock.ticker == ticker.upper())
            if active_only:
                stmt = stmt.where(Alert.is_active == True)
            if triggered_only:
                stmt = stmt.where(Alert.is_triggered == True)

            results = session.exec(stmt).all()

            # Refresh and expunge Alert objects to prevent DetachedInstanceError
            refreshed = []
            for alert, ticker_str in results:
                session.refresh(alert)
                session.expunge(alert)
                refreshed.append((alert, ticker_str))
            return refreshed

    def get_alert_history(
        self,
        ticker: Optional[str] = None,
        unacknowledged_only: bool = False,
        limit: int = 50,
    ) -> list[tuple[AlertHistory, str, str]]:
        """
        Get alert trigger history.

        Args:
            ticker: Optional ticker to filter by
            unacknowledged_only: Only return unacknowledged alerts
            limit: Maximum results

        Returns:
            List of (AlertHistory, ticker, alert_type) tuples
        """
        with get_session() as session:
            stmt = (
                select(AlertHistory, Stock.ticker, Alert.alert_type)
                .join(Alert, AlertHistory.alert_id == Alert.id)
                .join(Stock, Alert.stock_id == Stock.id)
            )

            if ticker:
                stmt = stmt.where(Stock.ticker == ticker.upper())
            if unacknowledged_only:
                stmt = stmt.where(AlertHistory.acknowledged == False)

            results = session.exec(
                stmt.order_by(AlertHistory.triggered_at.desc()).limit(limit)
            ).all()

            # Refresh and expunge AlertHistory objects to prevent DetachedInstanceError
            refreshed = []
            for history, ticker_str, alert_type in results:
                session.refresh(history)
                session.expunge(history)
                refreshed.append((history, ticker_str, alert_type))
            return refreshed

    def acknowledge_alert(self, alert_history_id: int, acknowledged_by: str = "user") -> bool:
        """
        Acknowledge an alert history record.

        Args:
            alert_history_id: ID of the AlertHistory record
            acknowledged_by: Who acknowledged (user, system, etc.)

        Returns:
            True if acknowledged, False if not found
        """
        with get_session() as session:
            history = session.exec(
                select(AlertHistory).where(AlertHistory.id == alert_history_id)
            ).first()
            if not history:
                return False

            history.acknowledged = True
            history.acknowledged_at = datetime.now(timezone.utc)
            history.acknowledged_by = acknowledged_by
            session.commit()
        return True

    def remove_alert(self, alert_id: int) -> bool:
        """
        Remove an alert configuration.

        Args:
            alert_id: ID of the Alert to remove

        Returns:
            True if removed, False if not found
        """
        with get_session() as session:
            alert = session.exec(select(Alert).where(Alert.id == alert_id)).first()
            if not alert:
                return False

            # Delete associated history
            histories = session.exec(
                select(AlertHistory).where(AlertHistory.alert_id == alert_id)
            ).all()
            for h in histories:
                session.delete(h)
            session.delete(alert)
            session.commit()
        return True

    def get_triggered_alerts(self) -> list[tuple[AlertHistory, str, str]]:
        """
        Get all currently triggered, unacknowledged alerts.

        Returns:
            List of (AlertHistory, ticker, alert_type) tuples
        """
        return self.get_alert_history(unacknowledged_only=True)
