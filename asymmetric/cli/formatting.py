"""Centralized formatting utilities for CLI output.

Provides consistent colors, indicators, and formatting across all CLI commands.
Mirrors the dashboard's visual language using Rich markup instead of HTML/SVG.
"""

from typing import Optional

from rich.console import Console


# =============================================================================
# Standard Padding & Borders
# =============================================================================

# Panel/Table padding standards
PANEL_PADDING = (1, 2)
TABLE_PADDING = (0, 2)

# Border style semantics (see docs/color-conventions.md)
BORDER_PRIMARY = "blue"      # Main content panels
BORDER_SUCCESS = "green"     # Success/confirmation panels
BORDER_METADATA = "dim"      # Secondary/metadata panels
BORDER_WARNING = "yellow"    # Warning panels
BORDER_ERROR = "red"         # Error/alert panels

# Missing value indicator
MISSING = "-"


# =============================================================================
# Score Color Functions
# =============================================================================


def get_score_color(score: int, max_score: int) -> str:
    """Get Rich color based on score percentage."""
    pct = score / max_score
    if pct >= 0.7:
        return "green"
    elif pct >= 0.4:
        return "yellow"
    else:
        return "red"


def get_zone_color(zone: str) -> str:
    """Get Rich color based on Altman zone."""
    colors = {
        "Safe": "green",
        "Grey": "yellow",
        "Distress": "red",
    }
    return colors.get(zone, "white")


def get_action_color(action: str) -> str:
    """Get Rich color based on decision action."""
    colors = {
        "buy": "green",
        "hold": "yellow",
        "sell": "red",
        "pass": "dim",
    }
    return colors.get(action.lower(), "white")


# =============================================================================
# Verdict Functions (Plain English interpretation)
# =============================================================================


def get_fscore_verdict(score: int) -> tuple[str, str]:
    """
    Get plain English verdict for F-Score.

    Returns:
        Tuple of (verdict_text, color)
    """
    if score >= 7:
        return "Financially Strong", "green"
    elif score >= 4:
        return "Moderate Health", "yellow"
    else:
        return "Financial Concerns", "red"


def get_zscore_verdict(zone: str) -> tuple[str, str]:
    """
    Get plain English verdict for Z-Score.

    Returns:
        Tuple of (verdict_text, color)
    """
    verdicts = {
        "Safe": ("Low Bankruptcy Risk", "green"),
        "Grey": ("Uncertain Risk", "yellow"),
        "Distress": ("High Bankruptcy Risk", "red"),
    }
    return verdicts.get(zone, ("Unknown", "white"))


# =============================================================================
# Signal Indicators (ASCII-safe for Windows compatibility)
# =============================================================================


class Signals:
    """ASCII signal indicators for CLI display.

    Uses ASCII characters for Windows cp1252 compatibility.
    Avoids Unicode symbols that may not render on all terminals.
    """

    # Pass/Fail indicators (ASCII-safe)
    CHECK = "+"
    CROSS = "-"
    TILDE = "~"
    WARNING = "!"

    # Winner/rank indicators (ASCII-safe)
    WINNER = "*"      # Asterisk - marks the best option
    STAR = "*"        # Asterisk - for ratings
    STAR_EMPTY = "o"  # Letter o - for ratings
    BULLET = "*"      # Asterisk - for lists/ranking
    ARROW_UP = "^"    # Caret - improvement
    ARROW_DOWN = "v"  # Letter v - decline


def signal_indicator(passed: Optional[bool]) -> tuple[str, str]:
    """
    Get signal indicator symbol and color.

    Args:
        passed: True for pass, False for fail, None for no data

    Returns:
        Tuple of (symbol, color)
    """
    if passed is None:
        return Signals.TILDE, "dim"
    elif passed:
        return Signals.CHECK, "green"
    else:
        return Signals.CROSS, "red"


# =============================================================================
# Quick Signals (for score summary)
# =============================================================================


def get_profitability_signal(score: int) -> tuple[str, str, str]:
    """Get profitability signal (symbol, text, color)."""
    if score >= 3:
        return Signals.CHECK, "Profitable", "green"
    elif score >= 2:
        return Signals.TILDE, "Marginally profitable", "yellow"
    else:
        return Signals.CROSS, "Unprofitable", "red"


def get_leverage_signal(score: int) -> tuple[str, str, str]:
    """Get leverage signal (symbol, text, color)."""
    if score >= 2:
        return Signals.CHECK, "Low debt", "green"
    elif score >= 1:
        return Signals.TILDE, "Moderate debt", "yellow"
    else:
        return Signals.WARNING, "High debt", "red"


def get_efficiency_signal(score: int) -> tuple[str, str, str]:
    """Get efficiency signal (symbol, text, color)."""
    if score >= 2:
        return Signals.CHECK, "Efficient operations", "green"
    elif score >= 1:
        return Signals.TILDE, "Mixed efficiency", "yellow"
    else:
        # Note: Declining efficiency is red (negative indicator)
        return Signals.WARNING, "Declining efficiency", "red"


def get_quick_signals(piotroski_result: dict, altman_result: dict) -> list[tuple[str, str, str]]:
    """
    Extract quick signal summary from score results.

    Args:
        piotroski_result: Dict with piotroski score data
        altman_result: Dict with altman score data (unused but kept for API consistency)

    Returns:
        List of (symbol, text, color) tuples
    """
    signals = []

    if piotroski_result and "error" not in piotroski_result:
        # Profitability check
        prof_score = piotroski_result.get("profitability_score", 0)
        signals.append(get_profitability_signal(prof_score))

        # Leverage check
        lev_score = piotroski_result.get("leverage_score", 0)
        signals.append(get_leverage_signal(lev_score))

        # Efficiency check
        eff_score = piotroski_result.get("efficiency_score", 0)
        signals.append(get_efficiency_signal(eff_score))

    return signals


# =============================================================================
# Progress Bar
# =============================================================================


def make_progress_bar(value: float, max_value: float, width: int = 10) -> str:
    """Create a text-based progress bar using ASCII characters."""
    filled = int((value / max_value) * width)
    empty = width - filled
    return "#" * filled + "-" * empty


# =============================================================================
# Winner Highlighting (for comparisons)
# =============================================================================


def highlight_winner(values: list, higher_is_better: bool = True) -> list[str]:
    """
    Return list of colors for values, highlighting the best one.

    Args:
        values: List of numeric values (or None for missing)
        higher_is_better: If True, highest value wins; if False, lowest wins

    Returns:
        List of color strings ("green" for winner, "white" for others, "dim" for None)
    """
    valid_values = [(i, v) for i, v in enumerate(values) if v is not None]

    if not valid_values:
        return ["dim"] * len(values)

    if higher_is_better:
        winner_idx = max(valid_values, key=lambda x: x[1])[0]
    else:
        winner_idx = min(valid_values, key=lambda x: x[1])[0]

    colors = []
    for i, v in enumerate(values):
        if v is None:
            colors.append("dim")
        elif i == winner_idx:
            colors.append("green")
        else:
            colors.append("white")

    return colors


def winner_indicator(is_winner: bool) -> str:
    """
    Get winner indicator symbol.

    Args:
        is_winner: Whether this is the winner

    Returns:
        Winner diamond symbol or empty string
    """
    if is_winner:
        return f" {Signals.WINNER}"
    return ""


# =============================================================================
# Helper Functions for Consistent Output
# =============================================================================


def format_missing(value, default: str = MISSING):
    """
    Return value or standard missing indicator.

    Args:
        value: The value to check
        default: Fallback for None values (default: "-")

    Returns:
        Original value if not None, else default
    """
    return value if value is not None else default


def print_next_steps(console: Console, steps: list[tuple[str, str]]) -> None:
    """
    Print standardized next-step hints.

    Args:
        console: Rich console instance
        steps: List of (label, command) tuples
    """
    console.print()
    console.print("[dim]Next steps:[/dim]")
    for label, cmd in steps:
        console.print(f"  [dim]{label}:[/dim]  {cmd}")


def print_empty_state(console: Console, entity: str, hint: str) -> None:
    """
    Print standardized empty state message.

    Args:
        console: Rich console instance
        entity: What's empty (e.g., "watchlist", "theses")
        hint: Command to get started
    """
    console.print(f"[yellow]No {entity} found.[/yellow]")
    console.print(f"[dim]Get started: {hint}[/dim]")
