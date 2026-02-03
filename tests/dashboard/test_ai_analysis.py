"""Tests for dashboard/utils/ai_analysis.py.

Tests AI analysis utilities including context building,
cost estimation, and analysis execution.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


class TestBuildComparisonContext:
    """Tests for build_comparison_context()."""

    def test_builds_context_for_single_stock(self):
        """Should build context for one stock."""
        from dashboard.utils.ai_analysis import build_comparison_context

        results = {
            "AAPL": {
                "piotroski": {
                    "score": 8,
                    "interpretation": "Strong",
                    "profitability": 4,
                    "leverage": 2,
                    "efficiency": 2,
                },
                "altman": {
                    "z_score": 4.5,
                    "zone": "Safe",
                    "interpretation": "Low bankruptcy risk",
                    "formula_used": "Standard",
                },
            }
        }

        context = build_comparison_context(results)

        assert "AAPL" in context
        assert "F-Score: 8/9" in context
        assert "Z-Score: 4.5" in context
        assert "Safe" in context

    def test_builds_context_for_multiple_stocks(self):
        """Should build context for multiple stocks."""
        from dashboard.utils.ai_analysis import build_comparison_context

        results = {
            "AAPL": {
                "piotroski": {"score": 8, "interpretation": "Strong"},
                "altman": {"z_score": 4.5, "zone": "Safe"},
            },
            "MSFT": {
                "piotroski": {"score": 7, "interpretation": "Good"},
                "altman": {"z_score": 5.0, "zone": "Safe"},
            },
        }

        context = build_comparison_context(results)

        assert "AAPL" in context
        assert "MSFT" in context
        assert "---" in context  # Separator between stocks

    def test_skips_stocks_with_errors(self):
        """Should skip stocks that have errors."""
        from dashboard.utils.ai_analysis import build_comparison_context

        results = {
            "AAPL": {
                "piotroski": {"score": 8},
                "altman": {"z_score": 4.5},
            },
            "INVALID": {"error": "No data found"},
        }

        context = build_comparison_context(results)

        assert "AAPL" in context
        assert "INVALID" not in context

    def test_returns_empty_for_empty_results(self):
        """Should return empty string for empty results."""
        from dashboard.utils.ai_analysis import build_comparison_context

        context = build_comparison_context({})

        assert context == ""

    def test_returns_empty_for_all_errors(self):
        """Should return empty string when all stocks have errors."""
        from dashboard.utils.ai_analysis import build_comparison_context

        results = {
            "INVALID1": {"error": "No data"},
            "INVALID2": {"error": "No data"},
        }

        context = build_comparison_context(results)

        assert context == ""


class TestEstimateAnalysisCost:
    """Tests for estimate_analysis_cost()."""

    def test_estimates_cost_for_flash_model(self):
        """Should estimate cost for flash model."""
        from dashboard.utils.ai_analysis import estimate_analysis_cost

        context = "a" * 4000  # ~1000 tokens

        result = estimate_analysis_cost(context, "flash")

        assert result["model"] == "flash"
        assert result["input_tokens"] == 1000
        assert result["estimated_output_tokens"] == 500  # Flash output estimate
        assert result["estimated_cost_usd"] > 0
        assert result["near_cliff"] is False

    def test_estimates_cost_for_pro_model(self):
        """Should estimate cost for pro model."""
        from dashboard.utils.ai_analysis import estimate_analysis_cost

        context = "a" * 4000  # ~1000 tokens

        result = estimate_analysis_cost(context, "pro")

        assert result["model"] == "pro"
        assert result["estimated_output_tokens"] == 1500  # Pro output estimate
        assert result["estimated_cost_usd"] > 0

    def test_detects_near_pricing_cliff(self):
        """Should detect when near 200K token pricing cliff."""
        from dashboard.utils.ai_analysis import estimate_analysis_cost

        # Create context near 200K tokens (~800K chars)
        context = "a" * 800000

        result = estimate_analysis_cost(context, "flash")

        assert result["near_cliff"] is True

    def test_not_near_cliff_for_small_context(self):
        """Should not flag small contexts as near cliff."""
        from dashboard.utils.ai_analysis import estimate_analysis_cost

        context = "a" * 1000

        result = estimate_analysis_cost(context, "flash")

        assert result["near_cliff"] is False


class TestFormatAnalysisMetadata:
    """Tests for format_analysis_metadata()."""

    def test_formats_successful_result(self):
        """Should format metadata for successful analysis."""
        from dashboard.utils.ai_analysis import format_analysis_metadata

        result = {
            "success": True,
            "model": "gemini-2.5-flash",
            "cached": True,
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost_usd": 0.0025,
            "latency_ms": 1500,
        }

        metadata = format_analysis_metadata(result)

        assert "gemini-2.5-flash" in metadata
        assert "Yes" in metadata  # cached
        assert "1,000" in metadata  # input tokens formatted
        assert "500" in metadata  # output tokens
        assert "$0.0025" in metadata
        assert "1,500ms" in metadata

    def test_formats_uncached_result(self):
        """Should show 'No' for uncached results."""
        from dashboard.utils.ai_analysis import format_analysis_metadata

        result = {
            "success": True,
            "model": "gemini-2.5-pro",
            "cached": False,
            "input_tokens": 2000,
            "output_tokens": 1000,
            "cost_usd": 0.015,
            "latency_ms": 3000,
        }

        metadata = format_analysis_metadata(result)

        assert "No" in metadata  # not cached
        assert "gemini-2.5-pro" in metadata

    def test_returns_empty_for_error_result(self):
        """Should return empty string for error results."""
        from dashboard.utils.ai_analysis import format_analysis_metadata

        result = {
            "error": "config",
            "message": "API key not configured",
        }

        metadata = format_analysis_metadata(result)

        assert metadata == ""


class TestRunSingleStockAnalysis:
    """Tests for run_single_stock_analysis()."""

    def test_returns_config_error_when_no_client(self, monkeypatch):
        """Should return config error when Gemini not configured."""
        from dashboard.utils import ai_analysis

        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: None)

        result = ai_analysis.run_single_stock_analysis(
            ticker="AAPL",
            scores={"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
        )

        assert result["error"] == "config"
        assert "GEMINI_API_KEY" in result["message"]

    def test_returns_success_result(self, monkeypatch):
        """Should return success result for valid analysis."""
        from dashboard.utils import ai_analysis

        mock_result = MagicMock()
        mock_result.content = "Analysis content here"
        mock_result.model = "gemini-2.5-flash"
        mock_result.cached = False
        mock_result.token_count_input = 500
        mock_result.token_count_output = 300
        mock_result.estimated_cost_usd = 0.001
        mock_result.latency_ms = 1000

        mock_client = MagicMock()
        mock_client.analyze_with_cache.return_value = mock_result
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        result = ai_analysis.run_single_stock_analysis(
            ticker="AAPL",
            scores={"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
            model="flash",
        )

        assert result["success"] is True
        assert result["content"] == "Analysis content here"
        assert result["model"] == "gemini-2.5-flash"
        assert "timestamp" in result

    def test_handles_context_too_large_error(self, monkeypatch):
        """Should handle context too large error."""
        from asymmetric.core.ai.exceptions import GeminiContextTooLargeError
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        mock_client.analyze_with_cache.side_effect = GeminiContextTooLargeError(
            token_count=250000
        )
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        result = ai_analysis.run_single_stock_analysis(
            ticker="AAPL",
            scores={"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
        )

        assert result["error"] == "context_too_large"
        assert "200K" in result["message"] or "200,000" in result["message"]

    def test_handles_rate_limit_error(self, monkeypatch):
        """Should handle rate limit error."""
        from asymmetric.core.ai.exceptions import GeminiRateLimitError
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        mock_client.analyze_with_cache.side_effect = GeminiRateLimitError("Rate limited")
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        result = ai_analysis.run_single_stock_analysis(
            ticker="AAPL",
            scores={"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
        )

        assert result["error"] == "rate_limited"

    def test_handles_cache_expired_error(self, monkeypatch):
        """Should handle cache expired error."""
        from asymmetric.core.ai.exceptions import GeminiCacheExpiredError
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        mock_client.analyze_with_cache.side_effect = GeminiCacheExpiredError(cache_name="test-cache")
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        result = ai_analysis.run_single_stock_analysis(
            ticker="AAPL",
            scores={"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
        )

        assert result["error"] == "cache_expired"

    def test_handles_unknown_error(self, monkeypatch):
        """Should handle unexpected errors."""
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        mock_client.analyze_with_cache.side_effect = Exception("Unexpected error")
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        result = ai_analysis.run_single_stock_analysis(
            ticker="AAPL",
            scores={"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
        )

        assert result["error"] == "unknown"
        assert "Unexpected error" in result["message"]


class TestRunComparisonAnalysis:
    """Tests for run_comparison_analysis()."""

    def test_returns_config_error_when_no_client(self, monkeypatch):
        """Should return config error when Gemini not configured."""
        from dashboard.utils import ai_analysis

        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: None)

        results = {
            "AAPL": {"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
            "MSFT": {"piotroski": {"score": 7}, "altman": {"z_score": 5.0}},
        }

        result = ai_analysis.run_comparison_analysis(results)

        assert result["error"] == "config"

    def test_returns_insufficient_data_error(self, monkeypatch):
        """Should return error when less than 2 valid stocks."""
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        results = {
            "AAPL": {"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
            "INVALID": {"error": "No data"},
        }

        result = ai_analysis.run_comparison_analysis(results)

        assert result["error"] == "insufficient_data"
        assert "at least 2 stocks" in result["message"]

    def test_returns_success_for_valid_comparison(self, monkeypatch):
        """Should return success for valid multi-stock comparison."""
        from dashboard.utils import ai_analysis

        mock_result = MagicMock()
        mock_result.content = "Comparison analysis"
        mock_result.model = "gemini-2.5-flash"
        mock_result.cached = True
        mock_result.token_count_input = 1000
        mock_result.token_count_output = 500
        mock_result.estimated_cost_usd = 0.002
        mock_result.latency_ms = 1200

        mock_client = MagicMock()
        mock_client.analyze_with_cache.return_value = mock_result
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        results = {
            "AAPL": {"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
            "MSFT": {"piotroski": {"score": 7}, "altman": {"z_score": 5.0}},
        }

        result = ai_analysis.run_comparison_analysis(results, model="flash")

        assert result["success"] is True
        assert result["content"] == "Comparison analysis"
        assert result["cached"] is True

    def test_uses_deep_prompt_for_pro_model(self, monkeypatch):
        """Should use deep analysis prompt for pro model."""
        from dashboard.utils import ai_analysis

        mock_result = MagicMock()
        mock_result.content = "Deep analysis"
        mock_result.model = "gemini-2.5-pro"
        mock_result.cached = False
        mock_result.token_count_input = 2000
        mock_result.token_count_output = 1500
        mock_result.estimated_cost_usd = 0.02
        mock_result.latency_ms = 3000

        mock_client = MagicMock()
        mock_client.analyze_with_cache.return_value = mock_result
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        results = {
            "AAPL": {"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
            "MSFT": {"piotroski": {"score": 7}, "altman": {"z_score": 5.0}},
        }

        result = ai_analysis.run_comparison_analysis(results, model="pro")

        assert result["success"] is True
        assert result["model"] == "gemini-2.5-pro"

        # Verify the prompt used was the deep analysis one
        call_args = mock_client.analyze_with_cache.call_args
        assert "comprehensive" in call_args.kwargs["prompt"].lower() or "comprehensive" in str(call_args)

    def test_handles_context_too_large_for_comparison(self, monkeypatch):
        """Should handle context too large error with helpful message."""
        from asymmetric.core.ai.exceptions import GeminiContextTooLargeError
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        error = GeminiContextTooLargeError(token_count=250000)
        mock_client.analyze_with_cache.side_effect = error
        monkeypatch.setattr(ai_analysis, "get_gemini_client_cached", lambda: mock_client)

        results = {
            "AAPL": {"piotroski": {"score": 8}, "altman": {"z_score": 4.5}},
            "MSFT": {"piotroski": {"score": 7}, "altman": {"z_score": 5.0}},
        }

        result = ai_analysis.run_comparison_analysis(results)

        assert result["error"] == "context_too_large"
        assert "fewer stocks" in result["message"]


class TestGetGeminiClientCached:
    """Tests for get_gemini_client_cached()."""

    def test_returns_client_when_configured(self, monkeypatch):
        """Should return client when API key configured."""
        from dashboard.utils import ai_analysis

        mock_client = MagicMock()
        monkeypatch.setattr(ai_analysis, "get_gemini_client", lambda: mock_client)
        # Clear the cache
        ai_analysis.get_gemini_client_cached.clear()

        result = ai_analysis.get_gemini_client_cached()

        assert result is mock_client

    def test_returns_none_when_not_configured(self, monkeypatch):
        """Should return None when API key not configured."""
        from asymmetric.core.ai.exceptions import GeminiConfigError
        from dashboard.utils import ai_analysis

        def raise_config_error():
            raise GeminiConfigError("GEMINI_API_KEY not set")

        monkeypatch.setattr(ai_analysis, "get_gemini_client", raise_config_error)
        ai_analysis.get_gemini_client_cached.clear()

        result = ai_analysis.get_gemini_client_cached()

        assert result is None
