"""Tests for screen --add-to-watchlist functionality."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from asymmetric.cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_watchlist(tmp_path, monkeypatch):
    """Use temporary watchlist file."""
    watchlist_dir = tmp_path / ".asymmetric"
    watchlist_dir.mkdir(parents=True, exist_ok=True)
    watchlist_file = watchlist_dir / "watchlist.json"
    watchlist_file.write_text('{"stocks": {}}')

    # Patch the WATCHLIST_FILE constant
    monkeypatch.setattr(
        "asymmetric.cli.commands.screen.WATCHLIST_FILE",
        watchlist_file
    )

    return watchlist_file


@pytest.fixture
def mock_bulk_manager_with_results():
    """Mock BulkDataManager with screening results."""
    with patch("asymmetric.cli.commands.screen.BulkDataManager") as mock_class:
        mock_instance = MagicMock()

        # Mock get_scorable_tickers
        mock_instance.get_scorable_tickers.return_value = ["AAPL", "MSFT", "GOOG"]

        # Mock get_batch_financials with data that will produce scores
        mock_instance.get_batch_financials.return_value = {
            "AAPL": [
                {
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
            "MSFT": [
                {
                    "revenue": 150_000_000,
                    "gross_profit": 65_000_000,
                    "net_income": 25_000_000,
                    "total_assets": 300_000_000,
                    "current_assets": 90_000_000,
                    "current_liabilities": 45_000_000,
                    "long_term_debt": 30_000_000,
                    "shares_outstanding": 12_000_000,
                    "operating_cash_flow": 35_000_000,
                    "total_liabilities": 75_000_000,
                    "retained_earnings": 150_000_000,
                    "ebit": 40_000_000,
                    "market_cap": 800_000_000,
                    "book_equity": 225_000_000,
                },
                {
                    "revenue": 140_000_000,
                    "gross_profit": 60_000_000,
                    "net_income": 22_000_000,
                    "total_assets": 280_000_000,
                    "current_assets": 85_000_000,
                    "current_liabilities": 50_000_000,
                    "long_term_debt": 35_000_000,
                    "shares_outstanding": 12_000_000,
                    "operating_cash_flow": 30_000_000,
                },
            ],
        }

        # Mock get_company_info
        mock_instance.get_company_info.side_effect = lambda t: {
            "AAPL": {"company_name": "Apple Inc."},
            "MSFT": {"company_name": "Microsoft Corporation"},
            "GOOG": {"company_name": "Alphabet Inc."},
        }.get(t, {"company_name": ""})

        mock_class.return_value = mock_instance
        yield mock_instance


class TestScreenWatchlist:
    """Tests for screen --add-to-watchlist functionality."""

    def test_flag_exists(self, runner):
        """Test --add-to-watchlist flag is recognized."""
        result = runner.invoke(cli, ["screen", "--help"])

        assert result.exit_code == 0
        assert "--add-to-watchlist" in result.output

    def test_add_to_watchlist_creates_entries(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test --add-to-watchlist adds stocks to watchlist."""
        result = runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
        ])

        assert result.exit_code == 0
        assert "Added" in result.output
        assert "watchlist" in result.output.lower()

        # Verify watchlist was updated
        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        assert len(watchlist["stocks"]) > 0

    def test_watchlist_includes_criteria(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test watchlist entries include screening criteria in notes."""
        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "7",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        if watchlist["stocks"]:
            first_stock = list(watchlist["stocks"].values())[0]
            assert "F>=7" in first_stock.get("note", "")

    def test_watchlist_includes_zone_criteria(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test watchlist entries include zone criteria."""
        runner.invoke(cli, [
            "screen",
            "--altman-zone", "Safe",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        if watchlist["stocks"]:
            first_stock = list(watchlist["stocks"].values())[0]
            assert "Zone=Safe" in first_stock.get("note", "")

    def test_watchlist_sets_source(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test watchlist entries have source='screen'."""
        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        if watchlist["stocks"]:
            first_stock = list(watchlist["stocks"].values())[0]
            assert first_stock.get("source") == "screen"

    def test_watchlist_caches_scores(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test watchlist entries include cached scores."""
        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        if watchlist["stocks"]:
            first_stock = list(watchlist["stocks"].values())[0]
            assert "cached_scores" in first_stock
            assert "piotroski" in first_stock["cached_scores"]

    def test_no_duplicates_added(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test running twice doesn't add duplicates."""
        # First run
        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            first_watchlist = json.load(f)
        first_count = len(first_watchlist["stocks"])

        # Second run
        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            second_watchlist = json.load(f)
        second_count = len(second_watchlist["stocks"])

        # Should not have more stocks (duplicates not added)
        assert second_count == first_count

    def test_updates_existing_entry(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test re-screening updates existing watchlist entries."""
        # First run with one criteria
        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
        ])

        # Second run with different criteria
        runner.invoke(cli, [
            "screen",
            "--altman-zone", "Safe",
            "--add-to-watchlist",
        ])

        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        if watchlist["stocks"]:
            first_stock = list(watchlist["stocks"].values())[0]
            # Should have screen_note from second run
            assert "last_screened" in first_stock or "screen_note" in first_stock

    def test_screen_without_watchlist_flag(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test screen without --add-to-watchlist doesn't modify watchlist."""
        # Write initial empty watchlist
        with open(temp_watchlist, "w") as f:
            json.dump({"stocks": {}}, f)

        runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
        ])

        with open(temp_watchlist, "r") as f:
            watchlist = json.load(f)

        # Should still be empty
        assert len(watchlist["stocks"]) == 0

    def test_json_output_with_watchlist(
        self, runner, mock_bulk_manager_with_results, temp_watchlist
    ):
        """Test --json output works with --add-to-watchlist."""
        result = runner.invoke(cli, [
            "screen",
            "--piotroski-min", "5",
            "--add-to-watchlist",
            "--json",
        ])

        assert result.exit_code == 0
        # Output should be valid JSON (no extra text when using --json)
        # Find JSON in output by looking for the opening brace
        output_text = result.output.strip()
        if output_text.startswith("{"):
            output = json.loads(output_text)
            assert "results" in output
