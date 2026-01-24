"""Mock helpers for Gemini API testing."""

from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock


@dataclass
class MockGeminiResponse:
    """Mock Gemini API response."""

    content: str = "This is a mock AI analysis of the company."
    model: str = "gemini-2.5-flash"
    cached: bool = False
    token_count_input: int = 1000
    token_count_output: int = 200
    estimated_cost_usd: float = 0.01
    latency_ms: int = 500


def create_mock_gemini_response(
    content: str = "This is a mock AI analysis.",
    model: str = "gemini-2.5-flash",
    cached: bool = False,
    token_count_input: int = 1000,
    token_count_output: int = 200,
    estimated_cost_usd: float = 0.01,
    latency_ms: int = 500,
) -> MockGeminiResponse:
    """
    Create a mock Gemini analysis response.

    Args:
        content: Analysis text content
        model: Model name used
        cached: Whether response came from cache
        token_count_input: Number of input tokens
        token_count_output: Number of output tokens
        estimated_cost_usd: Estimated cost in USD
        latency_ms: Response latency in milliseconds

    Returns:
        MockGeminiResponse instance
    """
    return MockGeminiResponse(
        content=content,
        model=model,
        cached=cached,
        token_count_input=token_count_input,
        token_count_output=token_count_output,
        estimated_cost_usd=estimated_cost_usd,
        latency_ms=latency_ms,
    )


def create_mock_gemini_client(
    response: Optional[MockGeminiResponse] = None,
) -> MagicMock:
    """
    Create a fully mocked GeminiClient.

    Args:
        response: Mock response to return from analyze_with_cache

    Returns:
        MagicMock configured as a GeminiClient
    """
    client = MagicMock()
    mock_response = response or create_mock_gemini_response()

    client.analyze_with_cache.return_value = mock_response
    client.count_tokens.return_value = 1000
    client.estimate_cost.return_value = 0.01
    client.extract_custom_xbrl.return_value = {"ARR": 1000000}

    return client


def create_mock_cache_entry(
    content_hash: str = "abc123def456",
    cache_name: str = "projects/test/cachedContents/cache-123",
    expire_time: str = "2024-01-01T00:00:00Z",
) -> MagicMock:
    """
    Create a mock Gemini cache entry.

    Args:
        content_hash: Hash of cached content
        cache_name: Full cache resource name
        expire_time: Cache expiration time

    Returns:
        MagicMock configured as a cache entry
    """
    entry = MagicMock()
    entry.name = cache_name
    entry.expire_time = expire_time
    entry.content_hash = content_hash
    return entry
