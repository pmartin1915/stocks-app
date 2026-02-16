"""Decisions components package.

Re-exports card/form components for backward compatibility,
plus tab-level render functions for the page.
"""

from dashboard.components.decisions.analytics_tab import render_analytics_tab
from dashboard.components.decisions.cards import (
    render_action_badge,
    render_bull_bear_columns,
    render_confidence_indicator,
    render_decision_card,
    render_decision_detail,
    render_decision_form,
    render_status_badge,
    render_thesis_card,
    render_thesis_detail,
    render_thesis_edit_form,
    render_thesis_form,
)
from dashboard.components.decisions.decisions_tab import render_decisions_tab
from dashboard.components.decisions.outcomes_tab import render_outcomes_tab
from dashboard.components.decisions.theses_tab import render_theses_tab

__all__ = [
    # Card/form components
    "render_action_badge",
    "render_bull_bear_columns",
    "render_confidence_indicator",
    "render_decision_card",
    "render_decision_detail",
    "render_decision_form",
    "render_status_badge",
    "render_thesis_card",
    "render_thesis_detail",
    "render_thesis_edit_form",
    "render_thesis_form",
    # Tab render functions
    "render_analytics_tab",
    "render_decisions_tab",
    "render_outcomes_tab",
    "render_theses_tab",
]
