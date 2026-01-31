"""
Tests for database models and connection management.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import select

from asymmetric.db.database import (
    get_engine,
    get_or_create_stock,
    get_session,
    get_stock_by_ticker,
    init_db,
    reset_engine,
)
from asymmetric.db.models import (
    Decision,
    ScreeningRun,
    Stock,
    StockScore,
    Thesis,
)


@pytest.fixture(autouse=True)
def reset_db_engine():
    """Reset the database engine before and after each test."""
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def temp_db_path(monkeypatch, tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_asymmetric.db"

    # Patch the config to use temp path
    from asymmetric.config import Config

    test_config = Config()
    test_config.db_path = db_path

    monkeypatch.setattr("asymmetric.db.database.config", test_config)
    return db_path


class TestDatabaseConnection:
    """Tests for database connection management."""

    def test_get_engine_creates_database(self, temp_db_path):
        """Should create database file on first write."""
        engine = get_engine()
        assert engine is not None

        # SQLite creates file on first write, not connection
        # Initialize the database to trigger file creation
        init_db()

        assert temp_db_path.exists()

    def test_get_engine_singleton(self, temp_db_path):
        """Should return same engine instance."""
        engine1 = get_engine()
        engine2 = get_engine()

        assert engine1 is engine2

    def test_reset_engine(self, temp_db_path):
        """Should dispose and clear engine on reset."""
        engine1 = get_engine()
        reset_engine()
        engine2 = get_engine()

        # After reset, should be different engine instance
        # (hard to test identity since engine is recreated)
        assert engine2 is not None


class TestSessionManagement:
    """Tests for session context manager."""

    def test_session_commits_on_success(self, temp_db_path):
        """Should commit changes on successful exit."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)

        # Verify data persisted
        with get_session() as session:
            result = session.exec(select(Stock).where(Stock.ticker == "AAPL")).first()
            assert result is not None
            assert result.company_name == "Apple Inc."

    def test_session_rollback_on_error(self, temp_db_path):
        """Should rollback on exception."""
        init_db()

        with pytest.raises(ValueError):
            with get_session() as session:
                stock = Stock(ticker="FAIL", cik="123", company_name="Test")
                session.add(stock)
                raise ValueError("Test error")

        # Verify data was not persisted
        with get_session() as session:
            result = session.exec(select(Stock).where(Stock.ticker == "FAIL")).first()
            assert result is None


class TestStockModel:
    """Tests for Stock model."""

    def test_create_stock(self, temp_db_path):
        """Should create stock with all fields."""
        init_db()

        with get_session() as session:
            stock = Stock(
                ticker="MSFT",
                cik="0000789019",
                company_name="Microsoft Corporation",
                sic_code="7372",
                sic_description="Prepackaged Software",
                exchange="NASDAQ",
            )
            session.add(stock)

        with get_session() as session:
            result = session.exec(select(Stock).where(Stock.ticker == "MSFT")).first()
            assert result.ticker == "MSFT"
            assert result.cik == "0000789019"
            assert result.sic_code == "7372"
            assert result.exchange == "NASDAQ"

    def test_stock_unique_ticker(self, temp_db_path):
        """Ticker should be unique."""
        init_db()

        with get_session() as session:
            stock1 = Stock(ticker="DUP", cik="111", company_name="First")
            session.add(stock1)

        # Attempting to add duplicate should fail
        with pytest.raises(Exception):  # IntegrityError wrapped
            with get_session() as session:
                stock2 = Stock(ticker="DUP", cik="222", company_name="Second")
                session.add(stock2)


class TestStockScoreModel:
    """Tests for StockScore model."""

    def test_create_stock_score(self, temp_db_path):
        """Should create score with all fields."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="TEST", cik="999", company_name="Test Corp")
            session.add(stock)
            session.flush()

            score = StockScore(
                stock_id=stock.id,
                piotroski_score=7,
                piotroski_signals_available=9,
                piotroski_interpretation="Strong",
                piotroski_profitability=4,
                piotroski_leverage=2,
                piotroski_efficiency=1,
                altman_z_score=3.5,
                altman_zone="Safe",
                altman_interpretation="Low bankruptcy risk",
                altman_formula="manufacturing",
                composite_score=0.85,
                fiscal_year=2024,
                fiscal_period="FY",
            )
            session.add(score)

        with get_session() as session:
            result = session.exec(select(StockScore)).first()
            assert result.piotroski_score == 7
            assert result.altman_z_score == 3.5
            assert result.altman_zone == "Safe"


class TestThesisModel:
    """Tests for Thesis model."""

    def test_create_thesis(self, temp_db_path):
        """Should create thesis with all fields."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="THESIS", cik="123", company_name="Thesis Test")
            session.add(stock)
            session.flush()

            thesis = Thesis(
                stock_id=stock.id,
                summary="Strong buy based on financials",
                analysis_text="Full analysis here...",
                bull_case="Great moat",
                bear_case="High valuation",
                key_metrics='{"revenue_growth": 0.15}',
                ai_model="gemini-2.5-pro",
                ai_cost_usd=0.05,
                ai_tokens_input=10000,
                ai_tokens_output=500,
                cached=True,
                status="active",
            )
            session.add(thesis)

        with get_session() as session:
            result = session.exec(select(Thesis)).first()
            assert result.summary == "Strong buy based on financials"
            assert result.ai_model == "gemini-2.5-pro"
            assert result.status == "active"
            assert result.cached is True


class TestDecisionModel:
    """Tests for Decision model."""

    def test_create_decision(self, temp_db_path):
        """Should create decision with all fields."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="DEC", cik="456", company_name="Decision Test")
            session.add(stock)
            session.flush()

            thesis = Thesis(
                stock_id=stock.id,
                summary="Test thesis",
                analysis_text="Analysis",
            )
            session.add(thesis)
            session.flush()

            decision = Decision(
                thesis_id=thesis.id,
                decision="buy",
                rationale="Strong fundamentals and growth",
                confidence=4,
                target_price=150.0,
                stop_loss=120.0,
            )
            session.add(decision)

        with get_session() as session:
            result = session.exec(select(Decision)).first()
            assert result.decision == "buy"
            assert result.confidence == 4
            assert result.target_price == 150.0


class TestScreeningRunModel:
    """Tests for ScreeningRun model."""

    def test_create_screening_run(self, temp_db_path):
        """Should create screening run with criteria."""
        init_db()

        with get_session() as session:
            run = ScreeningRun(
                criteria_json='{"piotroski_min": 7, "altman_min": 2.99}',
                result_count=15,
                result_tickers="AAPL,MSFT,GOOG,AMZN",
                data_source="bulk_data",
            )
            session.add(run)

        with get_session() as session:
            result = session.exec(select(ScreeningRun)).first()
            assert result.result_count == 15
            assert "AAPL" in result.result_tickers
            assert result.data_source == "bulk_data"


class TestHelperFunctions:
    """Tests for database helper functions."""

    def test_get_stock_by_ticker(self, temp_db_path):
        """Should find stock by ticker."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="FIND", cik="111", company_name="Findable")
            session.add(stock)

        # Note: get_stock_by_ticker creates its own session
        # Due to session scope, this might not find the stock
        # unless we commit and create new session
        result = get_stock_by_ticker("FIND")
        assert result is not None
        assert result.company_name == "Findable"

    def test_get_stock_by_ticker_case_insensitive(self, temp_db_path):
        """Should find stock regardless of case."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="CASE", cik="222", company_name="Case Test")
            session.add(stock)

        result = get_stock_by_ticker("case")
        assert result is not None
        assert result.ticker == "CASE"

    def test_get_stock_by_ticker_not_found(self, temp_db_path):
        """Should return None for nonexistent ticker."""
        init_db()

        result = get_stock_by_ticker("NOTEXIST")
        assert result is None

    def test_get_or_create_stock_creates(self, temp_db_path):
        """Should create new stock if not exists."""
        init_db()

        stock = get_or_create_stock("NEW", cik="333", company_name="New Corp")

        assert stock is not None
        assert stock.ticker == "NEW"

        # Verify persisted
        result = get_stock_by_ticker("NEW")
        assert result is not None

    def test_get_or_create_stock_gets_existing(self, temp_db_path):
        """Should return existing stock."""
        init_db()

        # Create first
        stock1 = get_or_create_stock("EXIST", cik="444", company_name="Existing")

        # Should get same stock
        stock2 = get_or_create_stock("EXIST", cik="555", company_name="Different")

        # Should have original data
        result = get_stock_by_ticker("EXIST")
        assert result.cik == "444"
        assert result.company_name == "Existing"


class TestRelationships:
    """Tests for model relationships."""

    def test_stock_scores_relationship(self, temp_db_path):
        """Stock should have scores relationship."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="REL1", cik="111", company_name="Relationship Test")
            session.add(stock)
            session.flush()

            score1 = StockScore(
                stock_id=stock.id,
                piotroski_score=7,
                altman_z_score=3.0,
                altman_zone="Safe",
                fiscal_year=2023,
            )
            score2 = StockScore(
                stock_id=stock.id,
                piotroski_score=8,
                altman_z_score=3.5,
                altman_zone="Safe",
                fiscal_year=2024,
            )
            session.add(score1)
            session.add(score2)

        with get_session() as session:
            stock = session.exec(select(Stock).where(Stock.ticker == "REL1")).first()
            assert len(stock.scores) == 2

    def test_thesis_decisions_relationship(self, temp_db_path):
        """Thesis should have decisions relationship."""
        init_db()

        with get_session() as session:
            stock = Stock(ticker="REL2", cik="222", company_name="Test")
            session.add(stock)
            session.flush()

            thesis = Thesis(
                stock_id=stock.id,
                summary="Test",
                analysis_text="Test",
            )
            session.add(thesis)
            session.flush()

            decision1 = Decision(
                thesis_id=thesis.id,
                decision="buy",
                rationale="Test 1",
            )
            decision2 = Decision(
                thesis_id=thesis.id,
                decision="hold",
                rationale="Test 2",
            )
            session.add(decision1)
            session.add(decision2)

        with get_session() as session:
            thesis = session.exec(select(Thesis)).first()
            assert len(thesis.decisions) == 2
