"""
Alert database models for Asymmetric.

Defines the schema for:
- Alert: Alert configuration for watchlist stocks
- AlertHistory: Record of alert triggers for audit and review
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from asymmetric.db.models import Stock


class Alert(SQLModel, table=True):
    """
    Alert configuration for watchlist stocks.

    Supports various alert types:
    - fscore_above: F-Score rises above threshold (entry signal)
    - fscore_below: F-Score drops below threshold (warning)
    - zscore_zone: Z-Score zone changes (Safe->Grey, Grey->Distress, etc.)
    - zscore_above: Z-Score rises above threshold
    - zscore_below: Z-Score drops below threshold
    """

    __tablename__ = "alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)

    # Alert configuration
    alert_type: str = Field(max_length=30)  # fscore_above, fscore_below, zscore_zone, etc.
    threshold_value: Optional[float] = None  # Numeric threshold (F-Score 0-9, Z-Score float)
    threshold_zone: Optional[str] = Field(default=None, max_length=20)  # For zone alerts: Safe, Grey, Distress
    condition_json: Optional[str] = None  # For custom alerts: {"field": "...", "op": ">=", "value": ...}

    # Severity and messaging
    severity: str = Field(default="warning", max_length=20)  # info, warning, critical
    message_template: Optional[str] = Field(default=None, max_length=500)  # Custom message template

    # Status
    is_active: bool = Field(default=True)
    is_triggered: bool = Field(default=False)  # Current trigger state
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = Field(default=0)

    # Last known values (for comparison)
    last_checked_value: Optional[float] = None
    last_checked_zone: Optional[str] = Field(default=None, max_length=20)
    last_checked_at: Optional[datetime] = None

    # Notification settings
    notify_console: bool = Field(default=True)
    notify_log: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    stock: Optional["Stock"] = Relationship(back_populates="alerts")
    history: list["AlertHistory"] = Relationship(back_populates="alert")


class AlertHistory(SQLModel, table=True):
    """
    Record of alert triggers for audit and review.

    Each time an alert condition is met, a history record is created.
    Supports acknowledgment workflow for critical alerts.
    """

    __tablename__ = "alert_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(foreign_key="alerts.id", index=True)

    # Trigger details
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_value: Optional[float] = None  # Value before trigger
    current_value: Optional[float] = None  # Value at trigger
    previous_zone: Optional[str] = Field(default=None, max_length=20)  # For zone changes
    current_zone: Optional[str] = Field(default=None, max_length=20)  # For zone changes
    message: str = Field(max_length=500)  # Generated alert message

    # Acknowledgment workflow
    acknowledged: bool = Field(default=False)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = Field(default=None, max_length=100)  # User or "system"

    # Relationships
    alert: Optional[Alert] = Relationship(back_populates="history")
