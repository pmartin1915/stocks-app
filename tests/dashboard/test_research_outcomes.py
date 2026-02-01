"""Tests for Research Wizard outcome tracking features."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from dashboard.utils.decisions import (
    update_decision_outcome,
    get_decisions_with_outcomes,
    analyze_by_conviction,
    calculate_portfolio_return,
)


class TestOutcomeTracking:
    """Test outcome tracking functionality."""

    @patch("dashboard.utils.decisions.get_session")
    @patch("dashboard.utils.decisions.init_db")
    def test_update_decision_outcome(self, mock_init_db, mock_get_session):
        """Test updating a decision with outcome data."""
        # Mock session and decision
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_decision = MagicMock()
        mock_decision.id = 1
        mock_session.get.return_value = mock_decision

        # Update outcome
        result = update_decision_outcome(
            decision_id=1,
            actual_outcome="success",
            actual_price=150.0,
            lessons_learned="Great call on the valuation",
            hit=True,
        )

        assert result is True
        assert mock_decision.actual_outcome == "success"
        assert mock_decision.actual_price == 150.0
        assert mock_decision.lessons_learned == "Great call on the valuation"
        assert mock_decision.hit is True
        assert mock_decision.outcome_date is not None

    def test_analyze_by_conviction(self):
        """Test hit rate calculation by conviction level."""
        # Sample decisions with outcomes
        decisions = [
            {"confidence": 5, "hit": True},
            {"confidence": 5, "hit": True},
            {"confidence": 5, "hit": False},
            {"confidence": 3, "hit": True},
            {"confidence": 3, "hit": False},
            {"confidence": 3, "hit": False},
            {"confidence": 1, "hit": False},
        ]

        stats = analyze_by_conviction(decisions)

        # Check conviction level 5: 2 hits out of 3 total = 66.7%
        level_5_stats = [s for s in stats if s["conviction_level"] == 5][0]
        assert level_5_stats["hit_count"] == 2
        assert level_5_stats["total_count"] == 3
        assert level_5_stats["hit_rate_pct"] == pytest.approx(66.7, rel=0.1)

        # Check conviction level 3: 1 hit out of 3 total = 33.3%
        level_3_stats = [s for s in stats if s["conviction_level"] == 3][0]
        assert level_3_stats["hit_count"] == 1
        assert level_3_stats["total_count"] == 3
        assert level_3_stats["hit_rate_pct"] == pytest.approx(33.3, rel=0.1)

        # Check conviction level 1: 0 hits out of 1 total = 0%
        level_1_stats = [s for s in stats if s["conviction_level"] == 1][0]
        assert level_1_stats["hit_count"] == 0
        assert level_1_stats["total_count"] == 1
        assert level_1_stats["hit_rate_pct"] == 0.0

    def test_calculate_portfolio_return(self):
        """Test hypothetical portfolio return calculation."""
        # Sample decisions with target and actual prices
        decisions = [
            {"confidence": 5, "target_price": 100.0, "actual_price": 120.0},  # +20%
            {"confidence": 5, "target_price": 50.0, "actual_price": 55.0},    # +10%
            {"confidence": 3, "target_price": 200.0, "actual_price": 180.0},  # -10%
            {"confidence": 1, "target_price": 75.0, "actual_price": 70.0},    # -6.67%
        ]

        # Test with minimum conviction 5 (only first two decisions)
        avg_return_high = calculate_portfolio_return(decisions, conviction_min=5)
        # (20% + 10%) / 2 = 15%
        assert avg_return_high == pytest.approx(15.0, rel=0.01)

        # Test with minimum conviction 3 (first three decisions)
        avg_return_medium = calculate_portfolio_return(decisions, conviction_min=3)
        # (20% + 10% - 10%) / 3 = 6.67%
        assert avg_return_medium == pytest.approx(6.67, rel=0.01)

        # Test with minimum conviction 1 (all decisions)
        avg_return_all = calculate_portfolio_return(decisions, conviction_min=1)
        # (20% + 10% - 10% - 6.67%) / 4 = 3.33%
        assert avg_return_all == pytest.approx(3.33, rel=0.01)

    def test_calculate_portfolio_return_empty(self):
        """Test portfolio return with no qualifying decisions."""
        decisions = [
            {"confidence": 1, "target_price": 100.0, "actual_price": 120.0},
        ]

        # No decisions with conviction >= 5
        avg_return = calculate_portfolio_return(decisions, conviction_min=5)
        assert avg_return == 0.0

    def test_calculate_portfolio_return_missing_prices(self):
        """Test portfolio return skips decisions with missing prices."""
        decisions = [
            {"confidence": 5, "target_price": 100.0, "actual_price": 120.0},  # +20%
            {"confidence": 5, "target_price": None, "actual_price": 110.0},   # Skip (no target)
            {"confidence": 5, "target_price": 50.0, "actual_price": None},    # Skip (no actual)
            {"confidence": 5, "target_price": 50.0, "actual_price": 60.0},    # +20%
        ]

        avg_return = calculate_portfolio_return(decisions, conviction_min=5)
        # (20% + 20%) / 2 = 20%
        assert avg_return == pytest.approx(20.0, rel=0.01)


class TestOutcomeValidation:
    """Test outcome tracking validation."""

    def test_analyze_by_conviction_ignores_none_hit(self):
        """Test that decisions with hit=None are excluded from stats."""
        decisions = [
            {"confidence": 5, "hit": True},
            {"confidence": 5, "hit": None},  # Should be ignored
            {"confidence": 5, "hit": False},
        ]

        stats = analyze_by_conviction(decisions)
        level_5_stats = [s for s in stats if s["conviction_level"] == 5][0]

        # Only 2 decisions counted (True and False), None ignored
        assert level_5_stats["total_count"] == 2
        assert level_5_stats["hit_count"] == 1
        assert level_5_stats["hit_rate_pct"] == 50.0

    def test_calculate_portfolio_return_zero_target_price(self):
        """Test that decisions with zero target price are skipped."""
        decisions = [
            {"confidence": 5, "target_price": 0.0, "actual_price": 120.0},   # Skip (zero target)
            {"confidence": 5, "target_price": 100.0, "actual_price": 110.0}, # +10%
        ]

        avg_return = calculate_portfolio_return(decisions, conviction_min=5)
        # Only second decision counted
        assert avg_return == pytest.approx(10.0, rel=0.01)
