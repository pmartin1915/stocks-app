"""
Database connection management for Asymmetric.

Provides SQLite connection with context managers for session handling.
Follows singleton pattern for the database engine.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Generator, Optional

from sqlmodel import Session, SQLModel, create_engine, select

from asymmetric.config import config

logger = logging.getLogger(__name__)

# Global engine (singleton)
_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """
    Get or create database engine (singleton pattern).

    Thread-safe initialization ensures only one engine is created
    across the entire application.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine

    if _engine is None:
        with _engine_lock:
            # Double-check locking pattern
            if _engine is None:
                db_path = config.db_path
                db_path.parent.mkdir(parents=True, exist_ok=True)

                _engine = create_engine(
                    f"sqlite:///{db_path}",
                    echo=False,  # Set True for SQL debugging
                    connect_args={
                        "check_same_thread": False  # Required for HTTP mode
                    },
                )
                logger.info(f"Database engine initialized: {db_path}")

    return _engine


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in the models if they don't exist.
    Safe to call multiple times.
    """
    # Import models to ensure they're registered with SQLModel metadata
    from asymmetric.db.models import (  # noqa: F401
        Decision,
        ScoreHistory,
        ScreeningRun,
        Stock,
        StockScore,
        Thesis,
    )
    from asymmetric.db.portfolio_models import (  # noqa: F401
        Holding,
        PortfolioSnapshot,
        Transaction,
    )
    from asymmetric.db.alert_models import (  # noqa: F401
        Alert,
        AlertHistory,
    )

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables initialized")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup.

    Usage:
        with get_session() as session:
            stock = Stock(ticker="AAPL", ...)
            session.add(stock)
            # Commits automatically on success

    Yields:
        SQLModel Session instance.

    Notes:
        - Automatically commits on successful exit
        - Rolls back on exception
        - Always closes the session
    """
    engine = get_engine()
    session = Session(engine)

    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(
            "Database transaction failed, rolling back: %s",
            str(e),
            exc_info=True,
        )
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """
    Reset the global engine instance.

    Primarily useful for testing. In production, the engine should
    persist for the lifetime of the application.
    """
    global _engine

    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
            logger.info("Database engine reset")


def get_stock_by_ticker(session: Session, ticker: str) -> Optional["Stock"]:
    """
    Get a stock by ticker within an existing session.

    Args:
        session: Active database session.
        ticker: Stock ticker symbol.

    Returns:
        Stock instance or None if not found.
    """
    from asymmetric.db.models import Stock

    ticker = ticker.upper() if ticker else ""
    return session.exec(select(Stock).where(Stock.ticker == ticker)).first()


def lookup_stock(ticker: str) -> Optional["Stock"]:
    """
    Look up a stock by ticker (standalone, creates its own session).

    The returned Stock is detached from the session and safe to use
    after this function returns.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Stock instance or None if not found.
    """
    from asymmetric.db.models import Stock

    ticker = ticker.upper() if ticker else ""

    with get_session() as session:
        stock = session.exec(select(Stock).where(Stock.ticker == ticker)).first()
        if stock is not None:
            session.refresh(stock)
            session.expunge(stock)
        return stock


def get_or_create_stock(
    session: Session,
    ticker: str,
    cik: str = "",
    company_name: str = "",
    **kwargs,
) -> "Stock":
    """
    Get existing stock or create a new one within an existing session.

    Args:
        session: Active database session.
        ticker: Stock ticker symbol.
        cik: SEC CIK number.
        company_name: Company name.
        **kwargs: Additional Stock fields.

    Returns:
        Existing or newly created Stock instance.
    """
    from asymmetric.db.models import Stock

    ticker = ticker.upper() if ticker else ""
    stock = session.exec(select(Stock).where(Stock.ticker == ticker)).first()

    if stock is None:
        stock = Stock(
            ticker=ticker,
            cik=cik,
            company_name=company_name or ticker,
            **kwargs,
        )
        session.add(stock)
        session.flush()  # Get ID without committing
        logger.info(f"Created new stock: {ticker}")

    return stock


def ensure_stock(
    ticker: str,
    cik: str = "",
    company_name: str = "",
    **kwargs,
) -> "Stock":
    """
    Get or create a stock (standalone, creates its own session).

    The returned Stock is detached from the session and safe to use
    after this function returns.

    Args:
        ticker: Stock ticker symbol.
        cik: SEC CIK number.
        company_name: Company name.
        **kwargs: Additional Stock fields.

    Returns:
        Existing or newly created Stock instance (detached).
    """
    from asymmetric.db.models import Stock

    ticker = ticker.upper() if ticker else ""

    with get_session() as session:
        stock = session.exec(select(Stock).where(Stock.ticker == ticker)).first()

        if stock is None:
            stock = Stock(
                ticker=ticker,
                cik=cik,
                company_name=company_name or ticker,
                **kwargs,
            )
            session.add(stock)
            session.flush()
            logger.info(f"Created new stock: {ticker}")

        session.refresh(stock)
        session.expunge(stock)
        return stock
