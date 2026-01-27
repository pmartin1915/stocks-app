"""
Gemini AI Client with mandatory context caching.

Provides cost-optimized access to Gemini 2.5 (Flash + Pro) with:
- Context caching for 10x cost reduction on multi-query sessions
- Token counting to avoid 200K pricing cliff
- Model routing (Flash for bulk ops, Pro for deep research)

Pricing Reference (as of 2024):
- Fresh reads: $1.25/1M tokens (≤200K), $2.50/1M tokens (>200K)
- Cached reads: $0.125/1M tokens (10x cheaper!)
- Cache storage: $1.00/1M tokens/hour

Critical: Cache TTL is 600s (10 min) - content auto-expires on Gemini's side.
"""

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from asymmetric.config import config
from asymmetric.core.ai.exceptions import (
    GeminiCacheExpiredError,
    GeminiConfigError,
    GeminiContextTooLargeError,
    GeminiRateLimitError,
)

logger = logging.getLogger(__name__)

# Token thresholds - use central config as source of truth
# These module-level constants are kept for backward compatibility
# but actual values are loaded from config at runtime
TOKEN_WARNING_THRESHOLD = 180_000  # Warn when approaching cliff
TOKEN_CLIFF_THRESHOLD = 200_000  # Cost doubles above this
CACHE_TTL_SECONDS = 600  # 10 minutes (Gemini minimum)
CACHE_MIN_TOKENS = 1024  # Gemini requires minimum 1024 tokens for caching


def _get_token_warning_threshold() -> int:
    """Get token warning threshold from central config."""
    return config.gemini_token_warning_threshold


def _get_token_cliff_threshold() -> int:
    """Get token cliff threshold from central config."""
    return config.gemini_token_cliff_threshold


def _get_cache_ttl_seconds() -> int:
    """Get cache TTL from central config."""
    return config.gemini_cache_ttl_seconds


class GeminiModel(Enum):
    """
    Available Gemini models with their use cases.

    FLASH: Fast, cheap - use for bulk operations, simple queries
    PRO: Powerful - use for deep research, complex analysis
    """

    FLASH = "gemini-2.5-flash"
    PRO = "gemini-2.5-pro"

    @property
    def display_name(self) -> str:
        """Human-readable model name."""
        return "Flash" if self == GeminiModel.FLASH else "Pro"


@dataclass
class GeminiConfig:
    """
    Configuration for Gemini client.

    Values default to the central config but can be overridden.
    """

    api_key: str
    default_model: GeminiModel = GeminiModel.FLASH
    cache_ttl_seconds: Optional[int] = None
    token_warning_threshold: Optional[int] = None
    token_cliff_threshold: Optional[int] = None
    max_output_tokens: Optional[int] = None

    def __post_init__(self):
        """Load defaults from central config."""
        if self.cache_ttl_seconds is None:
            self.cache_ttl_seconds = config.gemini_cache_ttl_seconds
        if self.token_warning_threshold is None:
            self.token_warning_threshold = config.gemini_token_warning_threshold
        if self.token_cliff_threshold is None:
            self.token_cliff_threshold = config.gemini_token_cliff_threshold
        if self.max_output_tokens is None:
            self.max_output_tokens = config.gemini_max_output_tokens

    @classmethod
    def from_env(cls) -> "GeminiConfig":
        """Create config from environment variables."""
        if not config.gemini_api_key:
            raise GeminiConfigError()
        return cls(api_key=config.gemini_api_key)


@dataclass
class CacheEntry:
    """
    Tracks a cached content entry on Gemini's servers.

    The cache_name is Gemini's server-side identifier.
    We track expiry locally to avoid using expired caches.
    """

    cache_name: str  # Gemini's cache identifier
    content_hash: str  # Hash of cached content for verification
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    token_count: int = 0
    model: GeminiModel = GeminiModel.FLASH

    def __post_init__(self):
        """Set expiry if not already set."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=_get_cache_ttl_seconds())

    @property
    def is_expired(self) -> bool:
        """Check if cache has expired (with 30s safety buffer before actual expiry)."""
        # We consider it expired 30s before the actual expiry to avoid using
        # a cache that might expire mid-request
        return datetime.utcnow() >= self.expires_at - timedelta(seconds=30)

    @property
    def ttl_remaining(self) -> int:
        """Seconds until cache expires."""
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class ContextCacheRegistry:
    """
    Manages context caches for Gemini API.

    Thread-safe registry that tracks cached content on Gemini's servers.
    Each unique content (by hash) gets one cache entry.

    Usage:
        registry = ContextCacheRegistry()
        cache = registry.get_or_create(content_hash)
        if cache and not cache.is_expired:
            # Use cached content
        else:
            # Upload new content and register cache
    """

    def __init__(self):
        self._caches: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, content_hash: str) -> Optional[CacheEntry]:
        """Get cache entry by content hash, or None if not found/expired."""
        with self._lock:
            entry = self._caches.get(content_hash)
            if entry and entry.is_expired:
                logger.info(f"Cache expired for hash {content_hash[:8]}...")
                del self._caches[content_hash]
                return None
            return entry

    def register(
        self,
        content_hash: str,
        cache_name: str,
        token_count: int,
        model: GeminiModel,
    ) -> CacheEntry:
        """Register a new cache entry."""
        entry = CacheEntry(
            cache_name=cache_name,
            content_hash=content_hash,
            token_count=token_count,
            model=model,
        )
        with self._lock:
            self._caches[content_hash] = entry
            logger.info(
                f"Registered cache: {cache_name} ({token_count:,} tokens, "
                f"TTL {entry.ttl_remaining}s)"
            )
        return entry

    def invalidate(self, content_hash: str) -> None:
        """Remove a cache entry."""
        with self._lock:
            if content_hash in self._caches:
                del self._caches[content_hash]
                logger.info(f"Invalidated cache for hash {content_hash[:8]}...")

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._caches)
            self._caches.clear()
            logger.info(f"Cleared {count} cache entries")

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            active = [e for e in self._caches.values() if not e.is_expired]
            return {
                "total_entries": len(self._caches),
                "active_entries": len(active),
                "total_tokens_cached": sum(e.token_count for e in active),
            }


@dataclass
class AnalysisResult:
    """Result from Gemini analysis."""

    content: str  # The analysis text
    model: str  # Model used
    cached: bool  # Whether cache was used
    token_count_input: int  # Input tokens
    token_count_output: int  # Output tokens
    estimated_cost_usd: float  # Estimated cost
    latency_ms: int  # Response time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "model": self.model,
            "cached": self.cached,
            "token_count_input": self.token_count_input,
            "token_count_output": self.token_count_output,
            "estimated_cost_usd": self.estimated_cost_usd,
            "latency_ms": self.latency_ms,
        }


class GeminiClient:
    """
    Gemini API client with mandatory context caching.

    Key features:
    - Automatic context caching for 10x cost reduction
    - Token counting to avoid 200K pricing cliff
    - Model routing (Flash for simple, Pro for complex)

    Usage:
        client = get_gemini_client()

        # First call creates cache
        result1 = await client.analyze_with_cache(filing_text, "Summarize risks")

        # Second call uses cache (10x cheaper)
        result2 = await client.analyze_with_cache(filing_text, "Identify moat")

        print(f"Cached: {result2.cached}")  # True
        print(f"Cost: ${result2.estimated_cost_usd:.4f}")  # ~$0.01
    """

    def __init__(self, gemini_config: Optional[GeminiConfig] = None):
        """
        Initialize Gemini client.

        Args:
            gemini_config: Optional configuration. Uses env vars if not provided.
        """
        self.config = gemini_config or GeminiConfig.from_env()
        self._cache_registry = ContextCacheRegistry()
        self._client: Any = None
        self._lock = threading.Lock()

    def _get_client(self) -> Any:
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        import google.generativeai as genai

                        genai.configure(api_key=self.config.api_key)
                        self._client = genai
                        logger.info("Gemini client initialized")
                    except ImportError:
                        raise GeminiConfigError(
                            "google-generativeai package not installed. "
                            "Run: pip install google-generativeai"
                        )
        return self._client

    def _hash_content(self, content: str) -> str:
        """Generate hash for content identification."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses rough approximation: ~4 chars per token for English text.
        For precise counts, use the actual token counting API.
        """
        return len(text) // 4

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached: bool,
        model: GeminiModel,
    ) -> float:
        """
        Calculate estimated cost in USD.

        Pricing (per 1M tokens):
        - Input (fresh, ≤200K): $1.25 (Flash), $1.25 (Pro)
        - Input (fresh, >200K): $2.50 (Flash), $2.50 (Pro)
        - Input (cached): $0.125 (both)
        - Output: $5.00 (Flash), $10.00 (Pro)
        """
        # Input cost
        if cached:
            input_rate = 0.125 / 1_000_000
        elif input_tokens > TOKEN_CLIFF_THRESHOLD:
            input_rate = 2.50 / 1_000_000
        else:
            input_rate = 1.25 / 1_000_000

        # Output cost
        output_rate = (5.00 if model == GeminiModel.FLASH else 10.00) / 1_000_000

        return (input_tokens * input_rate) + (output_tokens * output_rate)

    def count_tokens(self, text: str, model: GeminiModel = GeminiModel.FLASH) -> int:
        """
        Count tokens in text using Gemini's tokenizer.

        Args:
            text: Text to count tokens for.
            model: Model to use for tokenization.

        Returns:
            Exact token count.
        """
        genai = self._get_client()
        model_instance = genai.GenerativeModel(model.value)
        result = model_instance.count_tokens(text)
        return result.total_tokens

    def check_token_threshold(self, text: str) -> tuple[int, bool, bool]:
        """
        Check if text exceeds token thresholds.

        Args:
            text: Text to check.

        Returns:
            Tuple of (token_count, exceeds_warning, exceeds_cliff)
        """
        # Use estimate first (fast)
        estimated = self._estimate_tokens(text)

        # Only do precise count if near thresholds
        if estimated > TOKEN_WARNING_THRESHOLD - 20_000:
            token_count = self.count_tokens(text)
        else:
            token_count = estimated

        return (
            token_count,
            token_count >= TOKEN_WARNING_THRESHOLD,
            token_count >= TOKEN_CLIFF_THRESHOLD,
        )

    def analyze_with_cache(
        self,
        context: str,
        prompt: str,
        model: GeminiModel = GeminiModel.FLASH,
        system_instruction: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze content with automatic context caching.

        First call with new content creates a cache on Gemini's servers.
        Subsequent calls with same content use the cache (10x cheaper).

        Args:
            context: The large context to cache (e.g., 10-K filing text).
            prompt: The specific question/instruction.
            model: Model to use (FLASH or PRO).
            system_instruction: Optional system instruction.

        Returns:
            AnalysisResult with content, cost info, and cache status.

        Raises:
            GeminiContextTooLargeError: If context exceeds threshold and
                would cause 2x pricing.
            GeminiRateLimitError: If API rate limit exceeded.
            GeminiCacheExpiredError: If cache expired (auto-recovered).
        """
        start_time = time.time()
        genai = self._get_client()
        content_hash = self._hash_content(context)

        # Check token count
        token_count, near_cliff, exceeds_cliff = self.check_token_threshold(context)

        if exceeds_cliff:
            raise GeminiContextTooLargeError(token_count, TOKEN_CLIFF_THRESHOLD)

        if near_cliff:
            logger.warning(
                f"Context approaching 200K threshold ({token_count:,} tokens). "
                "Cost will double above 200K. Consider section-based analysis."
            )

        # Check for existing cache
        cache_entry = self._cache_registry.get(content_hash)
        cached = False
        use_caching = token_count >= CACHE_MIN_TOKENS

        try:
            if not use_caching:
                # Context too small for caching - use direct generation
                logger.info(
                    f"Context too small for caching ({token_count:,} < {CACHE_MIN_TOKENS} tokens). "
                    "Using direct generation."
                )
                model_instance = genai.GenerativeModel(model.value)
                # Include context in the prompt for direct generation
                full_prompt = f"{context}\n\n---\n\n{prompt}"
                prompt = full_prompt
            elif cache_entry and not cache_entry.is_expired:
                # Use existing cache
                cached = True
                logger.info(
                    f"Using cached context (TTL: {cache_entry.ttl_remaining}s)"
                )
                cached_content = genai.caching.CachedContent.get(cache_entry.cache_name)
                model_instance = genai.GenerativeModel.from_cached_content(
                    cached_content=cached_content
                )
            else:
                # Create new cache
                logger.info(f"Creating new context cache ({token_count:,} tokens)")

                # Build model config
                model_config = {"model_name": model.value}
                if system_instruction:
                    model_config["system_instruction"] = system_instruction

                # Create cached content
                cached_content = genai.caching.CachedContent.create(
                    model=model.value,
                    contents=[context],
                    ttl=timedelta(seconds=self.config.cache_ttl_seconds),
                    display_name=f"asymmetric-{content_hash[:8]}",
                )

                # Register in our local registry
                self._cache_registry.register(
                    content_hash=content_hash,
                    cache_name=cached_content.name,
                    token_count=token_count,
                    model=model,
                )

                model_instance = genai.GenerativeModel.from_cached_content(
                    cached_content=cached_content
                )

            # Generate response
            response = model_instance.generate_content(prompt)
            output_text = response.text

            # Get token counts from response
            input_tokens = token_count
            output_tokens = self._estimate_tokens(output_text)

            if hasattr(response, "usage_metadata"):
                if hasattr(response.usage_metadata, "prompt_token_count"):
                    input_tokens = response.usage_metadata.prompt_token_count
                if hasattr(response.usage_metadata, "candidates_token_count"):
                    output_tokens = response.usage_metadata.candidates_token_count

            latency_ms = int((time.time() - start_time) * 1000)

            return AnalysisResult(
                content=output_text,
                model=model.value,
                cached=cached,
                token_count_input=input_tokens,
                token_count_output=output_tokens,
                estimated_cost_usd=self._calculate_cost(
                    input_tokens, output_tokens, cached, model
                ),
                latency_ms=latency_ms,
            )

        except Exception as e:
            error_str = str(e).lower()

            # Handle rate limiting
            if "429" in str(e) or "quota" in error_str or "rate" in error_str:
                raise GeminiRateLimitError(str(e))

            # Handle expired cache
            if "not found" in error_str or "expired" in error_str:
                if cache_entry:
                    self._cache_registry.invalidate(content_hash)
                    raise GeminiCacheExpiredError(cache_entry.cache_name)

            raise

    def quick_classify(
        self,
        items: list[str],
        classification_prompt: str,
        model: GeminiModel = GeminiModel.FLASH,
    ) -> list[dict[str, Any]]:
        """
        Quickly classify multiple items in batch.

        Uses Flash model for cost efficiency. Good for:
        - Screening many stocks by simple criteria
        - Categorizing filings by type
        - Binary yes/no decisions at scale

        Args:
            items: List of items to classify.
            classification_prompt: Prompt template for classification.
            model: Model to use (defaults to FLASH for speed).

        Returns:
            List of classification results.
        """
        genai = self._get_client()
        model_instance = genai.GenerativeModel(model.value)

        results = []
        for item in items:
            prompt = f"{classification_prompt}\n\nItem: {item}"
            response = model_instance.generate_content(prompt)
            results.append({"item": item, "classification": response.text.strip()})

        return results

    def extract_custom_xbrl(
        self,
        filing_text: str,
        metrics: list[str],
        model: GeminiModel = GeminiModel.FLASH,
    ) -> dict[str, Any]:
        """
        Extract custom XBRL metrics using LLM fallback.

        Standard XBRL parsers miss company-specific metrics like ARR, NRR,
        and non-GAAP figures. This uses LLM to extract them from raw text.

        Args:
            filing_text: The filing text to extract from.
            metrics: List of metric names to extract.

        Returns:
            Dictionary mapping metric names to extracted values.
        """
        metrics_list = "\n".join(f"- {m}" for m in metrics)
        prompt = f"""Extract the following financial metrics from this SEC filing.
Return ONLY a JSON object with metric names as keys and values as numbers or null if not found.
Do not include any explanation.

Metrics to extract:
{metrics_list}

Filing text:
{filing_text[:50000]}  # Truncate to avoid token limits
"""

        result = self.analyze_with_cache(
            context=filing_text,
            prompt=prompt,
            model=model,
        )

        # Parse JSON response
        import json

        try:
            # Find JSON in response
            text = result.content
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            logger.warning("Failed to parse XBRL extraction response as JSON")

        return {m: None for m in metrics}

    @property
    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache_registry.stats


# Global singleton instance
_client: Optional[GeminiClient] = None
_client_lock = threading.Lock()


def get_gemini_client(
    gemini_config: Optional[GeminiConfig] = None,
) -> GeminiClient:
    """
    Get the global Gemini client instance (singleton pattern).

    This ensures caches are shared across the entire application.

    Args:
        gemini_config: Optional configuration for first initialization.

    Returns:
        The global GeminiClient instance.
    """
    global _client

    if _client is None:
        with _client_lock:
            # Double-check locking pattern
            if _client is None:
                _client = GeminiClient(gemini_config)
                logger.info("Gemini client singleton initialized")

    return _client


def reset_gemini_client() -> None:
    """
    Reset the global client instance.

    Primarily useful for testing. In production, the client should
    persist for the lifetime of the application.
    """
    global _client
    with _client_lock:
        if _client is not None:
            _client._cache_registry.clear()
            _client = None
            logger.info("Gemini client reset")
