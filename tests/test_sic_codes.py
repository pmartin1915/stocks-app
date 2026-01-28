"""Tests for SIC code mapping."""

import pytest

from asymmetric.core.data.sic_codes import (
    get_all_sectors,
    get_altman_formula,
    get_industries_for_sector,
    get_sector_from_sic,
    get_sic_ranges_for_sector,
    is_manufacturing,
    search_industries,
)


class TestSicCodeMapping:
    """Tests for SIC code to sector mapping."""

    def test_manufacturing_sic_codes(self):
        """Test that manufacturing SIC codes are correctly identified."""
        # Manufacturing range is 2000-3999
        assert is_manufacturing("2000") is True
        assert is_manufacturing("3000") is True
        assert is_manufacturing("3571") is True  # Electronic Computers
        assert is_manufacturing("3999") is True

    def test_non_manufacturing_sic_codes(self):
        """Test that non-manufacturing SIC codes are correctly identified."""
        assert is_manufacturing("1000") is False  # Mining
        assert is_manufacturing("4000") is False  # Transportation
        assert is_manufacturing("5000") is False  # Wholesale Trade
        assert is_manufacturing("6000") is False  # Finance
        assert is_manufacturing("7000") is False  # Services

    def test_invalid_sic_codes(self):
        """Test handling of invalid SIC codes."""
        assert is_manufacturing(None) is False
        assert is_manufacturing("") is False
        assert is_manufacturing("abc") is False

    def test_get_sector_from_sic_manufacturing(self):
        """Test sector lookup for manufacturing SIC codes."""
        result = get_sector_from_sic("3571")  # Electronic Computers
        assert result is not None
        assert result.sector == "Manufacturing"
        assert result.altman_formula == "manufacturing"

    def test_get_sector_from_sic_non_manufacturing(self):
        """Test sector lookup for non-manufacturing SIC codes."""
        result = get_sector_from_sic("6000")  # Depository Institutions
        assert result is not None
        assert result.sector == "Finance"
        assert result.altman_formula == "non_manufacturing"

    def test_get_sector_from_sic_invalid(self):
        """Test sector lookup for invalid SIC codes."""
        assert get_sector_from_sic(None) is None
        assert get_sector_from_sic("") is None
        assert get_sector_from_sic("abc") is None

    def test_altman_formula_selection(self):
        """Test correct Altman formula selection by SIC code."""
        assert get_altman_formula("3571") == "manufacturing"
        assert get_altman_formula("6000") == "non_manufacturing"
        assert get_altman_formula(None) == "non_manufacturing"


class TestSectorLists:
    """Tests for sector listing functions."""

    def test_get_all_sectors(self):
        """Test getting all available sectors."""
        sectors = get_all_sectors()
        assert isinstance(sectors, list)
        assert len(sectors) > 0
        assert "Manufacturing" in sectors
        assert "Finance" in sectors
        assert "Healthcare" in sectors

    def test_get_industries_for_sector(self):
        """Test getting industries within a sector."""
        industries = get_industries_for_sector("Manufacturing")
        assert isinstance(industries, list)
        assert len(industries) > 0
        assert "Electronic & Electrical Equipment" in industries

    def test_get_sic_ranges_for_sector(self):
        """Test getting SIC code ranges for a sector."""
        ranges = get_sic_ranges_for_sector("Manufacturing")
        assert isinstance(ranges, list)
        assert len(ranges) > 0
        # Manufacturing should have ranges in 2000-3999
        for start, end in ranges:
            assert 2000 <= start <= 3999
            assert 2000 <= end <= 3999


class TestIndustrySearch:
    """Tests for industry search functionality."""

    def test_search_industries_basic(self):
        """Test basic industry search."""
        results = search_industries("electronic")
        assert len(results) > 0
        # Should find Electronic & Electrical Equipment
        industries = [r[1] for r in results]
        assert any("Electronic" in ind for ind in industries)

    def test_search_industries_case_insensitive(self):
        """Test case-insensitive search."""
        results_lower = search_industries("computer")
        results_upper = search_industries("COMPUTER")
        assert len(results_lower) == len(results_upper)

    def test_search_industries_no_results(self):
        """Test search with no matches."""
        results = search_industries("xyznonexistent")
        assert len(results) == 0
