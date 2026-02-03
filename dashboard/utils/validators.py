"""Input validation utilities for the dashboard.

Provides reusable validation functions for user input like ticker symbols,
consolidating duplicate validation logic from individual pages.
Also provides HTML sanitization for XSS prevention.
"""

import html
import re


def validate_ticker(ticker: str, allow_empty: bool = False) -> tuple[bool, str]:
    """Validate stock ticker symbol format.

    Args:
        ticker: Stock ticker symbol to validate.
        allow_empty: If True, empty string is considered valid (for optional fields).

    Returns:
        Tuple of (is_valid, error_message). Error message is empty if valid.

    Examples:
        >>> validate_ticker("AAPL")
        (True, "")
        >>> validate_ticker("BRK-B")
        (True, "")
        >>> validate_ticker("")
        (False, "Please enter a ticker symbol")
        >>> validate_ticker("", allow_empty=True)
        (True, "")
        >>> validate_ticker("invalid123")
        (False, "Invalid ticker format...")
    """
    if not ticker:
        if allow_empty:
            return True, ""
        return False, "Please enter a ticker symbol"

    # Ticker format: 1-5 uppercase letters, optionally followed by hyphen and letter
    # Examples: AAPL, MSFT, BRK-B, BRK-A
    # Note: Input should be uppercased before calling this function
    if not re.match(r"^[A-Z]{1,5}(?:-[A-Z])?$", ticker):
        return False, f"Invalid ticker format: {ticker}. Expected format like AAPL or BRK-B."

    return True, ""


def validate_price(price: float, field_name: str = "Price") -> tuple[bool, str]:
    """Validate a price value is positive.

    Args:
        price: The price value to validate.
        field_name: Name of the field for error messages.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if price is None:
        return False, f"{field_name} is required"
    if price <= 0:
        return False, f"{field_name} must be greater than zero"
    return True, ""


def validate_price_targets(
    target_price: float | None,
    stop_loss: float | None,
) -> tuple[bool, str]:
    """Validate that target price is greater than stop loss.

    Args:
        target_price: The target price (optional).
        stop_loss: The stop loss price (optional).

    Returns:
        Tuple of (is_valid, error_message).
    """
    if target_price is not None and stop_loss is not None:
        if target_price <= stop_loss:
            return False, "Target price must be greater than stop loss"
    return True, ""


def sanitize_html(text: str) -> str:
    """Sanitize user-provided text for safe HTML display.

    Escapes HTML special characters to prevent XSS attacks.
    Use this function whenever displaying user-controlled content
    in HTML contexts (unsafe_allow_html=True).

    Args:
        text: User-provided text that may contain HTML.

    Returns:
        HTML-escaped text safe for display.

    Examples:
        >>> sanitize_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
        >>> sanitize_html("Normal text & symbols")
        "Normal text &amp; symbols"
    """
    if not text:
        return ""
    return html.escape(text)


def sanitize_html_multi(*texts: str) -> list[str]:
    """Sanitize multiple text values at once.

    Convenience function for sanitizing multiple fields.

    Args:
        *texts: Variable number of text strings to sanitize.

    Returns:
        List of sanitized strings in the same order.

    Examples:
        >>> sanitize_html_multi("<b>Title</b>", "<i>Description</i>")
        ["&lt;b&gt;Title&lt;/b&gt;", "&lt;i&gt;Description&lt;/i&gt;"]
    """
    return [sanitize_html(text) for text in texts]
