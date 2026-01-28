"""
Portfolio database models for Asymmetric.

Defines the schema for:
- Transaction: Immutable buy/sell records for audit trail
- Holding: Current portfolio positions with cost basis
- PortfolioSnapshot: Daily portfolio value snapshots for P&L tracking
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from asymmetric.db.models import Stock


class Transaction(SQLModel, table=True):
    """
    Immutable transaction record for audit trail.

    Transactions are never modified or deleted once created.
    Supports buy, sell, dividend, and split transaction types.
    """

    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)

    # Transaction details
    transaction_type: str = Field(max_length=20)  # buy, sell, dividend, split
    transaction_date: datetime
    quantity: float  # Positive for buy/dividend, negative for sell
    price_per_share: float  # Price at time of transaction
    fees: float = Field(default=0.0)  # Brokerage fees, commissions

    # Computed fields (stored for efficiency)
    total_cost: float  # For buys: quantity * price_per_share + fees
    total_proceeds: float = Field(default=0.0)  # For sells: abs(quantity) * price - fees

    # Cost basis tracking (populated for sells)
    cost_basis_per_share: Optional[float] = None  # FIFO basis at time of sale
    realized_gain: Optional[float] = None  # total_proceeds - (cost_basis_per_share * abs(quantity))

    # Notes
    notes: Optional[str] = Field(default=None, max_length=500)

    # Audit timestamp (immutable)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    stock: Optional["Stock"] = Relationship(back_populates="transactions")


class Holding(SQLModel, table=True):
    """
    Current portfolio position with real-time cost basis.

    Updated automatically when transactions are added.
    One holding per stock (unique constraint on stock_id).
    """

    __tablename__ = "holdings"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True, unique=True)

    # Position
    quantity: float = Field(default=0.0)  # Current shares held
    cost_basis_total: float = Field(default=0.0)  # Total cost basis (FIFO)
    cost_basis_per_share: float = Field(default=0.0)  # Average cost per share

    # Tracking
    first_purchase_date: Optional[datetime] = None
    last_transaction_date: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    stock: Optional["Stock"] = Relationship(back_populates="holding")


class PortfolioSnapshot(SQLModel, table=True):
    """
    Daily portfolio value snapshot for P&L tracking.

    Captures portfolio state at a point in time for historical analysis
    and P&L charting.
    """

    __tablename__ = "portfolio_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_date: datetime = Field(index=True)

    # Portfolio totals
    total_value: float  # Sum of all holdings at market price
    total_cost_basis: float  # Sum of all cost bases
    unrealized_pnl: float  # total_value - total_cost_basis
    unrealized_pnl_percent: float = Field(default=0.0)  # (unrealized_pnl / total_cost_basis) * 100

    # Realized P&L (cumulative)
    realized_pnl_ytd: float = Field(default=0.0)  # Year-to-date realized gains/losses
    realized_pnl_total: float = Field(default=0.0)  # All-time realized gains/losses

    # Holdings summary
    position_count: int  # Number of positions with quantity > 0

    # Score summary (at snapshot time)
    weighted_fscore: Optional[float] = None  # Position-weighted average F-Score
    weighted_zscore: Optional[float] = None  # Position-weighted average Z-Score

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
