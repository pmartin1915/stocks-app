"""Tests for db precompute command."""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from asymmetric.cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_bulk_manager_empty():
    """Mock BulkDataManager with no data."""
    with patch("asymmetric.cli.commands.db.BulkDataManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_stats.return_value = {
            "ticker_count": 0,
            "fact_count": 0,
            "db_size_mb": 0.0,
            "db_path": "/tmp/test.duckdb",
            "last_refresh": None,
        }
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_bulk_manager_with_data():
    """Mock BulkDataManager with bulk data loaded."""
    with patch("asymmetric.cli.commands.db.BulkDataManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_stats.return_value = {
            "ticker_count": 5000,
            "fact_count": 1_000_000,
            "db_size_mb": 250.0,
            "db_path": "/tmp/test.duckdb",
            "last_refresh": "2024-01-15T10:00:00",
        }
        mock_instance.get_scores_stats.return_value = {
            "total_scores": 3500,
            "last_computed": "2024-01-15T12:00:00",
        }
        mock_class.return_value = mock_instance
        yield mock_instance


class TestDbPrecompute:
    """Tests for db precompute command."""

    def test_precompute_no_data(self, runner, mock_bulk_manager_empty):
        """Test precompute fails gracefully with no bulk data."""
        result = runner.invoke(cli, ["db", "precompute"])

        assert result.exit_code == 1
        assert "No bulk data available" in result.output

    def test_precompute_success(self, runner, mock_bulk_manager_with_data):
        """Test precompute runs successfully with data."""
        result = runner.invoke(cli, ["db", "precompute"])

        assert result.exit_code == 0
        assert "Precomputation complete" in result.output
        mock_bulk_manager_with_data.precompute_scores.assert_called_once()

    def test_precompute_with_limit(self, runner, mock_bulk_manager_with_data):
        """Test precompute respects --limit flag."""
        result = runner.invoke(cli, ["db", "precompute", "--limit", "100"])

        assert result.exit_code == 0
        # Check that precompute_scores was called with limit=100
        call_kwargs = mock_bulk_manager_with_data.precompute_scores.call_args
        assert call_kwargs[1]["limit"] == 100

    def test_precompute_shows_stats(self, runner, mock_bulk_manager_with_data):
        """Test precompute displays completion stats."""
        result = runner.invoke(cli, ["db", "precompute"])

        assert result.exit_code == 0
        # Should show scores computed and time
        assert "Scores Computed" in result.output or "3,500" in result.output

    def test_precompute_help(self, runner):
        """Test precompute help displays correctly."""
        result = runner.invoke(cli, ["db", "precompute", "--help"])

        assert result.exit_code == 0
        assert "Precompute F-Scores and Z-Scores" in result.output
        assert "--limit" in result.output

    def test_precompute_calls_initialize_schema(self, runner, mock_bulk_manager_with_data):
        """Test precompute initializes schema before computing."""
        runner.invoke(cli, ["db", "precompute"])

        mock_bulk_manager_with_data.initialize_schema.assert_called_once()

    def test_precompute_closes_connection(self, runner, mock_bulk_manager_with_data):
        """Test precompute closes database connection."""
        runner.invoke(cli, ["db", "precompute"])

        mock_bulk_manager_with_data.close.assert_called()
