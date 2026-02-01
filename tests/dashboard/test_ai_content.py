"""Test AI content helper functions.

Tests for dashboard/components/ai_content.py - content hashing, model name formatting,
and HTML content formatting.
"""

import pytest

from dashboard.components.ai_content import (
    _format_content,
    _format_model_name,
    _generate_content_hash,
)


class TestContentHash:
    """Tests for content hash generation."""

    def test_deterministic(self):
        """Same inputs should produce same hash."""
        hash1 = _generate_content_hash("Test content", "flash", "AAPL")
        hash2 = _generate_content_hash("Test content", "flash", "AAPL")
        assert hash1 == hash2

    def test_different_content(self):
        """Different content should produce different hash."""
        hash1 = _generate_content_hash("Content A", "flash", "AAPL")
        hash2 = _generate_content_hash("Content B", "flash", "AAPL")
        assert hash1 != hash2

    def test_different_model(self):
        """Different model should produce different hash."""
        hash1 = _generate_content_hash("Same content", "flash", "AAPL")
        hash2 = _generate_content_hash("Same content", "pro", "AAPL")
        assert hash1 != hash2

    def test_different_ticker(self):
        """Different ticker should produce different hash."""
        hash1 = _generate_content_hash("Same content", "flash", "AAPL")
        hash2 = _generate_content_hash("Same content", "flash", "MSFT")
        assert hash1 != hash2

    def test_hash_length(self):
        """Hash should be 12 characters (truncated MD5)."""
        h = _generate_content_hash("x", "y", "z")
        assert len(h) == 12

    def test_hash_is_hex(self):
        """Hash should contain only hex characters."""
        h = _generate_content_hash("test", "model", "AAPL")
        assert all(c in "0123456789abcdef" for c in h)

    def test_long_content_truncation(self):
        """Long content should be truncated before hashing."""
        long_content = "x" * 1000
        short_content = "x" * 500
        # Both should hash the same since we truncate at 500
        hash1 = _generate_content_hash(long_content, "m", "t")
        hash2 = _generate_content_hash(short_content, "m", "t")
        assert hash1 == hash2

    def test_empty_content(self):
        """Empty content should still produce valid hash."""
        h = _generate_content_hash("", "model", "AAPL")
        assert len(h) == 12

    def test_empty_ticker(self):
        """Empty ticker should still produce valid hash."""
        h = _generate_content_hash("content", "model", "")
        assert len(h) == 12


class TestModelNameFormatting:
    """Tests for model name display formatting."""

    def test_flash_simple(self):
        """'flash' should become 'Flash'."""
        assert _format_model_name("flash") == "Flash"

    def test_flash_full_name(self):
        """Full Gemini flash name should format to 'Flash'."""
        # Implementation returns "Flash" for any model containing "flash"
        assert _format_model_name("gemini-2.5-flash") == "Flash"

    def test_pro_simple(self):
        """'pro' should become 'Pro'."""
        assert _format_model_name("pro") == "Pro"

    def test_pro_full_name(self):
        """Full Gemini 3 pro name should format to 'Pro'."""
        # Implementation returns "Pro" for any model containing "pro"
        assert _format_model_name("gemini-3-pro-preview") == "Pro"

    def test_gemini_25_pro(self):
        """Gemini 2.5 pro should return 'Pro'."""
        # Implementation checks "pro" before "gemini-2.5"
        assert _format_model_name("gemini-2.5-pro") == "Pro"

    def test_long_names_truncated(self):
        """Names longer than 15 chars should be truncated."""
        long_name = "some-very-long-model-name-here"
        formatted = _format_model_name(long_name)
        assert len(formatted) <= 15
        assert formatted.endswith("...")

    def test_short_unknown_name(self):
        """Short unknown names should pass through."""
        assert _format_model_name("claude") == "claude"

    def test_case_insensitive(self):
        """Model name matching should be case-insensitive."""
        assert _format_model_name("FLASH") == "Flash"
        assert _format_model_name("Flash") == "Flash"
        assert _format_model_name("PRO") == "Pro"


class TestContentFormatting:
    """Tests for content HTML formatting."""

    def test_html_escaping_script(self):
        """Script tags should be escaped."""
        content = "<script>alert('xss')</script>"
        formatted = _format_content(content)
        assert "<script>" not in formatted
        assert "&lt;script&gt;" in formatted

    def test_html_escaping_angle_brackets(self):
        """All angle brackets should be escaped."""
        content = "5 < 10 and 10 > 5"
        formatted = _format_content(content)
        assert "&lt;" in formatted
        assert "&gt;" in formatted

    def test_html_escaping_ampersand(self):
        """Ampersands should be escaped."""
        content = "R&D expenses"
        formatted = _format_content(content)
        assert "&amp;" in formatted

    def test_bullet_conversion_dash(self):
        """Dash bullets should be converted to HTML bullets."""
        content = "- First item\n- Second item"
        formatted = _format_content(content)
        assert "• First item" in formatted
        assert "• Second item" in formatted
        assert "margin-left:16px" in formatted

    def test_bullet_conversion_asterisk(self):
        """Asterisk bullets should be converted."""
        content = "* Item one\n* Item two"
        formatted = _format_content(content)
        assert "• Item one" in formatted
        assert "• Item two" in formatted

    def test_bullet_conversion_unicode(self):
        """Unicode bullets should be preserved."""
        content = "• Existing bullet"
        formatted = _format_content(content)
        assert "• Existing bullet" in formatted

    def test_empty_lines_spacing(self):
        """Empty lines should create vertical spacing."""
        content = "Line 1\n\nLine 2"
        formatted = _format_content(content)
        assert "height:8px" in formatted

    def test_regular_lines_wrapped_in_div(self):
        """Regular lines should be wrapped in divs."""
        content = "Regular line"
        formatted = _format_content(content)
        assert "<div>Regular line</div>" in formatted

    def test_whitespace_stripping(self):
        """Leading/trailing whitespace should be stripped."""
        content = "  Line with spaces  "
        formatted = _format_content(content)
        assert "<div>Line with spaces</div>" in formatted

    def test_mixed_content(self):
        """Mixed content (bullets, text, empty lines) should format correctly."""
        content = "Header\n\n- Bullet 1\n- Bullet 2\n\nConclusion"
        formatted = _format_content(content)
        assert "<div>Header</div>" in formatted
        assert "• Bullet 1" in formatted
        assert "• Bullet 2" in formatted
        assert "<div>Conclusion</div>" in formatted
        assert formatted.count("height:8px") == 2  # Two empty lines

    def test_empty_content(self):
        """Empty content should return spacing div (empty line)."""
        formatted = _format_content("")
        # Empty string becomes one empty line which creates a spacing div
        assert "height:8px" in formatted

    def test_only_whitespace(self):
        """Whitespace-only content should create spacing div."""
        formatted = _format_content("   ")
        # Empty line after stripping
        assert "height:8px" in formatted
