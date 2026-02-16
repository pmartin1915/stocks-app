"""
Portfolio database models for Asymmetric.

Defines the schema for:
- Transaction: Immutable buy/sell records for audit trail
- Holding: Current portfolio positions with cost basis
- PortfolioSnapshot: Daily portfolio value snapshots for P&L tracking
- TaxLot: Individual purchase lots for FIFO/LIFO/HIFO cost basis tracking
- LotDisposition: Links sell transactions to specific lots consumed
- CorporateAction: Stock splits, mergers, spinoffs
- CashFlow: Portfolio deposits/withdrawals for accurate return calculation
"""

from datetime import datetime, timezone
from decimal import Decimal
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
    quantity: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=6)  # Positive for buy/dividend, negative for sell
    price_per_share: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=4)  # Price at time of transaction
    fees: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)  # Brokerage fees, commissions

    # Computed fields (stored for efficiency)
    total_cost: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # For buys: quantity * price_per_share + fees
    total_proceeds: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # For sells: abs(quantity) * price - fees

    # Cost basis tracking (populated for sells)
    cost_basis_per_share: Optional[Decimal] = Field(default=None, max_digits=14, decimal_places=4)  # Weighted average basis at time of sale
    realized_gain: Optional[Decimal] = Field(default=None, max_digits=14, decimal_places=2)  # total_proceeds - (cost_basis_per_share * abs(quantity))

    # Notes
    notes: Optional[str] = Field(default=None, max_length=500)

    # Audit timestamp (immutable)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    stock: Optional["Stock"] = Relationship(back_populates="transactions")
    tax_lots: list["TaxLot"] = Relationship(
        back_populates="buy_transaction",
        sa_relationship_kwargs={"foreign_keys": "[TaxLot.buy_transaction_id]"},
    )
    lot_dispositions: list["LotDisposition"] = Relationship(
        back_populates="sell_transaction",
        sa_relationship_kwargs={"foreign_keys": "[LotDisposition.sell_transaction_id]"},
    )


class Holding(SQLModel, table=True):
    """
    Current portfolio position with real-time cost basis.

    Updated automatically when transactions are added.
    One holding per stock (unique constraint on stock_id).
    Soft-deleted: status='closed' when position fully sold (preserves history).
    """

    __tablename__ = "holdings"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True, unique=True)

    # Position
    quantity: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=6)  # Current shares held
    cost_basis_total: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # Total cost basis (weighted average)
    cost_basis_per_share: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=4)  # Average cost per share

    # Status (open/closed for soft-delete)
    status: str = Field(default="open", max_length=10)  # open, closed

    # Tracking
    first_purchase_date: Optional[datetime] = None
    last_transaction_date: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    stock: Optional["Stock"] = Relationship(back_populates="holding")
    tax_lots: list["TaxLot"] = Relationship(back_populates="holding")


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
    total_value: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # Sum of all holdings at market price
    total_cost_basis: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # Sum of all cost bases
    unrealized_pnl: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # total_value - total_cost_basis
    unrealized_pnl_percent: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=4)  # (unrealized_pnl / total_cost_basis) * 100

    # Realized P&L (cumulative)
    realized_pnl_ytd: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # Year-to-date realized gains/losses
    realized_pnl_total: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # All-time realized gains/losses

    # Cash flow tracking (for TWR calculation)
    cash_flow_on_date: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)  # Net cash in/out on this snapshot date

    # Holdings summary
    position_count: int  # Number of positions with quantity > 0

    # Score summary (at snapshot time)
    weighted_fscore: Optional[float] = None  # Position-weighted average F-Score
    weighted_zscore: Optional[float] = None  # Position-weighted average Z-Score

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaxLot(SQLModel, table=True):
    """
    Individual purchase lot for tax optimization.

    Each buy transaction creates a separate lot. When shares are sold,
    lots are consumed according to the chosen method (FIFO/LIFO/HIFO).
    Tracks wash sale adjustments per IRS rules.
    """

    __tablename__ = "tax_lots"

    id: Optional[int] = Field(default=None, primary_key=True)
    holding_id: int = Field(foreign_key="holdings.id", index=True)
    buy_transaction_id: int = Field(foreign_key="transactions.id", index=True)

    # Lot details
    purchase_date: datetime
    quantity_original: Decimal = Field(max_digits=14, decimal_places=6)  # Shares purchased
    quantity_remaining: Decimal = Field(max_digits=14, decimal_places=6)  # Shares still held
    cost_per_share: Decimal = Field(max_digits=14, decimal_places=4)  # Including fees
    fees: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)

    # Wash sale tracking (IRS 30-day rule)
    is_wash_sale: bool = Field(default=False)
    wash_sale_disallowed: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    wash_sale_adjusted_basis: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)

    # Status
    status: str = Field(default="open", max_length=10)  # open, partial, closed
    closed_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    holding: Optional["Holding"] = Relationship(back_populates="tax_lots")
    buy_transaction: Optional["Transaction"] = Relationship(
        back_populates="tax_lots",
        sa_relationship_kwargs={"foreign_keys": "[TaxLot.buy_transaction_id]"},
    )
    dispositions: list["LotDisposition"] = Relationship(back_populates="tax_lot")


class LotDisposition(SQLModel, table=True):
    """
    Links a sell transaction to specific lots consumed.

    Records the realized gain/loss and holding period classification
    for each lot consumed during a sale.
    """

    __tablename__ = "lot_dispositions"

    id: Optional[int] = Field(default=None, primary_key=True)
    tax_lot_id: int = Field(foreign_key="tax_lots.id", index=True)
    sell_transaction_id: int = Field(foreign_key="transactions.id", index=True)

    # Disposition details
    quantity_disposed: Decimal = Field(max_digits=14, decimal_places=6)
    proceeds_per_share: Decimal = Field(max_digits=14, decimal_places=4)
    cost_basis_per_share: Decimal = Field(max_digits=14, decimal_places=4)  # From the lot
    realized_gain: Decimal = Field(max_digits=14, decimal_places=2)

    # Tax classification
    is_long_term: bool = Field(default=False)  # Held > 365 days
    disposed_date: datetime

    # Wash sale (inherited from lot if applicable)
    is_wash_sale: bool = Field(default=False)
    wash_sale_loss_disallowed: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    tax_lot: Optional["TaxLot"] = Relationship(back_populates="dispositions")
    sell_transaction: Optional["Transaction"] = Relationship(
        back_populates="lot_dispositions",
        sa_relationship_kwargs={"foreign_keys": "[LotDisposition.sell_transaction_id]"},
    )


class CorporateAction(SQLModel, table=True):
    """
    Stock splits, mergers, spinoffs, and stock dividends.

    When applied, adjusts all open tax lots and the holding aggregate.
    Creates an audit trail of the adjustment.
    """

    __tablename__ = "corporate_actions"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)

    # Action details
    action_type: str = Field(max_length=20)  # split, reverse_split, merger, spinoff, stock_dividend
    ratio_numerator: int  # For 2:1 split: numerator=2
    ratio_denominator: int  # For 2:1 split: denominator=1
    effective_date: datetime
    notes: Optional[str] = Field(default=None, max_length=500)

    # Tracking
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lots_adjusted: int = Field(default=0)  # Number of lots modified

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CashFlow(SQLModel, table=True):
    """
    Portfolio deposits and withdrawals for accurate return calculation.

    Used by Time-Weighted Return (TWR) to separate investment returns
    from external cash movements.
    """

    __tablename__ = "cash_flows"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Flow details
    flow_type: str = Field(max_length=20)  # deposit, withdrawal
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    flow_date: datetime = Field(index=True)
    notes: Optional[str] = Field(default=None, max_length=500)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
