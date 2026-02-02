"""Formatting utilities for the dashboard.

Provides reusable formatting functions for dates, numbers, and text,
consolidating duplicate formatting logic from individual pages and components.
"""

from datetime import datetime
from typing import Optional


def format_date(
    iso_date: Optional[str],
    include_time: bool = False,
    default: str = "N/A",
) -> str:
    """Format ISO date string for display.

    Args:
        iso_date: ISO format date string (e.g., "2024-01-15T10:30:00").
        include_time: If True, include time in output (HH:MM).
        default: Value to return if date is None or invalid.

    Returns:
        Formatted date string like "2024-01-15" or "2024-01-15 10:30".

    Examples:
        >>> format_date("2024-01-15T10:30:00")
        "2024-01-15"
        >>> format_date("2024-01-15T10:30:00", include_time=True)
        "2024-01-15 10:30"
        >>> format_date(None)
        "N/A"
    """
    if not iso_date:
        return default
    try:
        dt = datetime.fromisoformat(iso_date)
        if include_time:
            return dt.strftime("%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return default


def format_relative_date(iso_date: Optional[str], default: str = "N/A") -> str:
    """Format ISO date as relative time (e.g., '2 days ago').

    Args:
        iso_date: ISO format date string.
        default: Value to return if date is None or invalid.

    Returns:
        Relative time string like "Just now", "2 hours ago", "Yesterday".
    """
    if not iso_date:
        return default
    try:
        dt = datetime.fromisoformat(iso_date)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt

        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                if minutes < 2:
                    return "Just now"
                return f"{minutes} minutes ago"
            elif hours == 1:
                return "1 hour ago"
            return f"{hours} hours ago"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return default


def format_large_number(num: float | int | None, precision: int = 2) -> str:
    """Format large numbers with K/M/B suffixes.

    Args:
        num: Number to format.
        precision: Decimal places to show.

    Returns:
        Formatted string like "1.5M" or "250K".

    Examples:
        >>> format_large_number(1500000)
        "1.50M"
        >>> format_large_number(250000)
        "250.00K"
        >>> format_large_number(500)
        "500"
    """
    if num is None:
        return "N/A"

    abs_num = abs(num)
    sign = "-" if num < 0 else ""

    if abs_num >= 1_000_000_000:
        return f"{sign}{abs_num / 1_000_000_000:.{precision}f}B"
    elif abs_num >= 1_000_000:
        return f"{sign}{abs_num / 1_000_000:.{precision}f}M"
    elif abs_num >= 1_000:
        return f"{sign}{abs_num / 1_000:.{precision}f}K"
    else:
        return f"{sign}{abs_num:.0f}" if abs_num == int(abs_num) else f"{sign}{abs_num:.{precision}f}"


def format_percentage(value: float | None, precision: int = 2, include_sign: bool = False) -> str:
    """Format a decimal or percentage value.

    Args:
        value: Value to format (e.g., 0.15 for 15% or 15.0 for 15%).
        precision: Decimal places to show.
        include_sign: If True, include + for positive values.

    Returns:
        Formatted percentage string like "15.00%" or "+15.00%".
    """
    if value is None:
        return "N/A"

    # Assume values > 1 or < -1 are already percentages
    if abs(value) <= 1:
        value = value * 100

    sign = "+" if include_sign and value > 0 else ""
    return f"{sign}{value:.{precision}f}%"


def format_currency(value: float | None, precision: int = 2, symbol: str = "$") -> str:
    """Format a value as currency.

    Args:
        value: Value to format.
        precision: Decimal places to show.
        symbol: Currency symbol to use.

    Returns:
        Formatted currency string like "$1,234.56".
    """
    if value is None:
        return "N/A"

    return f"{symbol}{value:,.{precision}f}"
