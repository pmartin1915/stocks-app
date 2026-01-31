"""Tests for historical score trend functionality."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import select

from asymmetric.db.database import get_session
from asymmetric.db.models import ScoreHistory, Stock


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


class TestScoreHistoryModel:
    """Tests for ScoreHistory database model."""

    def test_create_score_history(self):
        """Test creating a score history record."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=2024,
                fiscal_period="FY",
                piotroski_score=8,
                piotroski_profitability=4,
                piotroski_leverage=2,
                piotroski_efficiency=2,
                altman_z_score=3.5,
                altman_zone="Safe",
                data_source="live_api",
            )
            session.add(history)
            session.commit()
            session.refresh(history)

            assert history.id is not None
            assert history.piotroski_score == 8
            assert history.altman_z_score == 3.5
            assert history.altman_zone == "Safe"

    def test_score_history_unique_constraint(self):
        """Test that only one record per stock per fiscal period is allowed."""
        from sqlalchemy.exc import IntegrityError

        # First create stock and first history record
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)
            stock_id = stock.id

            history1 = ScoreHistory(
                stock_id=stock_id,
                fiscal_year=2024,
                fiscal_period="FY",
                piotroski_score=7,
                altman_z_score=3.0,
                altman_zone="Safe",
            )
            session.add(history1)
            session.commit()

        # Try to create duplicate in a separate session
        with pytest.raises(IntegrityError):
            with get_session() as session:
                history2 = ScoreHistory(
                    stock_id=stock_id,
                    fiscal_year=2024,
                    fiscal_period="FY",
                    piotroski_score=8,
                    altman_z_score=3.5,
                    altman_zone="Safe",
                )
                session.add(history2)
                session.commit()

    def test_score_history_multiple_periods(self):
        """Test creating multiple records for different fiscal periods."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            # Create records for different periods
            for year in [2022, 2023, 2024]:
                history = ScoreHistory(
                    stock_id=stock.id,
                    fiscal_year=year,
                    fiscal_period="FY",
                    piotroski_score=7 + (year - 2022),  # 7, 8, 9
                    altman_z_score=3.0 + (year - 2022) * 0.5,
                    altman_zone="Safe",
                )
                session.add(history)

            session.commit()

            # Query all records
            records = session.exec(
                select(ScoreHistory)
                .where(ScoreHistory.stock_id == stock.id)
                .order_by(ScoreHistory.fiscal_year)
            ).all()

            assert len(records) == 3
            assert records[0].piotroski_score == 7
            assert records[1].piotroski_score == 8
            assert records[2].piotroski_score == 9


class TestScoreHistoryComponents:
    """Tests for F-Score component tracking."""

    def test_profitability_component(self):
        """Test profitability component (0-4)."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=2024,
                fiscal_period="FY",
                piotroski_score=8,
                piotroski_profitability=4,
                altman_z_score=3.5,
                altman_zone="Safe",
            )
            session.add(history)
            session.commit()
            session.refresh(history)

            assert history.piotroski_profitability == 4

    def test_leverage_component(self):
        """Test leverage component (0-3)."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=2024,
                fiscal_period="FY",
                piotroski_score=8,
                piotroski_leverage=2,
                altman_z_score=3.5,
                altman_zone="Safe",
            )
            session.add(history)
            session.commit()
            session.refresh(history)

            assert history.piotroski_leverage == 2

    def test_efficiency_component(self):
        """Test efficiency component (0-2)."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            history = ScoreHistory(
                stock_id=stock.id,
                fiscal_year=2024,
                fiscal_period="FY",
                piotroski_score=8,
                piotroski_efficiency=2,
                altman_z_score=3.5,
                altman_zone="Safe",
            )
            session.add(history)
            session.commit()
            session.refresh(history)

            assert history.piotroski_efficiency == 2
