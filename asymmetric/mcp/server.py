"""
MCP Server for Asymmetric Investment Research.

Dual-mode Model Context Protocol server supporting both STDIO (development)
and HTTP (production) transports. Exposes 7 tools for financial research:

Tools:
1. lookup_company - Get company metadata (prefers bulk data)
2. get_financials_summary - Condensed financial data
3. calculate_scores - Piotroski F-Score + Altman Z-Score
4. get_filing_section - Lazy-load specific filing section
5. analyze_filing_with_ai - Gemini-powered analysis with caching
6. screen_universe - Filter stocks by criteria
7. extract_custom_metrics - LLM-aided XBRL parsing

Usage:
    # STDIO mode (development)
    asymmetric mcp start

    # HTTP mode (production)
    asymmetric mcp start --transport http --port 8000

    # Claude Code integration
    claude mcp add asymmetric -- poetry run asymmetric mcp start
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    TextContent,
    Tool,
)

logger = logging.getLogger(__name__)

# Maximum response size (~50K chars to stay under ~12.5K tokens)
MAX_RESPONSE_CHARS = 50_000


@dataclass
class ServerConfig:
    """
    Configuration for the MCP server.

    Port defaults are loaded from central config (single source of truth).
    """

    transport: str = "stdio"  # "stdio" or "http"
    port: Optional[int] = None  # Defaults to config.mcp_default_port
    host: str = "0.0.0.0"
    log_level: str = "INFO"

    # Feature flags
    enable_ai_tools: bool = True  # Requires GEMINI_API_KEY
    prefer_bulk_data: bool = True  # Use local DuckDB when possible
    auto_port: bool = False  # Automatically find available port if specified port is in use

    def __post_init__(self):
        """Load defaults from central config."""
        from asymmetric.config import config

        if self.port is None:
            self.port = config.mcp_default_port


def _truncate_response(text: str, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    """Truncate text to stay within token limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[Truncated: {len(text) - max_chars} chars omitted]"


def _format_json_response(data: Any) -> str:
    """Format data as JSON string for tool response."""
    return json.dumps(data, indent=2, default=str)


class AsymmetricMCPServer:
    """
    MCP Server for Asymmetric investment research tools.

    Provides 7 tools for financial research via MCP protocol:
    - Company lookup and metadata
    - Financial data retrieval
    - Scoring (Piotroski, Altman)
    - AI-powered filing analysis
    - Universe screening
    """

    def __init__(self, config: Optional[ServerConfig] = None):
        """Initialize the MCP server."""
        self.config = config or ServerConfig()
        self.server = Server("asymmetric")

        # Lazy-loaded dependencies
        self._edgar_client = None
        self._bulk_manager = None
        self._gemini_client = None
        self._piotroski_scorer = None
        self._altman_scorer = None

        # Register handlers
        self._register_handlers()

    def _get_edgar_client(self):
        """Lazy-load EdgarClient."""
        if self._edgar_client is None:
            from asymmetric.core.data.edgar_client import EdgarClient

            self._edgar_client = EdgarClient()
        return self._edgar_client

    def _get_bulk_manager(self):
        """Lazy-load BulkDataManager."""
        if self._bulk_manager is None:
            from asymmetric.core.data.bulk_manager import BulkDataManager

            self._bulk_manager = BulkDataManager()
        return self._bulk_manager

    def _get_gemini_client(self):
        """Lazy-load GeminiClient."""
        if self._gemini_client is None:
            from asymmetric.core.ai.gemini_client import get_gemini_client

            self._gemini_client = get_gemini_client()
        return self._gemini_client

    def _get_piotroski_scorer(self):
        """Lazy-load PiotroskiScorer."""
        if self._piotroski_scorer is None:
            from asymmetric.core.scoring.piotroski import PiotroskiScorer

            self._piotroski_scorer = PiotroskiScorer()
        return self._piotroski_scorer

    def _get_altman_scorer(self):
        """Lazy-load AltmanScorer."""
        if self._altman_scorer is None:
            from asymmetric.core.scoring.altman import AltmanScorer

            self._altman_scorer = AltmanScorer()
        return self._altman_scorer

    def _register_handlers(self):
        """Register MCP request handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            tools = [
                Tool(
                    name="lookup_company",
                    description=(
                        "Get company metadata by ticker symbol. Returns CIK, company name, "
                        "SIC code, and exchange. Prefers bulk data for zero-API-call access."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol (e.g., 'AAPL')",
                            },
                        },
                        "required": ["ticker"],
                    },
                ),
                Tool(
                    name="get_financials_summary",
                    description=(
                        "Get condensed financial summary for a company. Returns key metrics "
                        "like revenue, net income, assets, liabilities for recent periods."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol",
                            },
                            "periods": {
                                "type": "integer",
                                "description": "Number of annual periods (default: 3)",
                                "default": 3,
                            },
                        },
                        "required": ["ticker"],
                    },
                ),
                Tool(
                    name="calculate_scores",
                    description=(
                        "Calculate Piotroski F-Score (0-9) and Altman Z-Score for a company. "
                        "F-Score measures financial health. Z-Score predicts bankruptcy risk. "
                        "Returns scores, interpretations, and component breakdowns."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol",
                            },
                            "is_manufacturing": {
                                "type": "boolean",
                                "description": "Use manufacturing Z-Score formula (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["ticker"],
                    },
                ),
                Tool(
                    name="get_filing_section",
                    description=(
                        "Get a specific section from a company's SEC filing. "
                        "Use this for targeted analysis to reduce token usage. "
                        "Common sections: 'Item 1' (Business), 'Item 1A' (Risk Factors), "
                        "'Item 7' (MD&A), 'Item 8' (Financial Statements)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol",
                            },
                            "section": {
                                "type": "string",
                                "description": "Section to retrieve (e.g., 'Item 1A')",
                            },
                            "filing_type": {
                                "type": "string",
                                "description": "Filing type (default: '10-K')",
                                "default": "10-K",
                            },
                        },
                        "required": ["ticker", "section"],
                    },
                ),
                Tool(
                    name="analyze_filing_with_ai",
                    description=(
                        "Analyze SEC filing content with Gemini AI. Uses context caching "
                        "for 10x cost reduction on follow-up queries. Specify a prompt to "
                        "guide analysis (e.g., 'Summarize key risks', 'Identify competitive moat')."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "Analysis prompt/question",
                            },
                            "section": {
                                "type": "string",
                                "description": "Specific section to analyze (optional, reduces cost)",
                            },
                            "filing_type": {
                                "type": "string",
                                "description": "Filing type (default: '10-K')",
                                "default": "10-K",
                            },
                            "model": {
                                "type": "string",
                                "description": "Model to use: 'flash' (fast/cheap) or 'pro' (powerful)",
                                "enum": ["flash", "pro"],
                                "default": "flash",
                            },
                        },
                        "required": ["ticker", "prompt"],
                    },
                ),
                Tool(
                    name="screen_universe",
                    description=(
                        "Screen stocks by quantitative criteria. Filter by Piotroski F-Score, "
                        "Altman Z-Score zone, and other metrics. Returns list of matching tickers "
                        "with their scores."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "piotroski_min": {
                                "type": "integer",
                                "description": "Minimum Piotroski F-Score (0-9)",
                                "minimum": 0,
                                "maximum": 9,
                            },
                            "altman_zone": {
                                "type": "string",
                                "description": "Required Altman zone: 'Safe', 'Grey', or 'Distress'",
                                "enum": ["Safe", "Grey", "Distress"],
                            },
                            "altman_min": {
                                "type": "number",
                                "description": "Minimum Altman Z-Score",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results to return (default: 50)",
                                "default": 50,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="extract_custom_metrics",
                    description=(
                        "Extract custom metrics from SEC filings using LLM. "
                        "Use this for company-specific metrics like ARR, NRR, or non-GAAP "
                        "figures that standard XBRL parsers miss."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol",
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of metric names to extract",
                            },
                            "filing_type": {
                                "type": "string",
                                "description": "Filing type (default: '10-K')",
                                "default": "10-K",
                            },
                        },
                        "required": ["ticker", "metrics"],
                    },
                ),
            ]
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool execution."""
            logger.info(f"Tool called: {name} with args: {arguments}")

            try:
                result = await self._dispatch_tool(name, arguments)
                response_text = _format_json_response(result)
                response_text = _truncate_response(response_text)
                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.exception(f"Tool {name} failed: {e}")
                error_response = {"error": str(e), "tool": name}
                return [TextContent(type="text", text=_format_json_response(error_response))]

    async def _dispatch_tool(self, name: str, arguments: dict) -> dict[str, Any]:
        """Dispatch tool call to appropriate handler."""
        handlers = {
            "lookup_company": self._tool_lookup_company,
            "get_financials_summary": self._tool_get_financials_summary,
            "calculate_scores": self._tool_calculate_scores,
            "get_filing_section": self._tool_get_filing_section,
            "analyze_filing_with_ai": self._tool_analyze_filing_with_ai,
            "screen_universe": self._tool_screen_universe,
            "extract_custom_metrics": self._tool_extract_custom_metrics,
        }

        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        return await handler(arguments)

    # =========================================================================
    # Tool Implementations
    # =========================================================================

    async def _tool_lookup_company(self, args: dict) -> dict[str, Any]:
        """Lookup company by ticker."""
        ticker = args.get("ticker", "").upper()

        # Prefer bulk data (zero API calls)
        if self.config.prefer_bulk_data:
            bulk = self._get_bulk_manager()
            info = bulk.get_company_info(ticker)
            if info:
                info["source"] = "bulk_data"
                return info

        # Fall back to live API
        edgar = self._get_edgar_client()
        company = edgar.get_company(ticker)
        if not company:
            return {"error": f"Company not found: {ticker}"}

        return {
            "ticker": ticker,
            "cik": company.cik,
            "company_name": getattr(company, "name", None),
            "sic_code": getattr(company, "sic", None),
            "source": "live_api",
        }

    async def _tool_get_financials_summary(self, args: dict) -> dict[str, Any]:
        """Get condensed financial summary."""
        ticker = args.get("ticker", "").upper()
        periods = args.get("periods", 3)

        # Try bulk data first
        if self.config.prefer_bulk_data:
            bulk = self._get_bulk_manager()
            concepts = [
                "Revenues",
                "NetIncomeLoss",
                "Assets",
                "Liabilities",
                "StockholdersEquity",
                "NetCashProvidedByUsedInOperatingActivities",
            ]
            data = bulk.query_financials(ticker, concepts, years=periods)
            if data.get("data"):
                data["source"] = "bulk_data"
                return data

        # Fall back to live API
        edgar = self._get_edgar_client()
        financials = edgar.get_financials(ticker, periods=periods)
        financials["source"] = "live_api"
        return financials

    async def _tool_calculate_scores(self, args: dict) -> dict[str, Any]:
        """Calculate Piotroski and Altman scores."""
        ticker = args.get("ticker", "").upper()
        is_manufacturing = args.get("is_manufacturing", True)

        # Get financial data
        bulk = self._get_bulk_manager()
        financials = bulk.get_latest_financials(ticker)

        if not financials:
            edgar = self._get_edgar_client()
            financials_response = edgar.get_financials(ticker, periods=2)
            if not financials_response.get("periods"):
                return {"error": f"No financial data found for {ticker}"}
            financials = financials_response["periods"][0]

        # Need prior period for Piotroski
        prior_financials = {}
        if self.config.prefer_bulk_data:
            # Query for prior year
            bulk_data = bulk.query_financials(
                ticker,
                ["NetIncomeLoss", "Assets", "Liabilities"],
                years=2,
            )
            if bulk_data.get("data"):
                # Try to get prior year data
                for concept, values in bulk_data["data"].items():
                    if len(values) > 1:
                        prior_financials[concept.lower()] = values[1].get("value")

        # Calculate Piotroski F-Score
        piotroski_scorer = self._get_piotroski_scorer()
        try:
            piotroski_result = piotroski_scorer.calculate_from_dict(
                financials, prior_financials
            )
            piotroski = {
                "score": piotroski_result.score,
                "max_score": 9,
                "interpretation": piotroski_result.interpretation,
                "signals_available": piotroski_result.signals_available,
                "profitability_score": piotroski_result.profitability_score,
                "leverage_score": piotroski_result.leverage_score,
                "efficiency_score": piotroski_result.efficiency_score,
            }
        except Exception as e:
            logger.warning(f"Piotroski calculation failed for {ticker}: {e}")
            piotroski = {"error": str(e)}

        # Calculate Altman Z-Score
        altman_scorer = self._get_altman_scorer()
        try:
            altman_result = altman_scorer.calculate_from_dict(
                financials, is_manufacturing=is_manufacturing
            )
            altman = {
                "z_score": round(altman_result.z_score, 2),
                "zone": altman_result.zone,
                "interpretation": altman_result.interpretation,
                "formula_used": altman_result.formula_used,
                "components_calculated": altman_result.components_calculated,
            }
        except Exception as e:
            logger.warning(f"Altman calculation failed for {ticker}: {e}")
            altman = {"error": str(e)}

        return {
            "ticker": ticker,
            "piotroski": piotroski,
            "altman": altman,
            "fiscal_year": financials.get("fiscal_year"),
        }

    async def _tool_get_filing_section(self, args: dict) -> dict[str, Any]:
        """Get specific section from filing."""
        ticker = args.get("ticker", "").upper()
        section = args.get("section", "")
        filing_type = args.get("filing_type", "10-K")

        edgar = self._get_edgar_client()
        text = edgar.get_filing_text(ticker, filing_type=filing_type, section=section)

        if not text:
            return {"error": f"Section '{section}' not found for {ticker} {filing_type}"}

        # Truncate to fit within response limits
        text = _truncate_response(text, MAX_RESPONSE_CHARS - 1000)

        return {
            "ticker": ticker,
            "filing_type": filing_type,
            "section": section,
            "content": text,
            "char_count": len(text),
        }

    async def _tool_analyze_filing_with_ai(self, args: dict) -> dict[str, Any]:
        """Analyze filing with Gemini AI."""
        if not self.config.enable_ai_tools:
            return {"error": "AI tools are disabled. Set GEMINI_API_KEY to enable."}

        ticker = args.get("ticker", "").upper()
        prompt = args.get("prompt", "")
        section = args.get("section")
        filing_type = args.get("filing_type", "10-K")
        model_name = args.get("model", "flash")

        # Get filing text
        edgar = self._get_edgar_client()
        text = edgar.get_filing_text(ticker, filing_type=filing_type, section=section)

        if not text:
            return {"error": f"Filing not found for {ticker}"}

        # Analyze with Gemini
        from asymmetric.core.ai.gemini_client import GeminiModel

        model = GeminiModel.PRO if model_name == "pro" else GeminiModel.FLASH
        gemini = self._get_gemini_client()

        result = gemini.analyze_with_cache(
            context=text,
            prompt=prompt,
            model=model,
        )

        return {
            "ticker": ticker,
            "prompt": prompt,
            "analysis": result.content,
            "model": result.model,
            "cached": result.cached,
            "token_count_input": result.token_count_input,
            "token_count_output": result.token_count_output,
            "estimated_cost_usd": round(result.estimated_cost_usd, 4),
            "latency_ms": result.latency_ms,
        }

    async def _tool_screen_universe(self, args: dict) -> dict[str, Any]:
        """Screen stocks by criteria using optimized batch queries."""
        piotroski_min = args.get("piotroski_min")
        altman_zone = args.get("altman_zone")
        altman_min = args.get("altman_min")
        limit = args.get("limit", 50)

        bulk = self._get_bulk_manager()

        # Try precomputed scores first (near-instant)
        if bulk.has_precomputed_scores():
            results = bulk.get_precomputed_scores(
                piotroski_min=piotroski_min,
                altman_min=altman_min,
                altman_zone=altman_zone,
                limit=limit,
                sort_by="piotroski_score",
                sort_order="desc",
            )
            return {
                "criteria": {
                    "piotroski_min": piotroski_min,
                    "altman_zone": altman_zone,
                    "altman_min": altman_min,
                },
                "result_count": len(results),
                "results": results,
                "source": "precomputed",
            }

        # Fall back to batch calculation
        try:
            tickers = bulk.get_scorable_tickers(limit=1000)
            if not tickers:
                tickers = bulk.get_all_tickers(limit=1000)
        except Exception as e:
            return {"error": f"Failed to get tickers: {e}"}

        if not tickers:
            return {"error": "No tickers available. Run 'asymmetric db refresh' first."}

        # Use batch financial data retrieval
        batch_data = bulk.get_batch_financials(tickers, periods=2)

        results = []
        piotroski_scorer = self._get_piotroski_scorer()
        altman_scorer = self._get_altman_scorer()

        for ticker, periods_data in batch_data.items():
            if len(results) >= limit:
                break

            try:
                if not periods_data:
                    continue

                current = periods_data[0]
                prior = periods_data[1] if len(periods_data) > 1 else {}

                # Calculate scores
                piotroski_result = piotroski_scorer.calculate_from_dict(current, prior)
                altman_result = altman_scorer.calculate_from_dict(current)

                # Apply filters
                if piotroski_min and piotroski_result.score < piotroski_min:
                    continue
                if altman_zone and altman_result.zone != altman_zone:
                    continue
                if altman_min and altman_result.z_score < altman_min:
                    continue

                results.append({
                    "ticker": ticker,
                    "piotroski_score": piotroski_result.score,
                    "piotroski_interpretation": piotroski_result.interpretation,
                    "altman_z_score": round(altman_result.z_score, 2),
                    "altman_zone": altman_result.zone,
                })

            except Exception as e:
                logger.debug(f"Skipping {ticker}: {e}")
                continue

        return {
            "criteria": {
                "piotroski_min": piotroski_min,
                "altman_zone": altman_zone,
                "altman_min": altman_min,
            },
            "result_count": len(results),
            "results": results,
            "source": "batch_calculated",
        }

    async def _tool_extract_custom_metrics(self, args: dict) -> dict[str, Any]:
        """Extract custom metrics using LLM."""
        if not self.config.enable_ai_tools:
            return {"error": "AI tools are disabled. Set GEMINI_API_KEY to enable."}

        ticker = args.get("ticker", "").upper()
        metrics = args.get("metrics", [])
        filing_type = args.get("filing_type", "10-K")

        if not metrics:
            return {"error": "No metrics specified"}

        # Get filing text
        edgar = self._get_edgar_client()
        text = edgar.get_filing_text(ticker, filing_type=filing_type)

        if not text:
            return {"error": f"Filing not found for {ticker}"}

        # Extract with Gemini
        gemini = self._get_gemini_client()
        extracted = gemini.extract_custom_xbrl(text, metrics)

        return {
            "ticker": ticker,
            "filing_type": filing_type,
            "metrics_requested": metrics,
            "extracted_values": extracted,
        }

    # =========================================================================
    # Server Lifecycle
    # =========================================================================

    async def run_stdio(self):
        """Run server with STDIO transport (development mode)."""
        from mcp.server.stdio import stdio_server

        logger.info("Starting Asymmetric MCP server (STDIO mode)")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="asymmetric",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    async def run_http(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        auto_port: bool = False,
    ) -> int:
        """
        Run server with HTTP transport (production mode).

        Args:
            host: Host to bind to
            port: Port to bind to
            auto_port: If True, automatically find available port if specified port is in use

        Returns:
            The actual port the server is running on

        Raises:
            PortInUseError: If port is in use and auto_port is False
        """
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Route
        import uvicorn

        from asymmetric.utils.network import is_port_available, find_available_port
        from asymmetric.core.data.exceptions import PortInUseError

        # Check port availability
        actual_port = port
        if not is_port_available(host, port):
            if auto_port:
                logger.info(f"Port {port} is in use, searching for available port...")
                found_port = find_available_port(host, port + 1, max_attempts=10)
                if found_port is None:
                    raise PortInUseError(host, port)
                actual_port = found_port
                logger.info(f"Found available port: {actual_port}")
            else:
                raise PortInUseError(host, port)

        logger.info(f"Starting Asymmetric MCP server (HTTP mode on {host}:{actual_port})")

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self.server.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name="asymmetric",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
            # Return empty response to avoid NoneType error when client disconnects
            return Response()

        async def handle_messages(request):
            await sse.handle_post_message(request.scope, request.receive, request._send)
            return Response(status_code=202)

        app = Starlette(
            routes=[
                Route("/sse", handle_sse),
                Route("/messages", handle_messages, methods=["POST"]),
            ],
        )

        config = uvicorn.Config(app, host=host, port=actual_port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        return actual_port


def create_server(config: Optional[ServerConfig] = None) -> AsymmetricMCPServer:
    """Create a new MCP server instance."""
    return AsymmetricMCPServer(config)


def run_server(
    transport: str = "stdio",
    host: str = "0.0.0.0",
    port: int = 8000,
    auto_port: bool = False,
) -> int | None:
    """
    Run the MCP server.

    Args:
        transport: "stdio" or "http"
        host: Host to bind for HTTP mode
        port: Port for HTTP mode
        auto_port: If True, automatically find available port if specified port is in use

    Returns:
        The actual port the server is running on (HTTP mode only), or None (STDIO mode)

    Raises:
        PortInUseError: If port is in use and auto_port is False (HTTP mode only)
    """
    from asymmetric.config import config as app_config

    # Determine if AI tools should be enabled
    enable_ai = bool(app_config.gemini_api_key)

    server_config = ServerConfig(
        transport=transport,
        host=host,
        port=port,
        enable_ai_tools=enable_ai,
        auto_port=auto_port,
    )

    server = create_server(server_config)

    if transport == "http":
        return asyncio.run(server.run_http(host, port, auto_port))
    else:
        asyncio.run(server.run_stdio())
        return None
