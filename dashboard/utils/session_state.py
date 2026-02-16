"""Centralized session state initialization.

Provides a single source of truth for all session state defaults
and initialization functions to reduce duplication across pages.
"""

import streamlit as st
from typing import Any


# Define all session state defaults by page
SESSION_DEFAULTS = {
    # Theme (shared across all pages)
    "theme": "light",

    # Watchlist page — confirm_remove is now per-ticker, managed dynamically

    # Compare page
    "compare_tickers": [],
    "compare_results": {},
    "compare_ai_result": None,

    # Decisions page
    "selected_decision_id": None,
    "selected_thesis_id": None,
    "show_decision_form": False,
    "show_thesis_form": False,
    "decision_action_filter": "all",
    "decision_ticker_filter": "",
    "thesis_status_filter": "all",
    "thesis_ticker_filter": "",
    "editing_thesis_id": None,

    # Portfolio page
    "pending_buy": None,
    "pending_sell": None,

    # Research page
    "research_ticker": "",
    "research_step": 1,
}


# Page-specific keys mapping
PAGE_KEYS = {
    "watchlist": ["theme"],
    "compare": ["theme", "compare_tickers", "compare_results", "compare_ai_result"],
    "decisions": [
        "theme",
        "selected_decision_id",
        "selected_thesis_id",
        "show_decision_form",
        "show_thesis_form",
        "decision_action_filter",
        "decision_ticker_filter",
        "thesis_status_filter",
        "thesis_ticker_filter",
        "editing_thesis_id",
    ],
    "portfolio": ["theme", "pending_buy", "pending_sell"],
    "research": ["theme", "research_ticker", "research_step"],
}


def init_session_state(keys: list[str] | None = None) -> None:
    """Initialize session state with defaults.

    Args:
        keys: Specific keys to initialize. If None, initializes all.
    """
    to_init = keys if keys else SESSION_DEFAULTS.keys()

    for key in to_init:
        if key not in st.session_state and key in SESSION_DEFAULTS:
            # Use a copy for mutable defaults (lists, dicts)
            default = SESSION_DEFAULTS[key]
            if isinstance(default, (list, dict)):
                st.session_state[key] = default.copy() if default else type(default)()
            else:
                st.session_state[key] = default


def init_page_state(page: str) -> None:
    """Initialize session state for a specific page.

    Args:
        page: Page name ('watchlist', 'compare', 'decisions', 'portfolio', 'research')
    """
    keys = PAGE_KEYS.get(page, ["theme"])
    init_session_state(keys)


def reset_page_state(page: str) -> None:
    """Reset session state for a specific page to defaults.

    Args:
        page: Page name to reset.
    """
    keys = PAGE_KEYS.get(page, [])
    for key in keys:
        if key in SESSION_DEFAULTS and key != "theme":
            default = SESSION_DEFAULTS[key]
            if isinstance(default, (list, dict)):
                st.session_state[key] = default.copy() if default else type(default)()
            else:
                st.session_state[key] = default


def get_state(key: str, default: Any = None) -> Any:
    """Get session state value with optional default.

    Args:
        key: Session state key.
        default: Default value if key not in session state.

    Returns:
        Session state value or default.
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Set session state value.

    Args:
        key: Session state key.
        value: Value to set.
    """
    st.session_state[key] = value
