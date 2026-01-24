"""
Tests for the Gemini AI client with context caching.
"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from asymmetric.core.ai.exceptions import (
    GeminiConfigError,
    GeminiContextTooLargeError,
    GeminiRateLimitError,
)
from asymmetric.core.ai.gemini_client import (
    CACHE_TTL_SECONDS,
    TOKEN_CLIFF_THRESHOLD,
    TOKEN_WARNING_THRESHOLD,
    AnalysisResult,
    CacheEntry,
    ContextCacheRegistry,
    GeminiClient,
    GeminiConfig,
    GeminiModel,
    get_gemini_client,
    reset_gemini_client,
)


class TestGeminiModel:
    """Tests for GeminiModel enum."""

    def test_model_values(self):
        """Model values should be correct Gemini model IDs."""
        assert "flash" in GeminiModel.FLASH.value.lower()
        assert "pro" in GeminiModel.PRO.value.lower()

    def test_display_name(self):
        """Display names should be human-readable."""
        assert GeminiModel.FLASH.display_name == "Flash"
        assert GeminiModel.PRO.display_name == "Pro"


class TestGeminiConfig:
    """Tests for GeminiConfig."""

    def test_config_with_api_key(self):
        """Config should accept API key directly."""
        config = GeminiConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.default_model == GeminiModel.FLASH

    @patch("asymmetric.core.ai.gemini_client.config")
    def test_config_from_env_missing_key(self, mock_config):
        """Should raise error when API key not set."""
        mock_config.gemini_api_key = None

        with pytest.raises(GeminiConfigError):
            GeminiConfig.from_env()

    @patch("asymmetric.core.ai.gemini_client.config")
    def test_config_from_env_with_key(self, mock_config):
        """Should create config when API key is set."""
        mock_config.gemini_api_key = "test-api-key"

        config = GeminiConfig.from_env()
        assert config.api_key == "test-api-key"


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Should create cache entry with correct fields."""
        entry = CacheEntry(
            cache_name="cache-123",
            content_hash="abc123",
            token_count=50000,
            model=GeminiModel.FLASH,
        )

        assert entry.cache_name == "cache-123"
        assert entry.content_hash == "abc123"
        assert entry.token_count == 50000

    def test_cache_entry_expiry(self):
        """Should correctly calculate expiry."""
        # Create an entry that was created long ago (already expired)
        old_created = datetime.utcnow() - timedelta(seconds=CACHE_TTL_SECONDS + 60)
        entry = CacheEntry(
            cache_name="cache-123",
            content_hash="abc123",
            created_at=old_created,
            # expires_at will be auto-set by __post_init__ to created_at + TTL
            # which is still in the past
        )

        assert entry.is_expired

    def test_cache_entry_not_expired(self):
        """Should not be expired when fresh."""
        entry = CacheEntry(
            cache_name="cache-123",
            content_hash="abc123",
        )

        assert not entry.is_expired

    def test_ttl_remaining(self):
        """Should return correct TTL remaining."""
        entry = CacheEntry(
            cache_name="cache-123",
            content_hash="abc123",
        )

        # Should be close to CACHE_TTL_SECONDS
        assert entry.ttl_remaining > CACHE_TTL_SECONDS - 5
        assert entry.ttl_remaining <= CACHE_TTL_SECONDS


class TestContextCacheRegistry:
    """Tests for ContextCacheRegistry."""

    def test_register_and_get(self):
        """Should register and retrieve cache entries."""
        registry = ContextCacheRegistry()

        entry = registry.register(
            content_hash="hash123",
            cache_name="cache-name",
            token_count=10000,
            model=GeminiModel.FLASH,
        )

        retrieved = registry.get("hash123")
        assert retrieved is not None
        assert retrieved.cache_name == "cache-name"
        assert retrieved.token_count == 10000

    def test_get_nonexistent(self):
        """Should return None for nonexistent entries."""
        registry = ContextCacheRegistry()

        assert registry.get("nonexistent") is None

    def test_invalidate(self):
        """Should remove entries on invalidate."""
        registry = ContextCacheRegistry()

        registry.register(
            content_hash="hash123",
            cache_name="cache-name",
            token_count=10000,
            model=GeminiModel.FLASH,
        )

        registry.invalidate("hash123")
        assert registry.get("hash123") is None

    def test_clear(self):
        """Should clear all entries."""
        registry = ContextCacheRegistry()

        registry.register("hash1", "cache1", 1000, GeminiModel.FLASH)
        registry.register("hash2", "cache2", 2000, GeminiModel.PRO)

        registry.clear()
        assert registry.get("hash1") is None
        assert registry.get("hash2") is None

    def test_stats(self):
        """Should return correct statistics."""
        registry = ContextCacheRegistry()

        registry.register("hash1", "cache1", 1000, GeminiModel.FLASH)
        registry.register("hash2", "cache2", 2000, GeminiModel.PRO)

        stats = registry.stats
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["total_tokens_cached"] == 3000


class TestGeminiClient:
    """Tests for GeminiClient."""

    @pytest.fixture
    def client(self):
        """Create a client with mock API key."""
        config = GeminiConfig(api_key="test-key")
        return GeminiClient(config)

    def test_hash_content(self, client):
        """Should generate consistent hashes."""
        hash1 = client._hash_content("test content")
        hash2 = client._hash_content("test content")
        hash3 = client._hash_content("different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length

    def test_estimate_tokens(self, client):
        """Should estimate tokens based on character count."""
        # ~4 chars per token
        text = "a" * 400
        estimated = client._estimate_tokens(text)
        assert estimated == 100

    def test_calculate_cost_fresh(self, client):
        """Should calculate correct cost for fresh requests."""
        # Under 200K threshold
        cost = client._calculate_cost(
            input_tokens=100_000,
            output_tokens=1000,
            cached=False,
            model=GeminiModel.FLASH,
        )

        # $1.25/1M input + $5.00/1M output
        expected = (100_000 * 1.25 / 1_000_000) + (1000 * 5.00 / 1_000_000)
        assert abs(cost - expected) < 0.001

    def test_calculate_cost_cached(self, client):
        """Should calculate correct cost for cached requests (10x cheaper)."""
        cost = client._calculate_cost(
            input_tokens=100_000,
            output_tokens=1000,
            cached=True,
            model=GeminiModel.FLASH,
        )

        # $0.125/1M cached input + $5.00/1M output
        expected = (100_000 * 0.125 / 1_000_000) + (1000 * 5.00 / 1_000_000)
        assert abs(cost - expected) < 0.001

    def test_calculate_cost_over_threshold(self, client):
        """Should double input cost over 200K threshold."""
        cost = client._calculate_cost(
            input_tokens=250_000,  # Over threshold
            output_tokens=1000,
            cached=False,
            model=GeminiModel.FLASH,
        )

        # $2.50/1M input (doubled) + $5.00/1M output
        expected = (250_000 * 2.50 / 1_000_000) + (1000 * 5.00 / 1_000_000)
        assert abs(cost - expected) < 0.001


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        result = AnalysisResult(
            content="Test analysis",
            model="gemini-2.5-flash",
            cached=True,
            token_count_input=1000,
            token_count_output=200,
            estimated_cost_usd=0.01,
            latency_ms=500,
        )

        d = result.to_dict()
        assert d["content"] == "Test analysis"
        assert d["cached"] is True
        assert d["latency_ms"] == 500


class TestSingleton:
    """Tests for singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_gemini_client()
        yield
        reset_gemini_client()

    @patch("asymmetric.core.ai.gemini_client.config")
    def test_get_gemini_client_singleton(self, mock_config):
        """Should return same instance."""
        mock_config.gemini_api_key = "test-key"

        client1 = get_gemini_client()
        client2 = get_gemini_client()

        assert client1 is client2

    def test_reset_gemini_client(self):
        """Should clear singleton on reset."""
        config = GeminiConfig(api_key="test-key")
        client1 = get_gemini_client(config)

        reset_gemini_client()

        # After reset, should be able to create new instance
        config2 = GeminiConfig(api_key="different-key")
        client2 = get_gemini_client(config2)

        # They should be different instances (different configs)
        assert client2.config.api_key == "different-key"
