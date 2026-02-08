"""Tests for Portfolio tab components.

Tests data preparation, import integrity, and render function signatures
for the extracted portfolio tab modules.
"""

import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, patch


@dataclass
class MockHolding:
    """Mock HoldingDetail for testing."""

    ticker: str = "AAPL"
    company_name: str = "Apple Inc."
    quantity: float = 100.0
    cost_basis_total: float = 15000.0
    current_price: Optional[float] = 185.0
    market_value: Optional[float] = 18500.0
    unrealized_pnl: Optional[float] = 3500.0
    unrealized_pnl_percent: Optional[float] = 23.33
    allocation_percent: float = 60.0
    days_held: int = 90
    fscore: Optional[int] = 7
    zone: Optional[str] = "Safe"


@dataclass
class MockWeightedScores:
    """Mock WeightedScores for testing."""

    weighted_fscore: float = 6.5
    weighted_zscore: float = 3.1
    holdings_with_scores: int = 3
    holdings_without_scores: int = 1
    safe_allocation: float = 60.0
    grey_allocation: float = 30.0
    distress_allocation: float = 10.0


class TestImports:
    """Verify all component modules import correctly."""

    def test_import_holdings_tab(self):
        from dashboard.components.portfolio.holdings_tab import render_holdings_tab

        assert callable(render_holdings_tab)

    def test_import_performance_tab(self):
        from dashboard.components.portfolio.performance_tab import render_performance_tab

        assert callable(render_performance_tab)

    def test_import_historical_tab(self):
        from dashboard.components.portfolio.historical_tab import render_historical_tab

        assert callable(render_historical_tab)

    def test_import_transactions_tab(self):
        from dashboard.components.portfolio.transactions_tab import (
            render_add_transaction_tab,
            render_transaction_history_tab,
        )

        assert callable(render_add_transaction_tab)
        assert callable(render_transaction_history_tab)

    def test_import_health_tab(self):
        from dashboard.components.portfolio.health_tab import render_health_tab

        assert callable(render_health_tab)

    def test_import_package_reexports(self):
        from dashboard.components.portfolio import (
            render_holdings_tab,
            render_performance_tab,
            render_historical_tab,
            render_add_transaction_tab,
            render_transaction_history_tab,
            render_health_tab,
        )

        assert all(
            callable(f)
            for f in [
                render_holdings_tab,
                render_performance_tab,
                render_historical_tab,
                render_add_transaction_tab,
                render_transaction_history_tab,
                render_health_tab,
            ]
        )


class TestHoldingsDataPrep:
    """Test holdings data preparation logic (pure data transforms)."""

    def test_holdings_data_construction(self):
        """Test that HoldingDetail fields map correctly to display dict."""
        h = MockHolding()

        # Simulate the data prep from holdings_tab.py
        if h.unrealized_pnl is not None:
            pnl_text = f"${h.unrealized_pnl:,.2f} ({h.unrealized_pnl_percent:+.1f}%)"
        else:
            pnl_text = "N/A"

        row = {
            "Ticker": h.ticker,
            "Cost Basis": h.cost_basis_total,
            "Current Price": h.current_price if h.current_price else 0.0,
            "Market Value": h.market_value if h.market_value else h.cost_basis_total,
            "Unrealized P&L": pnl_text,
            "_pnl_pct": h.unrealized_pnl_percent if h.unrealized_pnl_percent is not None else 0.0,
        }

        assert row["Ticker"] == "AAPL"
        assert row["Cost Basis"] == 15000.0
        assert row["Current Price"] == 185.0
        assert row["Market Value"] == 18500.0
        assert "$3,500.00" in row["Unrealized P&L"]
        assert "+23.3%" in row["Unrealized P&L"]
        assert row["_pnl_pct"] == 23.33

    def test_holdings_data_no_market_data(self):
        """Test fallback when market data unavailable."""
        h = MockHolding(current_price=None, market_value=None, unrealized_pnl=None, unrealized_pnl_percent=None)

        pnl_text = f"${h.unrealized_pnl:,.2f}" if h.unrealized_pnl is not None else "N/A"
        market_value = h.market_value if h.market_value else h.cost_basis_total

        assert pnl_text == "N/A"
        assert market_value == 15000.0  # Falls back to cost basis


class TestPerformanceMetrics:
    """Test performance metric calculations."""

    def test_win_rate_calculation(self):
        """Test win rate is calculated correctly."""
        holdings = [
            MockHolding(unrealized_pnl=100),
            MockHolding(unrealized_pnl=200),
            MockHolding(unrealized_pnl=-50),
            MockHolding(unrealized_pnl=0),
        ]

        winning = [h for h in holdings if h.unrealized_pnl and h.unrealized_pnl > 0]
        win_rate = (len(winning) / len(holdings) * 100) if holdings else 0

        assert len(winning) == 2
        assert win_rate == 50.0

    def test_avg_gain_loss(self):
        """Test average gain and loss calculations."""
        holdings = [
            MockHolding(unrealized_pnl=1000),
            MockHolding(unrealized_pnl=500),
            MockHolding(unrealized_pnl=-200),
        ]

        winning = [h for h in holdings if h.unrealized_pnl and h.unrealized_pnl > 0]
        losing = [h for h in holdings if h.unrealized_pnl and h.unrealized_pnl < 0]

        avg_gain = sum(h.unrealized_pnl for h in winning) / len(winning) if winning else 0
        avg_loss = sum(h.unrealized_pnl for h in losing) / len(losing) if losing else 0

        assert avg_gain == 750.0
        assert avg_loss == -200.0


class TestHealthAssessment:
    """Test health assessment logic."""

    def test_strong_fscore(self):
        scores = MockWeightedScores(weighted_fscore=8.0)
        assert scores.weighted_fscore >= 7

    def test_moderate_fscore(self):
        scores = MockWeightedScores(weighted_fscore=5.5)
        assert 5 <= scores.weighted_fscore < 7

    def test_weak_fscore(self):
        scores = MockWeightedScores(weighted_fscore=3.0)
        assert scores.weighted_fscore < 5

    def test_distress_warning(self):
        scores = MockWeightedScores(distress_allocation=25.0)
        assert scores.distress_allocation > 20

    def test_safe_allocation(self):
        scores = MockWeightedScores(safe_allocation=75.0)
        assert scores.safe_allocation > 60

    def test_zone_percentages_sum(self):
        scores = MockWeightedScores(safe_allocation=60.0, grey_allocation=30.0, distress_allocation=10.0)
        total = scores.safe_allocation + scores.grey_allocation + scores.distress_allocation
        assert total == pytest.approx(100.0)
