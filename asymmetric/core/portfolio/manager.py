"""
Portfolio management for transaction and holdings tracking.

Provides comprehensive portfolio management:
- Transaction recording (buy/sell)
- Holdings tracking with FIFO cost basis
- P&L calculations (realized and unrealized)
- Portfolio-weighted score aggregation
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select

from asymmetric.db.database import get_or_create_stock, get_session, get_stock_by_ticker
from asymmetric.db.models import Stock, StockScore
from asymmetric.db.portfolio_models import Holding, PortfolioSnapshot, Transaction


@dataclass
class PortfolioSummary:
    """Overall portfolio summary."""

    total_cost_basis: float
    total_market_value: float  # Requires external price data
    unrealized_pnl: float
    unrealized_pnl_percent: float
    realized_pnl_total: float
    realized_pnl_ytd: float
    position_count: int
    cash_invested: float  # Total cash put in (sum of all buys)
    cash_received: float  # Total cash taken out (sum of all sells)


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

    Uses FIFO (First In, First Out) method for cost basis tracking.
    """

    def add_buy(
        self,
        ticker: str,
        quantity: float,
        price_per_share: float,
        transaction_date: Optional[datetime] = None,
        fees: float = 0.0,
        notes: Optional[str] = None,
    ) -> Transaction:
        """
        Record a stock purchase.

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
        if quantity <= 0:
            raise ValueError("Quantity must be positive for buy transactions")
        if price_per_share <= 0:
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
            total_cost = (quantity * price_per_share) + fees

            # Create transaction
            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="buy",
                transaction_date=transaction_date or datetime.now(timezone.utc),
                quantity=quantity,
                price_per_share=price_per_share,
                fees=fees,
                total_cost=total_cost,
                total_proceeds=0.0,
                notes=notes,
            )
            session.add(transaction)

            # Update or create holding
            holding = session.exec(select(Holding).where(Holding.stock_id == stock.id)).first()

            if holding:
                # Update existing holding
                new_quantity = holding.quantity + quantity
                new_cost_basis = holding.cost_basis_total + total_cost
                holding.quantity = new_quantity
                holding.cost_basis_total = new_cost_basis
                holding.cost_basis_per_share = new_cost_basis / new_quantity if new_quantity > 0 else 0
                holding.last_transaction_date = transaction.transaction_date
                holding.updated_at = datetime.now(timezone.utc)
            else:
                # Create new holding
                holding = Holding(
                    stock_id=stock.id,
                    quantity=quantity,
                    cost_basis_total=total_cost,
                    cost_basis_per_share=price_per_share + (fees / quantity) if quantity > 0 else 0,
                    first_purchase_date=transaction.transaction_date,
                    last_transaction_date=transaction.transaction_date,
                )
                session.add(holding)

            session.commit()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def add_sell(
        self,
        ticker: str,
        quantity: float,
        price_per_share: float,
        transaction_date: Optional[datetime] = None,
        fees: float = 0.0,
        notes: Optional[str] = None,
    ) -> Transaction:
        """
        Record a stock sale with FIFO cost basis.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares sold
            price_per_share: Sale price per share
            transaction_date: Date of transaction (defaults to now)
            fees: Brokerage fees
            notes: Optional notes

        Returns:
            Created Transaction record with realized gain

        Raises:
            ValueError: If insufficient shares owned
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive for sell transactions")
        if price_per_share <= 0:
            raise ValueError("Price must be positive")

        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                raise ValueError(f"Stock not found: {ticker}")

            holding = session.exec(select(Holding).where(Holding.stock_id == stock.id)).first()
            if not holding or holding.quantity < quantity:
                available = holding.quantity if holding else 0
                raise ValueError(
                    f"Insufficient shares to sell. Have {available}, trying to sell {quantity}"
                )

            # Calculate FIFO cost basis
            cost_basis_per_share = holding.cost_basis_per_share

            # Calculate proceeds and gain
            total_proceeds = (quantity * price_per_share) - fees
            cost_basis_for_sale = quantity * cost_basis_per_share
            realized_gain = total_proceeds - cost_basis_for_sale

            # Create transaction
            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="sell",
                transaction_date=transaction_date or datetime.now(timezone.utc),
                quantity=-quantity,  # Negative for sells
                price_per_share=price_per_share,
                fees=fees,
                total_cost=0.0,
                total_proceeds=total_proceeds,
                cost_basis_per_share=cost_basis_per_share,
                realized_gain=realized_gain,
                notes=notes,
            )
            session.add(transaction)

            # Update holding
            new_quantity = holding.quantity - quantity
            if new_quantity > 0:
                # Reduce cost basis proportionally
                holding.quantity = new_quantity
                holding.cost_basis_total = new_quantity * cost_basis_per_share
                holding.last_transaction_date = transaction.transaction_date
                holding.updated_at = datetime.now(timezone.utc)
            else:
                # Position closed
                session.delete(holding)

            session.commit()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def get_holdings(self, sort_by: str = "value") -> list[HoldingDetail]:
        """
        Get all current holdings.

        Args:
            sort_by: Sort field (ticker, value, fscore)

        Returns:
            List of HoldingDetail
        """
        with get_session() as session:
            holdings = session.exec(select(Holding).where(Holding.quantity > 0)).all()

            results = []
            total_value = sum(h.cost_basis_total for h in holdings)

            for holding in holdings:
                stock = session.exec(select(Stock).where(Stock.id == holding.stock_id)).first()
                if not stock:
                    continue

                # Get latest score
                latest_score = session.exec(
                    select(StockScore)
                    .where(StockScore.stock_id == stock.id)
                    .order_by(StockScore.calculated_at.desc())
                ).first()

                detail = HoldingDetail(
                    ticker=stock.ticker,
                    company_name=stock.company_name,
                    quantity=holding.quantity,
                    cost_basis_total=holding.cost_basis_total,
                    cost_basis_per_share=holding.cost_basis_per_share,
                    first_purchase_date=holding.first_purchase_date,
                    last_transaction_date=holding.last_transaction_date,
                    fscore=latest_score.piotroski_score if latest_score else None,
                    zscore=latest_score.altman_z_score if latest_score else None,
                    zone=latest_score.altman_zone if latest_score else None,
                    allocation_percent=(
                        (holding.cost_basis_total / total_value * 100) if total_value > 0 else 0
                    ),
                )
                results.append(detail)

            # Sort results
            if sort_by == "value":
                results.sort(key=lambda x: x.cost_basis_total, reverse=True)
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
        holdings = self.get_holdings()
        for h in holdings:
            if h.ticker.upper() == ticker.upper():
                return h
        return None

    def get_portfolio_summary(self) -> PortfolioSummary:
        """
        Get overall portfolio summary.

        Returns:
            PortfolioSummary with totals and P&L
        """
        with get_session() as session:
            # Get all holdings
            holdings = session.exec(select(Holding).where(Holding.quantity > 0)).all()

            total_cost_basis = sum(h.cost_basis_total for h in holdings)
            position_count = len(holdings)

            # Calculate realized P&L from all sell transactions
            sell_transactions = session.exec(
                select(Transaction).where(Transaction.transaction_type == "sell")
            ).all()

            realized_pnl_total = sum(t.realized_gain or 0 for t in sell_transactions)

            # YTD realized P&L
            current_year = datetime.now().year
            ytd_sells = [
                t
                for t in sell_transactions
                if t.transaction_date and t.transaction_date.year == current_year
            ]
            realized_pnl_ytd = sum(t.realized_gain or 0 for t in ytd_sells)

            # Cash flow calculations
            buy_transactions = session.exec(
                select(Transaction).where(Transaction.transaction_type == "buy")
            ).all()
            cash_invested = sum(t.total_cost for t in buy_transactions)
            cash_received = sum(t.total_proceeds for t in sell_transactions)

            return PortfolioSummary(
                total_cost_basis=total_cost_basis,
                total_market_value=total_cost_basis,  # Would need price feed for actual value
                unrealized_pnl=0.0,  # Would need price feed
                unrealized_pnl_percent=0.0,
                realized_pnl_total=realized_pnl_total,
                realized_pnl_ytd=realized_pnl_ytd,
                position_count=position_count,
                cash_invested=cash_invested,
                cash_received=cash_received,
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
            stmt = select(Transaction).join(Stock, Transaction.stock_id == Stock.id)

            if ticker:
                stmt = stmt.where(Stock.ticker == ticker.upper())

            transactions = session.exec(
                stmt.order_by(Transaction.transaction_date.desc()).limit(limit)
            ).all()

            results = []
            for t in transactions:
                stock = session.exec(select(Stock).where(Stock.id == t.stock_id)).first()
                results.append(
                    TransactionRecord(
                        id=t.id,
                        ticker=stock.ticker if stock else "???",
                        company_name=stock.company_name if stock else "Unknown",
                        transaction_type=t.transaction_type,
                        transaction_date=t.transaction_date,
                        quantity=abs(t.quantity),
                        price_per_share=t.price_per_share,
                        fees=t.fees,
                        total_cost=t.total_cost,
                        total_proceeds=t.total_proceeds,
                        realized_gain=t.realized_gain,
                        notes=t.notes,
                    )
                )

            return results

    def get_weighted_scores(self) -> WeightedScores:
        """
        Calculate portfolio-weighted F-Score and Z-Score.

        Weights each holding by its cost basis allocation.

        Returns:
            WeightedScores with portfolio-level metrics
        """
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
            weighted_fscore=weighted_fscore,
            weighted_zscore=weighted_zscore,
            holdings_with_scores=with_scores,
            holdings_without_scores=without_scores,
            safe_allocation=(safe_value / total_value * 100) if total_value > 0 else 0,
            grey_allocation=(grey_value / total_value * 100) if total_value > 0 else 0,
            distress_allocation=(distress_value / total_value * 100) if total_value > 0 else 0,
        )

    def take_snapshot(self, market_prices: Optional[dict[str, float]] = None) -> PortfolioSnapshot:
        """
        Take a snapshot of current portfolio state.

        Args:
            market_prices: Optional dict of ticker -> current price

        Returns:
            Created PortfolioSnapshot
        """
        summary = self.get_portfolio_summary()
        weighted = self.get_weighted_scores()

        # Calculate market value if prices provided
        total_market_value = summary.total_cost_basis
        if market_prices:
            holdings = self.get_holdings()
            total_market_value = sum(
                h.quantity * market_prices.get(h.ticker, h.cost_basis_per_share)
                for h in holdings
            )

        unrealized_pnl = total_market_value - summary.total_cost_basis
        unrealized_pnl_percent = (
            (unrealized_pnl / summary.total_cost_basis * 100)
            if summary.total_cost_basis > 0
            else 0
        )

        with get_session() as session:
            snapshot = PortfolioSnapshot(
                snapshot_date=datetime.now(timezone.utc),
                total_value=total_market_value,
                total_cost_basis=summary.total_cost_basis,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                realized_pnl_ytd=summary.realized_pnl_ytd,
                realized_pnl_total=summary.realized_pnl_total,
                position_count=summary.position_count,
                weighted_fscore=weighted.weighted_fscore,
                weighted_zscore=weighted.weighted_zscore,
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            return snapshot
