"""
Trend analysis for historical score tracking.

Analyzes F-Score and Z-Score trends over time to identify:
- Improving stocks (F-Score increasing)
- Declining stocks (F-Score decreasing)
- Consistent performers (sustained high F-Score)
- Turnaround candidates (Z-Score zone improvements)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select

from asymmetric.core.data.bulk_manager import BulkDataManager
from asymmetric.db.database import get_or_create_stock, get_session, get_stock_by_ticker
from asymmetric.db.models import ScoreHistory, Stock


@dataclass
class ScoreHistoryRecord:
    """Single historical score record."""

    fiscal_year: int
    fiscal_period: str
    piotroski_score: int
    piotroski_profitability: Optional[int]
    piotroski_leverage: Optional[int]
    piotroski_efficiency: Optional[int]
    altman_z_score: float
    altman_zone: str
    recorded_at: datetime


@dataclass
class TrendResult:
    """Result of trend analysis for a stock."""

    ticker: str
    company_name: str
    current_fscore: int
    previous_fscore: int
    fscore_change: int
    current_zscore: float
    previous_zscore: float
    zscore_change: float
    current_zone: str
    previous_zone: str
    zone_changed: bool
    periods_analyzed: int
    trend_direction: str  # "improving", "declining", "stable"


@dataclass
class ConsistentPerformer:
    """Stock with consistently high F-Score."""

    ticker: str
    company_name: str
    average_fscore: float
    min_fscore: int
    max_fscore: int
    consecutive_periods: int
    current_fscore: int
    current_zscore: float
    current_zone: str


@dataclass
class TurnaroundCandidate:
    """Stock transitioning from Distress zone."""

    ticker: str
    company_name: str
    previous_zone: str
    current_zone: str
    previous_zscore: float
    current_zscore: float
    zscore_improvement: float
    current_fscore: int
    periods_since_distress: int


class TrendAnalyzer:
    """
    Analyzes score trends over time.

    Uses both DuckDB (for bulk queries) and SQLite (for score history)
    to provide comprehensive trend analysis.
    """

    def __init__(self, bulk_manager: Optional[BulkDataManager] = None):
        """
        Initialize trend analyzer.

        Args:
            bulk_manager: Optional BulkDataManager instance for DuckDB queries
        """
        self.bulk = bulk_manager

    def get_score_history(
        self, ticker: str, years: int = 5, period_type: str = "FY"
    ) -> list[ScoreHistoryRecord]:
        """
        Get historical scores for a ticker.

        Args:
            ticker: Stock ticker symbol
            years: Number of years of history to retrieve
            period_type: "FY" for annual, "Q1"-"Q4" for quarterly

        Returns:
            List of ScoreHistoryRecord, newest first
        """
        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                return []

            # Query score history
            current_year = datetime.now(timezone.utc).year
            min_year = current_year - years

            stmt = (
                select(ScoreHistory)
                .where(ScoreHistory.stock_id == stock.id)
                .where(ScoreHistory.fiscal_year >= min_year)
            )

            if period_type == "FY":
                stmt = stmt.where(ScoreHistory.fiscal_period == "FY")
            else:
                stmt = stmt.where(ScoreHistory.fiscal_period.in_(["Q1", "Q2", "Q3", "Q4"]))

            results = session.exec(
                stmt.order_by(
                    ScoreHistory.fiscal_year.desc(), ScoreHistory.fiscal_period.desc()
                )
            ).all()

            return [
                ScoreHistoryRecord(
                    fiscal_year=r.fiscal_year,
                    fiscal_period=r.fiscal_period,
                    piotroski_score=r.piotroski_score,
                    piotroski_profitability=r.piotroski_profitability,
                    piotroski_leverage=r.piotroski_leverage,
                    piotroski_efficiency=r.piotroski_efficiency,
                    altman_z_score=r.altman_z_score,
                    altman_zone=r.altman_zone,
                    recorded_at=r.recorded_at,
                )
                for r in results
            ]

    def calculate_trend(self, ticker: str, periods: int = 4) -> Optional[TrendResult]:
        """
        Calculate trend direction and magnitude for a ticker.

        Args:
            ticker: Stock ticker symbol
            periods: Number of periods to analyze

        Returns:
            TrendResult or None if insufficient data
        """
        history = self.get_score_history(ticker, years=periods + 1)
        if len(history) < 2:
            return None

        # Get current and previous scores
        current = history[0]
        previous = history[min(periods - 1, len(history) - 1)]

        # Calculate changes
        fscore_change = current.piotroski_score - previous.piotroski_score
        zscore_change = current.altman_z_score - previous.altman_z_score

        # Determine trend direction
        if fscore_change >= 2:
            trend_direction = "improving"
        elif fscore_change <= -2:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        # Get company name
        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            company_name = stock.company_name if stock else ticker

        return TrendResult(
            ticker=ticker,
            company_name=company_name,
            current_fscore=current.piotroski_score,
            previous_fscore=previous.piotroski_score,
            fscore_change=fscore_change,
            current_zscore=current.altman_z_score,
            previous_zscore=previous.altman_z_score,
            zscore_change=zscore_change,
            current_zone=current.altman_zone,
            previous_zone=previous.altman_zone,
            zone_changed=current.altman_zone != previous.altman_zone,
            periods_analyzed=len(history),
            trend_direction=trend_direction,
        )

    def find_improving(
        self, min_improvement: int = 2, periods: int = 4, limit: int = 25
    ) -> list[TrendResult]:
        """
        Find stocks with improving F-Scores.

        Args:
            min_improvement: Minimum F-Score improvement required
            periods: Number of periods to compare
            limit: Maximum results to return

        Returns:
            List of TrendResult for improving stocks, sorted by improvement
        """
        results = []

        # Get all tickers with score history
        tickers = self._get_tickers_with_history()

        for ticker in tickers:
            trend = self.calculate_trend(ticker, periods)
            if trend and trend.fscore_change >= min_improvement:
                results.append(trend)

        # Sort by improvement (descending)
        results.sort(key=lambda x: x.fscore_change, reverse=True)
        return results[:limit]

    def find_declining(
        self, min_decline: int = 2, periods: int = 4, limit: int = 25
    ) -> list[TrendResult]:
        """
        Find stocks with declining F-Scores.

        Args:
            min_decline: Minimum F-Score decline (positive number)
            periods: Number of periods to compare
            limit: Maximum results to return

        Returns:
            List of TrendResult for declining stocks, sorted by decline
        """
        results = []

        tickers = self._get_tickers_with_history()

        for ticker in tickers:
            trend = self.calculate_trend(ticker, periods)
            if trend and trend.fscore_change <= -min_decline:
                results.append(trend)

        # Sort by decline (most negative first)
        results.sort(key=lambda x: x.fscore_change)
        return results[:limit]

    def find_consistent(
        self, min_score: int = 7, periods: int = 8, limit: int = 25
    ) -> list[ConsistentPerformer]:
        """
        Find stocks with consistently high F-Scores.

        Args:
            min_score: Minimum F-Score for each period
            periods: Number of consecutive periods required
            limit: Maximum results to return

        Returns:
            List of ConsistentPerformer, sorted by consecutive periods
        """
        results = []

        tickers = self._get_tickers_with_history()

        for ticker in tickers:
            history = self.get_score_history(ticker, years=periods + 1)
            if len(history) < periods:
                continue

            # Check if all periods meet minimum score
            recent_history = history[:periods]
            scores = [h.piotroski_score for h in recent_history]

            if all(s >= min_score for s in scores):
                with get_session() as session:
                    stock = get_stock_by_ticker(session, ticker)
                    company_name = stock.company_name if stock else ticker

                results.append(
                    ConsistentPerformer(
                        ticker=ticker,
                        company_name=company_name,
                        average_fscore=sum(scores) / len(scores),
                        min_fscore=min(scores),
                        max_fscore=max(scores),
                        consecutive_periods=len(scores),
                        current_fscore=scores[0],
                        current_zscore=recent_history[0].altman_z_score,
                        current_zone=recent_history[0].altman_zone,
                    )
                )

        # Sort by consecutive periods and average score
        results.sort(key=lambda x: (x.consecutive_periods, x.average_fscore), reverse=True)
        return results[:limit]

    def find_turnaround(self, limit: int = 25) -> list[TurnaroundCandidate]:
        """
        Find stocks transitioning from Distress zone.

        Identifies companies that were in Distress zone but have
        improved to Grey or Safe zone.

        Args:
            limit: Maximum results to return

        Returns:
            List of TurnaroundCandidate, sorted by Z-Score improvement
        """
        results = []

        tickers = self._get_tickers_with_history()

        for ticker in tickers:
            history = self.get_score_history(ticker, years=5)
            if len(history) < 2:
                continue

            current = history[0]

            # Skip if currently in Distress
            if current.altman_zone == "Distress":
                continue

            # Look for previous Distress zone
            for i, past in enumerate(history[1:], 1):
                if past.altman_zone == "Distress":
                    with get_session() as session:
                        stock = get_stock_by_ticker(session, ticker)
                        company_name = stock.company_name if stock else ticker

                    results.append(
                        TurnaroundCandidate(
                            ticker=ticker,
                            company_name=company_name,
                            previous_zone=past.altman_zone,
                            current_zone=current.altman_zone,
                            previous_zscore=past.altman_z_score,
                            current_zscore=current.altman_z_score,
                            zscore_improvement=current.altman_z_score - past.altman_z_score,
                            current_fscore=current.piotroski_score,
                            periods_since_distress=i,
                        )
                    )
                    break

        # Sort by Z-Score improvement
        results.sort(key=lambda x: x.zscore_improvement, reverse=True)
        return results[:limit]

    def save_score_to_history(
        self,
        ticker: str,
        fiscal_year: int,
        fiscal_period: str,
        piotroski_score: int,
        altman_z_score: float,
        altman_zone: str,
        piotroski_profitability: Optional[int] = None,
        piotroski_leverage: Optional[int] = None,
        piotroski_efficiency: Optional[int] = None,
        altman_formula: str = "manufacturing",
        data_source: str = "live_api",
    ) -> ScoreHistory:
        """
        Save a score to history (upsert).

        Args:
            ticker: Stock ticker symbol
            fiscal_year: Fiscal year of the score
            fiscal_period: Fiscal period (FY, Q1, Q2, Q3, Q4)
            piotroski_score: F-Score (0-9)
            altman_z_score: Z-Score value
            altman_zone: Zone classification (Safe, Grey, Distress)
            piotroski_profitability: Profitability component (0-4)
            piotroski_leverage: Leverage component (0-3)
            piotroski_efficiency: Efficiency component (0-2)
            altman_formula: Formula used (manufacturing, non_manufacturing)
            data_source: Data source (bulk_data, live_api)

        Returns:
            Created or updated ScoreHistory record
        """
        with get_session() as session:
            # Get or create stock
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                # Create minimal stock record
                stock = get_or_create_stock(
                    session, ticker=ticker, cik="", company_name=ticker
                )

            # Check for existing record
            existing = session.exec(
                select(ScoreHistory)
                .where(ScoreHistory.stock_id == stock.id)
                .where(ScoreHistory.fiscal_year == fiscal_year)
                .where(ScoreHistory.fiscal_period == fiscal_period)
            ).first()

            if existing:
                # Update existing record
                existing.piotroski_score = piotroski_score
                existing.piotroski_profitability = piotroski_profitability
                existing.piotroski_leverage = piotroski_leverage
                existing.piotroski_efficiency = piotroski_efficiency
                existing.altman_z_score = altman_z_score
                existing.altman_zone = altman_zone
                existing.altman_formula = altman_formula
                existing.data_source = data_source
                existing.recorded_at = datetime.now(timezone.utc)
                session.add(existing)
                result = existing
            else:
                # Create new record
                result = ScoreHistory(
                    stock_id=stock.id,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    piotroski_score=piotroski_score,
                    piotroski_profitability=piotroski_profitability,
                    piotroski_leverage=piotroski_leverage,
                    piotroski_efficiency=piotroski_efficiency,
                    altman_z_score=altman_z_score,
                    altman_zone=altman_zone,
                    altman_formula=altman_formula,
                    data_source=data_source,
                )
                session.add(result)

            # Commit, refresh, and expunge to prevent DetachedInstanceError
            session.commit()
            session.refresh(result)
            session.expunge(result)
            return result

    def _get_tickers_with_history(self) -> list[str]:
        """Get all tickers that have score history."""
        with get_session() as session:
            stmt = (
                select(Stock.ticker)
                .join(ScoreHistory, Stock.id == ScoreHistory.stock_id)
                .distinct()
            )
            results = session.exec(stmt).all()
            return [r for r in results]
