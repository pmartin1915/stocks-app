"""Watchlist workflow integration tests.

Tests the CLI watchlist add/remove/clear cycle using Click's CliRunner
with mocked file I/O to avoid touching the real watchlist file.
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from asymmetric.cli.main import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def watchlist_store():
    """In-memory watchlist store to replace file I/O."""
    return {"stocks": {}}


@pytest.fixture
def mock_watchlist_io(watchlist_store):
    """Patch _load_watchlist and _save_watchlist to use in-memory store."""
    import copy

    def _load():
        return copy.deepcopy(watchlist_store)

    def _save(data):
        watchlist_store.clear()
        watchlist_store.update(copy.deepcopy(data))

    with patch("asymmetric.cli.commands.watchlist._load_watchlist", side_effect=_load), \
         patch("asymmetric.cli.commands.watchlist._save_watchlist", side_effect=_save), \
         patch("asymmetric.config.config.validate"), \
         patch("asymmetric.config.config.ensure_directories"):
        yield watchlist_store


class TestAddRemoveCycle:
    """Test adding and removing tickers from the watchlist."""

    def test_add_then_list_shows_ticker(self, runner, mock_watchlist_io):
        """Adding a ticker makes it appear in the list."""
        result = runner.invoke(cli, ["watchlist", "add", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in mock_watchlist_io["stocks"]

    def test_add_then_remove_clears_ticker(self, runner, mock_watchlist_io):
        """Adding then removing a ticker leaves it gone."""
        runner.invoke(cli, ["watchlist", "add", "MSFT"])
        assert "MSFT" in mock_watchlist_io["stocks"]

        result = runner.invoke(cli, ["watchlist", "remove", "MSFT"])
        assert result.exit_code == 0
        assert "MSFT" not in mock_watchlist_io["stocks"]

    def test_remove_nonexistent_warns(self, runner, mock_watchlist_io):
        """Removing a ticker not on the watchlist shows a warning."""
        result = runner.invoke(cli, ["watchlist", "remove", "FAKE"])
        assert result.exit_code == 0
        assert "not on your watchlist" in result.output

    def test_add_with_note(self, runner, mock_watchlist_io):
        """Adding with a note stores the note."""
        runner.invoke(cli, ["watchlist", "add", "GOOG", "--note", "Cloud growth"])
        assert mock_watchlist_io["stocks"]["GOOG"]["note"] == "Cloud growth"

    def test_add_lowercase_normalizes(self, runner, mock_watchlist_io):
        """Lowercase ticker is normalized to uppercase."""
        runner.invoke(cli, ["watchlist", "add", "aapl"])
        assert "AAPL" in mock_watchlist_io["stocks"]
        assert "aapl" not in mock_watchlist_io["stocks"]


class TestAddDuplicate:
    """Test adding the same ticker twice."""

    def test_add_duplicate_shows_already_message(self, runner, mock_watchlist_io):
        """Adding a duplicate ticker shows 'already on watchlist'."""
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        result = runner.invoke(cli, ["watchlist", "add", "AAPL"])
        assert "already on your watchlist" in result.output

    def test_add_duplicate_does_not_create_second_entry(self, runner, mock_watchlist_io):
        """Adding a duplicate does not create a second entry."""
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        assert len(mock_watchlist_io["stocks"]) == 1

    def test_add_duplicate_with_note_updates_note(self, runner, mock_watchlist_io):
        """Re-adding with a note updates the existing note."""
        runner.invoke(cli, ["watchlist", "add", "AAPL", "--note", "Original"])
        runner.invoke(cli, ["watchlist", "add", "AAPL", "--note", "Updated"])
        assert mock_watchlist_io["stocks"]["AAPL"]["note"] == "Updated"


class TestClearAll:
    """Test clearing the entire watchlist."""

    def test_clear_removes_all(self, runner, mock_watchlist_io):
        """Clear removes all stocks from the watchlist."""
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        runner.invoke(cli, ["watchlist", "add", "MSFT"])
        runner.invoke(cli, ["watchlist", "add", "GOOG"])
        assert len(mock_watchlist_io["stocks"]) == 3

        result = runner.invoke(cli, ["watchlist", "clear"])
        assert result.exit_code == 0
        assert len(mock_watchlist_io["stocks"]) == 0

    def test_clear_empty_watchlist(self, runner, mock_watchlist_io):
        """Clearing an empty watchlist shows appropriate message."""
        result = runner.invoke(cli, ["watchlist", "clear"])
        assert result.exit_code == 0
        assert "already empty" in result.output

    def test_clear_shows_count(self, runner, mock_watchlist_io):
        """Clear shows how many stocks were removed."""
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        runner.invoke(cli, ["watchlist", "add", "MSFT"])
        result = runner.invoke(cli, ["watchlist", "clear"])
        assert "2" in result.output


class TestListCommand:
    """Test the list subcommand."""

    def test_list_empty_watchlist(self, runner, mock_watchlist_io):
        """Empty watchlist shows appropriate message."""
        result = runner.invoke(cli, ["watchlist", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output

    def test_list_shows_added_tickers(self, runner, mock_watchlist_io):
        """List shows tickers that were added."""
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        runner.invoke(cli, ["watchlist", "add", "MSFT"])
        result = runner.invoke(cli, ["watchlist", "list"])
        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "MSFT" in result.output

    def test_list_shows_stock_count(self, runner, mock_watchlist_io):
        """List header includes stock count."""
        runner.invoke(cli, ["watchlist", "add", "AAPL"])
        runner.invoke(cli, ["watchlist", "add", "GOOG"])
        result = runner.invoke(cli, ["watchlist", "list"])
        assert "2 stocks" in result.output
