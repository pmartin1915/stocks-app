"""Tests for score --save functionality."""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from asymmetric.cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_edgar_client():
    """Mock EdgarClient for score command tests."""
    with patch("asymmetric.cli.commands.score.EdgarClient") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_financials.return_value = {
            "ticker": "AAPL",
            "periods": [
                {
                    # Current period
                    "revenue": 100_000_000,
                    "gross_profit": 40_000_000,
                    "net_income": 15_000_000,
                    "total_assets": 200_000_000,
                    "current_assets": 50_000_000,
                    "current_liabilities": 30_000_000,
                    "long_term_debt": 20_000_000,
                    "shares_outstanding": 10_000_000,
                    "operating_cash_flow": 20_000_000,
                    "total_liabilities": 50_000_000,
                    "retained_earnings": 100_000_000,
                    "ebit": 25_000_000,
                    "market_cap": 500_000_000,
                    "book_equity": 150_000_000,
                },
                {
                    # Prior period
                    "revenue": 90_000_000,
                    "gross_profit": 35_000_000,
                    "net_income": 12_000_000,
                    "total_assets": 190_000_000,
                    "current_assets": 45_000_000,
                    "current_liabilities": 35_000_000,
                    "long_term_debt": 25_000_000,
                    "shares_outstanding": 10_000_000,
                    "operating_cash_flow": 16_000_000,
                },
            ],
        }
        mock_class.return_value = mock_instance
        yield mock_instance


class TestScoreSave:
    """Tests for score --save functionality."""

    def test_save_flag_exists(self, runner):
        """Test --save flag is recognized."""
        result = runner.invoke(cli, ["score", "--help"])

        assert result.exit_code == 0
        assert "--save" in result.output
        assert "Save scores to database" in result.output

    def test_score_without_save(self, runner, mock_edgar_client):
        """Test score command works without --save flag."""
        result = runner.invoke(cli, ["score", "AAPL"])

        assert result.exit_code == 0
        assert "saved" not in result.output.lower()

    def test_score_with_save_shows_message(self, runner, mock_edgar_client, tmp_db):
        """Test --save flag shows confirmation message."""
        result = runner.invoke(cli, ["score", "AAPL", "--save"])

        assert result.exit_code == 0
        assert "Score saved to database" in result.output

    def test_score_with_save_creates_record(self, runner, mock_edgar_client, tmp_db):
        """Test --save flag creates database record."""
        result = runner.invoke(cli, ["score", "AAPL", "--save"])

        assert result.exit_code == 0

        # Verify record was created
        from asymmetric.db import get_session, StockScore

        with get_session() as session:
            scores = session.query(StockScore).all()
            # At least one score should exist
            assert len(scores) >= 1
            # Latest score should have valid Piotroski score
            latest = scores[-1]
            assert latest.piotroski_score >= 0
            assert latest.piotroski_score <= 9

    def test_score_save_includes_timestamp(self, runner, mock_edgar_client, tmp_db):
        """Test saved scores have calculated_at timestamp."""
        runner.invoke(cli, ["score", "AAPL", "--save"])

        from asymmetric.db import get_session, StockScore

        with get_session() as session:
            score = session.query(StockScore).first()
            assert score is not None
            assert score.calculated_at is not None

    def test_score_save_with_json(self, runner, mock_edgar_client, tmp_db):
        """Test --save works with --json output."""
        result = runner.invoke(cli, ["score", "AAPL", "--save", "--json"])

        assert result.exit_code == 0
        # JSON output should not include "saved" message
        # but record should still be created
        from asymmetric.db import get_session, StockScore

        with get_session() as session:
            scores = session.query(StockScore).all()
            # At least one score should exist
            assert len(scores) >= 1

    def test_score_save_sets_data_source(self, runner, mock_edgar_client, tmp_db):
        """Test saved scores have correct data_source."""
        runner.invoke(cli, ["score", "AAPL", "--save"])

        from asymmetric.db import get_session, StockScore

        with get_session() as session:
            score = session.query(StockScore).first()
            assert score.data_source == "live_api"

    def test_score_save_links_to_stock(self, runner, mock_edgar_client, tmp_db):
        """Test saved scores are linked to stock record."""
        runner.invoke(cli, ["score", "AAPL", "--save"])

        from asymmetric.db import get_session, StockScore, Stock

        with get_session() as session:
            score = session.query(StockScore).first()
            stock = session.query(Stock).filter(Stock.ticker == "AAPL").first()
            assert stock is not None
            assert score.stock_id == stock.id
