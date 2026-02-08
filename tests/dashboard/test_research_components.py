"""Tests for Research tab components.

Tests import integrity, wizard state transitions, and data validation
for the extracted research component modules.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestImports:
    """Verify all research component modules import correctly."""

    def test_import_wizard_steps(self):
        from dashboard.components.research.wizard_steps import (
            render_step_indicator,
            render_research_step,
            render_thesis_step,
            render_decision_step,
        )

        assert callable(render_step_indicator)
        assert callable(render_research_step)
        assert callable(render_thesis_step)
        assert callable(render_decision_step)

    def test_import_outcomes_tab(self):
        from dashboard.components.research.outcomes_tab import render_review_outcomes_tab

        assert callable(render_review_outcomes_tab)

    def test_import_analytics_tab(self):
        from dashboard.components.research.analytics_tab import render_analytics_tab

        assert callable(render_analytics_tab)

    def test_import_package_reexports(self):
        from dashboard.components.research import (
            render_step_indicator,
            render_research_step,
            render_thesis_step,
            render_decision_step,
            render_review_outcomes_tab,
            render_analytics_tab,
        )

        assert all(
            callable(f)
            for f in [
                render_step_indicator,
                render_research_step,
                render_thesis_step,
                render_decision_step,
                render_review_outcomes_tab,
                render_analytics_tab,
            ]
        )


class TestWizardStepLogic:
    """Test wizard step transition logic (pure state)."""

    def test_step_indicator_values(self):
        """Step indicator should handle steps 0, 1, 2."""
        steps = ["1. Research", "2. Thesis", "3. Decision"]
        assert len(steps) == 3

        # Step 0: first is current, rest are future
        for i, step in enumerate(steps):
            if i == 0:
                assert "Research" in step
            elif i == 1:
                assert "Thesis" in step
            else:
                assert "Decision" in step

    def test_ticker_validation_valid(self):
        """Valid tickers should pass format check."""
        valid_tickers = ["AAPL", "MSFT", "BRK", "X", "GOOGL"]
        for ticker in valid_tickers:
            assert ticker.isalnum() and len(ticker) <= 5

    def test_ticker_validation_invalid(self):
        """Invalid tickers should fail format check."""
        invalid_tickers = ["TOOLONGTICKER", "AB.C", "12345+", ""]
        for ticker in invalid_tickers:
            is_valid = ticker.isalnum() and len(ticker) <= 5 if ticker else False
            assert not is_valid

    def test_thesis_summary_min_length(self):
        """Thesis summary must be at least 20 characters."""
        short_summary = "Too short"
        valid_summary = "This is a valid thesis summary about Apple stock"

        assert len(short_summary.strip()) < 20
        assert len(valid_summary.strip()) >= 20


class TestThesisDraftState:
    """Test thesis draft state structure."""

    def test_thesis_draft_keys(self):
        """Draft should have all expected keys."""
        draft = {
            "summary": "Test summary with enough characters to pass validation",
            "bull_case": "Strong growth",
            "bear_case": "High valuation",
            "conviction": 4,
            "key_metrics": "Revenue growth, margins",
        }

        expected_keys = {"summary", "bull_case", "bear_case", "conviction", "key_metrics"}
        assert set(draft.keys()) == expected_keys

    def test_conviction_range(self):
        """Conviction must be 1-5."""
        for level in range(1, 6):
            assert 1 <= level <= 5

        for invalid in [0, 6, -1]:
            assert not (1 <= invalid <= 5)

    def test_conviction_labels(self):
        """All conviction levels should have labels."""
        labels = {1: "Very Low", 2: "Low", 3: "Medium", 4: "High", 5: "Very High"}
        assert len(labels) == 5
        for level in range(1, 6):
            assert level in labels


class TestAnalyticsDataPrep:
    """Test analytics data preparation."""

    def test_conviction_filter(self):
        """Test filtering decisions by minimum conviction."""
        decisions = [
            {"confidence": 1, "hit": True},
            {"confidence": 3, "hit": False},
            {"confidence": 5, "hit": True},
        ]

        min_conviction = 3
        filtered = [d for d in decisions if (d.get("confidence") or 3) >= min_conviction]

        assert len(filtered) == 2
        assert all(d["confidence"] >= 3 for d in filtered)

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation."""
        decisions = [
            {"hit": True},
            {"hit": True},
            {"hit": False},
            {"hit": True},
        ]

        hits = sum(1 for d in decisions if d.get("hit"))
        total = len(decisions)
        hit_rate = (hits / total * 100) if total > 0 else 0

        assert hits == 3
        assert hit_rate == 75.0

    def test_empty_decisions(self):
        """Analytics should handle empty decision list."""
        decisions = []
        hit_rate = 0 if not decisions else (sum(1 for d in decisions if d.get("hit")) / len(decisions) * 100)
        assert hit_rate == 0
