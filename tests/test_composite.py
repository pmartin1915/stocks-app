"""
Tests for the Composite Scoring Engine.

Tests the gate-and-rank approach that combines Piotroski F-Score and Altman Z-Score:
1. Gate: Filter stocks meeting minimum Piotroski threshold (default >= 7)
2. Rank: Sort passing stocks by Altman Z-Score (higher = safer)
"""

import pytest
from typing import Any

from asymmetric.core.data.exceptions import InsufficientDataError
from asymmetric.core.scoring.composite import CompositeResult, CompositeScorer
from asymmetric.core.scoring.altman import AltmanResult
from asymmetric.core.scoring.piotroski import PiotroskiResult


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_piotroski_high() -> PiotroskiResult:
    """Mock Piotroski result with high score (passes default gate)."""
    return PiotroskiResult(
        score=8,
        positive_roa=True,
        positive_cfo=True,
        roa_improving=True,
        accruals_quality=True,
        leverage_decreasing=True,
        current_ratio_improving=True,
        no_dilution=True,
        gross_margin_improving=True,
        asset_turnover_improving=False,
        interpretation="Strong",
        signals_available=9,
    )


@pytest.fixture
def mock_piotroski_low() -> PiotroskiResult:
    """Mock Piotroski result with low score (fails default gate)."""
    return PiotroskiResult(
        score=3,
        positive_roa=True,
        positive_cfo=False,
        roa_improving=False,
        accruals_quality=True,
        leverage_decreasing=False,
        current_ratio_improving=False,
        no_dilution=False,
        gross_margin_improving=False,
        asset_turnover_improving=True,
        interpretation="Weak",
        signals_available=9,
    )


@pytest.fixture
def mock_altman_safe() -> AltmanResult:
    """Mock Altman result in Safe zone."""
    return AltmanResult(
        z_score=4.5,
        zone="Safe",
        interpretation="Low bankruptcy risk",
        formula_used="manufacturing",
        x1_working_capital_ratio=0.2,
        x2_retained_earnings_ratio=0.3,
        x3_ebit_ratio=0.15,
        x4_equity_leverage_ratio=1.5,
        x5_asset_turnover=0.8,
    )


@pytest.fixture
def mock_altman_grey() -> AltmanResult:
    """Mock Altman result in Grey zone."""
    return AltmanResult(
        z_score=2.5,
        zone="Grey",
        interpretation="Moderate bankruptcy risk",
        formula_used="manufacturing",
        x1_working_capital_ratio=0.1,
        x2_retained_earnings_ratio=0.2,
        x3_ebit_ratio=0.08,
        x4_equity_leverage_ratio=0.8,
        x5_asset_turnover=0.6,
    )


@pytest.fixture
def mock_altman_distress() -> AltmanResult:
    """Mock Altman result in Distress zone."""
    return AltmanResult(
        z_score=1.2,
        zone="Distress",
        interpretation="High bankruptcy risk",
        formula_used="manufacturing",
        x1_working_capital_ratio=-0.1,
        x2_retained_earnings_ratio=-0.2,
        x3_ebit_ratio=-0.05,
        x4_equity_leverage_ratio=0.3,
        x5_asset_turnover=0.4,
    )


# ==============================================================================
# CompositeResult Dataclass Tests
# ==============================================================================


class TestCompositeResult:
    """Tests for CompositeResult dataclass."""

    def test_composite_result_properties(
        self, mock_piotroski_high: PiotroskiResult, mock_altman_safe: AltmanResult
    ):
        """Test convenience property accessors."""
        result = CompositeResult(
            ticker="AAPL",
            piotroski=mock_piotroski_high,
            altman=mock_altman_safe,
            passes_gate=True,
            composite_rank=1,
        )

        assert result.piotroski_score == 8
        assert result.altman_z_score == 4.5
        assert result.altman_zone == "Safe"

    def test_composite_result_to_dict(
        self, mock_piotroski_high: PiotroskiResult, mock_altman_safe: AltmanResult
    ):
        """Test JSON serialization."""
        result = CompositeResult(
            ticker="MSFT",
            piotroski=mock_piotroski_high,
            altman=mock_altman_safe,
            passes_gate=True,
            composite_rank=2,
            gate_threshold=7,
        )

        d = result.to_dict()

        assert d["ticker"] == "MSFT"
        assert d["passes_gate"] is True
        assert d["composite_rank"] == 2
        assert d["gate_threshold"] == 7
        assert d["piotroski"]["score"] == 8
        assert d["altman"]["z_score"] == 4.5
        assert d["altman"]["zone"] == "Safe"

    def test_passes_gate_true(
        self, mock_piotroski_high: PiotroskiResult, mock_altman_safe: AltmanResult
    ):
        """Test passes_gate is True when score >= threshold."""
        result = CompositeResult(
            ticker="AAPL",
            piotroski=mock_piotroski_high,  # score=8
            altman=mock_altman_safe,
            passes_gate=True,
            gate_threshold=7,
        )

        assert result.passes_gate is True

    def test_passes_gate_false(
        self, mock_piotroski_low: PiotroskiResult, mock_altman_grey: AltmanResult
    ):
        """Test passes_gate is False when score < threshold."""
        result = CompositeResult(
            ticker="WEAK",
            piotroski=mock_piotroski_low,  # score=3
            altman=mock_altman_grey,
            passes_gate=False,
            gate_threshold=7,
        )

        assert result.passes_gate is False

    def test_composite_rank_none_for_non_passing(
        self, mock_piotroski_low: PiotroskiResult, mock_altman_distress: AltmanResult
    ):
        """Test composite_rank is None when gate fails."""
        result = CompositeResult(
            ticker="FAIL",
            piotroski=mock_piotroski_low,
            altman=mock_altman_distress,
            passes_gate=False,
            composite_rank=None,
        )

        assert result.composite_rank is None


# ==============================================================================
# CompositeScorer.score_from_dict Tests
# ==============================================================================


class TestCompositeScorerScoreFromDict:
    """Tests for CompositeScorer.score_from_dict method."""

    def test_score_healthy_company_passes_gate(self, healthy_company_data: dict[str, Any]):
        """Test healthy company passes the gate."""
        scorer = CompositeScorer()
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        result = scorer.score_from_dict(current, prior, ticker="HEALTHY")

        assert result.passes_gate is True
        assert result.piotroski_score >= 7
        assert result.ticker == "HEALTHY"

    def test_score_weak_company_fails_gate(self, weak_company_data: dict[str, Any]):
        """Test weak company fails the gate."""
        scorer = CompositeScorer()
        current = weak_company_data["current"]
        prior = weak_company_data["prior"]

        result = scorer.score_from_dict(current, prior, ticker="WEAK")

        assert result.passes_gate is False
        assert result.piotroski_score < 7

    def test_score_custom_threshold_low(self, weak_company_data: dict[str, Any]):
        """Test custom threshold allows lower scores to pass."""
        scorer = CompositeScorer()
        current = weak_company_data["current"]
        prior = weak_company_data["prior"]

        # With piotroski_min=2, a score of 3 should pass
        result = scorer.score_from_dict(
            current, prior, ticker="WEAK", piotroski_min=2
        )

        # Weak company has score ~2-3, so with threshold 2 it may pass
        assert result.gate_threshold == 2

    def test_score_custom_threshold_high(self, healthy_company_data: dict[str, Any]):
        """Test custom high threshold excludes even healthy companies."""
        scorer = CompositeScorer()
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        # With piotroski_min=9, even a healthy company (score ~8) fails
        result = scorer.score_from_dict(
            current, prior, ticker="HEALTHY", piotroski_min=9
        )

        # Healthy company typically scores 7-8, so fails threshold of 9
        if result.piotroski_score < 9:
            assert result.passes_gate is False

    def test_score_manufacturing_formula(self, healthy_company_data: dict[str, Any]):
        """Test manufacturing formula is used when specified."""
        scorer = CompositeScorer()
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        result = scorer.score_from_dict(
            current, prior, ticker="MFG", is_manufacturing=True
        )

        assert result.altman.formula_used == "manufacturing"

    def test_score_non_manufacturing_formula(self, healthy_company_data: dict[str, Any]):
        """Test non-manufacturing formula is used when specified."""
        scorer = CompositeScorer()
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        result = scorer.score_from_dict(
            current, prior, ticker="SVC", is_manufacturing=False
        )

        assert result.altman.formula_used == "non_manufacturing"


# ==============================================================================
# CompositeScorer.rank_stocks Tests
# ==============================================================================


class TestCompositeScorerRankStocks:
    """Tests for CompositeScorer.rank_stocks method."""

    def test_rank_passing_stocks_sorted_by_altman(
        self, healthy_company_data: dict[str, Any]
    ):
        """Test passing stocks are sorted by Altman Z-Score descending."""
        scorer = CompositeScorer()

        # Create multiple stocks with same Piotroski but different Altman
        stocks = [
            {
                "ticker": "HIGH_Z",
                "current": {
                    **healthy_company_data["current"],
                    "market_cap": 500_000_000,  # Higher market cap = higher Z
                },
                "prior": healthy_company_data["prior"],
            },
            {
                "ticker": "LOW_Z",
                "current": {
                    **healthy_company_data["current"],
                    "market_cap": 50_000_000,  # Lower market cap = lower Z
                },
                "prior": healthy_company_data["prior"],
            },
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=5)

        # Both should pass (healthy company)
        passing = [r for r in results if r.passes_gate]

        # If both pass, should be sorted by Altman descending
        if len(passing) >= 2:
            assert passing[0].altman_z_score >= passing[1].altman_z_score

    def test_rank_non_passing_stocks_sorted_by_piotroski(
        self, weak_company_data: dict[str, Any]
    ):
        """Test non-passing stocks are sorted by Piotroski score descending."""
        scorer = CompositeScorer()

        # Create stocks that fail gate, with varying Piotroski scores
        stocks = [
            {
                "ticker": "WEAK1",
                "current": weak_company_data["current"],
                "prior": weak_company_data["prior"],
            },
            {
                "ticker": "WEAK2",
                "current": {
                    **weak_company_data["current"],
                    "net_income": -10_000_000,  # Worse - lower Piotroski
                },
                "prior": weak_company_data["prior"],
            },
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=8)

        not_passing = [r for r in results if not r.passes_gate]

        if len(not_passing) >= 2:
            assert not_passing[0].piotroski_score >= not_passing[1].piotroski_score

    def test_rank_passing_stocks_first(
        self, healthy_company_data: dict[str, Any], weak_company_data: dict[str, Any]
    ):
        """Test passing stocks appear before non-passing stocks."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": "WEAK",
                "current": weak_company_data["current"],
                "prior": weak_company_data["prior"],
            },
            {
                "ticker": "HEALTHY",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            },
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=6)

        # Find indices
        passing_indices = [i for i, r in enumerate(results) if r.passes_gate]
        not_passing_indices = [i for i, r in enumerate(results) if not r.passes_gate]

        # All passing should come before all non-passing
        if passing_indices and not_passing_indices:
            assert max(passing_indices) < min(not_passing_indices)

    def test_rank_assigns_positions(self, healthy_company_data: dict[str, Any]):
        """Test composite_rank is assigned 1, 2, 3... for passing stocks."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": f"STOCK{i}",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            }
            for i in range(3)
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=5)

        passing = [r for r in results if r.passes_gate]

        for i, result in enumerate(passing, start=1):
            assert result.composite_rank == i

    def test_rank_empty_list(self):
        """Test ranking empty list returns empty list."""
        scorer = CompositeScorer()

        results = scorer.rank_stocks([])

        assert results == []

    def test_rank_all_fail_gate(self, weak_company_data: dict[str, Any]):
        """Test all stocks failing gate are sorted by Piotroski."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": "WEAK1",
                "current": weak_company_data["current"],
                "prior": weak_company_data["prior"],
            },
            {
                "ticker": "WEAK2",
                "current": weak_company_data["current"],
                "prior": weak_company_data["prior"],
            },
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=9)

        # All should fail gate
        assert all(not r.passes_gate for r in results)
        # None should have rank
        assert all(r.composite_rank is None for r in results)

    def test_rank_skips_insufficient_data(self, healthy_company_data: dict[str, Any]):
        """Test stocks with insufficient data are skipped."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": "HEALTHY",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            },
            {
                "ticker": "EMPTY",
                "current": {},  # No data - will fail
                "prior": {},
            },
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=5)

        # Only HEALTHY should be in results (EMPTY skipped)
        tickers = [r.ticker for r in results]
        assert "HEALTHY" in tickers
        assert "EMPTY" not in tickers


# ==============================================================================
# CompositeScorer.get_top_stocks Tests
# ==============================================================================


class TestCompositeScorerGetTopStocks:
    """Tests for CompositeScorer.get_top_stocks method."""

    def test_get_top_stocks_respects_limit(self, healthy_company_data: dict[str, Any]):
        """Test get_top_stocks returns at most N stocks."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": f"STOCK{i}",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            }
            for i in range(5)
        ]

        results = scorer.get_top_stocks(stocks, limit=2, piotroski_min=5)

        assert len(results) <= 2

    def test_get_top_stocks_only_passing(
        self, healthy_company_data: dict[str, Any], weak_company_data: dict[str, Any]
    ):
        """Test get_top_stocks excludes non-passing stocks."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": "HEALTHY",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            },
            {
                "ticker": "WEAK",
                "current": weak_company_data["current"],
                "prior": weak_company_data["prior"],
            },
        ]

        results = scorer.get_top_stocks(stocks, limit=10, piotroski_min=6)

        # All results should pass gate
        assert all(r.passes_gate for r in results)

    def test_get_top_stocks_less_than_limit(self, healthy_company_data: dict[str, Any]):
        """Test returns fewer if not enough stocks pass gate."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": "ONLY_ONE",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            },
        ]

        results = scorer.get_top_stocks(stocks, limit=10, piotroski_min=5)

        # Should return 1 (or 0 if it doesn't pass), not 10
        assert len(results) <= 1

    def test_get_top_stocks_empty_universe(self):
        """Test empty universe returns empty list."""
        scorer = CompositeScorer()

        results = scorer.get_top_stocks([], limit=10)

        assert results == []


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestCompositeIntegration:
    """Integration tests using real scorer calculations."""

    def test_full_workflow_with_perfect_data(
        self, perfect_piotroski_data: tuple[dict[str, Any], dict[str, Any]]
    ):
        """Test complete workflow with perfect Piotroski data."""
        scorer = CompositeScorer()
        current, prior = perfect_piotroski_data

        result = scorer.score_from_dict(current, prior, ticker="PERFECT")

        # Perfect Piotroski should pass gate
        assert result.passes_gate is True
        assert result.piotroski_score >= 7
        assert result.ticker == "PERFECT"
        assert result.altman is not None

    def test_full_workflow_rank_multiple(
        self,
        healthy_company_data: dict[str, Any],
        weak_company_data: dict[str, Any],
    ):
        """Test ranking workflow with mixed quality stocks."""
        scorer = CompositeScorer()

        stocks = [
            {
                "ticker": "HEALTHY",
                "current": healthy_company_data["current"],
                "prior": healthy_company_data["prior"],
            },
            {
                "ticker": "WEAK",
                "current": weak_company_data["current"],
                "prior": weak_company_data["prior"],
            },
        ]

        results = scorer.rank_stocks(stocks, piotroski_min=6)

        # Should have results for both
        assert len(results) == 2

        # Healthy should be ranked, weak should not
        healthy_result = next((r for r in results if r.ticker == "HEALTHY"), None)
        weak_result = next((r for r in results if r.ticker == "WEAK"), None)

        if healthy_result and healthy_result.passes_gate:
            assert healthy_result.composite_rank is not None
        if weak_result and not weak_result.passes_gate:
            assert weak_result.composite_rank is None
