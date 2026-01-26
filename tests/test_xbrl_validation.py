"""
Tests for XBRL data extraction validation in EdgarClient.

These tests verify that:
1. Data validation catches invalid values
2. Completeness tracking works correctly
3. Warnings are logged for low data quality
4. Invalid metrics are rejected appropriately
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from asymmetric.core.data.edgar_client import EdgarClient


class TestMetricValidation:
    """Tests for _validate_metric() method."""

    @pytest.fixture
    def client(self):
        """Create EdgarClient with mocked identity."""
        with patch.dict('os.environ', {'SEC_IDENTITY': 'Test/1.0 (test@test.com)'}):
            return EdgarClient()

    def test_valid_revenue(self, client):
        """Positive revenue is valid."""
        assert client._validate_metric("revenue", 1_000_000) == "valid"
        assert client._validate_metric("revenue", 0) == "valid"  # Zero is OK

    def test_negative_revenue_invalid(self, client):
        """Negative revenue is invalid."""
        assert client._validate_metric("revenue", -1_000_000) == "negative_revenue"

    def test_valid_total_assets(self, client):
        """Positive total assets is valid."""
        assert client._validate_metric("total_assets", 100_000_000) == "valid"

    def test_zero_assets_invalid(self, client):
        """Zero or negative total assets is invalid."""
        assert client._validate_metric("total_assets", 0) == "non_positive_assets"
        assert client._validate_metric("total_assets", -1) == "non_positive_assets"

    def test_valid_shares_outstanding(self, client):
        """Reasonable shares outstanding is valid."""
        assert client._validate_metric("shares_outstanding", 1_000_000) == "valid"
        assert client._validate_metric("shares_outstanding", 10_000_000_000) == "valid"  # 10B OK

    def test_unreasonable_shares_invalid(self, client):
        """Unreasonably high shares is invalid."""
        assert client._validate_metric("shares_outstanding", 200_000_000_000) == "unreasonable_shares"

    def test_zero_shares_invalid(self, client):
        """Zero or negative shares is invalid."""
        assert client._validate_metric("shares_outstanding", 0) == "non_positive_shares"
        assert client._validate_metric("shares_outstanding", -100) == "non_positive_shares"

    def test_negative_net_income_valid(self, client):
        """Negative net income (loss) is valid."""
        assert client._validate_metric("net_income", -50_000_000) == "valid"

    def test_negative_retained_earnings_valid(self, client):
        """Negative retained earnings (accumulated deficit) is valid."""
        assert client._validate_metric("retained_earnings", -100_000_000) == "valid"

    def test_negative_operating_cash_flow_valid(self, client):
        """Negative operating cash flow is valid."""
        assert client._validate_metric("operating_cash_flow", -20_000_000) == "valid"

    def test_negative_current_assets_invalid(self, client):
        """Negative current assets is invalid."""
        assert client._validate_metric("current_assets", -1_000) == "negative_current_assets"

    def test_negative_current_liabilities_invalid(self, client):
        """Negative current liabilities is invalid."""
        assert client._validate_metric("current_liabilities", -1_000) == "negative_current_liabilities"

    def test_negative_debt_invalid(self, client):
        """Negative long-term debt is invalid."""
        assert client._validate_metric("long_term_debt", -1_000) == "negative_debt"

    def test_nan_value_invalid(self, client):
        """NaN values are invalid."""
        import math
        assert client._validate_metric("revenue", float('nan')) == "nan_value"
        assert client._validate_metric("total_assets", math.nan) == "nan_value"

    def test_unknown_metric_valid(self, client):
        """Unknown metrics pass validation by default."""
        assert client._validate_metric("custom_metric", 12345) == "valid"


class TestExtractionMetadata:
    """Tests for extraction metadata and completeness tracking."""

    @pytest.fixture
    def client(self):
        """Create EdgarClient with mocked identity."""
        with patch.dict('os.environ', {'SEC_IDENTITY': 'Test/1.0 (test@test.com)'}):
            return EdgarClient()

    @pytest.fixture
    def mock_filing(self):
        """Create a mock filing object."""
        filing = MagicMock()
        filing.accession_number = "0000000001-24-000001"
        filing.filing_date = "2024-01-15"
        return filing

    @pytest.fixture
    def mock_xbrl_complete(self):
        """Create mock XBRL with complete core metrics."""
        xbrl = MagicMock()
        xbrl.period_of_report = "2023-12-31"

        # Create mock facts that return data for all core metrics
        def mock_get_facts(concept):
            core_values = {
                "Revenues": 100_000_000,
                "NetIncomeLoss": 15_000_000,
                "Assets": 200_000_000,
                "AssetsCurrent": 80_000_000,
                "LiabilitiesCurrent": 50_000_000,
                "NetCashProvidedByUsedInOperatingActivities": 20_000_000,
                "GrossProfit": 40_000_000,
                "Liabilities": 100_000_000,
                "StockholdersEquity": 100_000_000,
            }
            if concept in core_values:
                df = pd.DataFrame({
                    "numeric_value": [core_values[concept]],
                    "period_end": ["2023-12-31"],
                })
                return df
            return pd.DataFrame()

        facts = MagicMock()
        facts.get_facts_by_concept = mock_get_facts
        xbrl.facts = facts
        return xbrl

    @pytest.fixture
    def mock_xbrl_partial(self):
        """Create mock XBRL with only some core metrics."""
        xbrl = MagicMock()
        xbrl.period_of_report = "2023-12-31"

        # Only return revenue and assets
        def mock_get_facts(concept):
            partial_values = {
                "Revenues": 50_000_000,
                "Assets": 100_000_000,
            }
            if concept in partial_values:
                df = pd.DataFrame({
                    "numeric_value": [partial_values[concept]],
                    "period_end": ["2023-12-31"],
                })
                return df
            return pd.DataFrame()

        facts = MagicMock()
        facts.get_facts_by_concept = mock_get_facts
        xbrl.facts = facts
        return xbrl

    @pytest.fixture
    def mock_xbrl_no_facts(self):
        """Create mock XBRL with no facts."""
        xbrl = MagicMock()
        xbrl.period_of_report = "2023-12-31"
        xbrl.facts = None
        return xbrl

    def test_complete_extraction_high_completeness(
        self, client, mock_xbrl_complete, mock_filing
    ):
        """Complete data extraction should have high completeness."""
        result = client._extract_financials(mock_xbrl_complete, mock_filing)

        assert "_data_completeness" in result
        assert result["_data_completeness"] >= 0.8  # At least 80%
        assert "_extraction_metadata" in result
        assert result["_metrics_found"] >= 6

    def test_partial_extraction_low_completeness(
        self, client, mock_xbrl_partial, mock_filing
    ):
        """Partial data extraction should have low completeness."""
        result = client._extract_financials(mock_xbrl_partial, mock_filing)

        assert "_data_completeness" in result
        assert result["_data_completeness"] < 0.5  # Less than 50%
        assert "_extraction_metadata" in result

        # Check that missing metrics are tracked
        metadata = result["_extraction_metadata"]
        assert "net_income" in metadata
        assert metadata["net_income"] == "not_found"

    def test_no_facts_zero_completeness(
        self, client, mock_xbrl_no_facts, mock_filing
    ):
        """No facts should result in zero completeness."""
        result = client._extract_financials(mock_xbrl_no_facts, mock_filing)

        assert result["_data_completeness"] == 0.0
        assert "_extraction_metadata" in result
        assert "_error" in result["_extraction_metadata"]

    def test_invalid_values_tracked_separately(self, client, mock_filing):
        """Invalid values should be tracked in metrics_invalid."""
        xbrl = MagicMock()
        xbrl.period_of_report = "2023-12-31"

        # Return negative revenue (invalid)
        def mock_get_facts(concept):
            if concept == "Revenues":
                df = pd.DataFrame({
                    "numeric_value": [-100_000_000],  # Negative!
                    "period_end": ["2023-12-31"],
                })
                return df
            if concept == "Assets":
                df = pd.DataFrame({
                    "numeric_value": [200_000_000],
                    "period_end": ["2023-12-31"],
                })
                return df
            return pd.DataFrame()

        facts = MagicMock()
        facts.get_facts_by_concept = mock_get_facts
        xbrl.facts = facts

        result = client._extract_financials(xbrl, mock_filing)

        # Revenue should be invalid
        assert "_metrics_invalid" in result
        assert result["_metrics_invalid"] >= 1

        # Revenue should NOT be in the period_data (rejected)
        assert "revenue" not in result

        # But total_assets should be there
        assert result.get("total_assets") == 200_000_000

    def test_extraction_metadata_tracks_all_metrics(
        self, client, mock_xbrl_complete, mock_filing
    ):
        """Extraction metadata should track status of all attempted metrics."""
        result = client._extract_financials(mock_xbrl_complete, mock_filing)

        metadata = result["_extraction_metadata"]

        # Should have entries for all attempted metrics
        expected_metrics = [
            "revenue", "gross_profit", "net_income", "total_assets",
            "current_assets", "current_liabilities", "total_liabilities"
        ]

        for metric in expected_metrics:
            assert metric in metadata, f"Missing metadata for {metric}"
            # Status should be one of: found, not_found, or invalid:*
            assert metadata[metric] in ["found", "not_found"] or metadata[metric].startswith("invalid:")


class TestLowCompletenessWarning:
    """Tests for low completeness warning logging."""

    @pytest.fixture
    def client(self):
        """Create EdgarClient with mocked identity."""
        with patch.dict('os.environ', {'SEC_IDENTITY': 'Test/1.0 (test@test.com)'}):
            return EdgarClient()

    def test_low_completeness_logs_warning(self, client, caplog):
        """Low completeness should trigger a warning log."""
        import logging

        xbrl = MagicMock()
        xbrl.period_of_report = "2023-12-31"

        # Return only one metric
        def mock_get_facts(concept):
            if concept == "Revenues":
                df = pd.DataFrame({
                    "numeric_value": [100_000_000],
                    "period_end": ["2023-12-31"],
                })
                return df
            return pd.DataFrame()

        facts = MagicMock()
        facts.get_facts_by_concept = mock_get_facts
        xbrl.facts = facts

        filing = MagicMock()
        filing.accession_number = "0000000001-24-000001"
        filing.filing_date = "2024-01-15"

        with caplog.at_level(logging.WARNING):
            result = client._extract_financials(xbrl, filing)

        # Should have logged a warning about low completeness
        assert result["_data_completeness"] < 0.5
        assert any("Low data completeness" in record.message for record in caplog.records)


class TestIntegrationWithScoring:
    """Tests verifying extraction metadata integrates with scoring."""

    def test_extraction_metadata_doesnt_break_scoring(self):
        """Ensure extraction metadata fields don't interfere with scoring."""
        from asymmetric.core.scoring.piotroski import PiotroskiScorer

        # Financial data with extraction metadata (as would come from edgar_client)
        current = {
            "revenue": 100_000_000,
            "gross_profit": 40_000_000,
            "net_income": 15_000_000,
            "total_assets": 200_000_000,
            "current_assets": 80_000_000,
            "current_liabilities": 50_000_000,
            "long_term_debt": 30_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 20_000_000,
            # Metadata fields (should be ignored by scorer)
            "_extraction_metadata": {"revenue": "found", "net_income": "found"},
            "_data_completeness": 0.95,
            "_metrics_found": 10,
            "_metrics_invalid": 0,
        }

        prior = {
            "revenue": 90_000_000,
            "gross_profit": 35_000_000,
            "net_income": 12_000_000,
            "total_assets": 180_000_000,
            "current_assets": 70_000_000,
            "current_liabilities": 45_000_000,
            "long_term_debt": 35_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 16_000_000,
        }

        scorer = PiotroskiScorer()
        result = scorer.calculate_from_dict(current, prior, require_all_signals=False)

        # Should calculate successfully
        assert result.score >= 0
        assert result.score <= 9
