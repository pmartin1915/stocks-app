"""
Tests for the Altman Z-Score Calculator.

Tests cover:
- AltmanInputs dataclass creation and from_dict
- AltmanResult properties and zone classification
- AltmanScorer calculations for all 5 components
- Manufacturing vs non-manufacturing formulas
- Zone boundaries (Safe, Grey, Distress)
- Edge cases (zero denominators, missing data, negative values)
"""

import pytest

from asymmetric.core.scoring.altman import (
    AltmanInputs,
    AltmanResult,
    AltmanScorer,
    MANUFACTURING_SAFE,
    MANUFACTURING_GREY_LOW,
    NON_MANUFACTURING_SAFE,
    NON_MANUFACTURING_GREY_LOW,
)
from asymmetric.core.data.exceptions import InsufficientDataError


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def safe_manufacturing_company():
    """
    Company data that should result in Safe zone (Z > 2.99).

    Calculated expected Z-Score:
    X1 = (40M - 20M) / 100M = 0.20, contrib = 1.2 * 0.20 = 0.24
    X2 = 50M / 100M = 0.50, contrib = 1.4 * 0.50 = 0.70
    X3 = 15M / 100M = 0.15, contrib = 3.3 * 0.15 = 0.495
    X4 = 200M / 30M = 6.67, contrib = 0.6 * 6.67 = 4.00
    X5 = 80M / 100M = 0.80, contrib = 1.0 * 0.80 = 0.80
    Z = 0.24 + 0.70 + 0.495 + 4.00 + 0.80 = 6.235
    """
    return {
        "total_assets": 100_000_000,
        "current_assets": 40_000_000,
        "current_liabilities": 20_000_000,
        "total_liabilities": 30_000_000,
        "retained_earnings": 50_000_000,
        "revenue": 80_000_000,
        "ebit": 15_000_000,
        "market_cap": 200_000_000,
    }


@pytest.fixture
def grey_zone_company():
    """
    Company data that should result in Grey zone (1.81 <= Z <= 2.99).

    Calculated expected Z-Score:
    X1 = (30M - 25M) / 100M = 0.05, contrib = 1.2 * 0.05 = 0.06
    X2 = 20M / 100M = 0.20, contrib = 1.4 * 0.20 = 0.28
    X3 = 8M / 100M = 0.08, contrib = 3.3 * 0.08 = 0.264
    X4 = 80M / 50M = 1.60, contrib = 0.6 * 1.60 = 0.96
    X5 = 60M / 100M = 0.60, contrib = 1.0 * 0.60 = 0.60
    Z = 0.06 + 0.28 + 0.264 + 0.96 + 0.60 = 2.164
    """
    return {
        "total_assets": 100_000_000,
        "current_assets": 30_000_000,
        "current_liabilities": 25_000_000,
        "total_liabilities": 50_000_000,
        "retained_earnings": 20_000_000,
        "revenue": 60_000_000,
        "ebit": 8_000_000,
        "market_cap": 80_000_000,
    }


@pytest.fixture
def distress_company():
    """
    Company data that should result in Distress zone (Z < 1.81).

    Calculated expected Z-Score:
    X1 = (15M - 40M) / 100M = -0.25, contrib = 1.2 * -0.25 = -0.30
    X2 = -20M / 100M = -0.20, contrib = 1.4 * -0.20 = -0.28
    X3 = -5M / 100M = -0.05, contrib = 3.3 * -0.05 = -0.165
    X4 = 20M / 90M = 0.22, contrib = 0.6 * 0.22 = 0.133
    X5 = 50M / 100M = 0.50, contrib = 1.0 * 0.50 = 0.50
    Z = -0.30 - 0.28 - 0.165 + 0.133 + 0.50 = -0.112
    """
    return {
        "total_assets": 100_000_000,
        "current_assets": 15_000_000,
        "current_liabilities": 40_000_000,
        "total_liabilities": 90_000_000,
        "retained_earnings": -20_000_000,  # Accumulated deficit
        "revenue": 50_000_000,
        "ebit": -5_000_000,  # Operating loss
        "market_cap": 20_000_000,
    }


@pytest.fixture
def non_manufacturing_company():
    """
    Service company data using non-manufacturing formula.

    Calculated expected Z''-Score:
    X1 = (35M - 15M) / 80M = 0.25, contrib = 6.56 * 0.25 = 1.64
    X2 = 30M / 80M = 0.375, contrib = 3.26 * 0.375 = 1.2225
    X3 = 10M / 80M = 0.125, contrib = 6.72 * 0.125 = 0.84
    X4 = 40M / 40M = 1.00, contrib = 1.05 * 1.00 = 1.05
    Z'' = 1.64 + 1.2225 + 0.84 + 1.05 = 4.7525
    """
    return {
        "total_assets": 80_000_000,
        "current_assets": 35_000_000,
        "current_liabilities": 15_000_000,
        "total_liabilities": 40_000_000,
        "retained_earnings": 30_000_000,
        "revenue": 60_000_000,  # Not used in non-manufacturing
        "ebit": 10_000_000,
        "book_equity": 40_000_000,  # Uses book value, not market cap
    }


# ============================================================================
# AltmanInputs Tests
# ============================================================================


class TestAltmanInputs:
    """Tests for AltmanInputs dataclass."""

    def test_create_with_all_fields(self):
        """Test creating inputs with all fields populated."""
        inputs = AltmanInputs(
            total_assets=100_000,
            current_assets=40_000,
            current_liabilities=20_000,
            total_liabilities=30_000,
            retained_earnings=50_000,
            revenue=80_000,
            ebit=15_000,
            market_cap=200_000,
            book_equity=70_000,
            is_manufacturing=True,
        )

        assert inputs.total_assets == 100_000
        assert inputs.current_assets == 40_000
        assert inputs.is_manufacturing is True

    def test_create_with_defaults(self):
        """Test creating inputs with default values."""
        inputs = AltmanInputs()

        assert inputs.total_assets is None
        assert inputs.is_manufacturing is True  # Default

    def test_working_capital_property(self):
        """Test working capital calculation."""
        inputs = AltmanInputs(
            current_assets=40_000,
            current_liabilities=20_000,
        )

        assert inputs.working_capital == 20_000

    def test_working_capital_negative(self):
        """Test negative working capital (more liabilities than assets)."""
        inputs = AltmanInputs(
            current_assets=15_000,
            current_liabilities=40_000,
        )

        assert inputs.working_capital == -25_000

    def test_working_capital_missing_data(self):
        """Test working capital when data is missing."""
        inputs = AltmanInputs(current_assets=40_000)

        assert inputs.working_capital is None

    def test_from_dict_standard_keys(self):
        """Test creating from dict with standard key names."""
        data = {
            "total_assets": 100_000,
            "current_assets": 40_000,
            "current_liabilities": 20_000,
            "total_liabilities": 30_000,
            "retained_earnings": 50_000,
            "revenue": 80_000,
            "ebit": 15_000,
            "market_cap": 200_000,
        }

        inputs = AltmanInputs.from_dict(data)

        assert inputs.total_assets == 100_000
        assert inputs.revenue == 80_000
        assert inputs.is_manufacturing is True

    def test_from_dict_alternate_keys(self):
        """Test creating from dict with alternate key names."""
        data = {
            "assets": 100_000,
            "liabilities": 30_000,
            "revenues": 80_000,
            "sales": 90_000,  # Should be overridden by revenues
            "operating_income": 15_000,
            "stockholders_equity": 70_000,
        }

        inputs = AltmanInputs.from_dict(data)

        assert inputs.total_assets == 100_000
        assert inputs.total_liabilities == 30_000
        assert inputs.revenue == 80_000  # Uses 'revenues' first
        assert inputs.ebit == 15_000
        assert inputs.book_equity == 70_000

    def test_from_dict_non_manufacturing(self):
        """Test creating non-manufacturing inputs."""
        data = {"total_assets": 100_000}

        inputs = AltmanInputs.from_dict(data, is_manufacturing=False)

        assert inputs.is_manufacturing is False


# ============================================================================
# AltmanResult Tests
# ============================================================================


class TestAltmanResult:
    """Tests for AltmanResult dataclass."""

    def test_safe_zone_properties(self):
        """Test properties for safe zone result."""
        result = AltmanResult(
            z_score=5.0,
            zone="Safe",
            interpretation="Low bankruptcy risk",
            formula_used="manufacturing",
        )

        assert result.is_safe is True
        assert result.is_distressed is False
        assert result.is_grey is False

    def test_grey_zone_properties(self):
        """Test properties for grey zone result."""
        result = AltmanResult(
            z_score=2.5,
            zone="Grey",
            interpretation="Uncertain",
            formula_used="manufacturing",
        )

        assert result.is_safe is False
        assert result.is_distressed is False
        assert result.is_grey is True

    def test_distress_zone_properties(self):
        """Test properties for distress zone result."""
        result = AltmanResult(
            z_score=0.5,
            zone="Distress",
            interpretation="High bankruptcy risk",
            formula_used="manufacturing",
        )

        assert result.is_safe is False
        assert result.is_distressed is True
        assert result.is_grey is False


# ============================================================================
# AltmanScorer Component Tests
# ============================================================================


class TestAltmanScorerComponents:
    """Tests for individual Z-Score component calculations."""

    @pytest.fixture
    def scorer(self):
        return AltmanScorer()

    def test_working_capital_ratio_positive(self, scorer):
        """Test X1 with positive working capital."""
        inputs = AltmanInputs(
            current_assets=40_000,
            current_liabilities=20_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_working_capital_ratio(inputs)

        # (40000 - 20000) / 100000 = 0.20
        assert ratio == pytest.approx(0.20)

    def test_working_capital_ratio_negative(self, scorer):
        """Test X1 with negative working capital."""
        inputs = AltmanInputs(
            current_assets=15_000,
            current_liabilities=40_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_working_capital_ratio(inputs)

        # (15000 - 40000) / 100000 = -0.25
        assert ratio == pytest.approx(-0.25)

    def test_working_capital_ratio_missing_data(self, scorer):
        """Test X1 when data is missing."""
        inputs = AltmanInputs(current_assets=40_000)

        ratio = scorer._calc_working_capital_ratio(inputs)

        assert ratio is None

    def test_working_capital_ratio_zero_assets(self, scorer):
        """Test X1 when total assets is zero."""
        inputs = AltmanInputs(
            current_assets=40_000,
            current_liabilities=20_000,
            total_assets=0,
        )

        ratio = scorer._calc_working_capital_ratio(inputs)

        assert ratio is None

    def test_retained_earnings_ratio(self, scorer):
        """Test X2 calculation."""
        inputs = AltmanInputs(
            retained_earnings=50_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_retained_earnings_ratio(inputs)

        # 50000 / 100000 = 0.50
        assert ratio == pytest.approx(0.50)

    def test_retained_earnings_ratio_negative(self, scorer):
        """Test X2 with accumulated deficit."""
        inputs = AltmanInputs(
            retained_earnings=-20_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_retained_earnings_ratio(inputs)

        # -20000 / 100000 = -0.20
        assert ratio == pytest.approx(-0.20)

    def test_ebit_ratio(self, scorer):
        """Test X3 calculation."""
        inputs = AltmanInputs(
            ebit=15_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_ebit_ratio(inputs)

        # 15000 / 100000 = 0.15
        assert ratio == pytest.approx(0.15)

    def test_ebit_ratio_operating_loss(self, scorer):
        """Test X3 with operating loss."""
        inputs = AltmanInputs(
            ebit=-5_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_ebit_ratio(inputs)

        # -5000 / 100000 = -0.05
        assert ratio == pytest.approx(-0.05)

    def test_equity_leverage_ratio_manufacturing(self, scorer):
        """Test X4 with market cap (manufacturing)."""
        inputs = AltmanInputs(
            market_cap=200_000,
            total_liabilities=30_000,
            is_manufacturing=True,
        )

        ratio = scorer._calc_equity_leverage_ratio(inputs)

        # 200000 / 30000 = 6.67
        assert ratio == pytest.approx(6.67, rel=0.01)

    def test_equity_leverage_ratio_manufacturing_fallback_to_book(self, scorer):
        """Test X4 falls back to book equity when market cap missing."""
        inputs = AltmanInputs(
            book_equity=70_000,
            total_liabilities=30_000,
            is_manufacturing=True,
        )

        ratio = scorer._calc_equity_leverage_ratio(inputs)

        # 70000 / 30000 = 2.33
        assert ratio == pytest.approx(2.33, rel=0.01)

    def test_equity_leverage_ratio_non_manufacturing(self, scorer):
        """Test X4 with book equity (non-manufacturing)."""
        inputs = AltmanInputs(
            book_equity=40_000,
            market_cap=100_000,  # Should be ignored
            total_liabilities=40_000,
            is_manufacturing=False,
        )

        ratio = scorer._calc_equity_leverage_ratio(inputs)

        # 40000 / 40000 = 1.00
        assert ratio == pytest.approx(1.00)

    def test_equity_leverage_ratio_zero_liabilities(self, scorer):
        """Test X4 when no liabilities (good sign)."""
        inputs = AltmanInputs(
            market_cap=200_000,
            total_liabilities=0,
            is_manufacturing=True,
        )

        ratio = scorer._calc_equity_leverage_ratio(inputs)

        # Zero liabilities returns capped high value
        assert ratio == 10.0

    def test_asset_turnover(self, scorer):
        """Test X5 calculation."""
        inputs = AltmanInputs(
            revenue=80_000,
            total_assets=100_000,
        )

        ratio = scorer._calc_asset_turnover(inputs)

        # 80000 / 100000 = 0.80
        assert ratio == pytest.approx(0.80)


# ============================================================================
# AltmanScorer Full Calculation Tests
# ============================================================================


class TestAltmanScorerCalculation:
    """Tests for full Z-Score calculation."""

    @pytest.fixture
    def scorer(self):
        return AltmanScorer()

    def test_safe_zone_manufacturing(self, scorer, safe_manufacturing_company):
        """Test calculation resulting in safe zone."""
        result = scorer.calculate_from_dict(safe_manufacturing_company)

        # Z should be approximately 6.235 based on fixture calculations
        assert result.z_score > MANUFACTURING_SAFE
        assert result.zone == "Safe"
        assert result.is_safe is True
        assert result.formula_used == "manufacturing"
        assert result.components_calculated == 5

    def test_grey_zone_manufacturing(self, scorer, grey_zone_company):
        """Test calculation resulting in grey zone."""
        result = scorer.calculate_from_dict(grey_zone_company)

        # Z should be approximately 2.164
        assert MANUFACTURING_GREY_LOW <= result.z_score <= MANUFACTURING_SAFE
        assert result.zone == "Grey"
        assert result.is_grey is True

    def test_distress_zone_manufacturing(self, scorer, distress_company):
        """Test calculation resulting in distress zone."""
        result = scorer.calculate_from_dict(distress_company)

        # Z should be approximately -0.112
        assert result.z_score < MANUFACTURING_GREY_LOW
        assert result.zone == "Distress"
        assert result.is_distressed is True

    def test_non_manufacturing_formula(self, scorer, non_manufacturing_company):
        """Test non-manufacturing formula (4 components, no X5)."""
        result = scorer.calculate_from_dict(
            non_manufacturing_company, is_manufacturing=False
        )

        # Z'' should be approximately 4.7525
        assert result.z_score > NON_MANUFACTURING_SAFE
        assert result.zone == "Safe"
        assert result.formula_used == "non_manufacturing"
        assert result.components_calculated == 4
        assert result.x5_asset_turnover is None  # Not used

    def test_component_contributions(self, scorer, safe_manufacturing_company):
        """Test individual component contributions are calculated."""
        result = scorer.calculate_from_dict(safe_manufacturing_company)

        # All contributions should be present
        assert result.x1_contribution is not None
        assert result.x2_contribution is not None
        assert result.x3_contribution is not None
        assert result.x4_contribution is not None
        assert result.x5_contribution is not None

        # Sum of contributions should equal Z-Score
        total = (
            result.x1_contribution
            + result.x2_contribution
            + result.x3_contribution
            + result.x4_contribution
            + result.x5_contribution
        )
        assert total == pytest.approx(result.z_score, rel=0.001)

    def test_partial_data(self, scorer):
        """Test calculation with partial data when explicitly allowed."""
        data = {
            "total_assets": 100_000,
            "current_assets": 40_000,
            "current_liabilities": 20_000,
            # Missing: total_liabilities, retained_earnings, revenue, ebit, market_cap
        }

        # Must explicitly set require_all_components=False (default changed to True)
        result = scorer.calculate_from_dict(data, require_all_components=False)

        # Should calculate with available data
        assert result.components_calculated == 1  # Only X1
        assert result.x1_working_capital_ratio is not None
        assert result.x2_retained_earnings_ratio is None
        assert len(result.missing_inputs) > 0
        assert result.is_approximate is True

    def test_require_all_components_raises(self, scorer):
        """Test that require_all_components raises on missing data."""
        data = {
            "total_assets": 100_000,
            "current_assets": 40_000,
            "current_liabilities": 20_000,
        }

        with pytest.raises(InsufficientDataError) as exc_info:
            scorer.calculate_from_dict(data, require_all_components=True)

        assert "Cannot calculate all Z-Score components" in str(exc_info.value)

    def test_no_data_returns_distress(self, scorer):
        """Test that no data returns distress zone when partial allowed."""
        data = {}

        # Must explicitly allow partial components (default changed to True)
        result = scorer.calculate_from_dict(data, require_all_components=False)

        assert result.z_score == 0.0
        assert result.zone == "Distress"
        assert result.components_calculated == 0

    def test_from_altman_inputs(self, scorer):
        """Test calculation from AltmanInputs object directly."""
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

        assert result.zone == "Safe"
        assert result.components_calculated == 5


# ============================================================================
# Zone Boundary Tests
# ============================================================================


class TestZoneBoundaries:
    """Tests for exact zone boundary classification."""

    @pytest.fixture
    def scorer(self):
        return AltmanScorer()

    def test_manufacturing_safe_boundary(self, scorer):
        """Test manufacturing safe zone boundary (Z > 2.99)."""
        zone = scorer._determine_zone(3.00, is_manufacturing=True)
        assert zone == "Safe"

        zone = scorer._determine_zone(2.99, is_manufacturing=True)
        assert zone == "Grey"  # Exactly at boundary is Grey

    def test_manufacturing_grey_boundaries(self, scorer):
        """Test manufacturing grey zone boundaries (1.81 <= Z <= 2.99)."""
        zone = scorer._determine_zone(2.99, is_manufacturing=True)
        assert zone == "Grey"

        zone = scorer._determine_zone(1.81, is_manufacturing=True)
        assert zone == "Grey"

        zone = scorer._determine_zone(1.80, is_manufacturing=True)
        assert zone == "Distress"

    def test_manufacturing_distress_boundary(self, scorer):
        """Test manufacturing distress zone boundary (Z < 1.81)."""
        zone = scorer._determine_zone(1.80, is_manufacturing=True)
        assert zone == "Distress"

        zone = scorer._determine_zone(0.0, is_manufacturing=True)
        assert zone == "Distress"

        zone = scorer._determine_zone(-1.0, is_manufacturing=True)
        assert zone == "Distress"

    def test_non_manufacturing_safe_boundary(self, scorer):
        """Test non-manufacturing safe zone boundary (Z'' > 2.60)."""
        zone = scorer._determine_zone(2.61, is_manufacturing=False)
        assert zone == "Safe"

        zone = scorer._determine_zone(2.60, is_manufacturing=False)
        assert zone == "Grey"

    def test_non_manufacturing_grey_boundaries(self, scorer):
        """Test non-manufacturing grey zone boundaries (1.10 <= Z'' <= 2.60)."""
        zone = scorer._determine_zone(2.60, is_manufacturing=False)
        assert zone == "Grey"

        zone = scorer._determine_zone(1.10, is_manufacturing=False)
        assert zone == "Grey"

        zone = scorer._determine_zone(1.09, is_manufacturing=False)
        assert zone == "Distress"

    def test_non_manufacturing_distress_boundary(self, scorer):
        """Test non-manufacturing distress zone boundary (Z'' < 1.10)."""
        zone = scorer._determine_zone(1.09, is_manufacturing=False)
        assert zone == "Distress"


# ============================================================================
# Interpretation Tests
# ============================================================================


class TestInterpretation:
    """Tests for human-readable interpretations."""

    @pytest.fixture
    def scorer(self):
        return AltmanScorer()

    def test_safe_interpretation(self, scorer):
        """Test safe zone interpretation."""
        interpretation = scorer._get_interpretation("Safe")
        assert "Low bankruptcy risk" in interpretation

    def test_grey_interpretation(self, scorer):
        """Test grey zone interpretation."""
        interpretation = scorer._get_interpretation("Grey")
        assert "Uncertain" in interpretation or "monitoring" in interpretation.lower()

    def test_distress_interpretation(self, scorer):
        """Test distress zone interpretation."""
        interpretation = scorer._get_interpretation("Distress")
        assert "High bankruptcy risk" in interpretation

    def test_unknown_zone_interpretation(self, scorer):
        """Test unknown zone returns 'Unknown'."""
        interpretation = scorer._get_interpretation("InvalidZone")
        assert interpretation == "Unknown"


# ============================================================================
# Academic Validation Tests
# ============================================================================


class TestAcademicValidation:
    """
    Tests validating implementation against Altman (1968) academic paper.

    Reference: Altman, E. I. (1968). "Financial Ratios, Discriminant Analysis
    and the Prediction of Corporate Bankruptcy." Journal of Finance, 23(4), 589-609.
    """

    def test_manufacturing_coefficients_match_altman_1968(self):
        """
        Verify manufacturing coefficients match Altman (1968) paper.

        Original paper coefficients:
        - X1 (Working Capital/Total Assets): 1.2
        - X2 (Retained Earnings/Total Assets): 1.4
        - X3 (EBIT/Total Assets): 3.3
        - X4 (Market Value Equity/Total Liabilities): 0.6
        - X5 (Sales/Total Assets): 0.999 (implementation uses 1.0, universally accepted)
        """
        from asymmetric.core.scoring.altman import MANUFACTURING_COEFFICIENTS

        assert MANUFACTURING_COEFFICIENTS["x1"] == 1.2
        assert MANUFACTURING_COEFFICIENTS["x2"] == 1.4
        assert MANUFACTURING_COEFFICIENTS["x3"] == 3.3
        assert MANUFACTURING_COEFFICIENTS["x4"] == 0.6
        # Paper uses 0.999, but 1.0 is universally accepted as equivalent
        assert MANUFACTURING_COEFFICIENTS["x5"] == 1.0

    def test_non_manufacturing_coefficients_match_altman_revision(self):
        """
        Verify non-manufacturing coefficients match Altman Z''-Score revision.

        The Z''-Score (1995) is designed for non-manufacturing and emerging
        market companies, eliminating the Sales/Total Assets ratio which
        varies too much across service industries.
        """
        from asymmetric.core.scoring.altman import NON_MANUFACTURING_COEFFICIENTS

        assert NON_MANUFACTURING_COEFFICIENTS["x1"] == 6.56
        assert NON_MANUFACTURING_COEFFICIENTS["x2"] == 3.26
        assert NON_MANUFACTURING_COEFFICIENTS["x3"] == 6.72
        assert NON_MANUFACTURING_COEFFICIENTS["x4"] == 1.05
        # X5 is intentionally omitted in non-manufacturing formula
        assert "x5" not in NON_MANUFACTURING_COEFFICIENTS

    def test_zone_boundaries_match_altman_1968(self):
        """
        Verify zone boundaries match published thresholds.

        Manufacturing (1968):
        - Safe Zone: Z > 2.99
        - Grey Zone: 1.81 <= Z <= 2.99
        - Distress Zone: Z < 1.81

        Non-Manufacturing (Z''-Score):
        - Safe Zone: Z'' > 2.60
        - Grey Zone: 1.10 <= Z'' <= 2.60
        - Distress Zone: Z'' < 1.10
        """
        from asymmetric.core.scoring.altman import (
            MANUFACTURING_SAFE,
            MANUFACTURING_GREY_LOW,
            NON_MANUFACTURING_SAFE,
            NON_MANUFACTURING_GREY_LOW,
        )

        # Manufacturing boundaries
        assert MANUFACTURING_SAFE == 2.99
        assert MANUFACTURING_GREY_LOW == 1.81

        # Non-manufacturing boundaries
        assert NON_MANUFACTURING_SAFE == 2.60
        assert NON_MANUFACTURING_GREY_LOW == 1.10


class TestPracticalDeviations:
    """
    Tests for documented practical deviations from strict academic model.

    These deviations are necessary for real-world application but differ
    from the original paper's assumptions.
    """

    @pytest.fixture
    def scorer(self):
        return AltmanScorer()

    def test_zero_liabilities_caps_x4_at_10(self, scorer):
        """
        Verify X4 is capped at 10.0 when total liabilities = 0.

        This is a practical deviation from the academic model:
        - Original paper does not address zero liabilities (division by zero)
        - Cap of 10.0 limits X4 contribution to 6.0 (manufacturing) or 10.5 (non-mfg)
        - Zero liabilities indicates extremely strong financial position
        """
        inputs = AltmanInputs(
            total_assets=100_000_000,
            current_assets=50_000_000,
            current_liabilities=10_000_000,
            total_liabilities=0,  # Zero liabilities - edge case
            retained_earnings=60_000_000,
            revenue=80_000_000,
            ebit=20_000_000,
            market_cap=200_000_000,
        )

        x4 = scorer._calc_equity_leverage_ratio(inputs)

        # Should be capped at 10.0, not infinity
        assert x4 == 10.0

        # Verify contribution is bounded
        manufacturing_contribution = 0.6 * x4
        assert manufacturing_contribution == 6.0

    def test_manufacturing_falls_back_to_book_equity(self, scorer):
        """
        Verify manufacturing formula uses book equity when market cap unavailable.

        This is a practical deviation:
        - Original 1968 model requires market value of equity
        - When market_cap is None, implementation falls back to book_equity
        - May produce lower scores since market cap typically > book equity
        """
        inputs = AltmanInputs(
            total_assets=100_000_000,
            current_assets=40_000_000,
            current_liabilities=20_000_000,
            total_liabilities=30_000_000,
            retained_earnings=50_000_000,
            revenue=80_000_000,
            ebit=15_000_000,
            market_cap=None,  # Missing market cap
            book_equity=70_000_000,  # Fallback value
            is_manufacturing=True,
        )

        x4 = scorer._calc_equity_leverage_ratio(inputs)

        # Should use book_equity / total_liabilities
        expected = 70_000_000 / 30_000_000
        assert x4 == pytest.approx(expected)

    def test_non_manufacturing_uses_book_equity_by_design(self, scorer):
        """
        Verify non-manufacturing formula uses book equity as designed.

        Unlike the market cap fallback for manufacturing, non-manufacturing
        (Z''-Score) is designed to use book value of equity.
        """
        inputs = AltmanInputs(
            total_assets=80_000_000,
            current_assets=35_000_000,
            current_liabilities=15_000_000,
            total_liabilities=40_000_000,
            retained_earnings=30_000_000,
            revenue=60_000_000,
            ebit=10_000_000,
            market_cap=150_000_000,  # Should be ignored
            book_equity=40_000_000,
            is_manufacturing=False,
        )

        x4 = scorer._calc_equity_leverage_ratio(inputs)

        # Should use book_equity, not market_cap
        expected = 40_000_000 / 40_000_000  # = 1.0
        assert x4 == pytest.approx(expected)

    def test_partial_data_is_approximate(self, scorer):
        """Partial component calculation should be flagged as approximate."""
        data = {
            "total_assets": 100_000,
            "current_assets": 40_000,
            "current_liabilities": 20_000,
        }
        result = scorer.calculate_from_dict(data, require_all_components=False)
        assert result.is_approximate is True
        assert result.components_calculated < result.components_required
        assert "approximate" in result.interpretation.lower()

    def test_book_equity_fallback_is_approximate(self, scorer):
        """Manufacturing formula with book equity fallback should be approximate."""
        inputs = AltmanInputs(
            total_assets=100_000_000,
            current_assets=40_000_000,
            current_liabilities=20_000_000,
            total_liabilities=30_000_000,
            retained_earnings=50_000_000,
            revenue=80_000_000,
            ebit=15_000_000,
            market_cap=None,
            book_equity=70_000_000,
            is_manufacturing=True,
        )
        result = scorer.calculate(inputs, require_all_components=False)
        assert result.is_approximate is True
        assert result.used_book_equity_fallback is True
        assert "book equity" in result.interpretation.lower()

    def test_full_data_is_not_approximate(self, scorer):
        """Full data manufacturing calculation should not be approximate."""
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
        assert result.is_approximate is False
        assert result.components_calculated == result.components_required == 5

    def test_components_required_manufacturing_vs_non(self, scorer):
        """Manufacturing requires 5 components, non-manufacturing requires 4."""
        mfg_inputs = AltmanInputs(
            total_assets=100_000_000,
            current_assets=40_000_000,
            current_liabilities=20_000_000,
            total_liabilities=30_000_000,
            retained_earnings=50_000_000,
            revenue=80_000_000,
            ebit=15_000_000,
            market_cap=200_000_000,
            is_manufacturing=True,
        )
        non_mfg_inputs = AltmanInputs(
            total_assets=80_000_000,
            current_assets=35_000_000,
            current_liabilities=15_000_000,
            total_liabilities=40_000_000,
            retained_earnings=30_000_000,
            ebit=10_000_000,
            book_equity=40_000_000,
            is_manufacturing=False,
        )
        mfg_result = scorer.calculate(mfg_inputs)
        non_mfg_result = scorer.calculate(non_mfg_inputs)
        assert mfg_result.components_required == 5
        assert non_mfg_result.components_required == 4
