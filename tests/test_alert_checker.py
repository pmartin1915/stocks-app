"""Tests for AlertChecker business logic."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import select

from asymmetric.core.alerts.checker import AlertChecker
from asymmetric.db.alert_models import Alert, AlertHistory
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock, StockScore


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def checker():
    """Create AlertChecker instance."""
    return AlertChecker()


@pytest.fixture
def stock_with_score():
    """Create a stock with a score for testing."""
    with get_session() as session:
        stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        score = StockScore(
            stock_id=stock.id,
            piotroski_score=7,
            altman_z_score=3.5,
            altman_zone="Safe",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score)
        session.commit()

        return stock.id, stock.ticker


@pytest.fixture
def stock_in_distress():
    """Create a stock in Distress zone."""
    with get_session() as session:
        stock = Stock(ticker="WEAK", cik="0001234567", company_name="Weak Corp")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        score = StockScore(
            stock_id=stock.id,
            piotroski_score=3,
            altman_z_score=1.5,
            altman_zone="Distress",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score)
        session.commit()

        return stock.id, stock.ticker


class TestCreateAlert:
    """Tests for alert creation."""

    def test_create_fscore_above_alert(self, checker, stock_with_score):
        """Test creating an F-Score above threshold alert."""
        stock_id, ticker = stock_with_score

        # Create alert (may return detached object)
        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=8.0,
            severity="info",
        )

        # Verify by querying database directly
        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.stock_id == stock_id)).first()
            assert db_alert is not None
            assert db_alert.stock_id == stock_id
            assert db_alert.alert_type == "fscore_above"
            assert db_alert.threshold_value == 8.0
            assert db_alert.severity == "info"
            assert db_alert.is_active is True

    def test_create_fscore_below_alert(self, checker, stock_with_score):
        """Test creating an F-Score below threshold alert."""
        stock_id, ticker = stock_with_score

        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_below",
            threshold_value=5.0,
            severity="warning",
        )

        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.stock_id == stock_id)).first()
            assert db_alert.alert_type == "fscore_below"
            assert db_alert.threshold_value == 5.0

    def test_create_zscore_zone_alert(self, checker, stock_with_score):
        """Test creating a Z-Score zone change alert."""
        stock_id, ticker = stock_with_score

        checker.create_alert(
            ticker=ticker,
            alert_type="zscore_zone",
            threshold_zone="Distress",
            severity="critical",
        )

        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.stock_id == stock_id)).first()
            assert db_alert.alert_type == "zscore_zone"
            assert db_alert.threshold_zone == "Distress"
            assert db_alert.severity == "critical"

    def test_create_alert_stock_not_found(self, checker):
        """Test creating alert for non-existent stock raises error."""
        with pytest.raises(ValueError, match="Stock not found"):
            checker.create_alert(
                ticker="NOTEXIST",
                alert_type="fscore_above",
                threshold_value=7.0,
            )

    def test_create_alert_invalid_type(self, checker, stock_with_score):
        """Test creating alert with invalid type raises error."""
        _, ticker = stock_with_score

        with pytest.raises(ValueError, match="Invalid alert type"):
            checker.create_alert(
                ticker=ticker,
                alert_type="invalid_type",
                threshold_value=7.0,
            )

    def test_create_alert_missing_threshold(self, checker, stock_with_score):
        """Test creating fscore alert without threshold raises error."""
        _, ticker = stock_with_score

        with pytest.raises(ValueError, match="threshold_value required"):
            checker.create_alert(
                ticker=ticker,
                alert_type="fscore_above",
                # Missing threshold_value
            )

    def test_create_zscore_zone_missing_zone(self, checker, stock_with_score):
        """Test creating zscore_zone alert without zone raises error."""
        _, ticker = stock_with_score

        with pytest.raises(ValueError, match="threshold_zone required"):
            checker.create_alert(
                ticker=ticker,
                alert_type="zscore_zone",
                # Missing threshold_zone
            )

    def test_create_alert_captures_baseline(self, checker, stock_with_score):
        """Test that alert captures current value as baseline."""
        _, ticker = stock_with_score

        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=8.0,
        )

        # Should capture current F-Score (7) as baseline
        alerts = checker.get_alerts(ticker=ticker)
        db_alert, _ = alerts[0]
        assert db_alert.last_checked_value == 7.0
        assert db_alert.last_checked_zone == "Safe"


class TestCheckAlert:
    """Tests for alert checking logic."""

    def test_check_fscore_above_triggers(self, checker, stock_with_score):
        """Test F-Score above alert triggers when threshold crossed."""
        stock_id, ticker = stock_with_score

        # Create alert with threshold below current score
        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=6.0,  # Current score is 7
            severity="info",
        )

        # Get the alert id via get_alerts
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Manually set last_checked_value below threshold to simulate crossing
        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.id == alert_id)).first()
            db_alert.last_checked_value = 5.0
            session.commit()

        # Check alerts
        triggers = checker.check_ticker(ticker)

        assert len(triggers) == 1
        assert triggers[0].ticker == ticker
        assert triggers[0].alert_type == "fscore_above"
        assert triggers[0].current_value == 7.0

    def test_check_fscore_above_no_trigger_already_above(self, checker, stock_with_score):
        """Test F-Score above alert doesn't trigger if already above."""
        _, ticker = stock_with_score

        # Create alert - current score (7) is already above threshold (6)
        # baseline will be set to 7
        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=6.0,
        )

        # Check alerts - should not trigger since it was already above
        triggers = checker.check_ticker(ticker)

        assert len(triggers) == 0

    def test_check_fscore_below_triggers(self, checker, stock_in_distress):
        """Test F-Score below alert triggers when threshold crossed."""
        stock_id, ticker = stock_in_distress

        # Create alert with threshold above current score (3)
        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_below",
            threshold_value=5.0,
            severity="warning",
        )

        # Get the alert id via get_alerts
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Manually set last_checked_value above threshold
        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.id == alert_id)).first()
            db_alert.last_checked_value = 6.0
            session.commit()

        triggers = checker.check_ticker(ticker)

        assert len(triggers) == 1
        assert triggers[0].alert_type == "fscore_below"

    def test_check_zscore_zone_triggers(self, checker, stock_in_distress):
        """Test Z-Score zone alert triggers on zone change."""
        stock_id, ticker = stock_in_distress

        # Create alert watching for Distress zone
        checker.create_alert(
            ticker=ticker,
            alert_type="zscore_zone",
            threshold_zone="Distress",
            severity="critical",
        )

        # Get the alert id via get_alerts
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Manually set previous zone to different value
        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.id == alert_id)).first()
            db_alert.last_checked_zone = "Grey"  # Was Grey, now Distress
            session.commit()

        triggers = checker.check_ticker(ticker)

        assert len(triggers) == 1
        assert triggers[0].alert_type == "zscore_zone"
        assert triggers[0].current_zone == "Distress"
        assert triggers[0].previous_zone == "Grey"

    def test_check_all_multiple_alerts(self, checker, stock_with_score, stock_in_distress):
        """Test check_all processes multiple alerts."""
        _, ticker1 = stock_with_score
        _, ticker2 = stock_in_distress

        # Create alerts for both stocks
        checker.create_alert(ticker=ticker1, alert_type="fscore_above", threshold_value=8.0)
        checker.create_alert(ticker=ticker2, alert_type="fscore_below", threshold_value=5.0)

        # Check all - neither should trigger initially (baselines set)
        triggers = checker.check_all()
        assert len(triggers) == 0


class TestAlertAcknowledge:
    """Tests for alert acknowledgment."""

    def test_acknowledge_alert_persists(self, checker, stock_with_score):
        """Test that acknowledging alert is persisted to database."""
        _, ticker = stock_with_score

        # Create alert and history
        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=6.0,
        )

        # Get alert id
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        with get_session() as session:
            history = AlertHistory(
                alert_id=alert_id,
                message="Test alert",
                previous_value=5.0,
                current_value=7.0,
            )
            session.add(history)
            session.commit()
            history_id = history.id

        # Acknowledge
        result = checker.acknowledge_alert(history_id, acknowledged_by="test_user")

        assert result is True

        # Verify persistence
        with get_session() as session:
            history = session.exec(select(AlertHistory).where(AlertHistory.id == history_id)).first()
            assert history.acknowledged is True
            assert history.acknowledged_by == "test_user"
            assert history.acknowledged_at is not None

    def test_acknowledge_not_found(self, checker):
        """Test acknowledging non-existent alert returns False."""
        result = checker.acknowledge_alert(99999)

        assert result is False


class TestAlertRemove:
    """Tests for alert removal."""

    def test_remove_alert_deletes(self, checker, stock_with_score):
        """Test removing alert deletes it from database."""
        _, ticker = stock_with_score

        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=8.0,
        )

        # Get alert id
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Remove
        result = checker.remove_alert(alert_id)

        assert result is True

        # Verify deleted
        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.id == alert_id)).first()
            assert db_alert is None

    def test_remove_alert_cascades_history(self, checker, stock_with_score):
        """Test removing alert also deletes associated history."""
        _, ticker = stock_with_score

        checker.create_alert(
            ticker=ticker,
            alert_type="fscore_above",
            threshold_value=8.0,
        )

        # Get alert id
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Add history
        with get_session() as session:
            history = AlertHistory(
                alert_id=alert_id,
                message="Test",
            )
            session.add(history)
            session.commit()
            history_id = history.id

        # Remove alert
        checker.remove_alert(alert_id)

        # Verify history also deleted
        with get_session() as session:
            history = session.exec(select(AlertHistory).where(AlertHistory.id == history_id)).first()
            assert history is None

    def test_remove_not_found(self, checker):
        """Test removing non-existent alert returns False."""
        result = checker.remove_alert(99999)

        assert result is False


class TestGetAlerts:
    """Tests for alert retrieval."""

    def test_get_alerts_returns_tuples(self, checker, stock_with_score):
        """Test get_alerts returns (Alert, ticker) tuples."""
        _, ticker = stock_with_score

        checker.create_alert(ticker=ticker, alert_type="fscore_above", threshold_value=8.0)

        alerts = checker.get_alerts()

        assert len(alerts) == 1
        alert, alert_ticker = alerts[0]
        assert isinstance(alert, Alert)
        assert alert_ticker == ticker

    def test_get_alerts_filter_by_ticker(self, checker, stock_with_score, stock_in_distress):
        """Test get_alerts filters by ticker."""
        _, ticker1 = stock_with_score
        _, ticker2 = stock_in_distress

        checker.create_alert(ticker=ticker1, alert_type="fscore_above", threshold_value=8.0)
        checker.create_alert(ticker=ticker2, alert_type="fscore_below", threshold_value=5.0)

        # Filter by first ticker
        alerts = checker.get_alerts(ticker=ticker1)

        assert len(alerts) == 1
        _, alert_ticker = alerts[0]
        assert alert_ticker == ticker1

    def test_get_alerts_active_only(self, checker, stock_with_score):
        """Test get_alerts filters active alerts."""
        _, ticker = stock_with_score

        checker.create_alert(ticker=ticker, alert_type="fscore_above", threshold_value=8.0)

        # Get alert id
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Deactivate
        with get_session() as session:
            db_alert = session.exec(select(Alert).where(Alert.id == alert_id)).first()
            db_alert.is_active = False
            session.commit()

        # Should not return inactive
        alerts = checker.get_alerts(active_only=True)
        assert len(alerts) == 0

        # Should return when active_only=False
        alerts = checker.get_alerts(active_only=False)
        assert len(alerts) == 1


class TestAlertHistory:
    """Tests for alert history retrieval."""

    def test_get_alert_history(self, checker, stock_with_score):
        """Test getting alert history."""
        _, ticker = stock_with_score

        checker.create_alert(ticker=ticker, alert_type="fscore_above", threshold_value=8.0)

        # Get alert id
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Add history
        with get_session() as session:
            history = AlertHistory(alert_id=alert_id, message="Test trigger")
            session.add(history)
            session.commit()

        # Get history
        results = checker.get_alert_history()

        assert len(results) == 1
        history, history_ticker, alert_type = results[0]
        assert history_ticker == ticker
        assert alert_type == "fscore_above"

    def test_get_unacknowledged_only(self, checker, stock_with_score):
        """Test filtering unacknowledged alerts."""
        _, ticker = stock_with_score

        checker.create_alert(ticker=ticker, alert_type="fscore_above", threshold_value=8.0)

        # Get alert id
        alerts = checker.get_alerts(ticker=ticker)
        alert_obj, _ = alerts[0]
        alert_id = alert_obj.id

        # Add acknowledged and unacknowledged history
        with get_session() as session:
            h1 = AlertHistory(alert_id=alert_id, message="Acked", acknowledged=True)
            h2 = AlertHistory(alert_id=alert_id, message="Not acked", acknowledged=False)
            session.add_all([h1, h2])
            session.commit()

        results = checker.get_alert_history(unacknowledged_only=True)

        assert len(results) == 1
        history, _, _ = results[0]
        assert history.message == "Not acked"
