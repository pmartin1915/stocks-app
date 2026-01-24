"""
Tests for the Piotroski F-Score Calculator.
"""

import pytest

from asymmetric.core.data.exceptions import InsufficientDataError
from asymmetric.core.scoring.piotroski import (
    FinancialPeriod,
    PiotroskiResult,
    PiotroskiScorer,
)


class TestFinancialPeriod:
    """Tests for FinancialPeriod dataclass."""

    def test_default_values(self):
        """Test all fields default to None."""
        period = FinancialPeriod()

        assert period.revenue is None
        assert period.gross_profit is None
        assert period.net_income is None
        assert period.total_assets is None
        assert period.operating_cash_flow is None

    def test_from_dict(self):
        """Test creating FinancialPeriod from dictionary."""
        data = {
            "revenue": 1000,
            "gross_profit": 400,
            "net_income": 100,
            "total_assets": 2000,
            "operating_cash_flow": 150,
        }

        period = FinancialPeriod.from_dict(data)

        assert period.revenue == 1000
        assert period.gross_profit == 400
        assert period.net_income == 100
        assert period.total_assets == 2000
        assert period.operating_cash_flow == 150

    def test_from_dict_missing_fields(self):
        """Test creating FinancialPeriod with partial data."""
        data = {"revenue": 1000}

        period = FinancialPeriod.from_dict(data)

        assert period.revenue == 1000
        assert period.gross_profit is None


class TestPiotroskiResult:
    """Tests for PiotroskiResult dataclass."""

    def test_interpretation_strong(self):
        """Test strong interpretation for high scores."""
        result = PiotroskiResult(score=8)
        assert "Strong" in result.interpretation

        result = PiotroskiResult(score=7)
        assert "Strong" in result.interpretation

        result = PiotroskiResult(score=9)
        assert "Strong" in result.interpretation

    def test_interpretation_moderate(self):
        """Test moderate interpretation for mid scores."""
        result = PiotroskiResult(score=5)
        assert "Moderate" in result.interpretation

        result = PiotroskiResult(score=4)
        assert "Moderate" in result.interpretation

        result = PiotroskiResult(score=6)
        assert "Moderate" in result.interpretation

    def test_interpretation_weak(self):
        """Test weak interpretation for low scores."""
        result = PiotroskiResult(score=2)
        assert "Weak" in result.interpretation

        result = PiotroskiResult(score=0)
        assert "Weak" in result.interpretation

        result = PiotroskiResult(score=3)
        assert "Weak" in result.interpretation

    def test_profitability_score(self):
        """Test profitability subscore calculation."""
        result = PiotroskiResult(
            score=4,
            positive_roa=True,
            positive_cfo=True,
            roa_improving=False,
            accruals_quality=True,
        )

        assert result.profitability_score == 3

    def test_leverage_score(self):
        """Test leverage subscore calculation."""
        result = PiotroskiResult(
            score=2,
            leverage_decreasing=True,
            current_ratio_improving=True,
            no_dilution=False,
        )

        assert result.leverage_score == 2

    def test_efficiency_score(self):
        """Test efficiency subscore calculation."""
        result = PiotroskiResult(
            score=2,
            gross_margin_improving=True,
            asset_turnover_improving=True,
        )

        assert result.efficiency_score == 2


class TestPiotroskiScorer:
    """Tests for PiotroskiScorer class."""

    @pytest.fixture
    def scorer(self):
        return PiotroskiScorer()

    # ========== PROFITABILITY SIGNALS ==========

    def test_positive_roa(self, scorer):
        """Test Signal 1: Positive ROA."""
        current = FinancialPeriod(net_income=100, total_assets=1000)
        prior = FinancialPeriod()

        result = scorer.calculate(current, prior)

        assert result.positive_roa is True  # 100/1000 = 10% > 0

    def test_negative_roa(self, scorer):
        """Test Signal 1: Negative ROA."""
        current = FinancialPeriod(net_income=-50, total_assets=1000)
        prior = FinancialPeriod()

        result = scorer.calculate(current, prior)

        assert result.positive_roa is False  # -50/1000 = -5% < 0

    def test_positive_cfo(self, scorer):
        """Test Signal 2: Positive Operating Cash Flow."""
        current = FinancialPeriod(operating_cash_flow=200)
        prior = FinancialPeriod()

        result = scorer.calculate(current, prior)

        assert result.positive_cfo is True

    def test_negative_cfo(self, scorer):
        """Test Signal 2: Negative Operating Cash Flow."""
        current = FinancialPeriod(operating_cash_flow=-100)
        prior = FinancialPeriod()

        result = scorer.calculate(current, prior)

        assert result.positive_cfo is False

    def test_roa_improving(self, scorer):
        """Test Signal 3: ROA improving."""
        current = FinancialPeriod(net_income=120, total_assets=1000)  # 12%
        prior = FinancialPeriod(net_income=100, total_assets=1000)  # 10%

        result = scorer.calculate(current, prior)

        assert result.roa_improving is True

    def test_roa_declining(self, scorer):
        """Test Signal 3: ROA declining."""
        current = FinancialPeriod(net_income=80, total_assets=1000)  # 8%
        prior = FinancialPeriod(net_income=100, total_assets=1000)  # 10%

        result = scorer.calculate(current, prior)

        assert result.roa_improving is False

    def test_accruals_quality_positive(self, scorer):
        """Test Signal 4: Good earnings quality (CFO > Net Income)."""
        current = FinancialPeriod(operating_cash_flow=150, net_income=100)
        prior = FinancialPeriod()

        result = scorer.calculate(current, prior)

        assert result.accruals_quality is True

    def test_accruals_quality_negative(self, scorer):
        """Test Signal 4: Poor earnings quality (CFO < Net Income)."""
        current = FinancialPeriod(operating_cash_flow=80, net_income=100)
        prior = FinancialPeriod()

        result = scorer.calculate(current, prior)

        assert result.accruals_quality is False

    # ========== LEVERAGE/LIQUIDITY SIGNALS ==========

    def test_leverage_decreasing(self, scorer):
        """Test Signal 5: Leverage decreasing."""
        current = FinancialPeriod(long_term_debt=100, total_assets=1000)  # 10%
        prior = FinancialPeriod(long_term_debt=200, total_assets=1000)  # 20%

        result = scorer.calculate(current, prior)

        assert result.leverage_decreasing is True

    def test_leverage_increasing(self, scorer):
        """Test Signal 5: Leverage increasing."""
        current = FinancialPeriod(long_term_debt=300, total_assets=1000)  # 30%
        prior = FinancialPeriod(long_term_debt=200, total_assets=1000)  # 20%

        result = scorer.calculate(current, prior)

        assert result.leverage_decreasing is False

    def test_no_debt_passes(self, scorer):
        """Test Signal 5: No debt at all passes."""
        current = FinancialPeriod(long_term_debt=0, total_assets=1000)
        prior = FinancialPeriod(long_term_debt=0, total_assets=1000)

        result = scorer.calculate(current, prior)

        assert result.leverage_decreasing is True

    def test_current_ratio_improving(self, scorer):
        """Test Signal 6: Current ratio improving."""
        current = FinancialPeriod(current_assets=200, current_liabilities=100)  # 2.0
        prior = FinancialPeriod(current_assets=150, current_liabilities=100)  # 1.5

        result = scorer.calculate(current, prior)

        assert result.current_ratio_improving is True

    def test_current_ratio_declining(self, scorer):
        """Test Signal 6: Current ratio declining."""
        current = FinancialPeriod(current_assets=100, current_liabilities=100)  # 1.0
        prior = FinancialPeriod(current_assets=150, current_liabilities=100)  # 1.5

        result = scorer.calculate(current, prior)

        assert result.current_ratio_improving is False

    def test_no_dilution(self, scorer):
        """Test Signal 7: No share dilution."""
        current = FinancialPeriod(shares_outstanding=100)
        prior = FinancialPeriod(shares_outstanding=100)

        result = scorer.calculate(current, prior)

        assert result.no_dilution is True

    def test_dilution(self, scorer):
        """Test Signal 7: Share dilution occurred."""
        current = FinancialPeriod(shares_outstanding=120)  # 20% increase
        prior = FinancialPeriod(shares_outstanding=100)

        result = scorer.calculate(current, prior)

        assert result.no_dilution is False

    def test_minor_dilution_still_fails(self, scorer):
        """Test Signal 7: Even small share increases fail (strict academic definition)."""
        # 0.5% increase - would have passed with old 1% tolerance, now fails
        current = FinancialPeriod(shares_outstanding=100.5)
        prior = FinancialPeriod(shares_outstanding=100)

        result = scorer.calculate(current, prior)

        # Per Piotroski (2000): ANY increase in shares outstanding fails
        assert result.no_dilution is False

    # ========== OPERATING EFFICIENCY SIGNALS ==========

    def test_gross_margin_improving(self, scorer):
        """Test Signal 8: Gross margin improving."""
        current = FinancialPeriod(gross_profit=500, revenue=1000)  # 50%
        prior = FinancialPeriod(gross_profit=400, revenue=1000)  # 40%

        result = scorer.calculate(current, prior)

        assert result.gross_margin_improving is True

    def test_gross_margin_declining(self, scorer):
        """Test Signal 8: Gross margin declining."""
        current = FinancialPeriod(gross_profit=300, revenue=1000)  # 30%
        prior = FinancialPeriod(gross_profit=400, revenue=1000)  # 40%

        result = scorer.calculate(current, prior)

        assert result.gross_margin_improving is False

    def test_asset_turnover_improving(self, scorer):
        """Test Signal 9: Asset turnover improving."""
        current = FinancialPeriod(revenue=1200, total_assets=1000)  # 1.2x
        prior = FinancialPeriod(revenue=1000, total_assets=1000)  # 1.0x

        result = scorer.calculate(current, prior)

        assert result.asset_turnover_improving is True

    def test_asset_turnover_declining(self, scorer):
        """Test Signal 9: Asset turnover declining."""
        current = FinancialPeriod(revenue=800, total_assets=1000)  # 0.8x
        prior = FinancialPeriod(revenue=1000, total_assets=1000)  # 1.0x

        result = scorer.calculate(current, prior)

        assert result.asset_turnover_improving is False

    # ========== FULL SCORE TESTS ==========

    def test_perfect_score(self, scorer, healthy_company_data):
        """Test a company with perfect F-Score (9/9)."""
        result = scorer.calculate_from_dict(
            healthy_company_data["current"],
            healthy_company_data["prior"],
        )

        assert result.score == 9
        assert "Strong" in result.interpretation
        assert result.signals_available == 9
        assert len(result.missing_signals) == 0

    def test_weak_score(self, scorer, weak_company_data):
        """Test a company with weak F-Score."""
        result = scorer.calculate_from_dict(
            weak_company_data["current"],
            weak_company_data["prior"],
        )

        assert result.score <= 3
        assert "Weak" in result.interpretation

    def test_partial_data(self, scorer):
        """Test calculation with partial data."""
        current = FinancialPeriod(
            net_income=100,
            total_assets=1000,
            operating_cash_flow=150,
        )
        prior = FinancialPeriod(
            net_income=80,
            total_assets=1000,
            operating_cash_flow=120,
        )

        result = scorer.calculate(current, prior)

        # Should calculate available signals
        assert result.positive_roa is True
        assert result.positive_cfo is True
        assert result.roa_improving is True
        assert result.accruals_quality is True

        # Missing signals should be None
        assert result.gross_margin_improving is None
        assert result.no_dilution is None

        # Score should only count available signals
        assert result.score >= 4
        assert len(result.missing_signals) > 0

    def test_require_all_signals_raises(self, scorer):
        """Test that require_all_signals raises error on missing data."""
        current = FinancialPeriod(net_income=100)  # Very incomplete
        prior = FinancialPeriod(net_income=80)

        with pytest.raises(InsufficientDataError) as exc_info:
            scorer.calculate(current, prior, require_all_signals=True)

        assert len(exc_info.value.missing_fields) > 0

    def test_calculate_from_dict(self, scorer, sample_financial_data):
        """Test calculate_from_dict method."""
        result = scorer.calculate_from_dict(
            sample_financial_data["current"],
            sample_financial_data["prior"],
        )

        assert isinstance(result, PiotroskiResult)
        assert 0 <= result.score <= 9

    def test_zero_denominators_handled(self, scorer):
        """Test that zero denominators don't cause errors."""
        current = FinancialPeriod(
            net_income=100,
            total_assets=0,  # Zero denominator
            revenue=0,
            current_liabilities=0,
        )
        prior = FinancialPeriod(
            total_assets=0,
            revenue=0,
        )

        # Should not raise, just return None for affected signals
        result = scorer.calculate(current, prior)

        assert result.positive_roa is None  # Can't calculate with 0 assets
        assert result.gross_margin_improving is None  # Can't calculate with 0 revenue
