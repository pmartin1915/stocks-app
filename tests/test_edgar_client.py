"""
Tests for the SEC EDGAR Client.

Note: Tests marked with @pytest.mark.slow make actual API calls and
should be run sparingly to respect SEC rate limits.
"""

from unittest.mock import MagicMock, patch

import pytest

from asymmetric.core.data.edgar_client import EdgarClient, EdgarConfig
from asymmetric.core.data.exceptions import (
    SECEmptyResponseError,
    SECIdentityError,
    SECRateLimitError,
)


class TestEdgarConfig:
    """Tests for EdgarConfig dataclass."""

    def test_default_identity_from_env(self, monkeypatch):
        """Test identity loaded from environment."""
        monkeypatch.setenv("SEC_IDENTITY", "Test/1.0 (test@test.com)")

        config = EdgarConfig()

        assert config.identity == "Test/1.0 (test@test.com)"

    def test_identity_fallback(self, monkeypatch):
        """Test identity fallback when env not set."""
        monkeypatch.delenv("SEC_IDENTITY", raising=False)

        config = EdgarConfig()

        assert config.identity == "Asymmetric/1.0 (admin@example.com)"


class TestEdgarClientInitialization:
    """Tests for EdgarClient initialization."""

    def test_init_creates_directories(self, tmp_path, mock_sec_identity):
        """Test that init creates cache and bulk directories."""
        config = EdgarConfig(
            identity="Test/1.0 (test@test.com)",
            cache_dir=tmp_path / "cache",
            bulk_dir=tmp_path / "bulk",
        )

        with patch("edgar.set_identity"):
            client = EdgarClient(config)

        assert (tmp_path / "cache").exists()
        assert (tmp_path / "bulk").exists()

    def test_init_sets_identity(self, mock_sec_identity):
        """Test that init sets edgartools identity."""
        with patch("edgar.set_identity") as mock_set:
            config = EdgarConfig(identity="Test/1.0 (test@test.com)")
            EdgarClient(config)

            mock_set.assert_called_once_with("Test/1.0 (test@test.com)")

    def test_init_validates_identity_format(self, monkeypatch):
        """Test that invalid identity format raises error."""
        monkeypatch.setenv("SEC_IDENTITY", "invalid-format")

        with pytest.raises(SECIdentityError):
            config = EdgarConfig(identity="invalid-format")
            EdgarClient(config)


class TestEdgarClientGetCompany:
    """Tests for EdgarClient.get_company method."""

    @pytest.fixture
    def client(self, mock_sec_identity):
        """Create a client with mocked dependencies."""
        with patch("edgar.set_identity"):
            return EdgarClient()

    def test_get_company_success(self, client):
        """Test successful company lookup."""
        mock_company = MagicMock()
        mock_company.cik = "0000320193"
        mock_company.name = "APPLE INC"

        with patch("edgar.Company", return_value=mock_company):
            result = client.get_company("AAPL")

        assert result is not None
        assert result.cik == "0000320193"

    def test_get_company_empty_cik_raises(self, client):
        """Test that empty CIK (graylisting) raises error."""
        mock_company = MagicMock()
        mock_company.cik = None  # Simulates graylisting

        with patch("edgar.Company", return_value=mock_company):
            with pytest.raises(SECEmptyResponseError):
                client.get_company("FAKE")

    def test_get_company_rate_limit_error(self, client):
        """Test that 429 errors are handled."""
        with patch(
            "edgar.Company",
            side_effect=IOError("429 Too Many Requests"),
        ):
            with pytest.raises(SECRateLimitError) as exc_info:
                client.get_company("AAPL")

            assert exc_info.value.status_code == 429


class TestEdgarClientGetFinancials:
    """Tests for EdgarClient.get_financials method."""

    @pytest.fixture
    def client(self, mock_sec_identity):
        """Create a client with mocked dependencies."""
        with patch("edgar.set_identity"):
            return EdgarClient()

    def test_get_financials_returns_structure(self, client):
        """Test that get_financials returns expected structure."""
        mock_company = MagicMock()
        mock_company.cik = "0000320193"

        mock_filing = MagicMock()
        mock_filing.accession_number = "0000320193-24-000001"
        mock_filing.filing_date = "2024-01-15"
        mock_filing.xbrl.return_value = None  # No XBRL data

        mock_filings = MagicMock()
        mock_filings.head.return_value = [mock_filing]
        mock_company.get_filings.return_value = mock_filings

        with patch("edgar.Company", return_value=mock_company):
            result = client.get_financials("AAPL", periods=1)

        assert "ticker" in result
        assert "periods" in result
        assert "source" in result
        assert result["ticker"] == "AAPL"

    def test_get_financials_company_not_found(self, client):
        """Test handling of company not found."""
        mock_company = MagicMock()
        mock_company.cik = None

        with patch("edgar.Company", return_value=mock_company):
            with pytest.raises(SECEmptyResponseError):
                client.get_financials("NOTREAL")


class TestEdgarClientTextCleaning:
    """Tests for text cleaning functionality."""

    @pytest.fixture
    def client(self, mock_sec_identity):
        """Create a client with mocked dependencies."""
        with patch("edgar.set_identity"):
            return EdgarClient()

    def test_clean_removes_html_tags(self, client):
        """Test that HTML tags are removed."""
        text = "<div><p>Hello <b>World</b></p></div>"

        result = client._clean_filing_text(text)

        assert "<" not in result
        assert ">" not in result
        assert "Hello" in result
        assert "World" in result

    def test_clean_normalizes_whitespace(self, client):
        """Test that excessive whitespace is normalized."""
        text = "Hello    World\n\n\n\tTest"

        result = client._clean_filing_text(text)

        assert "    " not in result
        assert "\n\n" not in result
        assert "Hello World Test" == result

    def test_clean_handles_empty_string(self, client):
        """Test that empty strings are handled."""
        result = client._clean_filing_text("")

        assert result == ""

    def test_clean_handles_none(self, client):
        """Test that None is handled."""
        result = client._clean_filing_text(None)

        assert result == ""


# Integration tests (require actual API access)
@pytest.mark.slow
class TestEdgarClientIntegration:
    """Integration tests that make actual SEC API calls.

    Run with: pytest -m slow
    """

    @pytest.fixture
    def live_client(self, monkeypatch):
        """Create a client for live API testing."""
        # Use test identity
        monkeypatch.setenv("SEC_IDENTITY", "AsymmetricTest/1.0 (test@testing.dev)")
        return EdgarClient()

    def test_lookup_apple(self, live_client):
        """Test looking up Apple Inc."""
        company = live_client.get_company("AAPL")

        assert company is not None
        assert company.cik is not None
        assert "APPLE" in company.name.upper()

    def test_lookup_microsoft(self, live_client):
        """Test looking up Microsoft."""
        company = live_client.get_company("MSFT")

        assert company is not None
        assert company.cik is not None
