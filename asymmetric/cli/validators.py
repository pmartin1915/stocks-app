"""
Input validation utilities for CLI commands.

Provides reusable validation callbacks and helper functions for:
- Ticker symbol format validation
- Numeric bounds checking
- Price validation
- Common input sanitization
"""

import re
from typing import Optional

import click

# Stock ticker format: 1-10 uppercase alphanumeric chars, dots, hyphens
# Covers standard (AAPL), dot-suffix (BRK.A, BF.B), hyphenated (BRK-B),
# and numeric tickers. Matches manager._validate_ticker() regex.
TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,10}$")


def _validate_ticker_format(value: str) -> str:
    """
    Core ticker validation logic.

    Args:
        value: The ticker value (should already be uppercase/stripped)

    Returns:
        The validated ticker

    Raises:
        ValueError: If ticker format is invalid
    """
    if not TICKER_PATTERN.match(value):
        raise ValueError(
            f"Invalid ticker format: '{value}'. "
            "Expected 1-10 uppercase characters (e.g., AAPL, BRK.A, BRK-B)"
        )
    return value


def validate_ticker(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """
    Validate and normalize a stock ticker symbol (Click callback).

    Args:
        ctx: Click context
        param: Click parameter
        value: The ticker value to validate

    Returns:
        Uppercase ticker if valid

    Raises:
        click.BadParameter: If ticker format is invalid
    """
    if not value:
        raise click.BadParameter("Ticker symbol is required")

    value = value.upper().strip()

    try:
        return _validate_ticker_format(value)
    except ValueError as e:
        raise click.BadParameter(str(e))


def validate_positive_float(
    name: str, min_val: Optional[float] = None, max_val: Optional[float] = None
):
    """
    Create a validator for positive float values with optional bounds.

    Args:
        name: Name of the parameter (for error messages)
        min_val: Optional minimum value (inclusive)
        max_val: Optional maximum value (inclusive)

    Returns:
        Click callback function for validation
    """
    def validator(ctx: click.Context, param: click.Parameter, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None

        if value <= 0:
            raise click.BadParameter(f"{name} must be greater than 0")

        if min_val is not None and value < min_val:
            raise click.BadParameter(f"{name} must be at least {min_val}")

        if max_val is not None and value > max_val:
            raise click.BadParameter(f"{name} must be at most {max_val}")

        return value

    return validator


def validate_price_relationship(
    target_price: Optional[float],
    stop_loss: Optional[float],
    action: str,
) -> None:
    """
    Validate that target price and stop loss have a logical relationship.

    Args:
        target_price: Target sell price
        stop_loss: Stop loss price
        action: The decision action (buy/sell/hold/pass)

    Raises:
        click.BadParameter: If the price relationship is illogical
    """
    if target_price is None or stop_loss is None:
        return

    if action in ("buy", "hold"):
        # For buy/hold, target should be above stop loss
        if target_price <= stop_loss:
            raise click.BadParameter(
                f"Target price (${target_price:.2f}) must be greater than "
                f"stop loss (${stop_loss:.2f}) for {action} decisions"
            )


def validate_text_length(
    value: Optional[str],
    max_length: int,
    field_name: str,
    truncate: bool = True,
) -> tuple[Optional[str], bool]:
    """
    Validate and optionally truncate text to a maximum length.

    Args:
        value: The text value to validate
        max_length: Maximum allowed length
        field_name: Name of the field (for messages)
        truncate: If True, truncate; if False, raise error

    Returns:
        Tuple of (validated/truncated value, was_truncated flag)

    Raises:
        click.BadParameter: If truncate=False and value exceeds max_length
    """
    if value is None:
        return None, False

    if len(value) <= max_length:
        return value, False

    if truncate:
        return value[:max_length], True
    else:
        raise click.BadParameter(
            f"{field_name} exceeds maximum length of {max_length} characters"
        )


class TickerType(click.ParamType):
    """Custom Click parameter type for ticker symbols."""

    name = "ticker"

    def convert(self, value, param, ctx):
        if not value:
            self.fail("Ticker symbol is required", param, ctx)

        value = value.upper().strip()

        try:
            return _validate_ticker_format(value)
        except ValueError as e:
            self.fail(str(e), param, ctx)


# Singleton instance for reuse
TICKER = TickerType()
