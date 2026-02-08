"""
Tests for MCP server tools.
"""

import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from asymmetric.mcp.server import (
    AsymmetricMCPServer,
    ServerConfig,
    _format_json_response,
    _truncate_response,
    MAX_RESPONSE_CHARS,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_truncate_response_short(self):
        """Should not truncate short text."""
        text = "Short text"
        result = _truncate_response(text)
        assert result == text

    def test_truncate_response_long(self):
        """Should truncate long text."""
        text = "x" * (MAX_RESPONSE_CHARS + 1000)
        result = _truncate_response(text)

        assert len(result) < len(text)
        assert "Truncated" in result
        assert "1000 chars omitted" in result

    def test_truncate_response_custom_limit(self):
        """Should respect custom limit."""
        text = "x" * 200
        result = _truncate_response(text, max_chars=100)

        assert len(result) < 200
        assert "Truncated" in result

    def test_format_json_response(self):
        """Should format dict as JSON."""
        data = {"ticker": "AAPL", "score": 7}
        result = _format_json_response(data)

        assert json.loads(result) == data
        assert '"ticker": "AAPL"' in result

    def test_format_json_response_with_datetime(self):
        """Should handle datetime objects."""
        from datetime import datetime

        data = {"timestamp": datetime(2024, 1, 1, 12, 0, 0)}
        result = _format_json_response(data)

        # Should not raise, datetime converted to string
        parsed = json.loads(result)
        assert "2024" in parsed["timestamp"]


class TestServerConfig:
    """Tests for ServerConfig."""

    def test_default_config(self):
        """Should have sensible defaults loaded from central config."""
        from asymmetric.config import config as app_config

        server_config = ServerConfig()

        assert server_config.transport == "stdio"
        # Port default comes from central config (ASYMMETRIC_MCP_PORT)
        assert server_config.port == app_config.mcp_default_port
        assert server_config.host == "127.0.0.1"
        assert server_config.enable_ai_tools is True
        assert server_config.prefer_bulk_data is True

    def test_custom_config(self):
        """Should accept custom values."""
        config = ServerConfig(
            transport="http",
            port=9000,
            enable_ai_tools=False,
        )

        assert config.transport == "http"
        assert config.port == 9000
        assert config.enable_ai_tools is False


class TestAsymmetricMCPServer:
    """Tests for MCP server."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        config = ServerConfig(enable_ai_tools=False)
        return AsymmetricMCPServer(config)

    def test_server_creation(self, server):
        """Should create server with config."""
        assert server.config is not None
        assert server.server is not None

    def test_lazy_loading_edgar_client(self, server):
        """Should lazy-load EdgarClient."""
        # Client should be None initially
        assert server._edgar_client is None

        # Access should create it
        with patch("asymmetric.core.data.edgar_client.EdgarClient") as mock:
            mock.return_value = MagicMock()
            client = server._get_edgar_client()
            assert client is not None
            mock.assert_called_once()

    def test_lazy_loading_bulk_manager(self, server):
        """Should lazy-load BulkDataManager."""
        assert server._bulk_manager is None

        with patch("asymmetric.core.data.bulk_manager.BulkDataManager") as mock:
            mock.return_value = MagicMock()
            manager = server._get_bulk_manager()
            assert manager is not None
            mock.assert_called_once()


class TestMCPTools:
    """Tests for individual MCP tools."""

    @pytest.fixture
    def server(self):
        """Create server with mocked dependencies."""
        config = ServerConfig(enable_ai_tools=False, prefer_bulk_data=True)
        server = AsymmetricMCPServer(config)
        return server

    @pytest.mark.asyncio
    async def test_lookup_company_from_bulk(self, server):
        """Should lookup company from bulk data."""
        mock_bulk = MagicMock()
        mock_bulk.get_company_info.return_value = {
            "cik": "0000320193",
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
        }
        server._bulk_manager = mock_bulk

        result = await server._tool_lookup_company({"ticker": "AAPL"})

        assert result["ticker"] == "AAPL"
        assert result["source"] == "bulk_data"
        mock_bulk.get_company_info.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_lookup_company_fallback_to_api(self, server):
        """Should fall back to API when bulk data unavailable."""
        mock_bulk = MagicMock()
        mock_bulk.get_company_info.return_value = None
        server._bulk_manager = mock_bulk

        mock_edgar = MagicMock()
        mock_company = MagicMock()
        mock_company.cik = "0000320193"
        mock_company.name = "Apple Inc."
        mock_edgar.get_company.return_value = mock_company
        server._edgar_client = mock_edgar

        result = await server._tool_lookup_company({"ticker": "AAPL"})

        assert result["source"] == "live_api"
        assert result["cik"] == "0000320193"

    @pytest.mark.asyncio
    async def test_get_financials_summary(self, server):
        """Should get financials from bulk data."""
        mock_bulk = MagicMock()
        mock_bulk.query_financials.return_value = {
            "ticker": "AAPL",
            "cik": "0000320193",
            "data": {
                "Revenues": [{"fiscal_year": 2024, "value": 400_000_000_000}],
            },
        }
        server._bulk_manager = mock_bulk

        result = await server._tool_get_financials_summary({
            "ticker": "AAPL",
            "periods": 3,
        })

        assert result["ticker"] == "AAPL"
        assert result["source"] == "bulk_data"
        assert "Revenues" in result["data"]

    @pytest.mark.asyncio
    async def test_calculate_scores(self, server):
        """Should calculate Piotroski and Altman scores."""
        mock_bulk = MagicMock()
        mock_bulk.get_latest_financials.return_value = {
            "revenue": 100_000_000,
            "net_income": 10_000_000,
            "total_assets": 200_000_000,
            "current_assets": 50_000_000,
            "current_liabilities": 30_000_000,
            "operating_cash_flow": 15_000_000,
            "fiscal_year": 2024,
        }
        mock_bulk.query_financials.return_value = {"data": {}}
        server._bulk_manager = mock_bulk

        result = await server._tool_calculate_scores({"ticker": "AAPL"})

        assert result["ticker"] == "AAPL"
        assert "piotroski" in result
        assert "altman" in result

    @pytest.mark.asyncio
    async def test_get_filing_section(self, server):
        """Should get filing section."""
        mock_edgar = MagicMock()
        mock_edgar.get_filing_text.return_value = "Risk factors content here..."
        server._edgar_client = mock_edgar

        result = await server._tool_get_filing_section({
            "ticker": "AAPL",
            "section": "Item 1A",
            "filing_type": "10-K",
        })

        assert result["ticker"] == "AAPL"
        assert result["section"] == "Item 1A"
        assert "Risk factors" in result["content"]

    @pytest.mark.asyncio
    async def test_analyze_filing_disabled(self, server):
        """Should return error when AI tools disabled."""
        server.config.enable_ai_tools = False

        result = await server._tool_analyze_filing_with_ai({
            "ticker": "AAPL",
            "prompt": "Summarize risks",
        })

        assert "error" in result
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_screen_universe(self, server):
        """Should screen stocks by criteria."""
        mock_bulk = MagicMock()
        mock_bulk.conn.execute.return_value.fetchall.return_value = [
            ("AAPL",),
            ("MSFT",),
        ]
        mock_bulk.get_latest_financials.return_value = {
            "revenue": 100_000_000,
            "net_income": 10_000_000,
            "total_assets": 200_000_000,
            "current_assets": 50_000_000,
            "current_liabilities": 30_000_000,
        }
        server._bulk_manager = mock_bulk

        result = await server._tool_screen_universe({
            "piotroski_min": 5,
            "limit": 10,
        })

        assert "results" in result
        assert "criteria" in result
        assert result["criteria"]["piotroski_min"] == 5

    @pytest.mark.asyncio
    async def test_extract_custom_metrics_disabled(self, server):
        """Should return error when AI tools disabled."""
        server.config.enable_ai_tools = False

        result = await server._tool_extract_custom_metrics({
            "ticker": "AAPL",
            "metrics": ["ARR", "NRR"],
        })

        assert "error" in result

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self, server):
        """Should return error for unknown tool."""
        result = await server._dispatch_tool("unknown_tool", {})

        assert "error" in result
        assert "Unknown tool" in result["error"]


class TestToolDispatch:
    """Tests for tool dispatch."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        return AsymmetricMCPServer()

    @pytest.mark.asyncio
    async def test_dispatch_lookup_company(self, server):
        """Should dispatch to lookup_company handler."""
        with patch.object(server, "_tool_lookup_company", new_callable=AsyncMock) as mock:
            mock.return_value = {"ticker": "AAPL"}

            result = await server._dispatch_tool("lookup_company", {"ticker": "AAPL"})

            mock.assert_called_once_with({"ticker": "AAPL"})
            assert result["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_dispatch_calculate_scores(self, server):
        """Should dispatch to calculate_scores handler."""
        with patch.object(server, "_tool_calculate_scores", new_callable=AsyncMock) as mock:
            mock.return_value = {"ticker": "AAPL", "piotroski": {"score": 7}}

            result = await server._dispatch_tool("calculate_scores", {"ticker": "AAPL"})

            mock.assert_called_once()
            assert result["piotroski"]["score"] == 7
