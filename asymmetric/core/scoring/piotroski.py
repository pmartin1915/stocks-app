"""
Piotroski F-Score Calculator.

The Piotroski F-Score is a 9-point scoring system that measures the financial
health of a company based on profitability, leverage/liquidity, and operating
efficiency signals.

Scoring Components:
- Profitability (4 points):
  1. ROA > 0 (positive return on assets)
  2. Operating Cash Flow > 0
  3. ROA improving (current > prior year)
  4. Cash Flow > Net Income (quality of earnings / accruals)

- Leverage/Liquidity (3 points):
  5. Long-term Debt ratio decreasing
  6. Current Ratio improving
  7. No new share dilution

- Operating Efficiency (2 points):
  8. Gross Margin improving
  9. Asset Turnover improving

Interpretation:
- 7-9: Strong - Financially healthy
- 4-6: Moderate - Mixed signals
- 0-3: Weak - Financial concerns

Reference: Piotroski, J. D. (2000). "Value Investing: The Use of Historical
Financial Statement Information to Separate Winners from Losers."
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from asymmetric.core.data.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


@dataclass
class FinancialPeriod:
    """
    Financial data for a single period.

    All values should be in consistent units (typically in thousands or millions
    as reported in SEC filings). None indicates the metric was not available.
    """

    # Income Statement
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    net_income: Optional[float] = None

    # Balance Sheet
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    shares_outstanding: Optional[float] = None

    # Cash Flow Statement
    operating_cash_flow: Optional[float] = None

    # Metadata
    period_end: Optional[str] = None
    fiscal_year: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinancialPeriod":
        """Create a FinancialPeriod from a dictionary."""
        return cls(
            revenue=data.get("revenue"),
            gross_profit=data.get("gross_profit"),
            net_income=data.get("net_income"),
            total_assets=data.get("total_assets"),
            current_assets=data.get("current_assets"),
            current_liabilities=data.get("current_liabilities"),
            long_term_debt=data.get("long_term_debt"),
            shares_outstanding=data.get("shares_outstanding"),
            operating_cash_flow=data.get("operating_cash_flow"),
            period_end=data.get("period_end"),
            fiscal_year=data.get("fiscal_year"),
        )


@dataclass
class PiotroskiResult:
    """
    Detailed Piotroski F-Score result.

    Contains the overall score (0-9), individual signal results, and
    a human-readable interpretation.
    """

    score: int  # 0-9

    # Profitability signals (4 points)
    positive_roa: Optional[bool] = None  # Signal 1: ROA > 0
    positive_cfo: Optional[bool] = None  # Signal 2: Operating CF > 0
    roa_improving: Optional[bool] = None  # Signal 3: ROA increased
    accruals_quality: Optional[bool] = None  # Signal 4: CFO > Net Income

    # Leverage/Liquidity signals (3 points)
    leverage_decreasing: Optional[bool] = None  # Signal 5: LT Debt/Assets decreased
    current_ratio_improving: Optional[bool] = None  # Signal 6: Current ratio improved
    no_dilution: Optional[bool] = None  # Signal 7: Shares not increased

    # Operating efficiency signals (2 points)
    gross_margin_improving: Optional[bool] = None  # Signal 8: Gross margin improved
    asset_turnover_improving: Optional[bool] = None  # Signal 9: Asset turnover improved

    # Interpretation
    interpretation: str = ""

    # Metadata about calculation
    signals_available: int = 0  # How many signals could be calculated
    missing_signals: list[str] = field(default_factory=list)

    @property
    def max_score(self) -> int:
        """Maximum possible score (always 9 for Piotroski F-Score)."""
        return 9

    def __post_init__(self) -> None:
        """Set interpretation based on score."""
        if not self.interpretation:
            self.interpretation = self._get_interpretation()

    def _get_interpretation(self) -> str:
        """Get human-readable interpretation of the score."""
        if self.score >= 7:
            return "Strong - Financially healthy"
        elif self.score >= 4:
            return "Moderate - Mixed signals"
        else:
            return "Weak - Financial concerns"

    @property
    def profitability_score(self) -> int:
        """Sum of profitability signals (max 4)."""
        signals = [
            self.positive_roa,
            self.positive_cfo,
            self.roa_improving,
            self.accruals_quality,
        ]
        return sum(1 for s in signals if s is True)

    @property
    def leverage_score(self) -> int:
        """Sum of leverage/liquidity signals (max 3)."""
        signals = [
            self.leverage_decreasing,
            self.current_ratio_improving,
            self.no_dilution,
        ]
        return sum(1 for s in signals if s is True)

    @property
    def efficiency_score(self) -> int:
        """Sum of operating efficiency signals (max 2)."""
        signals = [
            self.gross_margin_improving,
            self.asset_turnover_improving,
        ]
        return sum(1 for s in signals if s is True)


class PiotroskiScorer:
    """
    Calculator for the Piotroski F-Score.

    Usage:
        scorer = PiotroskiScorer()

        # From FinancialPeriod objects
        result = scorer.calculate(current_period, prior_period)

        # From dictionaries (e.g., from EdgarClient)
        result = scorer.calculate_from_dict(current_dict, prior_dict)

        print(f"F-Score: {result.score}/9 - {result.interpretation}")
    """

    def calculate(
        self,
        current: FinancialPeriod,
        prior: FinancialPeriod,
        require_all_signals: bool = False,
    ) -> PiotroskiResult:
        """
        Calculate the Piotroski F-Score.

        Args:
            current: Financial data for the current period
            prior: Financial data for the prior period
            require_all_signals: If True, raise InsufficientDataError when
                                 any signal cannot be calculated

        Returns:
            PiotroskiResult with score, individual signals, and interpretation

        Raises:
            InsufficientDataError: If require_all_signals=True and data is missing
        """
        missing_signals: list[str] = []

        # Calculate each signal
        # Profitability (4 points)
        positive_roa = self._calc_positive_roa(current)
        if positive_roa is None:
            missing_signals.append("positive_roa")

        positive_cfo = self._calc_positive_cfo(current)
        if positive_cfo is None:
            missing_signals.append("positive_cfo")

        roa_improving = self._calc_roa_improving(current, prior)
        if roa_improving is None:
            missing_signals.append("roa_improving")

        accruals_quality = self._calc_accruals_quality(current)
        if accruals_quality is None:
            missing_signals.append("accruals_quality")

        # Leverage/Liquidity (3 points)
        leverage_decreasing = self._calc_leverage_decreasing(current, prior)
        if leverage_decreasing is None:
            missing_signals.append("leverage_decreasing")

        current_ratio_improving = self._calc_current_ratio_improving(current, prior)
        if current_ratio_improving is None:
            missing_signals.append("current_ratio_improving")

        no_dilution = self._calc_no_dilution(current, prior)
        if no_dilution is None:
            missing_signals.append("no_dilution")

        # Operating Efficiency (2 points)
        gross_margin_improving = self._calc_gross_margin_improving(current, prior)
        if gross_margin_improving is None:
            missing_signals.append("gross_margin_improving")

        asset_turnover_improving = self._calc_asset_turnover_improving(current, prior)
        if asset_turnover_improving is None:
            missing_signals.append("asset_turnover_improving")

        # Check if we have enough data
        if require_all_signals and missing_signals:
            raise InsufficientDataError(
                f"Cannot calculate all Piotroski signals. Missing: {missing_signals}",
                missing_fields=missing_signals,
            )

        # Calculate total score (True = 1, False/None = 0)
        all_signals = [
            positive_roa,
            positive_cfo,
            roa_improving,
            accruals_quality,
            leverage_decreasing,
            current_ratio_improving,
            no_dilution,
            gross_margin_improving,
            asset_turnover_improving,
        ]
        score = sum(1 for s in all_signals if s is True)
        signals_available = sum(1 for s in all_signals if s is not None)

        return PiotroskiResult(
            score=score,
            positive_roa=positive_roa,
            positive_cfo=positive_cfo,
            roa_improving=roa_improving,
            accruals_quality=accruals_quality,
            leverage_decreasing=leverage_decreasing,
            current_ratio_improving=current_ratio_improving,
            no_dilution=no_dilution,
            gross_margin_improving=gross_margin_improving,
            asset_turnover_improving=asset_turnover_improving,
            signals_available=signals_available,
            missing_signals=missing_signals,
        )

    def calculate_from_dict(
        self,
        current: dict[str, Any],
        prior: dict[str, Any],
        require_all_signals: bool = False,
    ) -> PiotroskiResult:
        """
        Calculate the Piotroski F-Score from dictionary data.

        Convenience method for use with EdgarClient output.

        Args:
            current: Dictionary with financial data for current period
            prior: Dictionary with financial data for prior period
            require_all_signals: If True, raise error when data is missing

        Returns:
            PiotroskiResult with score and signals
        """
        current_period = FinancialPeriod.from_dict(current)
        prior_period = FinancialPeriod.from_dict(prior)
        return self.calculate(current_period, prior_period, require_all_signals)

    # ========== PROFITABILITY SIGNALS (4 points) ==========

    def _calc_roa(self, period: FinancialPeriod) -> Optional[float]:
        """Calculate Return on Assets = Net Income / Total Assets."""
        if period.net_income is None or period.total_assets is None:
            return None
        if period.total_assets == 0:
            return None
        return period.net_income / period.total_assets

    def _calc_positive_roa(self, current: FinancialPeriod) -> Optional[bool]:
        """
        Signal 1: ROA > 0

        Positive return on assets indicates the company generated profit
        relative to its asset base.
        """
        roa = self._calc_roa(current)
        if roa is None:
            return None
        return roa > 0

    def _calc_positive_cfo(self, current: FinancialPeriod) -> Optional[bool]:
        """
        Signal 2: Operating Cash Flow > 0

        Positive operating cash flow indicates the company generates cash
        from its core operations (not just accounting profits).
        """
        if current.operating_cash_flow is None:
            return None
        return current.operating_cash_flow > 0

    def _calc_roa_improving(
        self, current: FinancialPeriod, prior: FinancialPeriod
    ) -> Optional[bool]:
        """
        Signal 3: ROA increased from prior period

        Improving ROA indicates the company is becoming more efficient
        at generating profits from its assets.
        """
        current_roa = self._calc_roa(current)
        prior_roa = self._calc_roa(prior)
        if current_roa is None or prior_roa is None:
            return None
        return current_roa > prior_roa

    def _calc_accruals_quality(self, current: FinancialPeriod) -> Optional[bool]:
        """
        Signal 4: Operating Cash Flow > Net Income (Accruals Quality)

        When cash flow exceeds accounting income, it suggests earnings
        are backed by real cash generation rather than accruals.
        This is a measure of earnings quality.

        Per Piotroski (2000): "Cash flow from operations scaled by beginning
        of year total assets exceeds ROA." Mathematically:
            CFO/TA > NI/TA  =>  CFO > NI (when TA > 0)

        This simplified form (CFO > NI) is equivalent to the paper's ratio
        comparison when Total Assets is positive, which is always true for
        operating companies.
        """
        if current.operating_cash_flow is None or current.net_income is None:
            return None
        return current.operating_cash_flow > current.net_income

    # ========== LEVERAGE/LIQUIDITY SIGNALS (3 points) ==========

    def _calc_leverage_ratio(self, period: FinancialPeriod) -> Optional[float]:
        """Calculate Long-term Debt to Total Assets ratio."""
        if period.long_term_debt is None or period.total_assets is None:
            return None
        if period.total_assets == 0:
            return None
        return period.long_term_debt / period.total_assets

    def _calc_leverage_decreasing(
        self, current: FinancialPeriod, prior: FinancialPeriod
    ) -> Optional[bool]:
        """
        Signal 5: Long-term Debt / Assets decreased

        Per Piotroski (2000): "The change in the ratio of total long-term debt
        to average total assets is negative." This tests for IMPROVEMENT in
        leverage position, not merely maintenance of a good position.

        Strictly interpreted: 0 -> 0 debt would be delta=0, which is NOT < 0,
        so it should fail. However, we award a point when a company maintains
        zero debt (0 -> 0) as this represents an already-optimal capital structure.

        Note: This is a practical deviation from strict academic interpretation.
        A company with no debt has no leverage risk to reduce.
        """
        current_leverage = self._calc_leverage_ratio(current)
        prior_leverage = self._calc_leverage_ratio(prior)

        # Special case: company paid off all debt (improvement)
        if current.long_term_debt == 0 and prior.long_term_debt is not None and prior.long_term_debt > 0:
            return True  # Paid off all debt - clear improvement

        # Special case: company maintained zero debt (optimal state)
        # Note: Strict academic interpretation would return False here (delta=0 is not < 0)
        # We choose to award the point since zero leverage is the best possible state
        if current.long_term_debt == 0 and prior.long_term_debt == 0:
            return True

        if current_leverage is None or prior_leverage is None:
            return None
        return current_leverage < prior_leverage

    def _calc_current_ratio(self, period: FinancialPeriod) -> Optional[float]:
        """Calculate Current Ratio = Current Assets / Current Liabilities."""
        if period.current_assets is None or period.current_liabilities is None:
            return None
        if period.current_liabilities == 0:
            # No current liabilities is technically infinite ratio (good)
            return float("inf") if period.current_assets else None
        return period.current_assets / period.current_liabilities

    def _calc_current_ratio_improving(
        self, current: FinancialPeriod, prior: FinancialPeriod
    ) -> Optional[bool]:
        """
        Signal 6: Current Ratio improved

        Improving current ratio indicates better short-term liquidity
        and ability to meet near-term obligations.
        """
        current_ratio = self._calc_current_ratio(current)
        prior_ratio = self._calc_current_ratio(prior)
        if current_ratio is None or prior_ratio is None:
            return None
        return current_ratio > prior_ratio

    def _calc_no_dilution(
        self, current: FinancialPeriod, prior: FinancialPeriod
    ) -> Optional[bool]:
        """
        Signal 7: No new share issuance (shares outstanding not increased)

        No dilution indicates management is not raising capital by issuing
        new shares, which would dilute existing shareholders.

        Per Piotroski (2000): "Firm did not issue common equity in the year
        preceding portfolio formation." This is a strict binary test - any
        increase in shares outstanding fails.

        Note: In practice, many companies have small share increases from
        stock-based compensation that don't represent meaningful dilution.
        A more lenient implementation might allow a small tolerance (e.g., 1%),
        but we follow the academic definition strictly here.
        """
        if current.shares_outstanding is None or prior.shares_outstanding is None:
            return None
        # Strict academic definition: shares must not increase at all
        return current.shares_outstanding <= prior.shares_outstanding

    # ========== OPERATING EFFICIENCY SIGNALS (2 points) ==========

    def _calc_gross_margin(self, period: FinancialPeriod) -> Optional[float]:
        """Calculate Gross Margin = Gross Profit / Revenue."""
        if period.gross_profit is None or period.revenue is None:
            return None
        if period.revenue == 0:
            return None
        return period.gross_profit / period.revenue

    def _calc_gross_margin_improving(
        self, current: FinancialPeriod, prior: FinancialPeriod
    ) -> Optional[bool]:
        """
        Signal 8: Gross Margin improved

        Improving gross margin indicates the company is either charging
        higher prices or reducing production costs.
        """
        current_margin = self._calc_gross_margin(current)
        prior_margin = self._calc_gross_margin(prior)
        if current_margin is None or prior_margin is None:
            return None
        return current_margin > prior_margin

    def _calc_asset_turnover(self, period: FinancialPeriod) -> Optional[float]:
        """Calculate Asset Turnover = Revenue / Total Assets."""
        if period.revenue is None or period.total_assets is None:
            return None
        if period.total_assets == 0:
            return None
        return period.revenue / period.total_assets

    def _calc_asset_turnover_improving(
        self, current: FinancialPeriod, prior: FinancialPeriod
    ) -> Optional[bool]:
        """
        Signal 9: Asset Turnover improved

        Improving asset turnover indicates the company is generating
        more revenue per dollar of assets (better asset utilization).
        """
        current_turnover = self._calc_asset_turnover(current)
        prior_turnover = self._calc_asset_turnover(prior)
        if current_turnover is None or prior_turnover is None:
            return None
        return current_turnover > prior_turnover
