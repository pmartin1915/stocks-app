"""Tests for dashboard.utils.formatters module."""

from datetime import datetime

import pytest

from dashboard.utils.formatters import (
    format_date,
    format_date_friendly,
    format_large_number,
    format_percentage,
    format_currency,
)


class TestFormatDate:
    """Tests for format_date function."""

    def test_format_date_without_time(self):
        """Test formatting date without time."""
        result = format_date("2024-01-15T10:30:00")
        assert result == "2024-01-15"

    def test_format_date_with_time(self):
        """Test formatting date with time."""
        result = format_date("2024-01-15T10:30:00", include_time=True)
        assert result == "2024-01-15 10:30"

    def test_format_date_none(self):
        """Test None returns default."""
        result = format_date(None)
        assert result == "N/A"

    def test_format_date_custom_default(self):
        """Test custom default value."""
        result = format_date(None, default="Unknown")
        assert result == "Unknown"

    def test_format_date_empty_string(self):
        """Test empty string returns default."""
        result = format_date("")
        assert result == "N/A"

    def test_format_date_invalid_format(self):
        """Test invalid format returns default."""
        result = format_date("not-a-date")
        assert result == "N/A"

    def test_format_date_with_timezone(self):
        """Test date with timezone."""
        result = format_date("2024-01-15T10:30:00+00:00")
        assert "2024-01-15" in result


class TestFormatDateFriendly:
    """Tests for format_date_friendly function."""

    def test_format_friendly_date(self):
        """Test formatting date in friendly format."""
        result = format_date_friendly("2024-01-15T10:30:00")
        assert result == "Jan 15, 2024"

    def test_format_friendly_date_none(self):
        """Test None returns default."""
        result = format_date_friendly(None)
        assert result == "Unknown date"

    def test_format_friendly_date_na(self):
        """Test 'N/A' string returns default."""
        result = format_date_friendly("N/A")
        assert result == "Unknown date"

    def test_format_friendly_date_custom_default(self):
        """Test custom default value."""
        result = format_date_friendly(None, default="No date")
        assert result == "No date"

    def test_format_friendly_date_invalid(self):
        """Test invalid date string returns the string itself."""
        result = format_date_friendly("invalid-date")
        assert result == "invalid-date"

    def test_format_friendly_date_empty(self):
        """Test empty string returns default."""
        result = format_date_friendly("")
        assert result == "Unknown date"

    def test_format_friendly_various_months(self):
        """Test various months are abbreviated correctly."""
        test_cases = [
            ("2024-01-15T00:00:00", "Jan 15, 2024"),
            ("2024-02-15T00:00:00", "Feb 15, 2024"),
            ("2024-12-31T00:00:00", "Dec 31, 2024"),
        ]
        for iso_date, expected in test_cases:
            result = format_date_friendly(iso_date)
            assert result == expected


class TestFormatLargeNumber:
    """Tests for format_large_number function."""

    def test_format_billions(self):
        """Test formatting billions."""
        result = format_large_number(1_500_000_000)
        assert result == "1.50B"

    def test_format_millions(self):
        """Test formatting millions."""
        result = format_large_number(2_500_000)
        assert result == "2.50M"

    def test_format_thousands(self):
        """Test formatting thousands."""
        result = format_large_number(350_000)
        assert result == "350.00K"

    def test_format_small_number(self):
        """Test formatting small numbers (no suffix)."""
        result = format_large_number(500)
        assert result == "500"

    def test_format_negative_number(self):
        """Test formatting negative numbers."""
        result = format_large_number(-1_500_000)
        assert result == "-1.50M"

    def test_format_none(self):
        """Test None returns N/A."""
        result = format_large_number(None)
        assert result == "N/A"

    def test_format_zero(self):
        """Test zero."""
        result = format_large_number(0)
        assert result == "0"

    def test_format_custom_precision(self):
        """Test custom precision."""
        result = format_large_number(1_234_567, precision=1)
        assert result == "1.2M"

    def test_format_decimal_number(self):
        """Test decimal numbers."""
        result = format_large_number(123.45)
        assert result == "123.45"


class TestFormatPercentage:
    """Tests for format_percentage function."""

    def test_format_decimal_as_percentage(self):
        """Test converting decimal to percentage."""
        result = format_percentage(0.15)
        assert result == "15.00%"

    def test_format_already_percentage(self):
        """Test value already as percentage."""
        result = format_percentage(15.0)
        assert result == "15.00%"

    def test_format_negative_percentage(self):
        """Test negative percentage."""
        result = format_percentage(-0.05)
        assert result == "-5.00%"

    def test_format_with_sign(self):
        """Test including + sign for positive."""
        result = format_percentage(0.10, include_sign=True)
        assert result == "+10.00%"

    def test_format_negative_with_sign(self):
        """Test negative with sign flag (no + added)."""
        result = format_percentage(-0.05, include_sign=True)
        assert result == "-5.00%"

    def test_format_custom_precision(self):
        """Test custom precision."""
        result = format_percentage(0.12345, precision=1)
        assert result == "12.3%"

    def test_format_none(self):
        """Test None returns N/A."""
        result = format_percentage(None)
        assert result == "N/A"

    def test_format_zero(self):
        """Test zero percentage."""
        result = format_percentage(0.0)
        assert result == "0.00%"

    def test_format_large_percentage(self):
        """Test large percentage."""
        result = format_percentage(150.0)
        assert result == "150.00%"


class TestFormatCurrency:
    """Tests for format_currency function."""

    def test_format_basic_currency(self):
        """Test basic currency formatting."""
        result = format_currency(1234.56)
        assert result == "$1,234.56"

    def test_format_large_currency(self):
        """Test large currency value with commas."""
        result = format_currency(1_234_567.89)
        assert result == "$1,234,567.89"

    def test_format_small_currency(self):
        """Test small currency value."""
        result = format_currency(9.99)
        assert result == "$9.99"

    def test_format_none(self):
        """Test None returns N/A."""
        result = format_currency(None)
        assert result == "N/A"

    def test_format_custom_symbol(self):
        """Test custom currency symbol."""
        result = format_currency(1000, symbol="€")
        assert result == "€1,000.00"

    def test_format_custom_precision(self):
        """Test custom precision."""
        result = format_currency(1234.5678, precision=0)
        assert result == "$1,235"

    def test_format_negative_currency(self):
        """Test negative currency."""
        result = format_currency(-500.25)
        assert result == "$-500.25"

    def test_format_zero(self):
        """Test zero currency."""
        result = format_currency(0)
        assert result == "$0.00"
