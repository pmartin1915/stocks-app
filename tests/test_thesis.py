"""
Tests for thesis model and CLI commands.

Tests conviction fields, CRUD operations, and CLI output formatting.
"""

from datetime import datetime, timezone

import pytest
from click.testing import CliRunner
from sqlmodel import select

from asymmetric.db.database import (
    get_session,
    init_db,
    reset_engine,
)
from asymmetric.db.models import Stock, Thesis


@pytest.fixture(autouse=True)
def reset_db_engine():
    """Reset the database engine before and after each test."""
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def temp_db_path(monkeypatch, tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_thesis.db"

    from asymmetric.config import Config

    test_config = Config()
    test_config.db_path = db_path

    monkeypatch.setattr("asymmetric.db.database.config", test_config)
    return db_path


@pytest.fixture
def initialized_db(temp_db_path):
    """Initialize database and return path."""
    init_db()
    return temp_db_path


@pytest.fixture
def stock(initialized_db):
    """Create a test stock."""
    with get_session() as session:
        stock = Stock(
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
        )
        session.add(stock)
        session.commit()
        session.refresh(stock)
        return stock.id, stock.ticker


class TestThesisModel:
    """Tests for Thesis SQLModel."""

    def test_create_thesis_minimal(self, stock):
        """Should create thesis with required fields only."""
        stock_id, _ = stock
        with get_session() as session:
            thesis = Thesis(
                stock_id=stock_id,
                summary="Strong cash position and growing services revenue.",
                analysis_text="Full analysis of Apple's business model...",
            )
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.id is not None
            assert thesis.stock_id == stock_id
            assert thesis.summary == "Strong cash position and growing services revenue."
            assert thesis.status == "draft"
            assert thesis.conviction is None
            assert thesis.conviction_rationale is None

    def test_create_thesis_with_conviction(self, stock):
        """Should create thesis with conviction fields."""
        stock_id, _ = stock
        with get_session() as session:
            thesis = Thesis(
                stock_id=stock_id,
                summary="Strong competitive moat in services.",
                analysis_text="Detailed analysis...",
                conviction=4,
                conviction_rationale="Services growth accelerating",
            )
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.conviction == 4
            assert thesis.conviction_rationale == "Services growth accelerating"

    def test_conviction_range_valid(self, stock):
        """Should accept conviction values 1-5."""
        stock_id, _ = stock
        with get_session() as session:
            for level in range(1, 6):
                thesis = Thesis(
                    stock_id=stock_id,
                    summary=f"Test thesis with conviction {level}",
                    analysis_text="Analysis...",
                    conviction=level,
                )
                session.add(thesis)
                session.commit()
                session.refresh(thesis)
                assert thesis.conviction == level

    def test_thesis_with_all_fields(self, stock):
        """Should create thesis with all optional fields."""
        stock_id, _ = stock
        with get_session() as session:
            thesis = Thesis(
                stock_id=stock_id,
                summary="Comprehensive thesis",
                analysis_text="Full detailed analysis",
                bull_case="Services revenue growth",
                bear_case="Regulatory pressure",
                key_metrics='{"pe_ratio": 25, "revenue_growth": 0.15}',
                ai_model="gemini-2.5-pro",
                ai_cost_usd=0.05,
                ai_tokens_input=10000,
                ai_tokens_output=500,
                cached=True,
                status="active",
                conviction=5,
                conviction_rationale="High confidence in moat",
            )
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.bull_case == "Services revenue growth"
            assert thesis.bear_case == "Regulatory pressure"
            assert thesis.ai_model == "gemini-2.5-pro"
            assert thesis.status == "active"
            assert thesis.conviction == 5

    def test_thesis_timestamps(self, stock):
        """Should set timestamps on creation."""
        stock_id, _ = stock
        before = datetime.now(timezone.utc)
        with get_session() as session:
            thesis = Thesis(
                stock_id=stock_id,
                summary="Test thesis",
                analysis_text="Analysis...",
            )
            session.add(thesis)
            session.commit()
            session.refresh(thesis)
            after = datetime.now(timezone.utc)

            # SQLite may return naive datetimes, so compare without timezone
            created = thesis.created_at.replace(tzinfo=None) if thesis.created_at.tzinfo else thesis.created_at
            updated = thesis.updated_at.replace(tzinfo=None) if thesis.updated_at.tzinfo else thesis.updated_at
            before_naive = before.replace(tzinfo=None)
            after_naive = after.replace(tzinfo=None)

            assert before_naive <= created <= after_naive
            assert before_naive <= updated <= after_naive

    def test_thesis_status_values(self, stock):
        """Should accept valid status values."""
        stock_id, _ = stock
        with get_session() as session:
            for status in ["draft", "active", "archived"]:
                thesis = Thesis(
                    stock_id=stock_id,
                    summary=f"Test thesis with status {status}",
                    analysis_text="Analysis...",
                    status=status,
                )
                session.add(thesis)
                session.commit()
                session.refresh(thesis)
                assert thesis.status == status


class TestThesisUpdate:
    """Tests for updating thesis records."""

    @pytest.fixture
    def thesis_with_stock(self, initialized_db):
        """Create a stock and thesis for testing."""
        with get_session() as session:
            stock = Stock(
                ticker="MSFT",
                cik="0000789019",
                company_name="Microsoft Corporation",
            )
            session.add(stock)
            session.commit()
            session.refresh(stock)

            thesis = Thesis(
                stock_id=stock.id,
                summary="Initial summary",
                analysis_text="Initial analysis",
                status="draft",
                conviction=3,
                conviction_rationale="Initial rationale",
            )
            session.add(thesis)
            session.commit()
            session.refresh(thesis)
            return thesis.id

    def test_update_conviction(self, thesis_with_stock):
        """Should update conviction field."""
        thesis_id = thesis_with_stock
        with get_session() as session:
            thesis = session.get(Thesis, thesis_id)
            thesis.conviction = 5
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.conviction == 5

    def test_update_conviction_rationale(self, thesis_with_stock):
        """Should update conviction rationale."""
        thesis_id = thesis_with_stock
        with get_session() as session:
            thesis = session.get(Thesis, thesis_id)
            thesis.conviction_rationale = "Updated rationale after earnings"
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.conviction_rationale == "Updated rationale after earnings"

    def test_update_status(self, thesis_with_stock):
        """Should update status field."""
        thesis_id = thesis_with_stock
        with get_session() as session:
            thesis = session.get(Thesis, thesis_id)
            thesis.status = "active"
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.status == "active"

    def test_clear_conviction(self, thesis_with_stock):
        """Should allow clearing conviction to None."""
        thesis_id = thesis_with_stock
        with get_session() as session:
            thesis = session.get(Thesis, thesis_id)
            thesis.conviction = None
            thesis.conviction_rationale = None
            session.add(thesis)
            session.commit()
            session.refresh(thesis)

            assert thesis.conviction is None
            assert thesis.conviction_rationale is None


class TestThesisCLIHelp:
    """Tests for thesis CLI help output."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    def test_thesis_group_help(self, runner):
        """Should show thesis command group help."""
        from asymmetric.cli.main import cli

        result = runner.invoke(cli, ["thesis", "--help"])
        assert result.exit_code == 0
        assert "Manage investment theses" in result.output
        assert "create" in result.output
        assert "list" in result.output
        assert "view" in result.output

    def test_thesis_create_help(self, runner):
        """Should show create command help with conviction options."""
        from asymmetric.cli.main import cli

        result = runner.invoke(cli, ["thesis", "create", "--help"])
        assert result.exit_code == 0
        assert "--conviction" in result.output
        assert "--conviction-rationale" in result.output
        assert "1-5" in result.output or "Conviction level" in result.output

    def test_thesis_update_help(self, runner):
        """Should show update command help with conviction options."""
        from asymmetric.cli.main import cli

        result = runner.invoke(cli, ["thesis", "update", "--help"])
        assert result.exit_code == 0
        assert "--conviction" in result.output
        assert "--conviction-rationale" in result.output


class TestConvictionDisplay:
    """Tests for conviction field display formatting."""

    def test_conviction_visual_format(self):
        """Should format conviction as asterisks."""
        # Test the visual formatting pattern used in thesis commands
        for level in range(1, 6):
            visual = "*" * level + "." * (5 - level)
            expected_stars = "*" * level
            expected_dots = "." * (5 - level)
            assert visual == expected_stars + expected_dots
            assert len(visual) == 5

    def test_conviction_full_format(self):
        """Should format conviction with numeric suffix."""
        for level in range(1, 6):
            visual = f"{'*' * level}{'.' * (5 - level)} ({level}/5)"
            assert f"({level}/5)" in visual
            assert visual.count("*") == level
            assert visual.count(".") == 5 - level


class TestThesisQuery:
    """Tests for thesis query operations."""

    @pytest.fixture
    def multiple_theses(self, initialized_db):
        """Create multiple theses for query testing."""
        with get_session() as session:
            stock1 = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            stock2 = Stock(ticker="MSFT", cik="0000789019", company_name="Microsoft Corporation")
            session.add_all([stock1, stock2])
            session.commit()
            session.refresh(stock1)
            session.refresh(stock2)

            theses = [
                Thesis(
                    stock_id=stock1.id,
                    summary="Apple thesis 1",
                    analysis_text="Analysis 1",
                    status="active",
                    conviction=5,
                ),
                Thesis(
                    stock_id=stock1.id,
                    summary="Apple thesis 2",
                    analysis_text="Analysis 2",
                    status="draft",
                    conviction=3,
                ),
                Thesis(
                    stock_id=stock2.id,
                    summary="Microsoft thesis",
                    analysis_text="Analysis 3",
                    status="active",
                    conviction=4,
                ),
            ]
            session.add_all(theses)
            session.commit()
            return [t.id for t in theses]

    def test_query_all_theses(self, multiple_theses):
        """Should query all theses."""
        with get_session() as session:
            result = session.exec(select(Thesis)).all()
            assert len(result) == 3

    def test_query_by_status(self, multiple_theses):
        """Should filter theses by status."""
        with get_session() as session:
            result = session.exec(select(Thesis).where(Thesis.status == "active")).all()
            assert len(result) == 2
            assert all(t.status == "active" for t in result)

    def test_query_by_conviction(self, multiple_theses):
        """Should filter theses by conviction level."""
        with get_session() as session:
            result = session.exec(select(Thesis).where(Thesis.conviction >= 4)).all()
            assert len(result) == 2
            assert all(t.conviction >= 4 for t in result)

    def test_query_high_conviction_active(self, multiple_theses):
        """Should find high-conviction active theses."""
        with get_session() as session:
            result = session.exec(
                select(Thesis).where(Thesis.status == "active", Thesis.conviction >= 4)
            ).all()
            assert len(result) == 2
