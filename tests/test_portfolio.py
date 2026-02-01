"""Tests for portfolio management functionality."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from asymmetric.db.database import get_session
from asymmetric.db.models import Stock
from asymmetric.db.portfolio_models import Holding, Transaction


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


class TestPortfolioModels:
    """Tests for portfolio database models."""

    def test_create_transaction(self):
        """Test creating a buy transaction."""
        with get_session() as session:
            # Create a stock first
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            # Create a transaction
            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="buy",
                transaction_date=datetime.now(UTC),
                quantity=10,
                price_per_share=150.00,
                fees=1.00,
                total_cost=1501.00,
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            assert transaction.id is not None
            assert transaction.transaction_type == "buy"
            assert transaction.quantity == 10
            assert transaction.total_cost == 1501.00

    def test_create_holding(self):
        """Test creating a holding."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            holding = Holding(
                stock_id=stock.id,
                quantity=10,
                cost_basis_total=1500.00,
                cost_basis_per_share=150.00,
                first_purchase_date=datetime.now(UTC),
                last_transaction_date=datetime.now(UTC),
            )
            session.add(holding)
            session.commit()
            session.refresh(holding)

            assert holding.id is not None
            assert holding.quantity == 10
            assert holding.cost_basis_per_share == 150.00

    def test_holding_unique_constraint(self):
        """Test that only one holding per stock is allowed."""
        from sqlalchemy.exc import IntegrityError

        # First create stock and first holding
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)
            stock_id = stock.id

            holding1 = Holding(
                stock_id=stock_id,
                quantity=10,
                cost_basis_total=1500.00,
                cost_basis_per_share=150.00,
            )
            session.add(holding1)
            session.commit()

        # Try to create second holding in a separate session
        with pytest.raises(IntegrityError):
            with get_session() as session:
                holding2 = Holding(
                    stock_id=stock_id,
                    quantity=5,
                    cost_basis_total=750.00,
                    cost_basis_per_share=150.00,
                )
                session.add(holding2)
                session.commit()


class TestTransactionTypes:
    """Tests for different transaction types."""

    def test_sell_transaction_negative_quantity(self):
        """Test that sell transactions use negative quantity."""
        with get_session() as session:
            stock = Stock(ticker="AAPL", cik="0000320193", company_name="Apple Inc.")
            session.add(stock)
            session.commit()
            session.refresh(stock)

            transaction = Transaction(
                stock_id=stock.id,
                transaction_type="sell",
                transaction_date=datetime.now(UTC),
                quantity=-5,  # Negative for sells
                price_per_share=175.00,
                fees=1.00,
                total_cost=0,
                total_proceeds=874.00,
                realized_gain=124.00,
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            assert transaction.quantity == -5
            assert transaction.total_proceeds == 874.00
            assert transaction.realized_gain == 124.00
