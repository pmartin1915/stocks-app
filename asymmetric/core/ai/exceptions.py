"""
Custom exceptions for AI operations.

Provides a hierarchy of exceptions for Gemini API operations.
"""

from asymmetric.core.data.exceptions import AsymmetricError


class AIError(AsymmetricError):
    """Base exception for AI-related errors."""

    pass


class GeminiConfigError(AIError):
    """
    Raised when Gemini API is not properly configured.

    Occurs when GEMINI_API_KEY is not set in environment.
    """

    def __init__(
        self,
        message: str = (
            "GEMINI_API_KEY not configured. "
            "Set GEMINI_API_KEY in your .env file to enable AI analysis."
        ),
    ):
        super().__init__(message)


class GeminiContextTooLargeError(AIError):
    """
    Raised when content exceeds 200K token threshold.

    Critical: Gemini pricing DOUBLES above 200K tokens.
    - ≤200K: $1.25/1M input
    - >200K: $2.50/1M input

    Consider using section-based analysis to stay under threshold.
    """

    def __init__(self, token_count: int, threshold: int = 200_000):
        self.token_count = token_count
        self.threshold = threshold
        super().__init__(
            f"Content exceeds {threshold:,} tokens ({token_count:,}). "
            "Cost doubles above this threshold. "
            "Consider using section-based analysis (--section flag)."
        )


class GeminiCacheExpiredError(AIError):
    """
    Raised when cached content has expired on Gemini's side.

    This is recoverable - the client will re-upload the content
    and create a new cache automatically.
    """

    def __init__(self, cache_name: str):
        self.cache_name = cache_name
        super().__init__(
            f"Cache '{cache_name}' has expired on Gemini's servers. "
            "Content will be re-uploaded automatically."
        )


class GeminiRateLimitError(AIError):
    """
    Raised when Gemini API rate limit is exceeded.

    Implement exponential backoff when this occurs.
    """

    def __init__(
        self,
        message: str = "Gemini API rate limit exceeded. Please retry after a short delay.",
        retry_after: int | None = None,
    ):
        self.retry_after = retry_after
        if retry_after:
            message = f"{message} Suggested wait: {retry_after}s"
        super().__init__(message)
