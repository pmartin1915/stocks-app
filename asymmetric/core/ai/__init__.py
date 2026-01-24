"""
AI integration module for Asymmetric.

Provides Gemini 2.5 client with mandatory context caching for cost optimization.
"""

from asymmetric.core.ai.exceptions import (
    AIError,
    GeminiCacheExpiredError,
    GeminiConfigError,
    GeminiContextTooLargeError,
    GeminiRateLimitError,
)
from asymmetric.core.ai.gemini_client import (
    AnalysisResult,
    ContextCacheRegistry,
    GeminiClient,
    GeminiConfig,
    GeminiModel,
    get_gemini_client,
    reset_gemini_client,
)

__all__ = [
    # Exceptions
    "AIError",
    "GeminiConfigError",
    "GeminiContextTooLargeError",
    "GeminiCacheExpiredError",
    "GeminiRateLimitError",
    # Client
    "GeminiClient",
    "GeminiConfig",
    "GeminiModel",
    "ContextCacheRegistry",
    "AnalysisResult",
    "get_gemini_client",
    "reset_gemini_client",
]
