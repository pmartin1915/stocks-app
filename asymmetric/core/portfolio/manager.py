"""
Portfolio management for transaction and holdings tracking.

Provides comprehensive portfolio management:
- Transaction recording (buy/sell) with tax lot creation
- Holdings tracking with weighted average cost basis
- Tax lot tracking (FIFO/LIFO/HIFO cost basis methods)
- P&L calculations (realized and unrealized)
- Portfolio-weighted score aggregation
- Corporate action handling (stock splits)
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

from sqlalchemy import func
from sqlmodel import select

from asymmetric.db.database import get_session, get_stock_by_ticker
from asymmetric.db.models import Stock, StockScore
from asymmetric.db.portfolio_models import (
    CashFlow,
    CorporateAction,
    Holding,
    LotDisposition,
    PortfolioSnapshot,
    TaxLot,
    Transaction,
)

# Import price data from core (no Streamlit dependency)
try:
    from asymmetric.core.data.market_data import (
        fetch_batch_prices,
        fetch_dividend_history,
    )

    PRICE_DATA_AVAILABLE = True
except ImportError:
    PRICE_DATA_AVAILABLE = False


def _to_decimal(value: Union[int, float, Decimal, str]) -> Decimal:
    """Convert a numeric value to Decimal safely."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_naive_utc(dt: datetime) -> datetime:
    """Convert a datetime to timezone-naive UTC.

    SQLite stores datetimes as naive strings (implicit UTC). This helper
    ensures consistent comparisons by stripping timezone info after
    converting to UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")


def _validate_ticker(ticker: str) -> str:
    """Validate and normalize a ticker symbol.

    Accepts 1-10 uppercase alphanumeric characters, dots, and hyphens.
    Raises ValueError for malformed tickers.
    """
    ticker = ticker.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Must be 1-10 characters: A-Z, 0-9, '.', '-'"
        )
    return ticker


@dataclass
class PortfolioSummary:
    """Overall portfolio summary."""

    total_cost_basis: float
    total_market_value: float  # Requires external price data
    unrealized_pnl: float
    unrealized_pnl_percent: Optional[float]  # None when total_cost_basis is 0
    realized_pnl_total: float
    realized_pnl_ytd: float
    position_count: int
    cash_invested: float  # Total cash put in (sum of all buys)
    cash_received: float  # Total cash taken out (sum of all sells)
    total_deposits: float = 0.0  # Total external deposits
    total_withdrawals: float = 0.0  # Total external withdrawals
    net_cash_flow: float = 0.0  # deposits - withdrawals
    total_dividends: float = 0.0  # Total dividend income received
    missing_prices: list[str] = None  # Tickers where price was unavailable (fell back to cost basis)

    def __post_init__(self):
        if self.missing_prices is None:
            self.missing_prices = []


@dataclass
class HoldingDetail:
    """Detailed holding information."""

    ticker: str
    company_name: str
    quantity: float
    cost_basis_total: float
    cost_basis_per_share: float
    first_purchase_date: datetime
    last_transaction_date: datetime
    # Score data (if available)
    fscore: Optional[int] = None
    zscore: Optional[float] = None
    zone: Optional[str] = None
    # Allocation
    allocation_percent: Optional[float] = None
    # Market data (requires price feed)
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None
    days_held: Optional[int] = None


@dataclass
class TransactionRecord:
    """Transaction record for display."""

    id: int
    ticker: str
    company_name: str
    transaction_type: str
    transaction_date: datetime
    quantity: float
    price_per_share: float
    fees: float
    total_cost: float
    total_proceeds: float
    realized_gain: Optional[float]
    notes: Optional[str]


@dataclass
class WeightedScores:
    """Portfolio-weighted scores."""

    weighted_fscore: float
    weighted_zscore: float
    holdings_with_scores: int
    holdings_without_scores: int
    safe_allocation: float  # % of portfolio in Safe zone
    grey_allocation: float
    distress_allocation: float


class PortfolioManager:
    """
    Manages portfolio transactions and holdings.

    Tracks holdings using WEIGHTED AVERAGE cost basis for the aggregate,
    while also maintaining individual tax lots for each purchase. This
    enables FIFO/LIFO/HIFO cost basis method selection at sell time.
    """

    def add_buy(
        self,
        ticker: str,
        quantity: Union[int, float, Decimal],
        price_per_share: Union[int, float, Decimal],
        transaction_date: Optional[datetime] = None,
        fees: Union[int, float, Decimal] = 0,
        notes: Optional[str] = None,
    ) -> Transaction:
        """
        Record a stock purchase and create a tax lot.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares purchased
            price_per_share: Purchase price per share
            transaction_date: Date of transaction (defaults to now)
            fees: Brokerage fees
            notes: Optional notes

        Returns:
            Created Transaction record
        """
        ticker = _validate_ticker(ticker)
        qty = _to_decimal(quantity)
        pps = _to_decimal(price_per_share)
        fee = _to_decimal(fees)

        if qty <= 0:
            raise ValueError("Quantity must be positive for buy transactions")
        if pps <= 0:
            raise ValueError("Price must be positive")

        with get_session() as session:
            # Get stock - must exist first (run 'asymmetric lookup TICKER' to add)
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                raise ValueError(
                    f"Stock {ticker.upper()} not found. "
                    f"Run 'asymmetric lookup {ticker.upper()}' first to add it to the database."
                )

            # Calculate total cost
            total_cost = (qty * pps) + fee

            # Create transaction (use timezone-aware datetime - SQLModel will handle storage)
            now_utc = datetime.now(timezone.utc)
            txn_date = transaction_date or now_utc
            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="buy",
                transaction_date=txn_date,
                quantity=qty,
                price_per_share=pps,
                fees=fee,
                total_cost=total_cost,
                total_proceeds=Decimal("0"),
                notes=notes,
            )
            session.add(transaction)

            # Update or create holding
            holding = session.exec(select(Holding).where(Holding.stock_id == stock.id)).first()

            if holding:
                # Reopen if previously closed
                if holding.status == "closed":
                    holding.status = "open"
                    holding.first_purchase_date = txn_date
                # Update existing holding
                new_quantity = holding.quantity + qty
                new_cost_basis = holding.cost_basis_total + total_cost
                holding.quantity = new_quantity
                holding.cost_basis_total = new_cost_basis
                holding.cost_basis_per_share = new_cost_basis / new_quantity if new_quantity > 0 else Decimal("0")
                holding.last_transaction_date = txn_date
                holding.updated_at = now_utc
            else:
                # Create new holding
                holding = Holding(
                    stock_id=stock.id,
                    quantity=qty,
                    cost_basis_total=total_cost,
                    cost_basis_per_share=pps + (fee / qty) if qty > 0 else Decimal("0"),
                    first_purchase_date=txn_date,
                    last_transaction_date=txn_date,
                )
                session.add(holding)

            session.flush()  # Get IDs for holding and transaction

            # Create tax lot for this purchase
            cost_per_share_with_fees = pps + (fee / qty) if qty > 0 else Decimal("0")
            lot = TaxLot(
                holding_id=holding.id,
                buy_transaction_id=transaction.id,
                purchase_date=txn_date,
                quantity_original=qty,
                quantity_remaining=qty,
                cost_per_share=cost_per_share_with_fees,
                fees=fee,
            )
            session.add(lot)

            session.flush()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def add_sell(
        self,
        ticker: str,
        quantity: Union[int, float, Decimal],
        price_per_share: Union[int, float, Decimal],
        transaction_date: Optional[datetime] = None,
        fees: Union[int, float, Decimal] = 0,
        notes: Optional[str] = None,
        cost_basis_method: str = "fifo",
    ) -> Transaction:
        """
        Record a stock sale with lot-level cost basis tracking.

        Consumes tax lots according to the chosen method and creates
        LotDisposition records linking the sale to specific lots.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares sold
            price_per_share: Sale price per share
            transaction_date: Date of transaction (defaults to now)
            fees: Brokerage fees
            notes: Optional notes
            cost_basis_method: How to select lots — 'fifo', 'lifo', 'hifo', or 'average'

        Returns:
            Created Transaction record with realized gain

        Raises:
            ValueError: If insufficient shares owned
        """
        ticker = _validate_ticker(ticker)
        qty = _to_decimal(quantity)
        pps = _to_decimal(price_per_share)
        fee = _to_decimal(fees)

        if qty <= 0:
            raise ValueError("Quantity must be positive for sell transactions")
        if pps <= 0:
            raise ValueError("Price must be positive")
        if cost_basis_method not in ("fifo", "lifo", "hifo", "average"):
            raise ValueError(f"Invalid cost_basis_method: {cost_basis_method}")

        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                raise ValueError(f"Stock not found: {ticker}")

            holding = session.exec(
                select(Holding).where(Holding.stock_id == stock.id, Holding.status == "open")
            ).first()
            if not holding or holding.quantity < qty:
                available = holding.quantity if holding else Decimal("0")
                raise ValueError(
                    f"Insufficient shares to sell. Have {available}, trying to sell {qty}"
                )

            now_utc = datetime.now(timezone.utc)
            txn_date = transaction_date or now_utc

            # Calculate gross proceeds and fee per share
            total_proceeds = (qty * pps) - fee
            fee_per_share = fee / qty if qty > 0 else Decimal("0")

            # Create transaction stub (realized_gain updated after lot consumption)
            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="sell",
                transaction_date=txn_date,
                quantity=-qty,  # Negative for sells
                price_per_share=pps,
                fees=fee,
                total_cost=Decimal("0"),
                total_proceeds=total_proceeds,
                notes=notes,
            )
            session.add(transaction)
            session.flush()  # Get transaction ID

            # Consume tax lots FIRST — returns dispositions and total cost consumed
            dispositions, lots_cost_total = self._consume_lots(
                session=session,
                holding=holding,
                sell_transaction=transaction,
                quantity_to_sell=qty,
                proceeds_per_share=pps,
                fee_per_share=fee_per_share,
                sell_date=txn_date,
                method=cost_basis_method,
            )

            # Calculate realized gain from actual lot costs (not weighted average)
            realized_gain = total_proceeds - lots_cost_total

            # Derive the effective cost basis per share from consumed lots
            effective_cost_per_share = lots_cost_total / qty if qty > 0 else Decimal("0")

            # Update transaction with lot-derived values
            transaction.realized_gain = realized_gain
            transaction.cost_basis_per_share = effective_cost_per_share

            # Update holding — subtract actual consumed lot cost
            new_quantity = holding.quantity - qty
            if new_quantity > 0:
                holding.quantity = new_quantity
                holding.cost_basis_total -= lots_cost_total
                # Recalculate per-share from remaining total
                holding.cost_basis_per_share = (
                    holding.cost_basis_total / new_quantity
                    if new_quantity > 0 else Decimal("0")
                )
                holding.last_transaction_date = txn_date
                holding.updated_at = now_utc
            else:
                # Soft-delete: mark as closed instead of deleting
                holding.quantity = Decimal("0")
                holding.cost_basis_total = Decimal("0")
                holding.cost_basis_per_share = Decimal("0")
                holding.status = "closed"
                holding.last_transaction_date = txn_date
                holding.updated_at = now_utc

            session.flush()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def _consume_lots(
        self,
        session,
        holding: Holding,
        sell_transaction: Transaction,
        quantity_to_sell: Decimal,
        proceeds_per_share: Decimal,
        fee_per_share: Decimal,
        sell_date: datetime,
        method: str,
    ) -> tuple[list[LotDisposition], Decimal]:
        """
        Consume tax lots for a sell transaction.

        Args:
            session: Active DB session
            holding: The holding being sold from
            sell_transaction: The sell Transaction record
            quantity_to_sell: Shares to sell
            proceeds_per_share: Sale price per share (gross, before fees)
            fee_per_share: Fee allocated per share (total_fees / quantity)
            sell_date: Date of sale
            method: Cost basis method (fifo, lifo, hifo, average)

        Returns:
            Tuple of (dispositions created, total cost basis consumed from lots)
        """
        # Fetch open lots ordered by method
        lot_query = (
            select(TaxLot)
            .where(TaxLot.holding_id == holding.id)
            .where(TaxLot.quantity_remaining > 0)
        )

        if method == "fifo":
            lot_query = lot_query.order_by(TaxLot.purchase_date.asc())
        elif method == "lifo":
            lot_query = lot_query.order_by(TaxLot.purchase_date.desc())
        elif method == "hifo":
            lot_query = lot_query.order_by(TaxLot.cost_per_share.desc())
        else:  # average — still consume lots but use avg cost
            lot_query = lot_query.order_by(TaxLot.purchase_date.asc())

        lots = list(session.exec(lot_query).all())
        remaining = quantity_to_sell
        dispositions = []
        lots_cost_total = Decimal("0")

        # Net proceeds per share (after fee allocation)
        net_proceeds_per_share = proceeds_per_share - fee_per_share

        for lot in lots:
            if remaining <= 0:
                break

            # How much to take from this lot
            take = min(lot.quantity_remaining, remaining)

            # Determine holding period (normalize to naive UTC for comparison)
            lot_date = _to_naive_utc(lot.purchase_date)
            sell_dt = _to_naive_utc(sell_date)
            is_long_term = (sell_dt - lot_date).days > 365

            # Calculate realized gain for this disposition (includes fee allocation)
            lot_cost = lot.cost_per_share
            disposition_gain = (net_proceeds_per_share - lot_cost) * take

            # Track total cost consumed from lots
            lots_cost_total += lot_cost * take

            disposition = LotDisposition(
                tax_lot_id=lot.id,
                sell_transaction_id=sell_transaction.id,
                quantity_disposed=take,
                proceeds_per_share=proceeds_per_share,
                cost_basis_per_share=lot_cost,
                realized_gain=disposition_gain,
                is_long_term=is_long_term,
                disposed_date=sell_date,
            )
            session.add(disposition)
            dispositions.append(disposition)

            # Update lot
            lot.quantity_remaining -= take
            if lot.quantity_remaining <= 0:
                lot.status = "closed"
                lot.closed_at = sell_date
            else:
                lot.status = "partial"

            remaining -= take

        return dispositions, lots_cost_total

    def refresh_market_prices(self, tickers: list[str]) -> dict[str, float]:
        """
        Fetch current market prices for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker -> current price (None if unavailable)
        """
        if not PRICE_DATA_AVAILABLE:
            return {ticker: None for ticker in tickers}

        if not tickers:
            return {}

        try:
            price_data = fetch_batch_prices(tuple(tickers))

            # Extract just the price field, handle errors gracefully
            prices = {}
            for ticker, data in price_data.items():
                if "error" in data:
                    prices[ticker] = None
                else:
                    prices[ticker] = data.get("price")

            return prices
        except Exception as e:
            # If API fails completely, return None for all tickers
            logger.warning(f"Failed to fetch prices: {e}")
            return {ticker: None for ticker in tickers}

    def get_holdings(
        self,
        sort_by: str = "value",
        include_market_data: bool = True,
        market_prices: Optional[Dict[str, float]] = None,
    ) -> list[HoldingDetail]:
        """
        Get all current holdings.

        Args:
            sort_by: Sort field (ticker, value, fscore, gainloss)
            include_market_data: Whether to fetch current prices and calculate P&L
            market_prices: Pre-fetched prices to avoid redundant API calls.
                If provided, these are used instead of fetching fresh prices.

        Returns:
            List of HoldingDetail
        """
        with get_session() as session:
            # Fetch holdings with stock data in a single JOIN query (avoids N+1)
            # Filter by status='open' (soft-delete support)
            statement = (
                select(Holding, Stock)
                .join(Stock, Holding.stock_id == Stock.id)
                .where(Holding.quantity > 0)
                .where(Holding.status == "open")
            )
            holding_stock_pairs = session.exec(statement).all()

            if not holding_stock_pairs:
                return []

            results = []
            total_cost_basis = float(sum(h.cost_basis_total for h, _ in holding_stock_pairs))

            # Use pre-fetched prices or fetch if needed
            if market_prices is None and include_market_data:
                tickers = [stock.ticker for _, stock in holding_stock_pairs]
                market_prices = self.refresh_market_prices(tickers)
            elif market_prices is None:
                market_prices = {}

            # Calculate total market value for allocation %
            total_market_value = 0.0
            if include_market_data:
                for holding, stock in holding_stock_pairs:
                    if market_prices.get(stock.ticker):
                        total_market_value += float(holding.quantity) * market_prices[stock.ticker]
                    else:
                        total_market_value += float(holding.cost_basis_total)

            # Use market value for allocation if available, otherwise cost basis
            allocation_base = total_market_value if include_market_data and total_market_value > 0 else total_cost_basis

            # Fetch all scores in one query (avoids N+1)
            stock_ids = [stock.id for _, stock in holding_stock_pairs]
            scores_statement = (
                select(StockScore)
                .where(StockScore.stock_id.in_(stock_ids))
                .order_by(StockScore.stock_id, StockScore.calculated_at.desc())
            )
            all_scores = session.exec(scores_statement).all()

            # Create a map of stock_id -> latest score
            scores_by_stock = {}
            for score in all_scores:
                if score.stock_id not in scores_by_stock:
                    scores_by_stock[score.stock_id] = score

            for holding, stock in holding_stock_pairs:
                # Get latest score from pre-fetched map
                latest_score = scores_by_stock.get(stock.id)

                # Convert Decimal → float for UI-layer dataclass
                h_qty = float(holding.quantity)
                h_cost_total = float(holding.cost_basis_total)
                h_cost_per = float(holding.cost_basis_per_share)

                # Calculate market data fields
                current_price = market_prices.get(stock.ticker) if include_market_data else None
                market_value = (
                    h_qty * current_price if current_price is not None else None
                )
                unrealized_pnl = (
                    market_value - h_cost_total if market_value is not None else None
                )
                unrealized_pnl_percent = (
                    (unrealized_pnl / h_cost_total * 100)
                    if unrealized_pnl is not None and h_cost_total > 0
                    else None
                )

                # Calculate days held (normalize to naive UTC)
                now_naive = _to_naive_utc(datetime.now(timezone.utc))
                if holding.first_purchase_date:
                    days_held = (now_naive - _to_naive_utc(holding.first_purchase_date)).days
                else:
                    days_held = 0

                # Calculate allocation percent based on market value if available
                value_for_allocation = market_value if market_value is not None else h_cost_total
                allocation_percent = (
                    (value_for_allocation / allocation_base * 100) if allocation_base > 0 else 0
                )

                detail = HoldingDetail(
                    ticker=stock.ticker,
                    company_name=stock.company_name,
                    quantity=h_qty,
                    cost_basis_total=h_cost_total,
                    cost_basis_per_share=h_cost_per,
                    first_purchase_date=holding.first_purchase_date,
                    last_transaction_date=holding.last_transaction_date,
                    fscore=latest_score.piotroski_score if latest_score else None,
                    zscore=latest_score.altman_z_score if latest_score else None,
                    zone=latest_score.altman_zone if latest_score else None,
                    allocation_percent=allocation_percent,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent,
                    days_held=days_held,
                )
                results.append(detail)

            # Sort results
            if sort_by == "value":
                # Sort by market value if available, otherwise cost basis
                results.sort(
                    key=lambda x: x.market_value if x.market_value is not None else x.cost_basis_total,
                    reverse=True,
                )
            elif sort_by == "gainloss":
                # Sort by unrealized P&L percent
                results.sort(
                    key=lambda x: x.unrealized_pnl_percent if x.unrealized_pnl_percent is not None else -float('inf'),
                    reverse=True,
                )
            elif sort_by == "fscore":
                results.sort(key=lambda x: (x.fscore or 0), reverse=True)
            elif sort_by == "ticker":
                results.sort(key=lambda x: x.ticker)

            return results

    def get_holding(self, ticker: str) -> Optional[HoldingDetail]:
        """
        Get holding detail for a specific ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            HoldingDetail or None if not held
        """
        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                return None

            holding = session.exec(
                select(Holding).where(
                    Holding.stock_id == stock.id,
                    Holding.quantity > 0,
                    Holding.status == "open",
                )
            ).first()
            if not holding:
                return None

            # Convert Decimal → float for UI
            h_qty = float(holding.quantity)
            h_cost_total = float(holding.cost_basis_total)
            h_cost_per = float(holding.cost_basis_per_share)

            # Fetch price for just this ticker
            market_prices = self.refresh_market_prices([stock.ticker])
            current_price = market_prices.get(stock.ticker)
            market_value = h_qty * current_price if current_price else None
            unrealized_pnl = market_value - h_cost_total if market_value else None
            unrealized_pnl_percent = (
                (unrealized_pnl / h_cost_total * 100)
                if unrealized_pnl is not None and h_cost_total > 0
                else None
            )

            # Get latest score
            latest_score = session.exec(
                select(StockScore)
                .where(StockScore.stock_id == stock.id)
                .order_by(StockScore.calculated_at.desc())
            ).first()

            # Days held (normalize to naive UTC)
            now_naive = _to_naive_utc(datetime.now(timezone.utc))
            days_held = (
                (now_naive - _to_naive_utc(holding.first_purchase_date)).days
                if holding.first_purchase_date else 0
            )

            return HoldingDetail(
                ticker=stock.ticker,
                company_name=stock.company_name,
                quantity=h_qty,
                cost_basis_total=h_cost_total,
                cost_basis_per_share=h_cost_per,
                first_purchase_date=holding.first_purchase_date,
                last_transaction_date=holding.last_transaction_date,
                fscore=latest_score.piotroski_score if latest_score else None,
                zscore=latest_score.altman_z_score if latest_score else None,
                zone=latest_score.altman_zone if latest_score else None,
                allocation_percent=None,  # Single holding can't calculate portfolio allocation
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                days_held=days_held,
            )

    def get_portfolio_summary(
        self,
        include_market_data: bool = True,
        market_prices: Optional[Dict[str, float]] = None,
    ) -> PortfolioSummary:
        """
        Get overall portfolio summary.

        Args:
            include_market_data: Whether to fetch current prices and calculate unrealized P&L
            market_prices: Pre-fetched prices to avoid redundant API calls.
                If provided, these are used instead of fetching fresh prices.

        Returns:
            PortfolioSummary with totals and P&L
        """
        with get_session() as session:
            # Get all holdings with stock data in a single JOIN query (avoids N+1)
            statement = (
                select(Holding, Stock)
                .join(Stock, Holding.stock_id == Stock.id)
                .where(Holding.quantity > 0)
                .where(Holding.status == "open")
            )
            holding_stock_pairs = session.exec(statement).all()

            total_cost_basis = float(sum(h.cost_basis_total for h, _ in holding_stock_pairs))
            position_count = len(holding_stock_pairs)

            # Calculate market value if requested
            total_market_value = total_cost_basis
            _missing_prices = []
            if include_market_data and holding_stock_pairs:
                if market_prices is None:
                    tickers = [stock.ticker for _, stock in holding_stock_pairs]
                    market_prices = self.refresh_market_prices(tickers)

                total_market_value = 0.0
                for holding, stock in holding_stock_pairs:
                    if market_prices.get(stock.ticker):
                        total_market_value += float(holding.quantity) * market_prices[stock.ticker]
                    else:
                        # Fallback to cost basis if price unavailable
                        total_market_value += float(holding.cost_basis_total)
                        _missing_prices.append(stock.ticker)

            # Calculate unrealized P&L
            unrealized_pnl = total_market_value - total_cost_basis
            unrealized_pnl_percent = (
                (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else None
            )

            # Calculate realized P&L from all sell transactions
            sell_transactions = session.exec(
                select(Transaction).where(Transaction.transaction_type == "sell")
            ).all()

            realized_pnl_total = float(sum(t.realized_gain or Decimal("0") for t in sell_transactions))

            # YTD realized P&L
            current_year = datetime.now(timezone.utc).year
            ytd_sells = [
                t
                for t in sell_transactions
                if t.transaction_date and t.transaction_date.year == current_year
            ]
            realized_pnl_ytd = float(sum(t.realized_gain or Decimal("0") for t in ytd_sells))

            # Cash flow calculations
            buy_transactions = session.exec(
                select(Transaction).where(Transaction.transaction_type == "buy")
            ).all()
            cash_invested = float(sum(t.total_cost for t in buy_transactions))
            cash_received = float(sum(t.total_proceeds for t in sell_transactions))

            # Dividend income total
            dividend_transactions = session.exec(
                select(Transaction).where(Transaction.transaction_type == "dividend")
            ).all()
            total_dividends = float(sum(t.total_proceeds for t in dividend_transactions))

            # External cash flow totals (deposits/withdrawals)
            all_flows = session.exec(select(CashFlow)).all()
            total_deposits = float(sum(
                cf.amount for cf in all_flows if cf.flow_type == "deposit"
            ))
            total_withdrawals = float(sum(
                cf.amount for cf in all_flows if cf.flow_type == "withdrawal"
            ))

            return PortfolioSummary(
                total_cost_basis=total_cost_basis,
                total_market_value=total_market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                realized_pnl_total=realized_pnl_total,
                realized_pnl_ytd=realized_pnl_ytd,
                position_count=position_count,
                cash_invested=cash_invested,
                cash_received=cash_received,
                total_deposits=total_deposits,
                total_withdrawals=total_withdrawals,
                net_cash_flow=total_deposits - total_withdrawals,
                total_dividends=total_dividends,
                missing_prices=_missing_prices,
            )

    def get_transaction_history(
        self, ticker: Optional[str] = None, limit: int = 50
    ) -> list[TransactionRecord]:
        """
        Get transaction history.

        Args:
            ticker: Optional ticker to filter by
            limit: Maximum results

        Returns:
            List of TransactionRecord, newest first
        """
        with get_session() as session:
            # Join with Stock to get stock data in single query (avoids N+1)
            stmt = (
                select(Transaction, Stock)
                .join(Stock, Transaction.stock_id == Stock.id)
            )

            if ticker:
                stmt = stmt.where(Stock.ticker == ticker.upper())

            transaction_stock_pairs = session.exec(
                stmt.order_by(Transaction.transaction_date.desc()).limit(limit)
            ).all()

            results = []
            for t, stock in transaction_stock_pairs:
                results.append(
                    TransactionRecord(
                        id=t.id,
                        ticker=stock.ticker,
                        company_name=stock.company_name,
                        transaction_type=t.transaction_type,
                        transaction_date=t.transaction_date,
                        quantity=float(abs(t.quantity)),
                        price_per_share=float(t.price_per_share),
                        fees=float(t.fees),
                        total_cost=float(t.total_cost),
                        total_proceeds=float(t.total_proceeds),
                        realized_gain=float(t.realized_gain) if t.realized_gain is not None else None,
                        notes=t.notes,
                    )
                )

            return results

    def get_realized_pnl_by_ticker(self) -> dict[str, float]:
        """
        Get total realized P&L grouped by ticker in a single query.

        Returns:
            Dict mapping ticker -> total realized gain
        """
        with get_session() as session:
            stmt = (
                select(Stock.ticker, func.sum(Transaction.realized_gain))
                .join(Stock, Transaction.stock_id == Stock.id)
                .where(Transaction.transaction_type == "sell")
                .where(Transaction.realized_gain.isnot(None))
                .group_by(Stock.ticker)
            )
            results = session.exec(stmt).all()
            return {ticker: float(gain or 0.0) for ticker, gain in results}

    def add_cash_flow(
        self,
        amount: Union[int, float, Decimal],
        flow_type: str,
        flow_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> CashFlow:
        """Record a portfolio deposit or withdrawal.

        Args:
            amount: Cash amount (must be positive)
            flow_type: "deposit" or "withdrawal"
            flow_date: Date of cash flow (defaults to now)
            notes: Optional notes

        Returns:
            Created CashFlow record
        """
        if flow_type not in ("deposit", "withdrawal"):
            raise ValueError(f"Invalid flow_type: {flow_type!r}. Must be 'deposit' or 'withdrawal'")

        amt = _to_decimal(amount)
        if amt <= 0:
            raise ValueError("Amount must be positive")

        now_utc = datetime.now(timezone.utc)
        cf_date = _to_naive_utc(flow_date) if flow_date else now_utc

        with get_session() as session:
            cash_flow = CashFlow(
                flow_type=flow_type,
                amount=amt,
                flow_date=cf_date,
                notes=notes,
            )
            session.add(cash_flow)
            session.flush()
            session.refresh(cash_flow)
            session.expunge(cash_flow)
            return cash_flow

    def get_cash_flows(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[CashFlow]:
        """Retrieve cash flow records within date range.

        Args:
            start_date: Filter flows >= this date
            end_date: Filter flows <= this date

        Returns:
            List of CashFlow records ordered by flow_date ascending.
        """
        with get_session() as session:
            query = select(CashFlow)

            if start_date:
                query = query.where(CashFlow.flow_date >= start_date)
            if end_date:
                query = query.where(CashFlow.flow_date <= end_date)

            query = query.order_by(CashFlow.flow_date.asc())
            results = session.exec(query).all()

            for cf in results:
                session.expunge(cf)
            return list(results)

    def get_total_cash_flows(self) -> dict:
        """Get aggregate cash flow totals.

        Returns:
            Dict with total_deposits, total_withdrawals, net_cash_flow (all float).
        """
        with get_session() as session:
            all_flows = session.exec(select(CashFlow)).all()

            total_deposits = float(sum(
                cf.amount for cf in all_flows if cf.flow_type == "deposit"
            ))
            total_withdrawals = float(sum(
                cf.amount for cf in all_flows if cf.flow_type == "withdrawal"
            ))

            return {
                "total_deposits": total_deposits,
                "total_withdrawals": total_withdrawals,
                "net_cash_flow": total_deposits - total_withdrawals,
            }

    def add_dividend(
        self,
        ticker: str,
        total_amount: Union[int, float, Decimal],
        pay_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> Transaction:
        """Record a dividend payment received.

        Creates a Transaction with type "dividend". Does NOT affect
        holding quantity or cost basis — dividends are income, not
        additional shares.

        Args:
            ticker: Stock ticker symbol
            total_amount: Total dividend amount received
            pay_date: Date dividend was paid (defaults to now)
            notes: Optional notes

        Returns:
            Created Transaction record
        """
        ticker = _validate_ticker(ticker)
        amt = _to_decimal(total_amount)
        if amt <= 0:
            raise ValueError("Dividend amount must be positive")

        now_utc = datetime.now(timezone.utc)
        div_date = _to_naive_utc(pay_date) if pay_date else now_utc

        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                raise ValueError(
                    f"Stock {ticker} not found. "
                    f"Run 'asymmetric lookup {ticker}' first to add it to the database."
                )

            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="dividend",
                transaction_date=div_date,
                quantity=Decimal("0"),
                price_per_share=Decimal("0"),
                fees=Decimal("0"),
                total_cost=Decimal("0"),
                total_proceeds=amt,
                notes=notes,
            )
            session.add(transaction)
            session.flush()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def sync_dividends(
        self,
        ticker: Optional[str] = None,
    ) -> dict:
        """Sync dividend history from yfinance for held tickers.

        For each ticker, fetches dividend payments from yfinance and records
        any new ones that aren't already in the database.

        Args:
            ticker: Specific ticker to sync. If None, syncs all open holdings.

        Returns:
            Dict with synced (count), tickers (list), errors (list).
        """
        if not PRICE_DATA_AVAILABLE:
            return {"synced": 0, "tickers": [], "errors": ["yfinance not available"]}

        synced = 0
        synced_tickers = []
        errors = []

        # Determine which tickers to sync
        if ticker:
            tickers_to_sync = [_validate_ticker(ticker)]
        else:
            holdings = self.get_holdings(include_market_data=False)
            tickers_to_sync = [h.ticker for h in holdings]

        for t in tickers_to_sync:
            try:
                # Find last recorded dividend date for this ticker
                last_div_date = None
                with get_session() as session:
                    stock = get_stock_by_ticker(session, t)
                    if not stock:
                        errors.append(f"{t}: stock not found")
                        continue

                    # Get the holding to know share quantity at each dividend date
                    holding = session.exec(
                        select(Holding).where(
                            Holding.stock_id == stock.id,
                            Holding.status == "open",
                        )
                    ).first()
                    if not holding:
                        errors.append(f"{t}: no open holding")
                        continue

                    shares = float(holding.quantity)

                    last_div = session.exec(
                        select(Transaction)
                        .where(
                            Transaction.stock_id == stock.id,
                            Transaction.transaction_type == "dividend",
                        )
                        .order_by(Transaction.transaction_date.desc())
                        .limit(1)
                    ).first()
                    if last_div:
                        last_div_date = last_div.transaction_date.strftime("%Y-%m-%d")

                # Fetch from yfinance (outside session)
                div_history = fetch_dividend_history(t, start_date=last_div_date)

                for div in div_history:
                    total_amount = div["amount_per_share"] * shares
                    pay_date = datetime.strptime(div["date"], "%Y-%m-%d")
                    self.add_dividend(
                        ticker=t,
                        total_amount=total_amount,
                        pay_date=pay_date,
                        notes=f"Auto-synced: ${div['amount_per_share']:.4f}/share",
                    )
                    synced += 1

                if div_history:
                    synced_tickers.append(t)

            except (ValueError, Exception) as e:
                errors.append(f"{t}: {e}")

        return {"synced": synced, "tickers": synced_tickers, "errors": errors}

    def get_weighted_scores(self, holdings: Optional[list] = None) -> WeightedScores:
        """
        Calculate portfolio-weighted F-Score and Z-Score.

        Weights each holding by its cost basis allocation.

        Args:
            holdings: Pre-fetched holdings to avoid redundant price fetches.
                If None, will call get_holdings() internally.

        Returns:
            WeightedScores with portfolio-level metrics
        """
        if holdings is None:
            holdings = self.get_holdings()

        if not holdings:
            return WeightedScores(
                weighted_fscore=0.0,
                weighted_zscore=0.0,
                holdings_with_scores=0,
                holdings_without_scores=0,
                safe_allocation=0.0,
                grey_allocation=0.0,
                distress_allocation=0.0,
            )

        total_value = sum(h.cost_basis_total for h in holdings)

        weighted_fscore = 0.0
        weighted_zscore = 0.0
        with_scores = 0
        without_scores = 0
        safe_value = 0.0
        grey_value = 0.0
        distress_value = 0.0

        for h in holdings:
            weight = h.cost_basis_total / total_value if total_value > 0 else 0

            if h.fscore is not None and h.zscore is not None:
                weighted_fscore += h.fscore * weight
                weighted_zscore += h.zscore * weight
                with_scores += 1

                # Zone allocation
                if h.zone == "Safe":
                    safe_value += h.cost_basis_total
                elif h.zone == "Grey":
                    grey_value += h.cost_basis_total
                elif h.zone == "Distress":
                    distress_value += h.cost_basis_total
            else:
                without_scores += 1

        return WeightedScores(
            weighted_fscore=round(weighted_fscore, 2),
            weighted_zscore=round(weighted_zscore, 2),
            holdings_with_scores=with_scores,
            holdings_without_scores=without_scores,
            safe_allocation=round((safe_value / total_value * 100) if total_value > 0 else 0, 1),
            grey_allocation=round((grey_value / total_value * 100) if total_value > 0 else 0, 1),
            distress_allocation=round((distress_value / total_value * 100) if total_value > 0 else 0, 1),
        )

    def take_snapshot(self, auto: bool = False) -> PortfolioSnapshot:
        """
        Take a snapshot of current portfolio state with current market prices.

        Args:
            auto: Whether this is an automated snapshot (for tracking purposes)

        Returns:
            Created PortfolioSnapshot
        """
        # Fetch prices once, share across summary + weighted scores (avoids redundant API calls)
        _tickers_holdings = self.get_holdings(include_market_data=False)
        _tickers = [h.ticker for h in _tickers_holdings]
        prices = self.refresh_market_prices(_tickers) if _tickers else {}
        summary = self.get_portfolio_summary(include_market_data=True, market_prices=prices)
        holdings = self.get_holdings(market_prices=prices)
        weighted = self.get_weighted_scores(holdings=holdings)

        with get_session() as session:
            # Use timezone-aware datetime - SQLModel will handle storage
            snapshot_date = datetime.now(timezone.utc)
            snapshot = PortfolioSnapshot(
                snapshot_date=snapshot_date,
                total_value=_to_decimal(summary.total_market_value),
                total_cost_basis=_to_decimal(summary.total_cost_basis),
                unrealized_pnl=_to_decimal(summary.unrealized_pnl),
                unrealized_pnl_percent=_to_decimal(summary.unrealized_pnl_percent or 0.0),
                realized_pnl_ytd=_to_decimal(summary.realized_pnl_ytd),
                realized_pnl_total=_to_decimal(summary.realized_pnl_total),
                position_count=summary.position_count,
                weighted_fscore=weighted.weighted_fscore,
                weighted_zscore=weighted.weighted_zscore,
            )

            # Populate cash_flow_on_date from CashFlow records for this date
            day_start = _to_naive_utc(snapshot_date).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999999)
            day_flows = session.exec(
                select(CashFlow).where(
                    CashFlow.flow_date >= day_start,
                    CashFlow.flow_date <= day_end,
                )
            ).all()
            net_flow = sum(
                cf.amount if cf.flow_type == "deposit" else -cf.amount
                for cf in day_flows
            ) if day_flows else Decimal("0")
            snapshot.cash_flow_on_date = _to_decimal(net_flow)

            session.add(snapshot)
            session.flush()
            session.refresh(snapshot)
            session.expunge(snapshot)
            return snapshot

    def get_snapshots(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[PortfolioSnapshot]:
        """
        Retrieve portfolio snapshots within date range.

        Args:
            start_date: Filter snapshots >= this date (default: all from beginning)
            end_date: Filter snapshots <= this date (default: now)
            limit: Maximum number of snapshots to return (default: no limit)

        Returns:
            List of snapshots ordered by snapshot_date ascending.
            Returns empty list if no snapshots found.

        Example:
            # Get last 7 days of snapshots
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            snapshots = manager.get_snapshots(start_date=week_ago)

            # Get first 10 snapshots ever
            snapshots = manager.get_snapshots(limit=10)
        """
        with get_session() as session:
            # Build query with optional filters
            query = select(PortfolioSnapshot)

            if start_date:
                query = query.where(PortfolioSnapshot.snapshot_date >= start_date)

            if end_date:
                query = query.where(PortfolioSnapshot.snapshot_date <= end_date)

            # Order ascending (oldest to newest)
            query = query.order_by(PortfolioSnapshot.snapshot_date.asc())

            if limit:
                query = query.limit(limit)

            results = session.exec(query).all()

            # Detach from session to avoid lazy-loading issues
            # Note: SQLite stores datetimes as strings without timezone info,
            # so they come back as timezone-naive. This is expected - all times are UTC.
            for snapshot in results:
                session.expunge(snapshot)

            return list(results)

    def calculate_twr(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        snapshots: Optional[List[PortfolioSnapshot]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Calculate Time-Weighted Return from snapshots and cash flows.

        TWR separates investment performance from the timing of cash flows
        (deposits/withdrawals). Each sub-period between cash flow events
        is chain-linked to produce an overall return.

        Args:
            start_date: Start of calculation window (default: 1 year ago)
            end_date: End of calculation window (default: now)
            snapshots: Pre-fetched snapshots (avoids redundant DB query)

        Returns:
            Dict with twr, twr_annualized, simple_return, periods, start_date,
            end_date. Returns None if insufficient data (<2 snapshots).
        """
        if snapshots is None:
            if start_date is None:
                start_date = _to_naive_utc(datetime.now(timezone.utc)) - timedelta(days=365)
            snapshots = self.get_snapshots(start_date=start_date, end_date=end_date)

        if not snapshots or len(snapshots) < 2:
            return None

        values = [float(s.total_value) for s in snapshots]
        cash_flows = [float(s.cash_flow_on_date) for s in snapshots]
        dates = [s.snapshot_date for s in snapshots]

        # Chain-link sub-period returns
        cumulative = 1.0
        periods = 0
        for i in range(1, len(values)):
            v_start = values[i - 1]
            v_end = values[i]
            cf = cash_flows[i]  # Cash flow on the ending snapshot date

            # Skip period if start value is zero (e.g., initial deposit)
            if v_start == 0:
                continue

            # Sub-period return: (V_end - CF) / V_start - 1
            sub_return = (v_end - cf) / v_start - 1
            cumulative *= (1 + sub_return)
            periods += 1

        twr = (cumulative - 1) * 100  # As percentage

        # Simple return for comparison
        simple_return = 0.0
        if values[0] != 0:
            simple_return = ((values[-1] - values[0]) / values[0]) * 100

        # Annualize if tracking period > 365 days
        total_days = (dates[-1] - dates[0]).days
        twr_annualized = None
        if total_days > 365 and cumulative > 0:
            twr_annualized = ((cumulative ** (365.0 / total_days)) - 1) * 100

        return {
            "twr": twr,
            "twr_annualized": twr_annualized,
            "simple_return": simple_return,
            "periods": periods,
            "start_date": dates[0],
            "end_date": dates[-1],
        }

    def get_performance_stats(
        self,
        snapshots: Optional[List[PortfolioSnapshot]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate performance statistics from snapshots.

        Args:
            snapshots: List of snapshots (default: fetch last 365 days)

        Returns:
            Dictionary with performance metrics, or None if insufficient data:
            {
                "total_return": float,           # (latest - first) / first * 100
                "total_return_dollars": float,   # latest - first
                "peak_value": float,             # Maximum portfolio value
                "current_drawdown": float,       # (current - peak) / peak * 100
                "max_drawdown": float,           # Worst historical drawdown %
                "avg_daily_return": float,       # Mean % change per snapshot
                "volatility": float,             # Std dev of daily returns
                "best_day": Dict,                # {"date": datetime, "return": float}
                "worst_day": Dict,               # {"date": datetime, "return": float}
                "days_tracked": int              # Number of snapshots
            }

        Note:
            total_return is a simple return that does NOT account for external
            cash flows. Use twr (Time-Weighted Return) for cash-flow-adjusted
            performance measurement.

        Example:
            stats = manager.get_performance_stats()
            print(f"Total Return: {stats['total_return']:.2f}%")
            print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        """
        # Fetch snapshots if not provided
        if snapshots is None:
            # Use timezone-naive datetime to match SQLite storage (implicit UTC)
            one_year_ago = _to_naive_utc(datetime.now(timezone.utc)) - timedelta(days=365)
            snapshots = self.get_snapshots(start_date=one_year_ago)

        # Need at least 2 snapshots to calculate performance
        if not snapshots or len(snapshots) < 2:
            return None

        # Extract values for calculations (convert Decimal → float for stats math)
        values = [float(s.total_value) for s in snapshots]
        dates = [s.snapshot_date for s in snapshots]

        first_value = values[0]
        latest_value = values[-1]

        # Calculate snapshot-to-snapshot returns
        daily_returns = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:  # Avoid division by zero
                daily_return = ((values[i] - values[i - 1]) / values[i - 1]) * 100
                daily_returns.append({
                    "date": dates[i],
                    "return": daily_return
                })

        # Total return
        total_return = 0.0
        total_return_dollars = 0.0
        if first_value != 0:
            total_return = ((latest_value - first_value) / first_value) * 100
            total_return_dollars = latest_value - first_value

        # Peak value and drawdown calculations
        peak_value = max(values)
        current_drawdown = 0.0
        if peak_value != 0:
            current_drawdown = ((latest_value - peak_value) / peak_value) * 100

        # Max drawdown (worst peak-to-trough decline)
        max_drawdown = 0.0
        running_peak = values[0]
        for value in values:
            if value > running_peak:
                running_peak = value
            if running_peak != 0:
                drawdown = ((value - running_peak) / running_peak) * 100
                if drawdown < max_drawdown:
                    max_drawdown = drawdown

        # Average daily return
        avg_daily_return = 0.0
        if daily_returns:
            avg_daily_return = sum(r["return"] for r in daily_returns) / len(daily_returns)

        # Volatility (standard deviation of daily returns)
        volatility = 0.0
        if len(daily_returns) > 1:
            mean_return = avg_daily_return
            variance = sum((r["return"] - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            volatility = variance ** 0.5

        # Best and worst days
        best_day = max(daily_returns, key=lambda x: x["return"]) if daily_returns else None
        worst_day = min(daily_returns, key=lambda x: x["return"]) if daily_returns else None

        # Calculate TWR (cash-flow-adjusted return)
        twr_result = self.calculate_twr(snapshots=snapshots)

        return {
            "total_return": total_return,
            "total_return_dollars": total_return_dollars,
            "peak_value": peak_value,
            "current_drawdown": current_drawdown,
            "max_drawdown": max_drawdown,
            "avg_daily_return": avg_daily_return,
            "volatility": volatility,
            "best_day": best_day,
            "worst_day": worst_day,
            "days_tracked": len(snapshots),
            "twr": twr_result["twr"] if twr_result else None,
            "twr_annualized": twr_result["twr_annualized"] if twr_result else None,
        }
