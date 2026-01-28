"""
Pytest configuration and shared fixtures for Asymmetric tests.

This module provides common fixtures used across all test modules,
including financial data fixtures, database fixtures, and mock helpers.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ==============================================================================
# Autouse Fixtures - Run automatically for all tests
# ==============================================================================


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Generator[None, None, None]:
    """Reset the global rate limiter singleton before each test."""
    from asymmetric.core.data.rate_limiter import reset_limiter

    reset_limiter()
    yield
    reset_limiter()


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for testing."""
    monkeypatch.setenv("SEC_IDENTITY", "Asymmetric-Test/1.0 (test@test.com)")
    monkeypatch.setenv("ASYMMETRIC_DB_PATH", ":memory:")


# ==============================================================================
# Financial Data Fixtures
# ==============================================================================


@pytest.fixture
def healthy_company_data() -> dict[str, Any]:
    """
    Financial data representing a healthy company that should score high.

    Expected F-Score: 9/9 (all signals positive)
    Expected Z-Score: Safe zone (>2.99)
    """
    return {
        "current": {
            # Piotroski inputs
            "revenue": 100_000_000,
            "gross_profit": 45_000_000,  # 45% margin (up from 40%)
            "net_income": 15_000_000,  # Positive
            "total_assets": 180_000_000,  # Assets decreased = better turnover
            "current_assets": 60_000_000,
            "current_liabilities": 30_000_000,  # Current ratio: 2.0 (up from 1.5)
            "long_term_debt": 15_000_000,  # Decreased
            "shares_outstanding": 10_000_000,  # No dilution
            "operating_cash_flow": 20_000_000,  # Greater than net income
            # Altman inputs
            "total_liabilities": 45_000_000,  # 30M current + 15M long-term
            "retained_earnings": 80_000_000,  # Strong retained earnings
            "ebit": 25_000_000,  # Healthy operating income
            "market_cap": 500_000_000,  # Large market cap
            "book_equity": 135_000_000,  # Assets - Liabilities
        },
        "prior": {
            "revenue": 90_000_000,
            "gross_profit": 36_000_000,  # 40% margin
            "net_income": 12_000_000,
            "total_assets": 200_000_000,
            "current_assets": 45_000_000,
            "current_liabilities": 30_000_000,  # Current ratio: 1.5
            "long_term_debt": 25_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 16_000_000,
        },
    }


@pytest.fixture
def healthy_company_prior() -> dict[str, Any]:
    """Prior year financial data for healthy company (standalone)."""
    return {
        "revenue": 90_000_000,
        "gross_profit": 36_000_000,  # 40% margin
        "net_income": 12_000_000,
        "total_assets": 200_000_000,
        "current_assets": 45_000_000,
        "current_liabilities": 30_000_000,  # Current ratio: 1.5
        "long_term_debt": 25_000_000,
        "shares_outstanding": 10_000_000,
        "operating_cash_flow": 16_000_000,
    }


@pytest.fixture
def weak_company_data() -> dict[str, Any]:
    """
    Financial data representing a weak company that should score low.

    Expected F-Score: ~2/9 (most signals negative)
    Expected Z-Score: Grey or Distress zone (<2.99)
    """
    return {
        "current": {
            # Piotroski inputs
            "revenue": 80_000_000,  # Revenue down
            "gross_profit": 24_000_000,  # 30% margin (down from 35%)
            "net_income": -5_000_000,  # Negative ROA
            "total_assets": 220_000_000,  # Assets up
            "current_assets": 40_000_000,
            "current_liabilities": 50_000_000,  # Current ratio: 0.8 (down)
            "long_term_debt": 60_000_000,  # Debt up
            "shares_outstanding": 12_000_000,  # Dilution
            "operating_cash_flow": -2_000_000,  # Negative CFO
            # Altman inputs
            "total_liabilities": 110_000_000,  # 50M current + 60M long-term
            "retained_earnings": -20_000_000,  # Accumulated losses
            "ebit": -3_000_000,  # Operating loss
            "market_cap": 50_000_000,  # Low market cap
            "book_equity": 110_000_000,  # Assets - Liabilities
        },
        "prior": {
            "revenue": 90_000_000,
            "gross_profit": 31_500_000,  # 35% margin
            "net_income": 5_000_000,
            "total_assets": 200_000_000,
            "current_assets": 50_000_000,
            "current_liabilities": 40_000_000,  # Current ratio: 1.25
            "long_term_debt": 40_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 8_000_000,
        },
    }


@pytest.fixture
def weak_company_prior() -> dict[str, Any]:
    """Prior year financial data for weak company (standalone)."""
    return {
        "revenue": 90_000_000,
        "gross_profit": 31_500_000,  # 35% margin
        "net_income": 5_000_000,
        "total_assets": 200_000_000,
        "current_assets": 50_000_000,
        "current_liabilities": 40_000_000,  # Current ratio: 1.25
        "long_term_debt": 40_000_000,
        "shares_outstanding": 10_000_000,
        "operating_cash_flow": 8_000_000,
    }


@pytest.fixture
def distressed_company_data() -> dict[str, Any]:
    """
    Financial data for a distressed company near bankruptcy.

    Should produce Z-Score < 1.81 (Distress zone).
    """
    return {
        "revenue": 10_000_000,
        "gross_profit": 1_000_000,
        "net_income": -5_000_000,
        "total_assets": 50_000_000,
        "current_assets": 5_000_000,
        "current_liabilities": 20_000_000,
        "long_term_debt": 40_000_000,
        "total_liabilities": 60_000_000,
        "shares_outstanding": 10_000_000,
        "operating_cash_flow": -3_000_000,
        "retained_earnings": -30_000_000,
        "ebit": -4_000_000,
        "market_cap": 5_000_000,
        "book_equity": -10_000_000,
    }


@pytest.fixture
def perfect_piotroski_data() -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Financial data designed to achieve a perfect 9/9 Piotroski F-Score.

    Returns (current, prior) tuple.
    Also includes Altman inputs for composite scoring tests.
    """
    current = {
        # Piotroski inputs
        "revenue": 100_000_000,
        "gross_profit": 40_000_000,
        "net_income": 15_000_000,
        "total_assets": 200_000_000,
        "current_assets": 80_000_000,
        "current_liabilities": 30_000_000,
        "long_term_debt": 20_000_000,
        "shares_outstanding": 10_000_000,
        "operating_cash_flow": 25_000_000,
        # Altman inputs
        "total_liabilities": 50_000_000,  # 30M current + 20M long-term
        "retained_earnings": 100_000_000,
        "ebit": 30_000_000,
        "market_cap": 600_000_000,
        "book_equity": 150_000_000,
    }
    prior = {
        "revenue": 90_000_000,
        "gross_profit": 33_000_000,
        "net_income": 10_000_000,
        "total_assets": 180_000_000,
        "current_assets": 70_000_000,
        "current_liabilities": 35_000_000,
        "long_term_debt": 25_000_000,
        "shares_outstanding": 10_000_000,
        "operating_cash_flow": 15_000_000,
    }
    return current, prior


@pytest.fixture
def sample_financial_data():
    """Sample financial data for Piotroski scoring tests."""
    return {
        "current": {
            "revenue": 100_000_000,
            "gross_profit": 40_000_000,
            "net_income": 15_000_000,
            "total_assets": 200_000_000,
            "current_assets": 50_000_000,
            "current_liabilities": 30_000_000,
            "long_term_debt": 20_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 20_000_000,
        },
        "prior": {
            "revenue": 90_000_000,
            "gross_profit": 35_000_000,
            "net_income": 12_000_000,
            "total_assets": 190_000_000,
            "current_assets": 45_000_000,
            "current_liabilities": 35_000_000,
            "long_term_debt": 25_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 16_000_000,
        },
    }


# ==============================================================================
# JSON Fixture Loaders
# ==============================================================================


@pytest.fixture
def aapl_financials() -> dict[str, Any]:
    """Load Apple FY2023 financial data from fixture file."""
    fixture_path = FIXTURES_DIR / "aapl_financials.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def distressed_fixture() -> dict[str, Any]:
    """Load distressed company data from fixture file."""
    fixture_path = FIXTURES_DIR / "distressed_company.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def expected_scores() -> dict[str, Any]:
    """Load expected scoring results from fixture file."""
    fixture_path = FIXTURES_DIR / "expected_scores.json"
    with open(fixture_path) as f:
        return json.load(f)


# ==============================================================================
# Database Fixtures
# ==============================================================================


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary database path."""
    return tmp_path / "test_asymmetric.db"


@pytest.fixture
def tmp_db(tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """
    Set up a temporary database for testing.

    Monkeypatches the database path and initializes the schema.
    """
    monkeypatch.setenv("ASYMMETRIC_DB_PATH", str(tmp_db_path))

    # CRITICAL: Also patch the config singleton directly since it reads env at import time
    from asymmetric.config import config

    monkeypatch.setattr(config, "db_path", tmp_db_path)

    # Reset any existing engine to force creation with new path
    from asymmetric.db.database import reset_engine

    reset_engine()

    from asymmetric.db import init_db

    init_db()

    yield tmp_db_path

    # Cleanup
    reset_engine()
    if tmp_db_path.exists():
        tmp_db_path.unlink()


@pytest.fixture
def in_memory_duckdb():
    """Create an in-memory DuckDB connection for testing."""
    import duckdb

    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


# ==============================================================================
# Rate Limiter Fixtures
# ==============================================================================


@pytest.fixture
def fast_limiter():
    """Create a rate limiter with fast refill for testing."""
    from asymmetric.core.data.rate_limiter import RateLimitConfig, TokenBucketLimiter

    config = RateLimitConfig(
        requests_per_second=100.0,  # Very fast for testing
        burst_allowance=10,
        max_backoff_seconds=1,
        initial_backoff_seconds=0.1,
    )
    return TokenBucketLimiter(config)


# ==============================================================================
# Mock Fixtures
# ==============================================================================


@pytest.fixture
def mock_sec_identity(monkeypatch):
    """Set a valid SEC_IDENTITY for testing."""
    monkeypatch.setenv("SEC_IDENTITY", "Asymmetric/1.0 (test@example.com)")
    yield


@pytest.fixture
def mock_edgar_response() -> dict[str, Any]:
    """Mock SEC EDGAR API response."""
    return {
        "cik": "0000320193",
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "filings": [
            {
                "accession_number": "0000320193-23-000001",
                "form": "10-K",
                "filing_date": "2023-10-27",
            }
        ],
    }


@pytest.fixture
def mock_gemini_response() -> dict[str, Any]:
    """Mock Gemini API response."""
    return {
        "content": "This is a mock AI analysis of the company.",
        "model": "gemini-2.5-flash",
        "cached": False,
        "token_count_input": 1000,
        "token_count_output": 200,
        "estimated_cost_usd": 0.01,
        "latency_ms": 500,
    }


# ==============================================================================
# CLI Test Fixtures
# ==============================================================================


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    from click.testing import CliRunner

    return CliRunner()
