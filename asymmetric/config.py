"""
Configuration management for Asymmetric.

Centralizes all configuration from environment variables with sensible defaults.
This is the SINGLE SOURCE OF TRUTH for all application configuration.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass
class Config:
    """
    Application configuration loaded from environment variables.

    Required:
        SEC_IDENTITY: User-Agent for SEC EDGAR requests.
                      Format: "AppName/Version (email@domain.com)"

    Optional:
        GEMINI_API_KEY: API key for Gemini AI analysis
        ANTHROPIC_API_KEY: API key for Claude analysis
        ASYMMETRIC_DB_PATH: Path to SQLite database
        ASYMMETRIC_BULK_DIR: Directory for SEC bulk data downloads
        ASYMMETRIC_CACHE_DIR: Directory for response caching
    """

    # SEC EDGAR (required for API access)
    sec_identity: str = field(
        default_factory=lambda: os.getenv(
            "SEC_IDENTITY", "Asymmetric/1.0 (user@example.com)"
        )
    )

    # AI APIs (optional in Phase 1)
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )

    # Storage paths
    db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("ASYMMETRIC_DB_PATH", "./data/asymmetric.db")
        )
    )
    bulk_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("ASYMMETRIC_BULK_DIR", "./data/bulk")
        )
    )
    cache_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("ASYMMETRIC_CACHE_DIR", "./data/cache")
        )
    )

    # ========================================================================
    # SEC Rate Limiting Configuration
    # CRITICAL: 5 req/s is 50% of SEC's stated 10 req/s to avoid graylisting
    # ========================================================================
    sec_requests_per_second: float = field(
        default_factory=lambda: float(
            os.getenv("ASYMMETRIC_SEC_RATE_LIMIT", "5.0")
        )
    )
    sec_burst_allowance: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_SEC_BURST", "2")
        )
    )
    sec_max_backoff_seconds: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_SEC_MAX_BACKOFF", "60")
        )
    )
    sec_initial_backoff_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("ASYMMETRIC_SEC_INITIAL_BACKOFF", "1.0")
        )
    )

    # ========================================================================
    # Gemini AI Configuration
    # CRITICAL: Cost DOUBLES above 200K tokens ($1.25 -> $2.50 per 1M)
    # ========================================================================
    gemini_token_warning_threshold: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_GEMINI_TOKEN_WARNING", "180000")
        )
    )
    gemini_token_cliff_threshold: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_GEMINI_TOKEN_CLIFF", "200000")
        )
    )
    gemini_cache_ttl_seconds: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_GEMINI_CACHE_TTL", "1800")
        )
    )
    gemini_max_output_tokens: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_GEMINI_MAX_OUTPUT", "8192")
        )
    )

    # ========================================================================
    # MCP Server Configuration
    # ========================================================================
    mcp_default_port: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_MCP_PORT", "8765")
        )
    )
    mcp_port_range_start: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_MCP_PORT_START", "8765")
        )
    )
    mcp_port_range_end: int = field(
        default_factory=lambda: int(
            os.getenv("ASYMMETRIC_MCP_PORT_END", "8785")
        )
    )

    def __post_init__(self) -> None:
        """Convert string paths to Path objects if needed."""
        if isinstance(self.db_path, str):
            self.db_path = Path(self.db_path)
        if isinstance(self.bulk_dir, str):
            self.bulk_dir = Path(self.bulk_dir)
        if isinstance(self.cache_dir, str):
            self.cache_dir = Path(self.cache_dir)

    def validate(self) -> None:
        """
        Validate required configuration.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        from asymmetric.core.data.exceptions import SECIdentityError

        # Check SEC_IDENTITY is configured (not the default example)
        if "example.com" in self.sec_identity or "user@example" in self.sec_identity:
            raise SECIdentityError(
                "SEC_IDENTITY not configured. "
                "Set SEC_IDENTITY='Asymmetric/1.0 (your-email@domain.com)' in your .env file"
            )

        # Validate SEC_IDENTITY format
        if "(" not in self.sec_identity or ")" not in self.sec_identity:
            raise SECIdentityError(
                f"Invalid SEC_IDENTITY format: {self.sec_identity}. "
                "Must include contact email in format: 'AppName/Version (email@domain.com)'"
            )

    def ensure_directories(self) -> None:
        """Create data directories if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.bulk_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def has_gemini(self) -> bool:
        """Check if Gemini API is configured."""
        return bool(self.gemini_api_key)

    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic API is configured."""
        return bool(self.anthropic_api_key)


# Global configuration instance
config = Config()
