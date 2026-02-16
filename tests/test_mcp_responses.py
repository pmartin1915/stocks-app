"""Tests for MCP tool response schemas and validation.

Validates that each MCP tool returns the expected keys and types,
including error cases and edge conditions.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_server():
    """Create an AsymmetricMCPServer with mocked dependencies."""
    from asymmetric.mcp.server import AsymmetricMCPServer

    server = AsymmetricMCPServer.__new__(AsymmetricMCPServer)
    server.config = MagicMock()
    server.config.enable_ai_tools = True
    server.config.prefer_bulk_data = True
    server._bulk_manager = None
    server._edgar_client = None
    server._gemini_client = None
    server._piotroski_scorer = None
    server._altman_scorer = None
    return server


class TestCalculateScoresSchema:
    """Test that calculate_scores returns expected schema."""

    @pytest.mark.asyncio
    async def test_returns_ticker_and_score_keys(self, mock_server):
        """Successful response includes ticker, piotroski, altman keys."""
        mock_bulk = MagicMock()
        mock_bulk.get_latest_financials.return_value = {
            "revenue": 100_000_000,
            "net_income": 10_000_000,
            "total_assets": 200_000_000,
            "current_assets": 50_000_000,
            "current_liabilities": 30_000_000,
            "long_term_debt": 20_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 15_000_000,
            "gross_profit": 40_000_000,
            "total_liabilities": 50_000_000,
            "retained_earnings": 80_000_000,
            "ebit": 20_000_000,
            "market_cap": 500_000_000,
            "book_equity": 150_000_000,
        }
        mock_bulk.query_financials.return_value = {"data": {}}

        mock_server._get_bulk_manager = lambda: mock_bulk

        result = await mock_server._tool_calculate_scores({"ticker": "AAPL"})

        assert "ticker" in result
        assert result["ticker"] == "AAPL"
        assert "piotroski" in result
        assert "altman" in result

    @pytest.mark.asyncio
    async def test_error_when_no_data(self, mock_server):
        """Returns error dict when no financial data is found."""
        mock_bulk = MagicMock()
        mock_bulk.get_latest_financials.return_value = None

        mock_edgar = MagicMock()
        mock_edgar.get_financials.return_value = {"periods": []}

        mock_server._get_bulk_manager = lambda: mock_bulk
        mock_server._get_edgar_client = lambda: mock_edgar

        result = await mock_server._tool_calculate_scores({"ticker": "FAKE"})

        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_ticker_raises(self, mock_server):
        """Invalid ticker format raises ValueError."""
        with pytest.raises(ValueError):
            await mock_server._tool_calculate_scores({"ticker": ""})


class TestGetFilingSectionSchema:
    """Test that get_filing_section returns expected schema."""

    @pytest.mark.asyncio
    async def test_returns_content_and_truncation_flag(self, mock_server):
        """Successful response includes content, char_count, truncated keys."""
        mock_edgar = MagicMock()
        mock_edgar.get_filing_text.return_value = "Sample filing text content"

        mock_server._get_edgar_client = lambda: mock_edgar

        result = await mock_server._tool_get_filing_section({
            "ticker": "AAPL",
            "section": "Item 1A",
            "filing_type": "10-K",
        })

        assert result["ticker"] == "AAPL"
        assert result["filing_type"] == "10-K"
        assert result["section"] == "Item 1A"
        assert "content" in result
        assert "char_count" in result
        assert "truncated" in result
        assert result["truncated"] is False
        assert "original_char_count" not in result

    @pytest.mark.asyncio
    async def test_truncated_includes_original_char_count(self, mock_server):
        """Truncated response includes original_char_count."""
        # Create text longer than MAX_RESPONSE_CHARS
        long_text = "x" * 200_000

        mock_edgar = MagicMock()
        mock_edgar.get_filing_text.return_value = long_text

        mock_server._get_edgar_client = lambda: mock_edgar

        result = await mock_server._tool_get_filing_section({
            "ticker": "AAPL",
            "section": "Item 1A",
        })

        assert result["truncated"] is True
        assert "original_char_count" in result
        assert result["original_char_count"] == 200_000
        assert result["char_count"] < 200_000

    @pytest.mark.asyncio
    async def test_error_when_section_not_found(self, mock_server):
        """Returns error when section text is empty/None."""
        mock_edgar = MagicMock()
        mock_edgar.get_filing_text.return_value = None

        mock_server._get_edgar_client = lambda: mock_edgar

        result = await mock_server._tool_get_filing_section({
            "ticker": "AAPL",
            "section": "Item 99",
        })

        assert "error" in result


class TestAnalyzeFilingSchema:
    """Test that analyze_filing_with_ai validates input and returns expected schema."""

    @pytest.mark.asyncio
    async def test_rejects_empty_prompt(self, mock_server):
        """Empty prompt returns error."""
        result = await mock_server._tool_analyze_filing_with_ai({
            "ticker": "AAPL",
            "prompt": "",
        })

        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_prompt(self, mock_server):
        """Whitespace-only prompt returns error."""
        result = await mock_server._tool_analyze_filing_with_ai({
            "ticker": "AAPL",
            "prompt": "   \n\t  ",
        })

        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_oversized_prompt(self, mock_server):
        """Prompt over 50K chars returns error with char count."""
        long_prompt = "x" * 51_000

        result = await mock_server._tool_analyze_filing_with_ai({
            "ticker": "AAPL",
            "prompt": long_prompt,
        })

        assert "error" in result
        assert "51000" in result["error"] or "50,000" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_when_ai_disabled(self, mock_server):
        """Returns error when AI tools are disabled."""
        mock_server.config.enable_ai_tools = False

        result = await mock_server._tool_analyze_filing_with_ai({
            "ticker": "AAPL",
            "prompt": "Analyze this company",
        })

        assert "error" in result
        assert "disabled" in result["error"].lower()


class TestScreenUniverseSchema:
    """Test that screen_universe returns expected schema."""

    @pytest.mark.asyncio
    async def test_returns_results_array(self, mock_server):
        """Successful response includes criteria, result_count, results."""
        mock_bulk = MagicMock()
        mock_bulk.has_precomputed_scores.return_value = True
        mock_bulk.get_precomputed_scores.return_value = [
            {
                "ticker": "AAPL",
                "piotroski_score": 8,
                "piotroski_interpretation": "Strong",
                "altman_z_score": 4.5,
                "altman_zone": "Safe",
            },
        ]

        mock_server._get_bulk_manager = lambda: mock_bulk

        result = await mock_server._tool_screen_universe({
            "piotroski_min": 7,
        })

        assert "criteria" in result
        assert "result_count" in result
        assert "results" in result
        assert isinstance(result["results"], list)
        assert result["result_count"] == 1

    @pytest.mark.asyncio
    async def test_result_items_have_required_keys(self, mock_server):
        """Each result item includes ticker, scores, and zone."""
        mock_bulk = MagicMock()
        mock_bulk.has_precomputed_scores.return_value = True
        mock_bulk.get_precomputed_scores.return_value = [
            {
                "ticker": "MSFT",
                "piotroski_score": 7,
                "piotroski_interpretation": "Strong",
                "altman_z_score": 3.2,
                "altman_zone": "Safe",
            },
        ]

        mock_server._get_bulk_manager = lambda: mock_bulk

        result = await mock_server._tool_screen_universe({})
        item = result["results"][0]

        assert "ticker" in item
        assert "piotroski_score" in item
        assert "altman_z_score" in item
        assert "altman_zone" in item
