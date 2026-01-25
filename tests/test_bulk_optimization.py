"""
Tests for the Bulk Data Manager optimization methods.

Tests cover:
- Phase 1: SIC code detection
- Phase 2: Batch financial queries
- Phase 2: Scorable tickers filtering
- Phase 3: Precomputed scores
"""

import pytest
from datetime import datetime

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
    """Create a BulkDataManager with sample data for optimization tests."""
    # Insert sample ticker data with SIC codes
    bulk_manager.conn.executemany(
        """
        INSERT INTO company_tickers (cik, ticker, company_name, sic_code)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("0000320193", "AAPL", "Apple Inc.", "3571"),  # Manufacturing
            ("0000789019", "MSFT", "Microsoft Corporation", "7372"),  # Software
            ("0001018724", "AMZN", "Amazon.com Inc.", "5961"),  # Retail
        ],
    )

    # Insert comprehensive financial data for multiple years
    sample_facts = [
        # Apple 2023 data
        ("0000320193", "us-gaap", "Revenues", "Total Revenue", "USD", "2023-09-30", 2023, "FY", "10-K", 383285000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "NetIncomeLoss", "Net Income", "USD", "2023-09-30", 2023, "FY", "10-K", 96995000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "Assets", "Total Assets", "USD", "2023-09-30", 2023, "FY", "10-K", 352583000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "AssetsCurrent", "Current Assets", "USD", "2023-09-30", 2023, "FY", "10-K", 143566000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "LiabilitiesCurrent", "Current Liabilities", "USD", "2023-09-30", 2023, "FY", "10-K", 145308000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "Liabilities", "Total Liabilities", "USD", "2023-09-30", 2023, "FY", "10-K", 290437000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "RetainedEarningsAccumulatedDeficit", "Retained Earnings", "USD", "2023-09-30", 2023, "FY", "10-K", -214000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "OperatingIncomeLoss", "Operating Income", "USD", "2023-09-30", 2023, "FY", "10-K", 114301000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "StockholdersEquity", "Stockholders Equity", "USD", "2023-09-30", 2023, "FY", "10-K", 62146000000, "0000320193-23-000001", "2023-10-27"),
        ("0000320193", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "Operating Cash Flow", "USD", "2023-09-30", 2023, "FY", "10-K", 110543000000, "0000320193-23-000001", "2023-10-27"),

        # Apple 2022 data (prior period)
        ("0000320193", "us-gaap", "Revenues", "Total Revenue", "USD", "2022-09-24", 2022, "FY", "10-K", 394328000000, "0000320193-22-000001", "2022-10-28"),
        ("0000320193", "us-gaap", "NetIncomeLoss", "Net Income", "USD", "2022-09-24", 2022, "FY", "10-K", 99803000000, "0000320193-22-000001", "2022-10-28"),
        ("0000320193", "us-gaap", "Assets", "Total Assets", "USD", "2022-09-24", 2022, "FY", "10-K", 352755000000, "0000320193-22-000001", "2022-10-28"),
        ("0000320193", "us-gaap", "AssetsCurrent", "Current Assets", "USD", "2022-09-24", 2022, "FY", "10-K", 135405000000, "0000320193-22-000001", "2022-10-28"),
        ("0000320193", "us-gaap", "LiabilitiesCurrent", "Current Liabilities", "USD", "2022-09-24", 2022, "FY", "10-K", 153982000000, "0000320193-22-000001", "2022-10-28"),
        ("0000320193", "us-gaap", "Liabilities", "Total Liabilities", "USD", "2022-09-24", 2022, "FY", "10-K", 302083000000, "0000320193-22-000001", "2022-10-28"),

        # Microsoft 2023 data
        ("0000789019", "us-gaap", "Revenues", "Total Revenue", "USD", "2023-06-30", 2023, "FY", "10-K", 211915000000, "0000789019-23-000001", "2023-07-25"),
        ("0000789019", "us-gaap", "NetIncomeLoss", "Net Income", "USD", "2023-06-30", 2023, "FY", "10-K", 72361000000, "0000789019-23-000001", "2023-07-25"),
        ("0000789019", "us-gaap", "Assets", "Total Assets", "USD", "2023-06-30", 2023, "FY", "10-K", 411976000000, "0000789019-23-000001", "2023-07-25"),
        ("0000789019", "us-gaap", "AssetsCurrent", "Current Assets", "USD", "2023-06-30", 2023, "FY", "10-K", 184257000000, "0000789019-23-000001", "2023-07-25"),
        ("0000789019", "us-gaap", "LiabilitiesCurrent", "Current Liabilities", "USD", "2023-06-30", 2023, "FY", "10-K", 104149000000, "0000789019-23-000001", "2023-07-25"),
        ("0000789019", "us-gaap", "Liabilities", "Total Liabilities", "USD", "2023-06-30", 2023, "FY", "10-K", 205753000000, "0000789019-23-000001", "2023-07-25"),
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
# Phase 1 Tests: SIC Code Detection
# ============================================================================


class TestSICDetection:
    """Tests for SIC code manufacturing detection."""

    def test_manufacturing_sic_code(self, bulk_manager):
        """Test that SIC codes 2000-3999 are manufacturing."""
        assert bulk_manager._is_manufacturing_sic("2834") is True  # Pharmaceuticals
        assert bulk_manager._is_manufacturing_sic("3571") is True  # Computer hardware
        assert bulk_manager._is_manufacturing_sic("2000") is True  # Lower bound
        assert bulk_manager._is_manufacturing_sic("3999") is True  # Upper bound

    def test_non_manufacturing_sic_code(self, bulk_manager):
        """Test that SIC codes outside 2000-3999 are non-manufacturing."""
        assert bulk_manager._is_manufacturing_sic("5961") is False  # Retail
        assert bulk_manager._is_manufacturing_sic("7372") is False  # Software
        assert bulk_manager._is_manufacturing_sic("1000") is False  # Mining
        assert bulk_manager._is_manufacturing_sic("4000") is False  # Just outside

    def test_invalid_sic_code(self, bulk_manager):
        """Test handling of invalid SIC codes."""
        assert bulk_manager._is_manufacturing_sic(None) is False
        assert bulk_manager._is_manufacturing_sic("") is False
        assert bulk_manager._is_manufacturing_sic("abc") is False

    def test_get_sic_info(self, populated_manager):
        """Test getting SIC info for a ticker."""
        info = populated_manager.get_sic_info("AAPL")
        assert info is not None
        assert info["sic_code"] == "3571"
        assert info["is_manufacturing"] is True

        info = populated_manager.get_sic_info("MSFT")
        assert info is not None
        assert info["sic_code"] == "7372"
        assert info["is_manufacturing"] is False

    def test_get_sic_info_not_found(self, populated_manager):
        """Test getting SIC info for unknown ticker."""
        info = populated_manager.get_sic_info("NOTREAL")
        assert info is None


# ============================================================================
# Phase 2 Tests: Batch Financial Queries
# ============================================================================


class TestBatchFinancials:
    """Tests for batch financial query methods."""

    def test_batch_query_returns_multiple_tickers(self, populated_manager):
        """Test batch query returns data for all requested tickers."""
        result = populated_manager.get_batch_financials(["AAPL", "MSFT"], periods=2)

        assert "AAPL" in result
        assert "MSFT" in result
        assert len(result["AAPL"]) >= 1
        assert len(result["MSFT"]) >= 1

    def test_batch_query_returns_multiple_periods(self, populated_manager):
        """Test batch query returns multiple periods of data."""
        result = populated_manager.get_batch_financials(["AAPL"], periods=2)

        assert "AAPL" in result
        assert len(result["AAPL"]) == 2  # 2023 and 2022
        assert result["AAPL"][0]["fiscal_year"] == 2023  # Newest first
        assert result["AAPL"][1]["fiscal_year"] == 2022

    def test_batch_query_maps_concepts(self, populated_manager):
        """Test that XBRL concepts are mapped to our field names."""
        result = populated_manager.get_batch_financials(["AAPL"], periods=1)

        assert "AAPL" in result
        data = result["AAPL"][0]

        # Check mapped fields
        assert "revenue" in data
        assert "net_income" in data
        assert "total_assets" in data
        assert data["revenue"] == 383285000000

    def test_batch_query_handles_missing_tickers(self, populated_manager):
        """Test batch query gracefully handles missing tickers."""
        result = populated_manager.get_batch_financials(["AAPL", "NOTREAL"], periods=2)

        assert "AAPL" in result
        assert "NOTREAL" not in result

    def test_batch_query_empty_list(self, populated_manager):
        """Test batch query with empty list."""
        result = populated_manager.get_batch_financials([], periods=2)
        assert result == {}


class TestScorableTickers:
    """Tests for scorable tickers filtering."""

    def test_get_scorable_tickers(self, populated_manager):
        """Test getting tickers with sufficient data."""
        tickers = populated_manager.get_scorable_tickers(
            require_piotroski=True,
            require_altman=True,
            limit=10,
        )

        # AAPL and MSFT have all required concepts
        assert "AAPL" in tickers or "MSFT" in tickers

    def test_get_scorable_tickers_limit(self, populated_manager):
        """Test limit parameter."""
        tickers = populated_manager.get_scorable_tickers(limit=1)
        assert len(tickers) <= 1

    def test_get_scorable_tickers_empty_db(self, bulk_manager):
        """Test on empty database."""
        tickers = bulk_manager.get_scorable_tickers()
        assert tickers == []


class TestBatchScoresData:
    """Tests for batch score data retrieval."""

    def test_get_batch_scores_data(self, populated_manager):
        """Test getting batch data ready for scoring."""
        data = populated_manager.get_batch_scores_data(tickers=["AAPL"], limit=10)

        assert len(data) >= 1
        record = data[0]

        assert record["ticker"] == "AAPL"
        assert "current_financials" in record
        assert "prior_financials" in record
        assert "company_name" in record


# ============================================================================
# Phase 3 Tests: Precomputed Scores
# ============================================================================


class TestPrecomputedScores:
    """Tests for precomputed scores functionality."""

    def test_has_precomputed_scores_empty(self, bulk_manager):
        """Test has_precomputed_scores on empty table."""
        assert bulk_manager.has_precomputed_scores() is False

    def test_precompute_scores(self, populated_manager):
        """Test precomputing scores."""
        count = populated_manager.precompute_scores(tickers=["AAPL", "MSFT"])

        # Should compute at least some scores
        assert count >= 1
        assert populated_manager.has_precomputed_scores() is True

    def test_get_precomputed_scores(self, populated_manager):
        """Test retrieving precomputed scores."""
        # First precompute
        populated_manager.precompute_scores(tickers=["AAPL", "MSFT"])

        # Then query
        results = populated_manager.get_precomputed_scores(limit=10)

        assert len(results) >= 1
        assert "ticker" in results[0]
        assert "piotroski_score" in results[0]
        assert "altman_z_score" in results[0]

    def test_get_precomputed_scores_filter(self, populated_manager):
        """Test filtering precomputed scores."""
        populated_manager.precompute_scores(tickers=["AAPL", "MSFT"])

        # Query with Piotroski filter
        results = populated_manager.get_precomputed_scores(piotroski_min=7)

        # All results should meet filter
        for r in results:
            if r["piotroski_score"] is not None:
                assert r["piotroski_score"] >= 7

    def test_get_precomputed_scores_zone_filter(self, populated_manager):
        """Test filtering by Altman zone."""
        populated_manager.precompute_scores(tickers=["AAPL", "MSFT"])

        # Query for Safe zone only
        results = populated_manager.get_precomputed_scores(altman_zone="Safe")

        for r in results:
            assert r["altman_zone"] == "Safe"

    def test_get_precomputed_scores_empty(self, bulk_manager):
        """Test querying empty precomputed scores."""
        results = bulk_manager.get_precomputed_scores()
        assert results == []

    def test_get_scores_stats(self, populated_manager):
        """Test getting scores statistics."""
        # Before precomputation
        stats = populated_manager.get_scores_stats()
        assert stats["scores_count"] == 0

        # After precomputation
        populated_manager.precompute_scores(tickers=["AAPL"])
        stats = populated_manager.get_scores_stats()
        assert stats["scores_count"] >= 1
        assert stats["last_computed"] is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestOptimizationIntegration:
    """Integration tests for optimization features."""

    def test_batch_vs_individual_consistency(self, populated_manager):
        """Verify batch query results match individual query results."""
        # Get individual results
        individual = populated_manager.get_financials_periods("AAPL", periods=2)

        # Get batch results
        batch = populated_manager.get_batch_financials(["AAPL"], periods=2)

        # Compare - both should have same fiscal years
        if individual and "AAPL" in batch:
            individual_years = [p["fiscal_year"] for p in individual if "fiscal_year" in p]
            batch_years = [p["fiscal_year"] for p in batch["AAPL"] if "fiscal_year" in p]

            # Both should have same years (order may differ)
            assert set(individual_years) == set(batch_years)

    def test_precompute_uses_batch(self, populated_manager):
        """Test that precompute_scores works correctly with batch data."""
        # Precompute should work without errors
        count = populated_manager.precompute_scores(tickers=["AAPL", "MSFT"])
        assert count >= 1

        # Results should be queryable
        results = populated_manager.get_precomputed_scores(limit=10)
        assert len(results) >= 1

        # Should include expected tickers
        tickers = [r["ticker"] for r in results]
        assert "AAPL" in tickers or "MSFT" in tickers
