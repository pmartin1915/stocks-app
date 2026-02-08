"""
Altman Z-Score Calculator.

The Altman Z-Score is a formula for predicting bankruptcy risk, developed by
Edward Altman in 1968. It combines five financial ratios using a weighted
formula to produce a single score indicating the probability of bankruptcy
within two years.

Formula (Original Manufacturing - 1968):
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

    Where:
    X1 = Working Capital / Total Assets (liquidity)
    X2 = Retained Earnings / Total Assets (cumulative profitability)
    X3 = EBIT / Total Assets (operating efficiency)
    X4 = Market Value of Equity / Total Liabilities (solvency/leverage)
    X5 = Sales / Total Assets (asset turnover)

Formula (Non-Manufacturing/Service - Altman Z''-Score):
    Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4

    Where X1-X3 are the same, but:
    X4 = Book Value of Equity / Total Liabilities (uses book value, not market)
    X5 is omitted (asset turnover varies too much across service industries)

Zone Interpretation (Manufacturing):
    > 2.99: Safe Zone - Low bankruptcy risk
    1.81 - 2.99: Grey Zone - Uncertain, requires monitoring
    < 1.81: Distress Zone - High bankruptcy risk

Zone Interpretation (Non-Manufacturing):
    > 2.60: Safe Zone - Low bankruptcy risk
    1.10 - 2.60: Grey Zone - Uncertain, requires monitoring
    < 1.10: Distress Zone - High bankruptcy risk

Reference: Altman, E. I. (1968). "Financial Ratios, Discriminant Analysis and
the Prediction of Corporate Bankruptcy." Journal of Finance, 23(4), 589-609.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from asymmetric.core.data.exceptions import InsufficientDataError
from asymmetric.core.scoring.constants import (
    ALTMAN_MFG_COEFFICIENTS,
    ALTMAN_NON_MFG_COEFFICIENTS,
    ZERO_LIABILITIES_EQUITY_CAP,
    ZSCORE_MFG_GREY_LOW,
    ZSCORE_MFG_SAFE,
    ZSCORE_NON_MFG_GREY_LOW,
    ZSCORE_NON_MFG_SAFE,
)

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
MANUFACTURING_SAFE = ZSCORE_MFG_SAFE
MANUFACTURING_GREY_LOW = ZSCORE_MFG_GREY_LOW
NON_MANUFACTURING_SAFE = ZSCORE_NON_MFG_SAFE
NON_MANUFACTURING_GREY_LOW = ZSCORE_NON_MFG_GREY_LOW
MANUFACTURING_COEFFICIENTS = ALTMAN_MFG_COEFFICIENTS
NON_MANUFACTURING_COEFFICIENTS = ALTMAN_NON_MFG_COEFFICIENTS


@dataclass
class AltmanInputs:
    """
    Financial inputs required for Altman Z-Score calculation.

    All values should be in consistent units (typically in thousands or millions
    as reported in SEC filings). None indicates the metric was not available.
    """

    # Balance Sheet
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_liabilities: Optional[float] = None
    retained_earnings: Optional[float] = None

    # Income Statement
    revenue: Optional[float] = None  # Sales
    ebit: Optional[float] = None  # Earnings Before Interest & Taxes

    # Market Data (for manufacturing formula)
    market_cap: Optional[float] = None  # Market Value of Equity

    # Book Value (for non-manufacturing formula, or fallback)
    book_equity: Optional[float] = None  # Stockholders' Equity

    # Company classification
    is_manufacturing: bool = True

    # Metadata
    period_end: Optional[str] = None
    fiscal_year: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], is_manufacturing: bool = True) -> "AltmanInputs":
        """
        Create AltmanInputs from a dictionary.

        Args:
            data: Dictionary with financial data. Supports various key names:
                - total_assets, assets
                - current_assets
                - current_liabilities
                - total_liabilities, liabilities
                - retained_earnings
                - revenue, revenues, sales
                - ebit, operating_income
                - market_cap, market_value_equity
                - book_equity, stockholders_equity, shareholders_equity
            is_manufacturing: Whether to use manufacturing formula

        Returns:
            AltmanInputs instance
        """
        return cls(
            total_assets=data.get("total_assets") or data.get("assets"),
            current_assets=data.get("current_assets"),
            current_liabilities=data.get("current_liabilities"),
            total_liabilities=data.get("total_liabilities") or data.get("liabilities"),
            retained_earnings=data.get("retained_earnings"),
            revenue=data.get("revenue") or data.get("revenues") or data.get("sales"),
            ebit=data.get("ebit") or data.get("operating_income"),
            market_cap=data.get("market_cap") or data.get("market_value_equity"),
            book_equity=(
                data.get("book_equity")
                or data.get("stockholders_equity")
                or data.get("shareholders_equity")
            ),
            is_manufacturing=is_manufacturing,
            period_end=data.get("period_end"),
            fiscal_year=data.get("fiscal_year"),
        )

    @property
    def working_capital(self) -> Optional[float]:
        """Calculate working capital = current assets - current liabilities."""
        if self.current_assets is not None and self.current_liabilities is not None:
            return self.current_assets - self.current_liabilities
        return None


@dataclass
class AltmanResult:
    """
    Detailed Altman Z-Score result.

    Contains the Z-Score, zone classification, individual components,
    and a human-readable interpretation.
    """

    z_score: float
    zone: str  # "Safe", "Grey", "Distress"
    interpretation: str

    # Formula used
    formula_used: str  # "manufacturing" or "non_manufacturing"

    # Individual components (ratios)
    x1_working_capital_ratio: Optional[float] = None  # Working Capital / Total Assets
    x2_retained_earnings_ratio: Optional[float] = None  # Retained Earnings / Total Assets
    x3_ebit_ratio: Optional[float] = None  # EBIT / Total Assets
    x4_equity_leverage_ratio: Optional[float] = None  # Equity / Total Liabilities
    x5_asset_turnover: Optional[float] = None  # Sales / Total Assets (manufacturing only)

    # Weighted contributions to Z-Score
    x1_contribution: Optional[float] = None
    x2_contribution: Optional[float] = None
    x3_contribution: Optional[float] = None
    x4_contribution: Optional[float] = None
    x5_contribution: Optional[float] = None

    # Metadata
    missing_inputs: list[str] = field(default_factory=list)
    components_calculated: int = 0

    @property
    def is_safe(self) -> bool:
        """Check if company is in the safe zone."""
        return self.zone == "Safe"

    @property
    def is_distressed(self) -> bool:
        """Check if company is in the distress zone."""
        return self.zone == "Distress"

    @property
    def is_grey(self) -> bool:
        """Check if company is in the grey (uncertain) zone."""
        return self.zone == "Grey"


class AltmanScorer:
    """
    Calculator for the Altman Z-Score bankruptcy prediction.

    Usage:
        scorer = AltmanScorer()

        # From AltmanInputs object
        inputs = AltmanInputs(
            total_assets=100_000_000,
            current_assets=40_000_000,
            current_liabilities=20_000_000,
            total_liabilities=30_000_000,
            retained_earnings=50_000_000,
            revenue=80_000_000,
            ebit=15_000_000,
            market_cap=200_000_000,
        )
        result = scorer.calculate(inputs)

        # From dictionary (e.g., from EdgarClient)
        result = scorer.calculate_from_dict(financial_data)

        print(f"Z-Score: {result.z_score:.2f} - {result.zone} - {result.interpretation}")
    """

    def calculate(
        self,
        inputs: AltmanInputs,
        require_all_components: bool = True,
    ) -> AltmanResult:
        """
        Calculate the Altman Z-Score.

        Args:
            inputs: Financial data for the period
            require_all_components: If True (default), raise InsufficientDataError
                                    when any component cannot be calculated. This
                                    prevents misleading partial scores.

        Returns:
            AltmanResult with Z-Score, zone, components, and interpretation

        Raises:
            InsufficientDataError: If require_all_components=True and data is missing
        """
        missing_inputs: list[str] = []
        components_calculated = 0

        is_manufacturing = inputs.is_manufacturing
        coefficients = (
            MANUFACTURING_COEFFICIENTS if is_manufacturing else NON_MANUFACTURING_COEFFICIENTS
        )

        # Calculate X1: Working Capital / Total Assets
        x1 = self._calc_working_capital_ratio(inputs)
        x1_contrib = None
        if x1 is not None:
            x1_contrib = coefficients["x1"] * x1
            components_calculated += 1
        else:
            missing_inputs.append("working_capital_ratio (current_assets, current_liabilities, total_assets)")

        # Calculate X2: Retained Earnings / Total Assets
        x2 = self._calc_retained_earnings_ratio(inputs)
        x2_contrib = None
        if x2 is not None:
            x2_contrib = coefficients["x2"] * x2
            components_calculated += 1
        else:
            missing_inputs.append("retained_earnings_ratio (retained_earnings, total_assets)")

        # Calculate X3: EBIT / Total Assets
        x3 = self._calc_ebit_ratio(inputs)
        x3_contrib = None
        if x3 is not None:
            x3_contrib = coefficients["x3"] * x3
            components_calculated += 1
        else:
            missing_inputs.append("ebit_ratio (ebit, total_assets)")

        # Calculate X4: Equity / Total Liabilities
        x4 = self._calc_equity_leverage_ratio(inputs)
        x4_contrib = None
        if x4 is not None:
            x4_contrib = coefficients["x4"] * x4
            components_calculated += 1
        else:
            if is_manufacturing:
                missing_inputs.append("equity_leverage_ratio (market_cap, total_liabilities)")
            else:
                missing_inputs.append("equity_leverage_ratio (book_equity, total_liabilities)")

        # Calculate X5: Sales / Total Assets (manufacturing only)
        x5 = None
        x5_contrib = None
        if is_manufacturing:
            x5 = self._calc_asset_turnover(inputs)
            if x5 is not None:
                x5_contrib = coefficients["x5"] * x5
                components_calculated += 1
            else:
                missing_inputs.append("asset_turnover (revenue, total_assets)")

        # Check if we have enough data
        required_components = 5 if is_manufacturing else 4
        if require_all_components and components_calculated < required_components:
            raise InsufficientDataError(
                f"Cannot calculate all Z-Score components. "
                f"Only {components_calculated}/{required_components} available.",
                missing_fields=missing_inputs,
            )

        # Calculate Z-Score from available contributions
        contributions = [c for c in [x1_contrib, x2_contrib, x3_contrib, x4_contrib, x5_contrib] if c is not None]

        if not contributions:
            # Can't calculate anything
            z_score = 0.0
            zone = "Distress"
            interpretation = "Insufficient data - Unable to calculate Z-Score"
            logger.warning("No Z-Score components could be calculated")
        else:
            z_score = sum(contributions)
            zone = self._determine_zone(z_score, is_manufacturing)
            interpretation = self._get_interpretation(zone)
            logger.info(
                f"Z-Score calculated: {z_score:.2f} ({zone}) using "
                f"{components_calculated}/{required_components} components"
            )

        return AltmanResult(
            z_score=z_score,
            zone=zone,
            interpretation=interpretation,
            formula_used="manufacturing" if is_manufacturing else "non_manufacturing",
            x1_working_capital_ratio=x1,
            x2_retained_earnings_ratio=x2,
            x3_ebit_ratio=x3,
            x4_equity_leverage_ratio=x4,
            x5_asset_turnover=x5,
            x1_contribution=x1_contrib,
            x2_contribution=x2_contrib,
            x3_contribution=x3_contrib,
            x4_contribution=x4_contrib,
            x5_contribution=x5_contrib,
            missing_inputs=missing_inputs,
            components_calculated=components_calculated,
        )

    def calculate_from_dict(
        self,
        data: dict[str, Any],
        is_manufacturing: bool = True,
        require_all_components: bool = True,
    ) -> AltmanResult:
        """
        Calculate Z-Score from a dictionary of financial data.

        Convenience method that creates AltmanInputs from a dict.

        Args:
            data: Dictionary with financial data
            is_manufacturing: Whether to use manufacturing formula
            require_all_components: If True (default), raise InsufficientDataError
                                    when data is missing. Prevents misleading scores.

        Returns:
            AltmanResult with Z-Score and analysis

        Raises:
            InsufficientDataError: If require_all_components=True and data is missing
        """
        inputs = AltmanInputs.from_dict(data, is_manufacturing=is_manufacturing)
        return self.calculate(inputs, require_all_components=require_all_components)

    def _calc_working_capital_ratio(self, inputs: AltmanInputs) -> Optional[float]:
        """
        Calculate X1: Working Capital / Total Assets.

        Measures short-term liquidity relative to firm size.
        Working Capital = Current Assets - Current Liabilities
        """
        working_capital = inputs.working_capital
        total_assets = inputs.total_assets

        if working_capital is None or total_assets is None:
            return None

        if total_assets == 0:
            logger.warning("Total assets is zero, cannot calculate working capital ratio")
            return None

        return working_capital / total_assets

    def _calc_retained_earnings_ratio(self, inputs: AltmanInputs) -> Optional[float]:
        """
        Calculate X2: Retained Earnings / Total Assets.

        Measures cumulative profitability. Younger firms typically have lower
        retained earnings, so this ratio penalizes newer companies.
        """
        if inputs.retained_earnings is None or inputs.total_assets is None:
            return None

        if inputs.total_assets == 0:
            logger.warning("Total assets is zero, cannot calculate retained earnings ratio")
            return None

        return inputs.retained_earnings / inputs.total_assets

    def _calc_ebit_ratio(self, inputs: AltmanInputs) -> Optional[float]:
        """
        Calculate X3: EBIT / Total Assets.

        Measures operating efficiency. This is the most significant predictor
        in the model due to its high coefficient (3.3 for manufacturing).
        """
        if inputs.ebit is None or inputs.total_assets is None:
            return None

        if inputs.total_assets == 0:
            logger.warning("Total assets is zero, cannot calculate EBIT ratio")
            return None

        return inputs.ebit / inputs.total_assets

    def _calc_equity_leverage_ratio(self, inputs: AltmanInputs) -> Optional[float]:
        """
        Calculate X4: Equity / Total Liabilities.

        For manufacturing: Market Value of Equity / Total Liabilities
        For non-manufacturing: Book Value of Equity / Total Liabilities

        Measures how much the firm's assets can decline before liabilities
        exceed assets (insolvency threshold).

        Practical Deviations from Academic Model:

        1. Zero Liabilities Cap: When total_liabilities = 0, this method returns
           10.0 instead of causing a division by zero. This caps the X4
           contribution at 6.0 (0.6 * 10.0) for manufacturing or 10.5 (1.05 * 10.0)
           for non-manufacturing. Zero liabilities indicates an extremely strong
           equity position. The original Altman (1968) paper does not address
           this edge case as the study sample excluded such firms.

        2. Market Cap Fallback (Manufacturing Only): If market_cap is unavailable,
           the method falls back to book_equity for the manufacturing formula.
           This may produce lower Z-Scores since market cap typically exceeds
           book equity for healthy firms. The fallback is logged as a warning.
           For strict academic accuracy, market_cap should always be provided
           when using the manufacturing formula.
        """
        if inputs.total_liabilities is None or inputs.total_liabilities == 0:
            if inputs.total_liabilities == 0:
                # No liabilities is actually a good sign - return high ratio
                # DEVIATION: Capped to prevent infinite/undefined values
                logger.info(f"Total liabilities is zero, using maximum equity ratio of {ZERO_LIABILITIES_EQUITY_CAP}")
                return ZERO_LIABILITIES_EQUITY_CAP
            return None

        # Use market cap for manufacturing, book equity for non-manufacturing
        if inputs.is_manufacturing:
            equity = inputs.market_cap
            # Fall back to book equity if market cap not available
            if equity is None:
                equity = inputs.book_equity
                if equity is not None:
                    logger.info("Market cap not available, using book equity for X4")
        else:
            equity = inputs.book_equity

        if equity is None:
            return None

        return equity / inputs.total_liabilities

    def _calc_asset_turnover(self, inputs: AltmanInputs) -> Optional[float]:
        """
        Calculate X5: Sales / Total Assets.

        Measures asset utilization efficiency. Only used in manufacturing formula
        because service industries have highly variable asset turnover.
        """
        if inputs.revenue is None or inputs.total_assets is None:
            return None

        if inputs.total_assets == 0:
            logger.warning("Total assets is zero, cannot calculate asset turnover")
            return None

        return inputs.revenue / inputs.total_assets

    def _determine_zone(self, z_score: float, is_manufacturing: bool) -> str:
        """
        Determine the bankruptcy risk zone based on Z-Score.

        Args:
            z_score: Calculated Z-Score
            is_manufacturing: Whether manufacturing thresholds apply

        Returns:
            "Safe", "Grey", or "Distress"
        """
        if is_manufacturing:
            if z_score > MANUFACTURING_SAFE:
                return "Safe"
            elif z_score >= MANUFACTURING_GREY_LOW:
                return "Grey"
            else:
                return "Distress"
        else:
            if z_score > NON_MANUFACTURING_SAFE:
                return "Safe"
            elif z_score >= NON_MANUFACTURING_GREY_LOW:
                return "Grey"
            else:
                return "Distress"

    def _get_interpretation(self, zone: str) -> str:
        """
        Get human-readable interpretation of the zone.

        Args:
            zone: "Safe", "Grey", or "Distress"

        Returns:
            Interpretation string
        """
        interpretations = {
            "Safe": "Low bankruptcy risk - Financially stable",
            "Grey": "Uncertain - Requires monitoring",
            "Distress": "High bankruptcy risk - Financial concerns",
        }
        return interpretations.get(zone, "Unknown")
