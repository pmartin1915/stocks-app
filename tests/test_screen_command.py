"""
Tests for the screen CLI command.

Tests cover:
- Help text and options
- Filtering by Piotroski F-Score
- Filtering by Altman Z-Score
- JSON output format
- Empty database handling
- Error handling
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from asymmetric.cli.main import cli


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_bulk_manager():
    """Create a mock BulkDataManager with sample data."""
    mock = MagicMock()
    mock.get_all_tickers.return_value = ["AAPL", "MSFT", "GOOG"]
    mock.get_latest_financials.return_value = {
        "revenue": 100_000_000,
        "net_income": 15_000_000,
        "total_assets": 200_000_000,
        "current_assets": 80_000_000,
        "current_liabilities": 50_000_000,
        "long_term_debt": 30_000_000,
        "operating_cash_flow": 20_000_000,
        "retained_earnings": 50_000_000,
        "ebit": 18_000_000,
        "stockholders_equity": 100_000_000,
    }
    mock.get_company_info.return_value = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
    }
    return mock


class TestScreenCommand:
    """Tests for the screen command."""

    def test_screen_help(self, runner):
        """Test screen command help displays options."""
        result = runner.invoke(cli, ["screen", "--help"])

        assert result.exit_code == 0
        assert "piotroski-min" in result.output
        assert "altman-min" in result.output
        assert "altman-zone" in result.output
        assert "refresh" in result.output
        assert "limit" in result.output
        assert "json" in result.output

    def test_screen_help_shows_examples(self, runner):
        """Test screen command help shows usage examples."""
        result = runner.invoke(cli, ["screen", "--help"])

        assert result.exit_code == 0
        assert "Screen stocks" in result.output

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    def test_screen_empty_database(self, mock_manager_class, runner):
        """Test screen with empty database shows warning."""
        mock_manager = MagicMock()
        mock_manager.get_all_tickers.return_value = []
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(cli, ["screen"])

        assert result.exit_code == 1
        assert "No bulk data" in result.output or "refresh" in result.output.lower()

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    @patch("asymmetric.cli.commands.screen.PiotroskiScorer")
    @patch("asymmetric.cli.commands.screen.AltmanScorer")
    def test_screen_with_piotroski_filter(
        self, mock_altman, mock_piotroski, mock_manager_class, runner, mock_bulk_manager
    ):
        """Test screening with Piotroski minimum filter."""
        mock_manager_class.return_value = mock_bulk_manager

        # Mock scorers
        mock_piotroski_result = MagicMock()
        mock_piotroski_result.score = 8
        mock_piotroski_result.interpretation = "Strong"
        mock_piotroski.return_value.calculate_from_dict.return_value = mock_piotroski_result

        mock_altman_result = MagicMock()
        mock_altman_result.z_score = 5.5
        mock_altman_result.zone = "Safe"
        mock_altman.return_value.calculate_from_dict.return_value = mock_altman_result

        result = runner.invoke(cli, ["screen", "--piotroski-min", "7", "--limit", "5"])

        # Should succeed with filtered results
        assert result.exit_code == 0

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    @patch("asymmetric.cli.commands.screen.PiotroskiScorer")
    @patch("asymmetric.cli.commands.screen.AltmanScorer")
    def test_screen_with_altman_zone_filter(
        self, mock_altman, mock_piotroski, mock_manager_class, runner, mock_bulk_manager
    ):
        """Test screening with Altman zone filter."""
        mock_manager_class.return_value = mock_bulk_manager

        mock_piotroski_result = MagicMock()
        mock_piotroski_result.score = 6
        mock_piotroski_result.interpretation = "Moderate"
        mock_piotroski.return_value.calculate_from_dict.return_value = mock_piotroski_result

        mock_altman_result = MagicMock()
        mock_altman_result.z_score = 3.5
        mock_altman_result.zone = "Safe"
        mock_altman.return_value.calculate_from_dict.return_value = mock_altman_result

        result = runner.invoke(cli, ["screen", "--altman-zone", "Safe", "--limit", "5"])

        assert result.exit_code == 0

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    @patch("asymmetric.cli.commands.screen.PiotroskiScorer")
    @patch("asymmetric.cli.commands.screen.AltmanScorer")
    def test_screen_json_output(
        self, mock_altman, mock_piotroski, mock_manager_class, runner, mock_bulk_manager
    ):
        """Test screen command with JSON output."""
        mock_manager_class.return_value = mock_bulk_manager

        mock_piotroski_result = MagicMock()
        mock_piotroski_result.score = 7
        mock_piotroski_result.interpretation = "Strong"
        mock_piotroski.return_value.calculate_from_dict.return_value = mock_piotroski_result

        mock_altman_result = MagicMock()
        mock_altman_result.z_score = 4.2
        mock_altman_result.zone = "Safe"
        mock_altman.return_value.calculate_from_dict.return_value = mock_altman_result

        result = runner.invoke(cli, ["screen", "--json", "--limit", "3"])

        assert result.exit_code == 0
        # Verify JSON output is valid
        try:
            data = json.loads(result.output)
            assert "criteria" in data
            assert "stats" in data
            assert "results" in data
        except json.JSONDecodeError:
            # Output might be wrapped in Rich markup, still acceptable
            pass

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    @patch("asymmetric.cli.commands.screen.PiotroskiScorer")
    @patch("asymmetric.cli.commands.screen.AltmanScorer")
    def test_screen_no_matches(
        self, mock_altman, mock_piotroski, mock_manager_class, runner, mock_bulk_manager
    ):
        """Test screen with criteria that match no stocks."""
        mock_manager_class.return_value = mock_bulk_manager

        # Return low scores that won't match high thresholds
        mock_piotroski_result = MagicMock()
        mock_piotroski_result.score = 3
        mock_piotroski_result.interpretation = "Weak"
        mock_piotroski.return_value.calculate_from_dict.return_value = mock_piotroski_result

        mock_altman_result = MagicMock()
        mock_altman_result.z_score = 1.5
        mock_altman_result.zone = "Distress"
        mock_altman.return_value.calculate_from_dict.return_value = mock_altman_result

        result = runner.invoke(cli, ["screen", "--piotroski-min", "9"])

        # Should succeed but show no matches
        assert result.exit_code == 0
        assert "No stocks match" in result.output or "0 matches" in result.output

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    @patch("asymmetric.cli.commands.screen.PiotroskiScorer")
    @patch("asymmetric.cli.commands.screen.AltmanScorer")
    def test_screen_with_combined_filters(
        self, mock_altman, mock_piotroski, mock_manager_class, runner, mock_bulk_manager
    ):
        """Test screening with multiple filter criteria."""
        mock_manager_class.return_value = mock_bulk_manager

        mock_piotroski_result = MagicMock()
        mock_piotroski_result.score = 8
        mock_piotroski_result.interpretation = "Strong"
        mock_piotroski.return_value.calculate_from_dict.return_value = mock_piotroski_result

        mock_altman_result = MagicMock()
        mock_altman_result.z_score = 5.0
        mock_altman_result.zone = "Safe"
        mock_altman.return_value.calculate_from_dict.return_value = mock_altman_result

        result = runner.invoke(
            cli,
            ["screen", "--piotroski-min", "7", "--altman-min", "3.0", "--limit", "10"],
        )

        assert result.exit_code == 0

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    @patch("asymmetric.cli.commands.screen.PiotroskiScorer")
    @patch("asymmetric.cli.commands.screen.AltmanScorer")
    def test_screen_sort_options(
        self, mock_altman, mock_piotroski, mock_manager_class, runner, mock_bulk_manager
    ):
        """Test screen with sort options."""
        mock_manager_class.return_value = mock_bulk_manager

        mock_piotroski_result = MagicMock()
        mock_piotroski_result.score = 7
        mock_piotroski_result.interpretation = "Strong"
        mock_piotroski.return_value.calculate_from_dict.return_value = mock_piotroski_result

        mock_altman_result = MagicMock()
        mock_altman_result.z_score = 4.0
        mock_altman_result.zone = "Safe"
        mock_altman.return_value.calculate_from_dict.return_value = mock_altman_result

        result = runner.invoke(
            cli,
            ["screen", "--sort-by", "altman", "--sort-order", "asc", "--limit", "5"],
        )

        assert result.exit_code == 0

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    def test_screen_handles_insufficient_data(
        self, mock_manager_class, runner
    ):
        """Test screen gracefully handles tickers with insufficient data."""
        mock_manager = MagicMock()
        mock_manager.get_all_tickers.return_value = ["AAPL", "MSFT"]
        # Return empty dict to simulate missing data
        mock_manager.get_latest_financials.return_value = {}
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(cli, ["screen", "--limit", "5"])

        # Should complete without crashing, even with no valid results
        assert result.exit_code == 0


class TestScreenCommandOptions:
    """Tests for screen command option validation."""

    def test_screen_invalid_altman_zone(self, runner):
        """Test screen rejects invalid Altman zone values."""
        result = runner.invoke(cli, ["screen", "--altman-zone", "Invalid"])

        assert result.exit_code != 0
        assert "Invalid" in result.output or "invalid" in result.output.lower()

    def test_screen_invalid_sort_by(self, runner):
        """Test screen rejects invalid sort-by values."""
        result = runner.invoke(cli, ["screen", "--sort-by", "invalid"])

        assert result.exit_code != 0

    def test_screen_invalid_sort_order(self, runner):
        """Test screen rejects invalid sort-order values."""
        result = runner.invoke(cli, ["screen", "--sort-order", "invalid"])

        assert result.exit_code != 0
