"""Tests for TrendAnalyzer business logic."""

from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

from asymmetric.core.trends.analyzer import TrendAnalyzer
from asymmetric.db.database import get_session
from asymmetric.db.models import ScoreHistory, Stock


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def analyzer():
    """Create TrendAnalyzer instance."""
    return TrendAnalyzer()


@pytest.fixture
def stock_with_improving_history():
    """Create a stock with improving F-Score history."""
    current_year = datetime.now(UTC).year
    with get_session() as session:
        stock = Stock(ticker="IMPR", cik="0001111111", company_name="Improving Corp")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        # Add historical scores - improving over time (relative to current year)
        scores = [
            (current_year - 3, 4, 1.5, "Distress"),
            (current_year - 2, 5, 2.0, "Grey"),
            (current_year - 1, 6, 2.5, "Grey"),
            (current_year, 8, 3.5, "Safe"),
        ]
        for year, fscore, zscore, zone in scores:
            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=year,
                fiscal_period="FY",
                piotroski_score=fscore,
                piotroski_profitability=2,
                piotroski_leverage=1,
                piotroski_efficiency=1,
                altman_z_score=zscore,
                altman_zone=zone,
            )
            session.add(history)
        session.commit()

        return stock.ticker


@pytest.fixture
def stock_with_declining_history():
    """Create a stock with declining F-Score history."""
    current_year = datetime.now(UTC).year
    with get_session() as session:
        stock = Stock(ticker="DECL", cik="0002222222", company_name="Declining Corp")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        # Add historical scores - declining over time (relative to current year)
        scores = [
            (current_year - 3, 8, 4.0, "Safe"),
            (current_year - 2, 7, 3.5, "Safe"),
            (current_year - 1, 5, 2.5, "Grey"),
            (current_year, 3, 1.5, "Distress"),
        ]
        for year, fscore, zscore, zone in scores:
            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=year,
                fiscal_period="FY",
                piotroski_score=fscore,
                piotroski_profitability=1,
                piotroski_leverage=1,
                piotroski_efficiency=1,
                altman_z_score=zscore,
                altman_zone=zone,
            )
            session.add(history)
        session.commit()

        return stock.ticker


@pytest.fixture
def stock_with_consistent_history():
    """Create a stock with consistently high F-Score history."""
    current_year = datetime.now(UTC).year
    with get_session() as session:
        stock = Stock(ticker="CONS", cik="0003333333", company_name="Consistent Corp")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        # Add historical scores - consistently high (relative to current year)
        for i in range(8):
            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=current_year - i,
                fiscal_period="FY",
                piotroski_score=8,
                piotroski_profitability=3,
                piotroski_leverage=3,
                piotroski_efficiency=2,
                altman_z_score=4.0,
                altman_zone="Safe",
            )
            session.add(history)
        session.commit()

        return stock.ticker


@pytest.fixture
def stock_turnaround():
    """Create a stock that recovered from Distress."""
    current_year = datetime.now(UTC).year
    with get_session() as session:
        stock = Stock(ticker="TURN", cik="0004444444", company_name="Turnaround Corp")
        session.add(stock)
        session.commit()
        session.refresh(stock)

        # Add historical scores - was in distress, now recovering (relative to current year)
        scores = [
            (current_year - 3, 2, 1.2, "Distress"),
            (current_year - 2, 3, 1.5, "Distress"),
            (current_year - 1, 5, 2.0, "Grey"),
            (current_year, 6, 2.5, "Grey"),
        ]
        for year, fscore, zscore, zone in scores:
            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=year,
                fiscal_period="FY",
                piotroski_score=fscore,
                altman_z_score=zscore,
                altman_zone=zone,
            )
            session.add(history)
        session.commit()

        return stock.ticker


class TestGetScoreHistory:
    """Tests for score history retrieval."""

    def test_get_score_history_returns_records(self, analyzer, stock_with_improving_history):
        """Test getting score history returns records."""
        current_year = datetime.now(UTC).year
        history = analyzer.get_score_history(stock_with_improving_history, years=5)

        assert len(history) == 4
        # Newest first
        assert history[0].fiscal_year == current_year
        assert history[0].piotroski_score == 8

    def test_get_score_history_filters_by_years(self, analyzer, stock_with_improving_history):
        """Test history is filtered by year range."""
        current_year = datetime.now(UTC).year
        history = analyzer.get_score_history(stock_with_improving_history, years=2)

        # With years=2, min_year = current_year - 2, so we get current, current-1, current-2 (3 records)
        # The filter is >= min_year which is inclusive
        assert len(history) == 3
        for h in history:
            assert h.fiscal_year >= current_year - 2

    def test_get_score_history_no_data(self, analyzer):
        """Test getting history for non-existent stock."""
        history = analyzer.get_score_history("NOTEXIST", years=5)
        assert history == []


class TestCalculateTrend:
    """Tests for trend calculation."""

    def test_calculate_trend_improving(self, analyzer, stock_with_improving_history):
        """Test trend detection for improving stocks."""
        trend = analyzer.calculate_trend(stock_with_improving_history, periods=4)

        assert trend is not None
        assert trend.ticker == stock_with_improving_history
        assert trend.trend_direction == "improving"
        assert trend.fscore_change >= 2  # 8 - 4 = 4

    def test_calculate_trend_declining(self, analyzer, stock_with_declining_history):
        """Test trend detection for declining stocks."""
        trend = analyzer.calculate_trend(stock_with_declining_history, periods=4)

        assert trend is not None
        assert trend.trend_direction == "declining"
        assert trend.fscore_change <= -2  # 3 - 8 = -5

    def test_calculate_trend_stable(self, analyzer, stock_with_consistent_history):
        """Test trend detection for stable stocks."""
        trend = analyzer.calculate_trend(stock_with_consistent_history, periods=4)

        assert trend is not None
        assert trend.trend_direction == "stable"
        # Change should be small
        assert abs(trend.fscore_change) < 2

    def test_calculate_trend_zone_changed(self, analyzer, stock_with_improving_history):
        """Test zone change detection."""
        trend = analyzer.calculate_trend(stock_with_improving_history, periods=4)

        assert trend.zone_changed is True
        assert trend.previous_zone == "Distress"
        assert trend.current_zone == "Safe"

    def test_calculate_trend_insufficient_data(self, analyzer):
        """Test trend calculation with insufficient data."""
        # Create stock with only 1 data point
        with get_session() as session:
            stock = Stock(ticker="SOLO", cik="0005555555", company_name="Solo Corp")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=2023,
                fiscal_period="FY",
                piotroski_score=7,
                altman_z_score=3.0,
                altman_zone="Safe",
            )
            session.add(history)
            session.commit()

        trend = analyzer.calculate_trend("SOLO", periods=4)
        assert trend is None  # Insufficient data


class TestFindImproving:
    """Tests for finding improving stocks."""

    def test_find_improving(self, analyzer, stock_with_improving_history, stock_with_declining_history):
        """Test finding improving stocks."""
        results = analyzer.find_improving(min_improvement=2, periods=4)

        tickers = [r.ticker for r in results]
        assert stock_with_improving_history in tickers
        assert stock_with_declining_history not in tickers

    def test_find_improving_sorted_by_improvement(
        self, analyzer, stock_with_improving_history, stock_turnaround
    ):
        """Test improving stocks are sorted by improvement amount."""
        results = analyzer.find_improving(min_improvement=2, periods=4)

        if len(results) >= 2:
            # Should be sorted by fscore_change descending
            assert results[0].fscore_change >= results[1].fscore_change

    def test_find_improving_respects_limit(
        self, analyzer, stock_with_improving_history, stock_turnaround
    ):
        """Test limit parameter is respected."""
        results = analyzer.find_improving(min_improvement=1, periods=4, limit=1)

        assert len(results) <= 1


class TestFindDeclining:
    """Tests for finding declining stocks."""

    def test_find_declining(self, analyzer, stock_with_improving_history, stock_with_declining_history):
        """Test finding declining stocks."""
        results = analyzer.find_declining(min_decline=2, periods=4)

        tickers = [r.ticker for r in results]
        assert stock_with_declining_history in tickers
        assert stock_with_improving_history not in tickers


class TestFindConsistent:
    """Tests for finding consistent performers."""

    def test_find_consistent(self, analyzer, stock_with_consistent_history, stock_with_declining_history):
        """Test finding consistent performers."""
        results = analyzer.find_consistent(min_score=7, periods=4)

        tickers = [r.ticker for r in results]
        assert stock_with_consistent_history in tickers
        assert stock_with_declining_history not in tickers

    def test_find_consistent_requires_all_periods(self, analyzer, stock_with_improving_history):
        """Test that all periods must meet minimum score."""
        # IMPR had scores 4, 5, 6, 8 - only last one meets min_score=7
        results = analyzer.find_consistent(min_score=7, periods=4)

        tickers = [r.ticker for r in results]
        assert stock_with_improving_history not in tickers


class TestFindTurnaround:
    """Tests for finding turnaround candidates."""

    def test_find_turnaround(self, analyzer, stock_turnaround, stock_with_consistent_history):
        """Test finding turnaround candidates."""
        results = analyzer.find_turnaround()

        tickers = [r.ticker for r in results]
        assert stock_turnaround in tickers
        # CONS was never in distress
        assert stock_with_consistent_history not in tickers

    def test_find_turnaround_attributes(self, analyzer, stock_turnaround):
        """Test turnaround candidate has correct attributes."""
        results = analyzer.find_turnaround()

        turnaround = next((r for r in results if r.ticker == stock_turnaround), None)
        assert turnaround is not None
        assert turnaround.previous_zone == "Distress"
        assert turnaround.current_zone == "Grey"
        assert turnaround.zscore_improvement > 0


class TestSaveScoreToHistory:
    """Tests for saving scores to history."""

    def test_save_score_creates_record(self, analyzer):
        """Test saving score creates new history record."""
        current_year = datetime.now(UTC).year
        with get_session() as session:
            stock = Stock(ticker="NEW", cik="0006666666", company_name="New Corp")
            session.add(stock)
            session.commit()

        result = analyzer.save_score_to_history(
            ticker="NEW",
            fiscal_year=current_year,
            fiscal_period="FY",
            piotroski_score=7,
            altman_z_score=3.5,
            altman_zone="Safe",
        )

        assert result is not None
        assert result.piotroski_score == 7

        # Verify it was saved
        history = analyzer.get_score_history("NEW", years=1)
        assert len(history) == 1

    def test_save_score_upserts_existing(self, analyzer, stock_with_improving_history):
        """Test saving score updates existing record."""
        current_year = datetime.now(UTC).year
        # Update current year score (fixture creates one at current_year)
        result = analyzer.save_score_to_history(
            ticker=stock_with_improving_history,
            fiscal_year=current_year,
            fiscal_period="FY",
            piotroski_score=9,  # Changed from 8
            altman_z_score=4.0,
            altman_zone="Safe",
        )

        assert result.piotroski_score == 9

        # Verify update
        history = analyzer.get_score_history(stock_with_improving_history, years=5)
        current_year_record = next(h for h in history if h.fiscal_year == current_year)
        assert current_year_record.piotroski_score == 9


class TestTrendResultAttributes:
    """Tests for TrendResult dataclass attributes."""

    def test_trend_result_has_all_attributes(self, analyzer, stock_with_improving_history):
        """Test TrendResult contains all expected attributes."""
        trend = analyzer.calculate_trend(stock_with_improving_history, periods=4)

        assert hasattr(trend, "ticker")
        assert hasattr(trend, "company_name")
        assert hasattr(trend, "current_fscore")
        assert hasattr(trend, "previous_fscore")
        assert hasattr(trend, "fscore_change")
        assert hasattr(trend, "current_zscore")
        assert hasattr(trend, "previous_zscore")
        assert hasattr(trend, "zscore_change")
        assert hasattr(trend, "current_zone")
        assert hasattr(trend, "previous_zone")
        assert hasattr(trend, "zone_changed")
        assert hasattr(trend, "periods_analyzed")
        assert hasattr(trend, "trend_direction")
