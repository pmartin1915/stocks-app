"""Research wizard tab components."""

from dashboard.components.research.wizard_steps import (
    render_step_indicator,
    render_research_step,
    render_thesis_step,
    render_decision_step,
)
from dashboard.components.research.outcomes_tab import render_review_outcomes_tab
from dashboard.components.research.analytics_tab import render_analytics_tab

__all__ = [
    "render_step_indicator",
    "render_research_step",
    "render_thesis_step",
    "render_decision_step",
    "render_review_outcomes_tab",
    "render_analytics_tab",
]
