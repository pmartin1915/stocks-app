"""Portfolio tab components."""

from dashboard.components.portfolio.holdings_tab import render_holdings_tab
from dashboard.components.portfolio.performance_tab import render_performance_tab
from dashboard.components.portfolio.historical_tab import render_historical_tab
from dashboard.components.portfolio.transactions_tab import (
    render_add_transaction_tab,
    render_transaction_history_tab,
)
from dashboard.components.portfolio.health_tab import render_health_tab

__all__ = [
    "render_holdings_tab",
    "render_performance_tab",
    "render_historical_tab",
    "render_add_transaction_tab",
    "render_transaction_history_tab",
    "render_health_tab",
]
