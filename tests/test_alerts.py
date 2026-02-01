"""Tests for alert management functionality."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from asymmetric.db.alert_models import Alert, AlertHistory
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


class TestAlertModels:
    """Tests for alert database models."""

    def test_create_fscore_alert(self):
        """Test creating an F-Score threshold alert."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            alert = Alert(
                stock_id=stock.id,
                alert_type="fscore_above",
                threshold_value=7.0,
                severity="warning",
                is_active=True,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            assert alert.id is not None
            assert alert.alert_type == "fscore_above"
            assert alert.threshold_value == 7.0
            assert alert.is_active is True
            assert alert.is_triggered is False

    def test_create_zscore_zone_alert(self):
        """Test creating a Z-Score zone change alert."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            alert = Alert(
                stock_id=stock.id,
                alert_type="zscore_zone",
                threshold_zone="Distress",
                severity="critical",
                is_active=True,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            assert alert.id is not None
            assert alert.alert_type == "zscore_zone"
            assert alert.threshold_zone == "Distress"
            assert alert.severity == "critical"

    def test_create_alert_history(self):
        """Test creating an alert history record."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            alert = Alert(
                stock_id=stock.id,
                alert_type="fscore_below",
                threshold_value=5.0,
                severity="warning",
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            history = AlertHistory(
                alert_id=alert.id,
                previous_value=6.0,
                current_value=4.0,
                message="AAPL F-Score dropped to 4 (threshold: 5)",
            )
            session.add(history)
            session.commit()
            session.refresh(history)

            assert history.id is not None
            assert history.previous_value == 6.0
            assert history.current_value == 4.0
            assert history.acknowledged is False


class TestAlertSeverity:
    """Tests for alert severity levels."""

    @pytest.mark.parametrize("severity", ["info", "warning", "critical"])
    def test_valid_severities(self, severity):
        """Test that valid severity levels are accepted."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            alert = Alert(
                stock_id=stock.id,
                alert_type="fscore_above",
                threshold_value=7.0,
                severity=severity,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            assert alert.severity == severity


class TestAlertAcknowledgment:
    """Tests for alert acknowledgment workflow."""

    def test_acknowledge_alert(self):
        """Test acknowledging an alert history record."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            alert = Alert(
                stock_id=stock.id,
                alert_type="fscore_below",
                threshold_value=5.0,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)

            history = AlertHistory(
                alert_id=alert.id,
                message="Test alert",
            )
            session.add(history)
            session.commit()
            session.refresh(history)

            # Acknowledge
            history.acknowledged = True
            history.acknowledged_at = datetime.now(UTC)
            history.acknowledged_by = "test_user"
            session.add(history)
            session.commit()
            session.refresh(history)

            assert history.acknowledged is True
            assert history.acknowledged_at is not None
            assert history.acknowledged_by == "test_user"
