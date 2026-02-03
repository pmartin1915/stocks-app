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


def get_stock_by_ticker(session_or_ticker, ticker: str = None) -> Optional["Stock"]:
    """
    Helper to get a stock by ticker.

    Can be called two ways:
    1. get_stock_by_ticker(session, ticker) - uses existing session
    2. get_stock_by_ticker(ticker) - creates new session

    Args:
        session_or_ticker: Either a Session or ticker string.
        ticker: Stock ticker symbol if first arg is session.

    Returns:
        Stock instance or None if not found.

    Note:
        The returned Stock object may be detached from the session
        when called without a session argument.
    """
    from asymmetric.db.models import Stock

    # Handle both calling patterns
    if isinstance(session_or_ticker, Session):
        session = session_or_ticker
        ticker = ticker.upper() if ticker else ""
        return session.exec(select(Stock).where(Stock.ticker == ticker)).first()
    else:
        # Called with just ticker - use new session
        ticker = session_or_ticker.upper() if session_or_ticker else ""

        with get_session() as session:
            stock = session.exec(select(Stock).where(Stock.ticker == ticker)).first()
            if stock is not None:
                # Eagerly load all attributes before session closes
                session.refresh(stock)
                # Expunge from session to prevent DetachedInstanceError
                session.expunge(stock)
            return stock


def get_or_create_stock(
    session_or_ticker,
    ticker: str = None,
    cik: str = "",
    company_name: str = "",
    **kwargs,
) -> "Stock":
    """
    Get existing stock or create a new one.

    Can be called two ways:
    1. get_or_create_stock(session, ticker=..., cik=...) - uses existing session
    2. get_or_create_stock(ticker, cik=...) - creates new session

    Args:
        session_or_ticker: Either a Session or ticker string.
        ticker: Stock ticker symbol if first arg is session.
        cik: SEC CIK number.
        company_name: Company name.
        **kwargs: Additional Stock fields.

    Returns:
        Existing or newly created Stock instance.

    Note:
        The returned Stock object may be detached from the session
        when called without a session argument.
    """
    from asymmetric.db.models import Stock

    # Handle both calling patterns
    if isinstance(session_or_ticker, Session):
        session = session_or_ticker
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
    else:
        # Called with just ticker - use new session
        ticker = session_or_ticker.upper() if session_or_ticker else ""

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
                session.flush()  # Get ID without committing
                logger.info(f"Created new stock: {ticker}")

            # Eagerly load all attributes before session closes
            session.refresh(stock)
            # Expunge from session to prevent DetachedInstanceError
            session.expunge(stock)
            return stock
