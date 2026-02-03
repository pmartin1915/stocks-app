"""Tests for dashboard/utils/watchlist.py.

Tests watchlist management utilities including file I/O,
stock management, and cache operations.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoadWatchlist:
    """Tests for load_watchlist()."""

    def test_returns_empty_when_file_not_exists(self, tmp_path, monkeypatch):
        """Non-existent file should return empty watchlist."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "nonexistent" / "watchlist.json"
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.load_watchlist()

        assert result == {"stocks": {}}

    def test_loads_valid_json(self, tmp_path, monkeypatch):
        """Valid JSON file should be loaded correctly."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"added": "2025-01-01T00:00:00", "note": "Tech"}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.load_watchlist()

        assert result == data
        assert "AAPL" in result["stocks"]

    def test_returns_empty_on_corrupt_json(self, tmp_path, monkeypatch):
        """Corrupt JSON should return empty watchlist."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text("{invalid json")
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.load_watchlist()

        assert result == {"stocks": {}}

    def test_returns_empty_on_io_error(self, tmp_path, monkeypatch):
        """IO error during read should return empty watchlist."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text("{}")
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        # Make file unreadable by patching open
        def raise_io_error(*args, **kwargs):
            raise IOError("Permission denied")

        with patch("builtins.open", side_effect=raise_io_error):
            result = watchlist.load_watchlist()

        assert result == {"stocks": {}}


class TestSaveWatchlist:
    """Tests for save_watchlist()."""

    def test_saves_valid_watchlist(self, tmp_path, monkeypatch):
        """Valid watchlist should be saved to file."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        data = {"stocks": {"MSFT": {"added": "2025-01-01T00:00:00", "note": ""}}}
        watchlist.save_watchlist(data)

        assert fake_file.exists()
        loaded = json.loads(fake_file.read_text())
        assert loaded == data

    def test_creates_parent_directory(self, tmp_path, monkeypatch):
        """Parent directory should be created if it doesn't exist."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "subdir" / "watchlist.json"
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        watchlist.save_watchlist({"stocks": {}})

        assert fake_file.parent.exists()
        assert fake_file.exists()

    def test_atomic_write_no_temp_file_remains(self, tmp_path, monkeypatch):
        """Temp file should not remain after successful save."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        watchlist.save_watchlist({"stocks": {}})

        temp_file = fake_file.with_suffix(".tmp")
        assert not temp_file.exists()


class TestGetStocks:
    """Tests for get_stocks()."""

    def test_returns_empty_list_when_no_stocks(self, tmp_path, monkeypatch):
        """Empty watchlist should return empty list."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.get_stocks()

        assert result == []

    def test_returns_ticker_list(self, tmp_path, monkeypatch):
        """Should return list of ticker symbols."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {}, "MSFT": {}, "GOOGL": {}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.get_stocks()

        assert set(result) == {"AAPL", "MSFT", "GOOGL"}


class TestGetStockData:
    """Tests for get_stock_data()."""

    def test_returns_data_for_existing_ticker(self, tmp_path, monkeypatch):
        """Should return data dict for existing ticker."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        stock_data = {"added": "2025-01-01T00:00:00", "note": "Test note"}
        data = {"stocks": {"AAPL": stock_data}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.get_stock_data("AAPL")

        assert result == stock_data

    def test_returns_none_for_nonexistent_ticker(self, tmp_path, monkeypatch):
        """Should return None for ticker not in watchlist."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {"AAPL": {}}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.get_stock_data("MSFT")

        assert result is None

    def test_case_insensitive_lookup(self, tmp_path, monkeypatch):
        """Ticker lookup should be case-insensitive."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"note": "found"}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.get_stock_data("aapl")

        assert result is not None
        assert result["note"] == "found"


class TestAddStock:
    """Tests for add_stock()."""

    def test_adds_new_stock(self, tmp_path, monkeypatch):
        """Should add new stock and return True."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.add_stock("AAPL")

        assert result is True
        stocks = watchlist.get_stocks()
        assert "AAPL" in stocks

    def test_returns_false_for_duplicate(self, tmp_path, monkeypatch):
        """Should return False for existing stock."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"added": "2025-01-01T00:00:00", "note": ""}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.add_stock("AAPL")

        assert result is False

    def test_adds_stock_with_note(self, tmp_path, monkeypatch):
        """Should add stock with note."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        watchlist.add_stock("MSFT", note="Tech giant")

        data = watchlist.get_stock_data("MSFT")
        assert data["note"] == "Tech giant"

    def test_updates_note_for_existing_stock(self, tmp_path, monkeypatch):
        """Should update note for existing stock."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"added": "2025-01-01T00:00:00", "note": "Old note"}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        watchlist.add_stock("AAPL", note="New note")

        stock_data = watchlist.get_stock_data("AAPL")
        assert stock_data["note"] == "New note"

    def test_uppercases_ticker(self, tmp_path, monkeypatch):
        """Should uppercase ticker symbol."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        watchlist.add_stock("aapl")

        stocks = watchlist.get_stocks()
        assert "AAPL" in stocks
        assert "aapl" not in stocks


class TestRemoveStock:
    """Tests for remove_stock()."""

    def test_removes_existing_stock(self, tmp_path, monkeypatch):
        """Should remove existing stock and return True."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {}, "MSFT": {}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.remove_stock("AAPL")

        assert result is True
        stocks = watchlist.get_stocks()
        assert "AAPL" not in stocks
        assert "MSFT" in stocks

    def test_returns_false_for_nonexistent(self, tmp_path, monkeypatch):
        """Should return False for non-existent stock."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {"AAPL": {}}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.remove_stock("MSFT")

        assert result is False


class TestUpdateCachedScores:
    """Tests for update_cached_scores()."""

    def test_updates_scores_for_existing_stock(self, tmp_path, monkeypatch):
        """Should update cached scores for existing stock."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"added": "2025-01-01T00:00:00", "note": ""}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        scores = {"piotroski": 8, "altman": 3.5}
        watchlist.update_cached_scores("AAPL", scores)

        stock_data = watchlist.get_stock_data("AAPL")
        assert stock_data["cached_scores"] == scores
        assert "cached_at" in stock_data

    def test_does_nothing_for_nonexistent_stock(self, tmp_path, monkeypatch):
        """Should not create stock entry for non-existent ticker."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        watchlist.update_cached_scores("AAPL", {"piotroski": 8})

        stocks = watchlist.get_stocks()
        assert "AAPL" not in stocks


class TestGetCachedScores:
    """Tests for get_cached_scores()."""

    def test_returns_valid_cache(self, tmp_path, monkeypatch):
        """Should return cached scores if not expired."""
        from dashboard.utils import watchlist
        from dashboard import config

        fake_file = tmp_path / "watchlist.json"
        now = datetime.now(UTC).isoformat()
        scores = {"piotroski": 8, "altman": 3.5}
        data = {
            "stocks": {
                "AAPL": {
                    "added": "2025-01-01T00:00:00",
                    "cached_scores": scores,
                    "cached_at": now,
                }
            }
        }
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)
        monkeypatch.setattr(config, "SCORE_CACHE_TTL", 300)

        result = watchlist.get_cached_scores("AAPL")

        assert result == scores

    def test_returns_none_for_expired_cache(self, tmp_path, monkeypatch):
        """Should return None for expired cache."""
        from dashboard.utils import watchlist
        from dashboard import config

        fake_file = tmp_path / "watchlist.json"
        old_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        data = {
            "stocks": {
                "AAPL": {
                    "added": "2025-01-01T00:00:00",
                    "cached_scores": {"piotroski": 8},
                    "cached_at": old_time,
                }
            }
        }
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)
        monkeypatch.setattr(config, "SCORE_CACHE_TTL", 300)

        result = watchlist.get_cached_scores("AAPL")

        assert result is None

    def test_returns_none_for_no_cache(self, tmp_path, monkeypatch):
        """Should return None if no cache exists."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"added": "2025-01-01T00:00:00"}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.get_cached_scores("AAPL")

        assert result is None


class TestIsCacheExpired:
    """Tests for is_cache_expired()."""

    def test_returns_false_for_fresh_cache(self, tmp_path, monkeypatch):
        """Fresh cache should not be expired."""
        from dashboard.utils import watchlist
        from dashboard import config

        fake_file = tmp_path / "watchlist.json"
        now = datetime.now(UTC).isoformat()
        data = {
            "stocks": {
                "AAPL": {
                    "cached_scores": {"piotroski": 8},
                    "cached_at": now,
                }
            }
        }
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)
        monkeypatch.setattr(config, "SCORE_CACHE_TTL", 300)

        result = watchlist.is_cache_expired("AAPL")

        assert result is False

    def test_returns_true_for_old_cache(self, tmp_path, monkeypatch):
        """Old cache should be expired."""
        from dashboard.utils import watchlist
        from dashboard import config

        fake_file = tmp_path / "watchlist.json"
        old_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        data = {
            "stocks": {
                "AAPL": {
                    "cached_scores": {"piotroski": 8},
                    "cached_at": old_time,
                }
            }
        }
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)
        monkeypatch.setattr(config, "SCORE_CACHE_TTL", 300)

        result = watchlist.is_cache_expired("AAPL")

        assert result is True

    def test_returns_false_for_no_cache(self, tmp_path, monkeypatch):
        """No cache should return False (not expired, just missing)."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {"added": "2025-01-01T00:00:00"}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        result = watchlist.is_cache_expired("AAPL")

        assert result is False


class TestClearWatchlist:
    """Tests for clear_watchlist()."""

    def test_clears_all_stocks(self, tmp_path, monkeypatch):
        """Should remove all stocks."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        data = {"stocks": {"AAPL": {}, "MSFT": {}, "GOOGL": {}}}
        fake_file.write_text(json.dumps(data))
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        count = watchlist.clear_watchlist()

        assert count == 3
        stocks = watchlist.get_stocks()
        assert stocks == []

    def test_returns_zero_for_empty_watchlist(self, tmp_path, monkeypatch):
        """Should return 0 for empty watchlist."""
        from dashboard.utils import watchlist

        fake_file = tmp_path / "watchlist.json"
        fake_file.write_text('{"stocks": {}}')
        monkeypatch.setattr(watchlist, "WATCHLIST_FILE", fake_file)

        count = watchlist.clear_watchlist()

        assert count == 0
