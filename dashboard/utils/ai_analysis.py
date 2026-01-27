"""AI analysis utilities for the dashboard."""

from typing import Any

import streamlit as st

from asymmetric.core.ai.gemini_client import (
    AnalysisResult,
    GeminiClient,
    GeminiModel,
    get_gemini_client,
)
from asymmetric.core.ai.exceptions import (
    GeminiCacheExpiredError,
    GeminiConfigError,
    GeminiContextTooLargeError,
    GeminiRateLimitError,
)


@st.cache_resource
def get_gemini_client_cached() -> GeminiClient | None:
    """
    Get cached Gemini client for dashboard use.

    Returns:
        GeminiClient instance, or None if not configured.
    """
    try:
        return get_gemini_client()
    except GeminiConfigError:
        return None


def build_comparison_context(results: dict[str, dict]) -> str:
    """
    Build AI context string from comparison results.

    Args:
        results: Dict mapping ticker to score data.

    Returns:
        Formatted context string for AI analysis.
    """
    context_parts = []

    for ticker, data in results.items():
        # Skip tickers with errors
        if "error" in data:
            continue

        piotroski = data.get("piotroski", {})
        altman = data.get("altman", {})

        # Build stock summary
        summary = f"""## {ticker}

### Piotroski F-Score: {piotroski.get('score', 'N/A')}/9 ({piotroski.get('interpretation', 'N/A')})
- Profitability: {piotroski.get('profitability', 'N/A')}/4
- Leverage/Liquidity: {piotroski.get('leverage', 'N/A')}/3
- Operating Efficiency: {piotroski.get('efficiency', 'N/A')}/2

### Altman Z-Score: {altman.get('z_score', 'N/A')} ({altman.get('zone', 'N/A')})
- Interpretation: {altman.get('interpretation', 'N/A')}
- Formula Used: {altman.get('formula_used', 'Standard')}
"""
        context_parts.append(summary)

    return "\n---\n".join(context_parts)


def estimate_analysis_cost(context: str, model: str) -> dict[str, Any]:
    """
    Estimate cost before running AI analysis.

    Args:
        context: The context string to analyze.
        model: Model name ("flash" or "pro").

    Returns:
        Dict with cost estimate details.
    """
    # Rough token estimate: ~4 chars per token
    token_estimate = len(context) // 4

    # Pricing per 1M tokens (as of 2024)
    if model == "flash":
        input_rate = 1.25 / 1_000_000
        output_rate = 5.00 / 1_000_000
    else:  # pro
        input_rate = 1.25 / 1_000_000
        output_rate = 10.00 / 1_000_000

    # Estimate ~500 output tokens for summary, ~1500 for deep analysis
    estimated_output = 500 if model == "flash" else 1500
    estimated_cost = (token_estimate * input_rate) + (estimated_output * output_rate)

    return {
        "input_tokens": token_estimate,
        "estimated_output_tokens": estimated_output,
        "estimated_cost_usd": estimated_cost,
        "model": model,
        "near_cliff": token_estimate > 180_000,  # Near 200K pricing cliff
    }


# Prompt templates
QUICK_COMPARE_PROMPT = """Compare these {count} stocks based on their financial health metrics:

{context}

Provide a concise comparison (3-5 bullet points) covering:
1. Which stock has the strongest financial health (highest F-Score)?
2. Which has the lowest bankruptcy risk (highest Z-Score in Safe zone)?
3. Key differences in profitability, leverage, and efficiency components
4. Your recommendation for the best candidate for further research

Keep your response under 300 words. Focus on actionable insights for a value investor."""


DEEP_ANALYSIS_PROMPT = """Perform a comprehensive investment comparison of these {count} stocks:

{context}

Provide detailed analysis covering:

1. **Financial Health Comparison**: Compare F-Score components and what they reveal about each company's financial trajectory

2. **Bankruptcy Risk Assessment**: Evaluate Z-Score zones and their implications for investment safety

3. **Profitability Analysis**:
   - ROA trends and quality
   - Cash flow quality vs. accruals
   - Earnings sustainability

4. **Leverage & Liquidity**:
   - Debt level trends
   - Current ratio and liquidity position
   - Share dilution risk

5. **Operating Efficiency**:
   - Gross margin trends
   - Asset turnover improvements
   - Operational execution quality

6. **Risk Assessment**: Which stock carries more financial risk and why?

7. **Investment Thesis**: For a value investor seeking quality at reasonable prices, which stock offers the best risk-adjusted opportunity? Support your recommendation with specific metrics.

Be specific with numbers and provide actionable insights."""


def run_comparison_analysis(
    results: dict[str, dict],
    model: str = "flash",
) -> dict[str, Any]:
    """
    Run AI comparison analysis with context caching.

    Args:
        results: Dict mapping ticker to score data.
        model: Model to use ("flash" or "pro").

    Returns:
        Dict with analysis result and metadata, or error info.
    """
    client = get_gemini_client_cached()

    if client is None:
        return {
            "error": "config",
            "message": "GEMINI_API_KEY not configured. Set it in your .env file.",
        }

    # Build context
    context = build_comparison_context(results)
    stock_count = len([t for t in results if "error" not in results[t]])

    if stock_count < 2:
        return {
            "error": "insufficient_data",
            "message": "Need at least 2 stocks with valid data for comparison.",
        }

    # Select prompt template
    if model == "flash":
        prompt = QUICK_COMPARE_PROMPT.format(count=stock_count, context=context)
        gemini_model = GeminiModel.FLASH
    else:
        prompt = DEEP_ANALYSIS_PROMPT.format(count=stock_count, context=context)
        gemini_model = GeminiModel.PRO

    try:
        result = client.analyze_with_cache(
            context=context,
            prompt=prompt,
            model=gemini_model,
        )

        return {
            "success": True,
            "content": result.content,
            "model": result.model,
            "cached": result.cached,
            "input_tokens": result.token_count_input,
            "output_tokens": result.token_count_output,
            "cost_usd": result.estimated_cost_usd,
            "latency_ms": result.latency_ms,
        }

    except GeminiContextTooLargeError as e:
        return {
            "error": "context_too_large",
            "message": f"Context exceeds 200K token limit ({e.token_count:,} tokens). Try comparing fewer stocks.",
        }

    except GeminiRateLimitError:
        return {
            "error": "rate_limited",
            "message": "Gemini API rate limit reached. Please wait a moment and try again.",
        }

    except GeminiCacheExpiredError:
        return {
            "error": "cache_expired",
            "message": "Analysis cache expired. Please try again.",
        }

    except Exception as e:
        return {
            "error": "unknown",
            "message": f"Analysis failed: {str(e)}",
        }


def format_analysis_metadata(result: dict[str, Any]) -> str:
    """
    Format analysis result metadata for display.

    Args:
        result: Analysis result dict.

    Returns:
        Formatted metadata string.
    """
    if "error" in result:
        return ""

    parts = [
        f"Model: {result.get('model', 'unknown')}",
        f"Cached: {'Yes' if result.get('cached') else 'No'}",
        f"Tokens: {result.get('input_tokens', 0):,} in / {result.get('output_tokens', 0):,} out",
        f"Cost: ${result.get('cost_usd', 0):.4f}",
        f"Latency: {result.get('latency_ms', 0):,}ms",
    ]

    return " | ".join(parts)
