"""Test pure utility functions (no external dependencies).

Tests for format_large_number() and format_percentage() from price_data.py.
"""

import pytest

from dashboard.utils.price_data import format_large_number, format_percentage


class TestFormatLargeNumber:
    """Tests for format_large_number()."""

    def test_trillions(self):
        """Numbers >= 1T should display as $X.XT."""
        assert format_large_number(1_500_000_000_000) == "$1.5T"
        assert format_large_number(2_000_000_000_000) == "$2.0T"
        assert format_large_number(1_000_000_000_000) == "$1.0T"

    def test_billions(self):
        """Numbers >= 1B and < 1T should display as $X.XB."""
        assert format_large_number(250_000_000_000) == "$250.0B"
        assert format_large_number(1_000_000_000) == "$1.0B"
        # 500M stays in millions format (clearer than $0.5B)
        assert format_large_number(500_000_000) == "$500.0M"

    def test_millions(self):
        """Numbers >= 1M and < 1B should display as $X.XM."""
        assert format_large_number(50_000_000) == "$50.0M"
        assert format_large_number(1_500_000) == "$1.5M"
        assert format_large_number(1_000_000) == "$1.0M"

    def test_thousands(self):
        """Numbers >= 1K and < 1M should display as $X.XK."""
        assert format_large_number(5_000) == "$5.0K"
        assert format_large_number(1_234) == "$1.2K"
        assert format_large_number(999_999) == "$1000.0K"

    def test_small_numbers(self):
        """Numbers < 1K should display as plain numbers."""
        assert format_large_number(500) == "$500"
        assert format_large_number(99) == "$99"
        assert format_large_number(0) == "$0"

    def test_none(self):
        """None should return N/A."""
        assert format_large_number(None) == "N/A"

    def test_edge_cases(self):
        """Test boundary values."""
        # Exactly at boundaries
        assert format_large_number(1e12) == "$1.0T"
        assert format_large_number(1e9) == "$1.0B"
        assert format_large_number(1e6) == "$1.0M"
        assert format_large_number(1e3) == "$1.0K"


class TestFormatPercentage:
    """Tests for format_percentage()."""

    def test_positive_with_sign(self):
        """Positive percentages should have + prefix by default."""
        assert format_percentage(5.25) == "+5.25%"
        assert format_percentage(0.5) == "+0.50%"
        assert format_percentage(100.0) == "+100.00%"

    def test_negative(self):
        """Negative percentages should have - prefix."""
        assert format_percentage(-3.5) == "-3.50%"
        assert format_percentage(-0.01) == "-0.01%"
        assert format_percentage(-100.0) == "-100.00%"

    def test_zero(self):
        """Zero should display as +0.00%."""
        assert format_percentage(0.0) == "+0.00%"

    def test_without_sign(self):
        """With include_sign=False, no +/- prefix should appear."""
        assert format_percentage(5.25, include_sign=False) == "5.25%"
        assert format_percentage(-3.5, include_sign=False) == "-3.50%"
        assert format_percentage(0.0, include_sign=False) == "0.00%"

    def test_none(self):
        """None should return N/A."""
        assert format_percentage(None) == "N/A"
        assert format_percentage(None, include_sign=False) == "N/A"

    def test_precision(self):
        """Verify 2 decimal place precision."""
        assert format_percentage(1.234) == "+1.23%"
        assert format_percentage(1.235) == "+1.24%"  # Rounding
        assert format_percentage(-0.001) == "-0.00%"
