"""SVG icon system for professional dashboard UI.

Replaces emoji-based indicators with clean, minimal SVG icons
that render consistently across all platforms.
"""

import html as html_module
from typing import Optional

from dashboard.theme import get_color, get_semantic_color

# Color palette (matches dark theme semantic colors)
COLORS = {
    "green": "#10b981",
    "yellow": "#f59e0b",
    "red": "#f87171",
    "gray": "#9ca3af",
    "blue": "#60a5fa",
}


def _get_semantic_colors() -> dict[str, str]:
    """Get theme-aware semantic colors."""
    return {
        "green": get_semantic_color("green"),
        "yellow": get_semantic_color("yellow"),
        "red": get_semantic_color("red"),
        "gray": get_semantic_color("gray"),
        "blue": get_semantic_color("blue"),
    }

# Default icon size
DEFAULT_SIZE = 18  # Slightly larger for better visibility


def _svg(path: str, color: str, size: int = DEFAULT_SIZE, filled: bool = False) -> str:
    """Render SVG with consistent styling."""
    if filled:
        style = f'fill="{color}"'
    else:
        style = f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'width="{size}" height="{size}" {style}>{path}</svg>'
    )


# --- Status Circle Icons (solid filled circles) ---

def circle(color: str, size: int = DEFAULT_SIZE) -> str:
    """Solid circle indicator."""
    return _svg('<circle cx="12" cy="12" r="8"/>', color, size, filled=True)


def circle_green(size: int = DEFAULT_SIZE) -> str:
    """Green circle - safe/success."""
    return circle(get_semantic_color("green"), size)


def circle_yellow(size: int = DEFAULT_SIZE) -> str:
    """Yellow circle - warning/grey zone."""
    return circle(get_semantic_color("yellow"), size)


def circle_red(size: int = DEFAULT_SIZE) -> str:
    """Red circle - danger/distress."""
    return circle(get_semantic_color("red"), size)


def circle_gray(size: int = DEFAULT_SIZE) -> str:
    """Gray circle - neutral/no data."""
    return circle(get_semantic_color("gray"), size)


# --- Signal Icons (outline strokes) ---

def check(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Checkmark - pass/success."""
    if color is None:
        color = get_semantic_color("green")
    return _svg('<polyline points="20 6 9 17 4 12"/>', color, size)


def x_mark(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """X mark - fail/error."""
    if color is None:
        color = get_semantic_color("red")
    return _svg('<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>', color, size)


def minus(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Minus/dash - no data."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg('<line x1="5" y1="12" x2="19" y2="12"/>', color, size)


# --- Action Icons ---

def refresh(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Refresh/reload icon."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg(
        '<path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>'
        '<path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>',
        color, size
    )


def trash(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Trash/delete icon."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg(
        '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
        '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
        color, size
    )


def chart(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Bar chart icon."""
    if color is None:
        color = get_semantic_color("blue")
    return _svg(
        '<line x1="18" y1="20" x2="18" y2="10"/>'
        '<line x1="12" y1="20" x2="12" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="14"/>',
        color, size
    )


def search(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Search/magnifying glass icon."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg(
        '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
        color, size
    )


def clipboard(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Clipboard/list icon."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg(
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
        color, size
    )


def edit(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Pencil/edit icon."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg(
        '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
        '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
        color, size
    )


def archive(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Archive/box icon."""
    if color is None:
        color = get_semantic_color("gray")
    return _svg(
        '<path d="M21 8v13H3V8"/><path d="M1 3h22v5H1z"/>'
        '<path d="M10 12h4"/>',
        color, size
    )


# --- Star Rating ---

def star_filled(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Filled star."""
    if color is None:
        color = get_semantic_color("yellow")
    return _svg(
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        color, size, filled=True
    )


def star_empty(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Empty star outline."""
    if color is None:
        color = get_semantic_color("yellow")
    return _svg(
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        color, size
    )


def stars_rating(rating: int, max_stars: int = 5, size: int = DEFAULT_SIZE) -> str:
    """Generate star rating display (e.g., 3/5 stars)."""
    filled = min(max(0, rating), max_stars)
    empty = max_stars - filled
    return "".join([star_filled(size=size) for _ in range(filled)] +
                   [star_empty(size=size) for _ in range(empty)])


# --- Semantic Helpers ---

def status_icon(zone: str, size: int = DEFAULT_SIZE) -> str:
    """Get status indicator by zone name."""
    zone_map = {
        "safe": circle_green,
        "grey": circle_yellow,
        "gray": circle_yellow,
        "distress": circle_red,
        "neutral": circle_gray,
    }
    fn = zone_map.get(zone.lower(), circle_gray)
    return fn(size)


def signal_icon(passed: Optional[bool], size: int = DEFAULT_SIZE) -> str:
    """Get signal indicator by pass/fail state."""
    if passed is None:
        return minus(size=size)
    elif passed:
        return check(size=size)
    else:
        return x_mark(size=size)


def thesis_status_icon(status: str, size: int = DEFAULT_SIZE) -> str:
    """Get thesis status indicator."""
    yellow = get_semantic_color("yellow")
    green = get_semantic_color("green")
    gray = get_semantic_color("gray")

    status_map = {
        "draft": lambda s: edit(yellow, s),
        "active": lambda s: check(green, s),
        "archived": lambda s: archive(gray, s),
    }
    fn = status_map.get(status.lower(), lambda s: edit(gray, s))
    return fn(size)


def action_icon(action: str, size: int = DEFAULT_SIZE) -> str:
    """Get action indicator by action name."""
    action_map = {
        "buy": circle_green,
        "hold": circle_yellow,
        "sell": circle_red,
        "pass": circle_gray,
    }
    fn = action_map.get(action.lower(), circle_gray)
    return fn(size)


# --- HTML Helper for Streamlit ---

def icon_text(icon_html: str, text: str, gap: int = 6) -> str:
    """Combine icon with text for inline display."""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:{gap}px">'
        f'{icon_html}<span>{text}</span></span>'
    )


# --- Styled Badges (professional status indicators) ---

def badge(text: str, bg_color: str, text_color: str = "#fff", size: str = "small") -> str:
    """
    Create a styled badge/pill component.

    Args:
        text: Badge text.
        bg_color: Background color (hex or CSS color).
        text_color: Text color (default white).
        size: "small" or "normal".

    Returns:
        HTML string for styled badge.
    """
    padding = "2px 8px" if size == "small" else "4px 12px"
    font_size = "0.75rem" if size == "small" else "0.875rem"

    escaped = html_module.escape(text)
    return (
        f'<span role="img" aria-label="{escaped}" style="display:inline-block;background:{bg_color};color:{text_color};'
        f'padding:{padding};border-radius:12px;font-size:{font_size};font-weight:600;'
        f'line-height:1.4">{escaped}</span>'
    )


def status_badge(zone: str, size: str = "small") -> str:
    """
    Create a colored status badge for zone display.

    Args:
        zone: Zone name (Safe/Grey/Distress).
        size: "small" or "normal".

    Returns:
        HTML badge string.
    """
    colors = _get_semantic_colors()
    text_on_accent = get_color("text_on_accent")
    text_on_yellow = get_color("text_on_yellow")
    zone_styles = {
        "safe": (colors["green"], text_on_accent),
        "grey": (colors["yellow"], text_on_yellow),
        "gray": (colors["yellow"], text_on_yellow),
        "distress": (colors["red"], text_on_accent),
    }
    bg, fg = zone_styles.get(zone.lower(), (colors["gray"], text_on_accent))
    return badge(zone.title(), bg, fg, size)


def fscore_badge(
    score: int | None,
    size: str = "small",
    signals_available: int = 9,
) -> str:
    """
    Create a colored badge for F-Score display.

    Args:
        score: Piotroski F-Score (0-9) or None.
        size: "small" or "normal".
        signals_available: How many of 9 signals were calculable.

    Returns:
        HTML badge string.
    """
    colors = _get_semantic_colors()
    text_on_accent = get_color("text_on_accent")
    text_on_yellow = get_color("text_on_yellow")

    if score is None:
        return badge("N/A", colors["gray"], text_on_accent, size)

    if score >= 7:
        bg, fg = colors["green"], text_on_accent
    elif score >= 4:
        bg, fg = colors["yellow"], text_on_yellow
    else:
        bg, fg = colors["red"], text_on_accent

    label = f"F:{score}/9"
    if signals_available < 9:
        label += f" ({signals_available}sig)"
    return badge(label, bg, fg, size)


def zscore_badge(
    z_score: float | None,
    zone: str | None,
    size: str = "small",
    is_approximate: bool = False,
) -> str:
    """
    Create a colored badge for Z-Score display.

    Args:
        z_score: Altman Z-Score value.
        zone: Zone classification.
        size: "small" or "normal".
        is_approximate: If True, prefix with ~ to indicate unreliable score.

    Returns:
        HTML badge string.
    """
    colors = _get_semantic_colors()
    text_on_accent = get_color("text_on_accent")
    text_on_yellow = get_color("text_on_yellow")

    if z_score is None or zone is None:
        return badge("Z:N/A", colors["gray"], text_on_accent, size)

    zone_styles = {
        "safe": (colors["green"], text_on_accent),
        "grey": (colors["yellow"], text_on_yellow),
        "gray": (colors["yellow"], text_on_yellow),
        "distress": (colors["red"], text_on_accent),
    }
    bg, fg = zone_styles.get(zone.lower(), (colors["gray"], text_on_accent))
    prefix = "~" if is_approximate else ""
    return badge(f"Z:{prefix}{z_score:.1f}", bg, fg, size)


def action_badge(action: str, size: str = "small") -> str:
    """
    Create a colored badge for decision actions.

    Args:
        action: Action type (buy/hold/sell/pass).
        size: "small" or "normal".

    Returns:
        HTML badge string.
    """
    colors = _get_semantic_colors()
    text_on_accent = get_color("text_on_accent")
    text_on_yellow = get_color("text_on_yellow")
    action_styles = {
        "buy": (colors["green"], text_on_accent, "BUY"),
        "hold": (colors["yellow"], text_on_yellow, "HOLD"),
        "sell": (colors["red"], text_on_accent, "SELL"),
        "pass": (colors["gray"], text_on_accent, "PASS"),
    }
    bg, fg, label = action_styles.get(action.lower(), (colors["gray"], text_on_accent, action.upper()))
    return badge(label, bg, fg, size)


def thesis_status_badge(status: str, size: str = "small") -> str:
    """
    Create a colored badge for thesis status.

    Args:
        status: Thesis status (draft/active/archived).
        size: "small" or "normal".

    Returns:
        HTML badge string.
    """
    colors = _get_semantic_colors()
    text_on_accent = get_color("text_on_accent")
    text_on_yellow = get_color("text_on_yellow")
    status_styles = {
        "draft": (colors["yellow"], text_on_yellow, "Draft"),
        "active": (colors["green"], text_on_accent, "Active"),
        "archived": (colors["gray"], text_on_accent, "Archived"),
    }
    bg, fg, label = status_styles.get(status.lower(), (colors["gray"], text_on_accent, status.title()))
    return badge(label, bg, fg, size)


# --- Winner/Award Icons ---

def trophy(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Trophy icon for winner highlighting."""
    if color is None:
        color = get_semantic_color("yellow")
    return _svg(
        '<path d="M6 9H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h2"/>'
        '<path d="M18 9h2a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2h-2"/>'
        '<path d="M4 22h16"/><path d="M10 22V8"/><path d="M14 22V8"/>'
        '<path d="M8 2h8a2 2 0 0 1 2 2v4.5a6 6 0 0 1-12 0V4a2 2 0 0 1 2-2z"/>',
        color, size
    )


def medal(color: str | None = None, size: int = DEFAULT_SIZE) -> str:
    """Medal icon for awards/achievements."""
    if color is None:
        color = get_semantic_color("yellow")
    return _svg(
        '<circle cx="12" cy="13" r="5"/>'
        '<path d="M8.21 13.89L7 23l5-3 5 3-1.21-9.11"/>',
        color, size, filled=False
    )
