"""
Database module for Asymmetric.

Provides SQLModel definitions and connection management for thesis/decision persistence.
"""

from asymmetric.db.database import get_engine, get_session, init_db, reset_engine
from asymmetric.db.models import Decision, ScreeningRun, Stock, StockScore, Thesis
from asymmetric.db.alert_models import Alert, AlertHistory  # noqa: F401 - register with mapper
from asymmetric.db.portfolio_models import Holding, PortfolioSnapshot, Transaction  # noqa: F401 - register with mapper

__all__ = [
    # Models
    "Stock",
    "StockScore",
    "Thesis",
    "Decision",
    "ScreeningRun",
    # Database
    "get_engine",
    "get_session",
    "init_db",
    "reset_engine",
]
