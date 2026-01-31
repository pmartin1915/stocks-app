"""
Tests for the Bulk Data Manager.

Tests cover:
- Schema initialization
- Ticker/CIK mapping
- Financial data queries
- Metadata management
- Context manager behavior

Note: These are unit tests using a temporary DuckDB database.
Integration tests that download actual SEC data are marked with @pytest.mark.slow.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest

from asymmetric.core.data.bulk_manager import BulkDataManager


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_sec_data.duckdb"


@pytest.fixture
def bulk_manager(tmp_path, tmp_db_path):
    """Create a BulkDataManager with temporary paths."""
    manager = BulkDataManager(
        db_path=tmp_db_path,
        bulk_dir=tmp_path / "bulk",
    )
    manager.initialize_schema()
    yield manager
    manager.close()


@pytest.fixture
def populated_manager(bulk_manager):
    """Create a BulkDataManager with sample data."""
    # Insert sample ticker data
    bulk_manager.conn.executemany(
        """
        INSERT INTO company_tickers (cik, ticker, company_name)
        VALUES (?, ?, ?)
        """,
        [
            ("0000320193", "AAPL", "Apple Inc."),
            ("0000789019", "MSFT", "Microsoft Corporation"),
            ("0001018724", "AMZN", "Amazon.com Inc."),
        ],
    )

    # Insert sample company facts (no id column - removed from schema)
    # Format: (cik, taxonomy, concept, label, unit, period_end, fiscal_year, fiscal_period, form, value, accession_number, filed_date)
    sample_facts = [
        # Apple data
        ("0000320193", "us-gaap", "Revenues", "Total Revenue", "USD", "2023-09-30", 2023, "FY", "10-K", 383285000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "Revenues", "Total Revenue", "USD", "2022-09-24", 2022, "FY", "10-K", 394328000000, "0000320193-22-000001", "2022-10-28"),
        ("0000320193", "us-gaap", "NetIncomeLoss", "Net Income", "USD", "2023-09-30", 2023, "FY", "10-K", 96995000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "Assets", "Total Assets", "USD", "2023-09-30", 2023, "FY", "10-K", 352583000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "AssetsCurrent", "Current Assets", "USD", "2023-09-30", 2023, "FY", "10-K", 143566000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "LiabilitiesCurrent", "Current Liabilities", "USD", "2023-09-30", 2023, "FY", "10-K", 145308000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "Liabilities", "Total Liabilities", "USD", "2023-09-30", 2023, "FY", "10-K", 290437000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "RetainedEarningsAccumulatedDeficit", "Retained Earnings", "USD", "2023-09-30", 2023, "FY", "10-K", -214000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "OperatingIncomeLoss", "Operating Income", "USD", "2023-09-30", 2023, "FY", "10-K", 114301000000, "0000320193-23-000001", "2023-10-27"),
        # Microsoft data
        ("0000789019", "us-gaap", "Revenues", "Total Revenue", "USD", "2023-06-30", 2023, "FY", "10-K", 211915000000, "0000789019-23-000001", "2023-07-25"),
        ("0000789019", "us-gaap", "NetIncomeLoss", "Net Income", "USD", "2023-06-30", 2023, "FY", "10-K", 72361000000, "0000789019-23-000001", "2023-07-25"),
    ]

    bulk_manager.conn.executemany(
        """
        INSERT INTO company_facts
        (cik, taxonomy, concept, label, unit, period_end, fiscal_year, fiscal_period, form, value, accession_number, filed_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sample_facts,
    )

    return bulk_manager


# ============================================================================
# Schema Tests
# ============================================================================


class TestSchemaInitialization:
    """Tests for database schema initialization."""

    def test_initialize_creates_tables(self, tmp_path, tmp_db_path):
        """Test that initialize_schema creates required tables."""
        manager = BulkDataManager(db_path=tmp_db_path, bulk_dir=tmp_path / "bulk")
        manager.initialize_schema()

        # Check tables exist (DuckDB uses information_schema)
        tables = manager.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "company_tickers" in table_names
        assert "company_facts" in table_names
        assert "bulk_metadata" in table_names

        manager.close()

    def test_initialize_creates_indexes(self, bulk_manager):
        """Test that initialize_schema creates indexes."""
        # Check indexes exist (DuckDB uses duckdb_indexes)
        indexes = bulk_manager.conn.execute(
            "SELECT index_name FROM duckdb_indexes()"
        ).fetchall()
        index_names = [i[0] for i in indexes]

        assert "idx_tickers_ticker" in index_names
        assert "idx_facts_cik" in index_names
        assert "idx_facts_concept" in index_names

    def test_initialize_idempotent(self, bulk_manager):
        """Test that initialize_schema can be called multiple times safely."""
        # Call again - should not error
        bulk_manager.initialize_schema()
        bulk_manager.initialize_schema()

        # Should still work
        result = bulk_manager.conn.execute(
            "SELECT COUNT(*) FROM company_tickers"
        ).fetchone()
        assert result[0] == 0

    def test_drop_tables(self, populated_manager):
        """Test that drop_tables removes all tables."""
        # Verify data exists first
        count = populated_manager.conn.execute(
            "SELECT COUNT(*) FROM company_tickers"
        ).fetchone()[0]
        assert count > 0

        # Drop tables
        populated_manager.drop_tables()

        # Tables should be gone
        with pytest.raises(duckdb.CatalogException):
            populated_manager.conn.execute("SELECT * FROM company_tickers")


# ============================================================================
# Ticker Mapping Tests
# ============================================================================


class TestTickerMapping:
    """Tests for ticker/CIK mapping functionality."""

    def test_get_cik(self, populated_manager):
        """Test looking up CIK by ticker."""
        cik = populated_manager.get_cik("AAPL")
        assert cik == "0000320193"

    def test_get_cik_case_insensitive(self, populated_manager):
        """Test that ticker lookup is case-insensitive."""
        cik = populated_manager.get_cik("aapl")
        assert cik == "0000320193"

    def test_get_cik_not_found(self, populated_manager):
        """Test that missing ticker returns None."""
        cik = populated_manager.get_cik("NOTREAL")
        assert cik is None

    def test_get_ticker(self, populated_manager):
        """Test looking up ticker by CIK."""
        ticker = populated_manager.get_ticker("0000320193")
        assert ticker == "AAPL"

    def test_get_ticker_without_padding(self, populated_manager):
        """Test that CIK without leading zeros works."""
        ticker = populated_manager.get_ticker("320193")
        assert ticker == "AAPL"

    def test_get_ticker_not_found(self, populated_manager):
        """Test that missing CIK returns None."""
        ticker = populated_manager.get_ticker("0000000001")
        assert ticker is None

    def test_get_company_info(self, populated_manager):
        """Test getting full company info."""
        info = populated_manager.get_company_info("MSFT")

        assert info is not None
        assert info["cik"] == "0000789019"
        assert info["ticker"] == "MSFT"
        assert info["company_name"] == "Microsoft Corporation"


# ============================================================================
# Financial Query Tests
# ============================================================================


class TestFinancialQueries:
    """Tests for financial data query methods."""

    def test_query_financials_single_concept(self, populated_manager):
        """Test querying a single financial concept."""
        result = populated_manager.query_financials(
            ticker="AAPL",
            concepts=["Revenues"],
            years=5,
        )

        assert result["ticker"] == "AAPL"
        assert result["cik"] == "0000320193"
        assert result["error"] is None
        assert "Revenues" in result["data"]
        assert len(result["data"]["Revenues"]) >= 1

    def test_query_financials_multiple_concepts(self, populated_manager):
        """Test querying multiple financial concepts."""
        result = populated_manager.query_financials(
            ticker="AAPL",
            concepts=["Revenues", "NetIncomeLoss", "Assets"],
            years=5,
        )

        assert "Revenues" in result["data"]
        assert "NetIncomeLoss" in result["data"]
        assert "Assets" in result["data"]

    def test_query_financials_values_correct(self, populated_manager):
        """Test that queried values match inserted data."""
        result = populated_manager.query_financials(
            ticker="AAPL",
            concepts=["Revenues"],
            years=5,
        )

        revenues = result["data"]["Revenues"]
        values = [r["value"] for r in revenues]

        assert 383285000000 in values  # 2023 revenue
        assert 394328000000 in values  # 2022 revenue

    def test_query_financials_company_not_found(self, populated_manager):
        """Test querying unknown company."""
        result = populated_manager.query_financials(
            ticker="NOTREAL",
            concepts=["Revenues"],
            years=5,
        )

        assert result["cik"] is None
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

    def test_query_financials_concept_not_found(self, populated_manager):
        """Test querying non-existent concept returns empty list."""
        result = populated_manager.query_financials(
            ticker="AAPL",
            concepts=["FakeConcept"],
            years=5,
        )

        assert result["error"] is None
        assert result["data"]["FakeConcept"] == []

    def test_get_latest_financials(self, populated_manager):
        """Test getting latest financials for scoring."""
        result = populated_manager.get_latest_financials("AAPL")

        # Should have mapped fields
        assert "revenue" in result
        assert "net_income" in result
        assert "total_assets" in result
        assert "current_assets" in result
        assert "current_liabilities" in result
        assert "total_liabilities" in result

        # Values should match our sample data
        assert result["revenue"] == 383285000000
        assert result["net_income"] == 96995000000

    def test_get_latest_financials_not_found(self, populated_manager):
        """Test getting latest financials for unknown company."""
        result = populated_manager.get_latest_financials("NOTREAL")
        assert result == {}


# ============================================================================
# Metadata Tests
# ============================================================================


class TestMetadata:
    """Tests for metadata management."""

    def test_update_metadata(self, bulk_manager):
        """Test updating metadata."""
        bulk_manager._update_metadata("test_key", "test_value")

        result = bulk_manager.conn.execute(
            "SELECT value FROM bulk_metadata WHERE key = 'test_key'"
        ).fetchone()

        assert result[0] == "test_value"

    def test_update_metadata_upsert(self, bulk_manager):
        """Test that metadata updates existing keys."""
        bulk_manager._update_metadata("test_key", "value1")
        bulk_manager._update_metadata("test_key", "value2")

        result = bulk_manager.conn.execute(
            "SELECT value FROM bulk_metadata WHERE key = 'test_key'"
        ).fetchone()

        assert result[0] == "value2"

    def test_is_fresh_no_data(self, bulk_manager):
        """Test freshness check when no refresh has happened."""
        assert bulk_manager._is_fresh() is False

    def test_is_fresh_recent(self, bulk_manager):
        """Test freshness check after recent refresh."""
        bulk_manager._update_metadata("last_refresh", datetime.now(timezone.utc).isoformat())

        assert bulk_manager._is_fresh(max_age_hours=24) is True

    def test_is_fresh_old(self, bulk_manager):
        """Test freshness check with old data."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        bulk_manager._update_metadata("last_refresh", old_time.isoformat())

        assert bulk_manager._is_fresh(max_age_hours=24) is False

    def test_get_stats(self, populated_manager):
        """Test getting database statistics."""
        stats = populated_manager.get_stats()

        assert stats["ticker_count"] == 3
        assert stats["fact_count"] > 0
        assert "db_path" in stats
        assert "db_size_mb" in stats


# ============================================================================
# Context Manager Tests
# ============================================================================


class TestContextManager:
    """Tests for context manager behavior."""

    def test_context_manager(self, tmp_path, tmp_db_path):
        """Test using BulkDataManager as context manager."""
        with BulkDataManager(db_path=tmp_db_path, bulk_dir=tmp_path / "bulk") as manager:
            manager.initialize_schema()
            result = manager.conn.execute(
                "SELECT COUNT(*) FROM company_tickers"
            ).fetchone()
            assert result[0] == 0

        # Connection should be closed (thread-local storage)
        assert not hasattr(manager._local, "conn") or manager._local.conn is None

    def test_close_idempotent(self, bulk_manager):
        """Test that close() can be called multiple times."""
        bulk_manager.close()
        bulk_manager.close()  # Should not error

        # Reopening should work - accessing conn creates a new connection
        _ = bulk_manager.conn
        assert hasattr(bulk_manager._local, "conn") and bulk_manager._local.conn is not None


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_database_queries(self, bulk_manager):
        """Test queries on empty database."""
        # Should return None/empty, not error
        assert bulk_manager.get_cik("AAPL") is None
        assert bulk_manager.get_ticker("0000320193") is None
        assert bulk_manager.get_company_info("AAPL") is None

        result = bulk_manager.query_financials("AAPL", ["Revenues"], years=5)
        assert result["error"] is not None

    def test_stats_empty_database(self, bulk_manager):
        """Test getting stats on empty database."""
        stats = bulk_manager.get_stats()

        assert stats["ticker_count"] == 0
        assert stats["fact_count"] == 0
        assert stats["last_refresh"] is None

    def test_malformed_cik_handling(self, populated_manager):
        """Test handling of malformed CIK values."""
        # These should not crash
        ticker = populated_manager.get_ticker("")
        assert ticker is None

        ticker = populated_manager.get_ticker("abc")
        assert ticker is None


# ============================================================================
# Import Data Tests
# ============================================================================


class TestDataImport:
    """Tests for data import functionality."""

    def test_import_company_data(self, bulk_manager):
        """Test importing a single company's data."""
        sample_data = {
            "cik": 12345,
            "entityName": "Test Company Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "label": "Total Revenue",
                        "description": "Total revenue",
                        "units": {
                            "USD": [
                                {
                                    "end": "2023-12-31",
                                    "fy": 2023,
                                    "fp": "FY",
                                    "form": "10-K",
                                    "val": 1000000,
                                    "accn": "0000012345-24-000001",
                                    "filed": "2024-02-15",
                                }
                            ]
                        },
                    }
                }
            },
        }

        bulk_manager._import_company_data(sample_data)

        # Check facts were imported
        result = bulk_manager.conn.execute(
            "SELECT value FROM company_facts WHERE concept = 'Revenues'"
        ).fetchone()

        assert result[0] == 1000000

    def test_import_empty_facts(self, bulk_manager):
        """Test importing company with no facts."""
        sample_data = {
            "cik": 99999,
            "entityName": "Empty Company",
            "facts": {},
        }

        # Should not error
        bulk_manager._import_company_data(sample_data)

        result = bulk_manager.conn.execute(
            "SELECT COUNT(*) FROM company_facts WHERE cik = '0000099999'"
        ).fetchone()
        assert result[0] == 0
