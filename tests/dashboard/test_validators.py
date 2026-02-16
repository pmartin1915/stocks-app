"""Tests for dashboard.utils.validators module."""

import pytest

from dashboard.utils.validators import (
    validate_ticker,
    validate_price,
    validate_price_targets,
    sanitize_html,
    sanitize_html_multi,
)


class TestValidateTicker:
    """Tests for validate_ticker function."""

    def test_valid_simple_ticker(self):
        """Test valid single-letter ticker."""
        is_valid, error = validate_ticker("A")
        assert is_valid
        assert error == ""

    def test_valid_multi_letter_ticker(self):
        """Test valid multi-letter ticker."""
        is_valid, error = validate_ticker("AAPL")
        assert is_valid
        assert error == ""

    def test_valid_hyphenated_ticker(self):
        """Test valid hyphenated ticker like BRK-B."""
        is_valid, error = validate_ticker("BRK-B")
        assert is_valid
        assert error == ""

    def test_invalid_empty_ticker(self):
        """Test empty ticker is invalid by default."""
        is_valid, error = validate_ticker("")
        assert not is_valid
        assert "enter a ticker" in error.lower()

    def test_empty_ticker_allowed(self):
        """Test empty ticker is valid when allowed."""
        is_valid, error = validate_ticker("", allow_empty=True)
        assert is_valid
        assert error == ""

    def test_invalid_lowercase_ticker(self):
        """Test lowercase ticker is invalid."""
        is_valid, error = validate_ticker("aapl")
        assert not is_valid
        assert "Invalid ticker format" in error

    def test_invalid_too_long_ticker(self):
        """Test ticker longer than 10 chars is invalid."""
        is_valid, error = validate_ticker("TOOLONGXXXX1")
        assert not is_valid
        assert "Invalid ticker format" in error

    def test_valid_ticker_with_numbers(self):
        """Test ticker with numbers is valid (e.g., 3M)."""
        is_valid, error = validate_ticker("3M")
        assert is_valid
        assert error == ""

    def test_valid_dot_suffix_ticker(self):
        """Test dot-suffix tickers like BRK.A are valid."""
        is_valid, error = validate_ticker("BRK.A")
        assert is_valid
        assert error == ""

    def test_invalid_special_characters(self):
        """Test ticker with special characters is invalid."""
        is_valid, error = validate_ticker("AAP$L")
        assert not is_valid
        assert "Invalid ticker format" in error


class TestValidatePrice:
    """Tests for validate_price function."""

    def test_valid_positive_price(self):
        """Test valid positive price."""
        is_valid, error = validate_price(100.50)
        assert is_valid
        assert error == ""

    def test_valid_small_price(self):
        """Test valid small positive price."""
        is_valid, error = validate_price(0.01)
        assert is_valid
        assert error == ""

    def test_invalid_zero_price(self):
        """Test zero price is invalid."""
        is_valid, error = validate_price(0.0)
        assert not is_valid
        assert "greater than zero" in error.lower()

    def test_invalid_negative_price(self):
        """Test negative price is invalid."""
        is_valid, error = validate_price(-10.0)
        assert not is_valid
        assert "greater than zero" in error.lower()

    def test_invalid_none_price(self):
        """Test None price is invalid."""
        is_valid, error = validate_price(None)
        assert not is_valid
        assert "required" in error.lower()

    def test_custom_field_name(self):
        """Test custom field name appears in error message."""
        is_valid, error = validate_price(None, field_name="Target Price")
        assert not is_valid
        assert "Target Price" in error


class TestValidatePriceTargets:
    """Tests for validate_price_targets function."""

    def test_valid_target_greater_than_stop(self):
        """Test valid case where target > stop loss."""
        is_valid, error = validate_price_targets(target_price=150.0, stop_loss=100.0)
        assert is_valid
        assert error == ""

    def test_invalid_target_less_than_stop(self):
        """Test invalid case where target < stop loss."""
        is_valid, error = validate_price_targets(target_price=100.0, stop_loss=150.0)
        assert not is_valid
        assert "greater than stop loss" in error.lower()

    def test_invalid_target_equals_stop(self):
        """Test invalid case where target = stop loss."""
        is_valid, error = validate_price_targets(target_price=100.0, stop_loss=100.0)
        assert not is_valid
        assert "greater than stop loss" in error.lower()

    def test_valid_only_target_provided(self):
        """Test valid when only target price is provided."""
        is_valid, error = validate_price_targets(target_price=150.0, stop_loss=None)
        assert is_valid
        assert error == ""

    def test_valid_only_stop_provided(self):
        """Test valid when only stop loss is provided."""
        is_valid, error = validate_price_targets(target_price=None, stop_loss=100.0)
        assert is_valid
        assert error == ""

    def test_valid_both_none(self):
        """Test valid when both are None."""
        is_valid, error = validate_price_targets(target_price=None, stop_loss=None)
        assert is_valid
        assert error == ""


class TestSanitizeHtml:
    """Tests for sanitize_html function."""

    def test_sanitize_script_tag(self):
        """Test script tags are escaped."""
        result = sanitize_html("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        assert "<script>" not in result

    def test_sanitize_html_tags(self):
        """Test HTML tags are escaped."""
        result = sanitize_html("<b>Bold</b> <i>Italic</i>")
        assert "&lt;b&gt;" in result
        assert "&lt;/b&gt;" in result
        assert "&lt;i&gt;" in result
        assert "<b>" not in result

    def test_sanitize_ampersand(self):
        """Test ampersands are escaped."""
        result = sanitize_html("A & B")
        assert "&amp;" in result
        assert result == "A &amp; B"

    def test_sanitize_quotes(self):
        """Test quotes in attributes are escaped."""
        result = sanitize_html('<img src="x" onerror="alert(1)">')
        assert "&lt;img" in result
        assert "&gt;" in result
        assert '"' in result or "&quot;" in result

    def test_sanitize_empty_string(self):
        """Test empty string returns empty string."""
        result = sanitize_html("")
        assert result == ""

    def test_sanitize_none(self):
        """Test None returns empty string."""
        result = sanitize_html(None)
        assert result == ""

    def test_sanitize_normal_text(self):
        """Test normal text is unchanged."""
        text = "This is normal text with no HTML"
        result = sanitize_html(text)
        assert result == text

    def test_sanitize_preserves_newlines(self):
        """Test newlines are preserved."""
        text = "Line 1\nLine 2\nLine 3"
        result = sanitize_html(text)
        assert "\n" in result


class TestSanitizeHtmlMulti:
    """Tests for sanitize_html_multi function."""

    def test_sanitize_multiple_strings(self):
        """Test multiple strings are sanitized."""
        results = sanitize_html_multi("<b>Title</b>", "<i>Desc</i>", "Normal text")
        assert len(results) == 3
        assert "&lt;b&gt;" in results[0]
        assert "&lt;i&gt;" in results[1]
        assert results[2] == "Normal text"

    def test_sanitize_empty_list(self):
        """Test empty input returns empty list."""
        results = sanitize_html_multi()
        assert results == []

    def test_sanitize_single_string(self):
        """Test single string works."""
        results = sanitize_html_multi("<script>xss</script>")
        assert len(results) == 1
        assert "&lt;script&gt;" in results[0]

    def test_sanitize_with_none_values(self):
        """Test None values are handled."""
        results = sanitize_html_multi("<b>Text</b>", None, "Normal")
        assert len(results) == 3
        assert results[1] == ""  # None becomes empty string
