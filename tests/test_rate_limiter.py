"""
Tests for the Token Bucket Rate Limiter.
"""

import threading
import time

import pytest

from asymmetric.core.data.rate_limiter import (
    RateLimitConfig,
    TokenBucketLimiter,
    get_limiter,
    reset_limiter,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.requests_per_second == 5.0
        assert config.burst_allowance == 2
        assert config.max_backoff_seconds == 60
        assert config.initial_backoff_seconds == 1.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests_per_second=3.0,
            burst_allowance=5,
            max_backoff_seconds=120,
            initial_backoff_seconds=2.0,
        )

        assert config.requests_per_second == 3.0
        assert config.burst_allowance == 5
        assert config.max_backoff_seconds == 120
        assert config.initial_backoff_seconds == 2.0


class TestTokenBucketLimiter:
    """Tests for TokenBucketLimiter class."""

    def test_initialization_default(self):
        """Test limiter initializes with default config."""
        limiter = TokenBucketLimiter()

        assert limiter.config.requests_per_second == 5.0
        assert limiter.tokens == 2.0  # burst_allowance
        assert limiter.backoff_count == 0

    def test_initialization_custom(self):
        """Test limiter initializes with custom config."""
        config = RateLimitConfig(burst_allowance=5)
        limiter = TokenBucketLimiter(config)

        assert limiter.tokens == 5.0
        assert limiter.max_tokens == 5.0

    def test_acquire_immediate(self):
        """Test immediate token acquisition when tokens available."""
        limiter = TokenBucketLimiter()

        # Should acquire immediately (burst tokens available)
        start = time.monotonic()
        result = limiter.acquire()
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed < 0.1  # Should be nearly instant

    def test_acquire_depletes_tokens(self):
        """Test that acquiring tokens depletes the bucket."""
        config = RateLimitConfig(burst_allowance=2)
        limiter = TokenBucketLimiter(config)

        # Acquire both burst tokens
        assert limiter.acquire(timeout=0.1) is True
        assert limiter.acquire(timeout=0.1) is True

        # Third acquire should need to wait for refill
        # With 5 req/s, we need 0.2s for 1 token
        assert limiter.tokens < 1.0

    def test_acquire_timeout(self):
        """Test acquisition times out when no tokens available."""
        config = RateLimitConfig(burst_allowance=1, requests_per_second=1.0)
        limiter = TokenBucketLimiter(config)

        # Deplete the single token
        limiter.acquire()

        # Try to acquire with very short timeout
        start = time.monotonic()
        result = limiter.acquire(timeout=0.1)
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed >= 0.1

    def test_token_refill(self):
        """Test that tokens refill over time."""
        config = RateLimitConfig(burst_allowance=1, requests_per_second=10.0)
        limiter = TokenBucketLimiter(config)

        # Deplete token
        limiter.acquire()
        assert limiter.tokens < 1.0

        # Wait for refill (10 req/s = 0.1s per token)
        time.sleep(0.15)

        # Should have token now
        result = limiter.acquire(timeout=0.01)
        assert result is True

    def test_tokens_cap_at_max(self):
        """Test that tokens don't exceed max_tokens."""
        config = RateLimitConfig(burst_allowance=2, requests_per_second=100.0)
        limiter = TokenBucketLimiter(config)

        # Wait way more than needed
        time.sleep(0.1)

        # Force refill by acquiring
        limiter.acquire()

        # Should still be capped at max (minus the one we just acquired)
        assert limiter.tokens <= limiter.max_tokens

    def test_report_error_429(self):
        """Test backoff on 429 error."""
        config = RateLimitConfig(initial_backoff_seconds=0.05)
        limiter = TokenBucketLimiter(config)

        assert limiter.backoff_count == 0

        start = time.monotonic()
        limiter.report_error(429)
        elapsed = time.monotonic() - start

        assert limiter.backoff_count == 1
        assert elapsed >= 0.05  # Should have slept

    def test_report_error_403(self):
        """Test backoff on 403 error."""
        config = RateLimitConfig(initial_backoff_seconds=0.05)
        limiter = TokenBucketLimiter(config)

        limiter.report_error(403)

        assert limiter.backoff_count == 1

    def test_report_error_other_codes_ignored(self):
        """Test that non-rate-limit errors don't trigger backoff."""
        limiter = TokenBucketLimiter()

        limiter.report_error(500)
        limiter.report_error(404)

        assert limiter.backoff_count == 0

    def test_exponential_backoff(self):
        """Test that backoff increases exponentially."""
        config = RateLimitConfig(
            initial_backoff_seconds=0.01, max_backoff_seconds=1.0
        )
        limiter = TokenBucketLimiter(config)

        # First backoff: 0.01 * 2^1 = 0.02
        limiter.report_error(429)
        assert limiter.backoff_count == 1

        # Second backoff: 0.01 * 2^2 = 0.04
        limiter.report_error(429)
        assert limiter.backoff_count == 2

        # Third backoff: 0.01 * 2^3 = 0.08
        limiter.report_error(429)
        assert limiter.backoff_count == 3

    def test_report_empty_response(self):
        """Test backoff on empty response (graylisting)."""
        config = RateLimitConfig(initial_backoff_seconds=0.05)
        limiter = TokenBucketLimiter(config)

        start = time.monotonic()
        limiter.report_empty_response()
        elapsed = time.monotonic() - start

        assert limiter.backoff_count == 1
        assert elapsed >= 0.05

    def test_reset_backoff(self):
        """Test backoff counter reset."""
        limiter = TokenBucketLimiter()

        limiter.report_error(429)
        assert limiter.backoff_count == 1

        limiter.reset_backoff()
        assert limiter.backoff_count == 0

    def test_thread_safety(self):
        """Test limiter is thread-safe."""
        config = RateLimitConfig(burst_allowance=10, requests_per_second=100.0)
        limiter = TokenBucketLimiter(config)

        acquired_count = 0
        lock = threading.Lock()

        def acquire_token():
            nonlocal acquired_count
            if limiter.acquire(timeout=1.0):
                with lock:
                    acquired_count += 1

        # Start multiple threads trying to acquire tokens
        threads = [threading.Thread(target=acquire_token) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should have succeeded (burst + refill)
        assert acquired_count >= 10  # At least burst tokens

    def test_repr(self):
        """Test string representation."""
        limiter = TokenBucketLimiter()
        repr_str = repr(limiter)

        assert "TokenBucketLimiter" in repr_str
        assert "rate=5.0/s" in repr_str


class TestGetLimiter:
    """Tests for the global limiter singleton."""

    def test_returns_same_instance(self):
        """Test that get_limiter returns the same instance."""
        limiter1 = get_limiter()
        limiter2 = get_limiter()

        assert limiter1 is limiter2

    def test_reset_clears_instance(self):
        """Test that reset_limiter clears the global instance."""
        limiter1 = get_limiter()
        reset_limiter()
        limiter2 = get_limiter()

        assert limiter1 is not limiter2

    def test_initial_config(self):
        """Test that initial config is used."""
        reset_limiter()
        config = RateLimitConfig(burst_allowance=10)
        limiter = get_limiter(config)

        assert limiter.max_tokens == 10.0

    def test_subsequent_config_ignored(self):
        """Test that config is ignored after initialization."""
        reset_limiter()
        config1 = RateLimitConfig(burst_allowance=10)
        limiter1 = get_limiter(config1)

        config2 = RateLimitConfig(burst_allowance=20)
        limiter2 = get_limiter(config2)

        # Should be same instance with original config
        assert limiter1 is limiter2
        assert limiter2.max_tokens == 10.0
