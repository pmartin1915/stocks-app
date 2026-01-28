"""
Sector analysis for peer comparison and filtering.

Provides sector-based analysis capabilities:
- Sector classification using SIC codes
- Peer identification within sectors
- Sector average score calculation
- Sector leader identification
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Integer, and_, cast, func, or_

from asymmetric.core.data.bulk_manager import BulkDataManager
from asymmetric.core.data.sic_codes import (
    SectorInfo,
    get_all_sectors,
    get_altman_formula,
    get_industries_for_sector,
    get_sector_from_sic,
    get_sic_ranges_for_sector,
)
from asymmetric.db.database import get_session, get_stock_by_ticker
from asymmetric.db.models import ScoreHistory, Stock, StockScore


@dataclass
class SectorAverage:
    """Average scores for a sector."""

    sector: str
    company_count: int
    avg_fscore: float
    avg_zscore: float
    safe_count: int
    grey_count: int
    distress_count: int
    top_performer: Optional[str] = None
    top_performer_fscore: Optional[int] = None


@dataclass
class PeerComparison:
    """Comparison of a stock to its sector peers."""

    ticker: str
    company_name: str
    sector: str
    industry: str
    fscore: int
    zscore: float
    zone: str
    sector_avg_fscore: float
    sector_avg_zscore: float
    fscore_vs_sector: float  # Difference from sector average
    zscore_vs_sector: float
    sector_rank: int  # Rank within sector by F-Score
    sector_total: int  # Total companies in sector
    percentile: float  # Percentile rank (0-100)


@dataclass
class SectorLeader:
    """Top performer in a sector."""

    ticker: str
    company_name: str
    sector: str
    industry: str
    fscore: int
    zscore: float
    zone: str
    rank: int


class SectorAnalyzer:
    """
    Analyzes stocks by sector and provides peer comparisons.

    Uses SIC codes to classify companies and enables sector-based
    screening, filtering, and comparison.
    """

    def __init__(self, bulk_manager: Optional[BulkDataManager] = None):
        """
        Initialize sector analyzer.

        Args:
            bulk_manager: Optional BulkDataManager for DuckDB queries
        """
        self.bulk = bulk_manager

    def _build_sic_filter(self, sector: str):
        """
        Build SQLAlchemy filter for SIC code ranges.

        Args:
            sector: Sector name

        Returns:
            SQLAlchemy OR condition for all SIC ranges in sector, or None
        """
        sic_ranges = get_sic_ranges_for_sector(sector)
        if not sic_ranges:
            return None

        conditions = []
        for start, end in sic_ranges:
            conditions.append(
                and_(
                    cast(Stock.sic_code, Integer) >= start,
                    cast(Stock.sic_code, Integer) <= end,
                )
            )
        return or_(*conditions)

    def _latest_score_subquery(self, session):
        """
        Create subquery to get latest StockScore per stock.

        Args:
            session: SQLAlchemy session

        Returns:
            Subquery with stock_id and max calculated_at
        """
        latest = (
            session.query(
                StockScore.stock_id, func.max(StockScore.calculated_at).label("max_date")
            )
            .group_by(StockScore.stock_id)
            .subquery()
        )
        return latest

    def get_sector_for_ticker(self, ticker: str) -> Optional[SectorInfo]:
        """
        Get sector information for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            SectorInfo or None if not found
        """
        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock or not stock.sic_code:
                # Try bulk manager if available
                if self.bulk:
                    info = self.bulk.get_company_info(ticker)
                    if info and info.get("sic_code"):
                        return get_sector_from_sic(info["sic_code"])
                return None

            return get_sector_from_sic(stock.sic_code)

    def get_peers(self, ticker: str, limit: int = 10) -> list[str]:
        """
        Get peer tickers in the same sector.

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of peers to return

        Returns:
            List of peer ticker symbols
        """
        sector_info = self.get_sector_for_ticker(ticker)
        if not sector_info:
            return []

        with get_session() as session:
            sic_filter = self._build_sic_filter(sector_info.sector)
            if sic_filter is None:
                return []

            # Single query with SIC filter in SQL
            peers = (
                session.query(Stock.ticker)
                .filter(Stock.sic_code.isnot(None))
                .filter(Stock.ticker != ticker.upper())
                .filter(sic_filter)
                .limit(limit)
                .all()
            )
            return [p[0] for p in peers]

    def get_sector_averages(self, sector: Optional[str] = None) -> list[SectorAverage]:
        """
        Calculate average scores per sector.

        Args:
            sector: Optional specific sector to analyze (all if None)

        Returns:
            List of SectorAverage for each sector
        """
        sectors_to_process = [sector] if sector else get_all_sectors()
        results = []

        with get_session() as session:
            latest = self._latest_score_subquery(session)

            for sec in sectors_to_process:
                sic_filter = self._build_sic_filter(sec)
                if sic_filter is None:
                    continue

                # Single query: JOIN Stock + StockScore with SIC filter
                stocks_with_scores = (
                    session.query(Stock, StockScore)
                    .join(StockScore, Stock.id == StockScore.stock_id)
                    .join(
                        latest,
                        and_(
                            StockScore.stock_id == latest.c.stock_id,
                            StockScore.calculated_at == latest.c.max_date,
                        ),
                    )
                    .filter(Stock.sic_code.isnot(None))
                    .filter(sic_filter)
                    .all()
                )

                if not stocks_with_scores:
                    continue

                # Calculate averages in memory (already have all data)
                fscores = [s[1].piotroski_score for s in stocks_with_scores]
                zscores = [s[1].altman_z_score for s in stocks_with_scores]
                zones = [s[1].altman_zone for s in stocks_with_scores]

                # Find top performer
                top = max(stocks_with_scores, key=lambda x: x[1].piotroski_score)

                results.append(
                    SectorAverage(
                        sector=sec,
                        company_count=len(stocks_with_scores),
                        avg_fscore=sum(fscores) / len(fscores),
                        avg_zscore=sum(zscores) / len(zscores),
                        safe_count=zones.count("Safe"),
                        grey_count=zones.count("Grey"),
                        distress_count=zones.count("Distress"),
                        top_performer=top[0].ticker,
                        top_performer_fscore=top[1].piotroski_score,
                    )
                )

        return results

    def compare_to_peers(self, ticker: str) -> Optional[PeerComparison]:
        """
        Compare a stock to its sector peers.

        Args:
            ticker: Stock ticker symbol

        Returns:
            PeerComparison or None if insufficient data
        """
        sector_info = self.get_sector_for_ticker(ticker)
        if not sector_info:
            return None

        with get_session() as session:
            stock = get_stock_by_ticker(session, ticker)
            if not stock:
                return None

            latest = self._latest_score_subquery(session)

            # Query 1: Get this stock's latest score
            latest_score = (
                session.query(StockScore)
                .join(
                    latest,
                    and_(
                        StockScore.stock_id == latest.c.stock_id,
                        StockScore.calculated_at == latest.c.max_date,
                    ),
                )
                .filter(StockScore.stock_id == stock.id)
                .first()
            )
            if not latest_score:
                return None

            # Query 2: Get sector averages (now optimized - 1 query per sector)
            averages = self.get_sector_averages(sector_info.sector)
            if not averages:
                return None
            sector_avg = averages[0]

            # Query 3: Get all peer scores in one query (for ranking)
            sic_filter = self._build_sic_filter(sector_info.sector)

            all_sector_scores = (
                session.query(StockScore.piotroski_score)
                .join(Stock, StockScore.stock_id == Stock.id)
                .join(
                    latest,
                    and_(
                        StockScore.stock_id == latest.c.stock_id,
                        StockScore.calculated_at == latest.c.max_date,
                    ),
                )
                .filter(Stock.sic_code.isnot(None))
                .filter(sic_filter)
                .all()
            )

            all_scores = sorted([s[0] for s in all_sector_scores], reverse=True)
            total = len(all_scores)

            # Calculate rank (count how many have higher score)
            rank = 1
            for score in all_scores:
                if score > latest_score.piotroski_score:
                    rank += 1
                else:
                    break

            percentile = ((total - rank) / total) * 100 if total > 0 else 0

            return PeerComparison(
                ticker=ticker,
                company_name=stock.company_name,
                sector=sector_info.sector,
                industry=sector_info.industry,
                fscore=latest_score.piotroski_score,
                zscore=latest_score.altman_z_score,
                zone=latest_score.altman_zone,
                sector_avg_fscore=sector_avg.avg_fscore,
                sector_avg_zscore=sector_avg.avg_zscore,
                fscore_vs_sector=latest_score.piotroski_score - sector_avg.avg_fscore,
                zscore_vs_sector=latest_score.altman_z_score - sector_avg.avg_zscore,
                sector_rank=rank,
                sector_total=total,
                percentile=percentile,
            )

    def get_sector_leaders(
        self, sector: str, metric: str = "fscore", limit: int = 10
    ) -> list[SectorLeader]:
        """
        Get top performers in a sector.

        Args:
            sector: Sector name
            metric: Ranking metric ("fscore" or "zscore")
            limit: Maximum results

        Returns:
            List of SectorLeader sorted by the metric
        """
        with get_session() as session:
            sic_filter = self._build_sic_filter(sector)
            if sic_filter is None:
                return []

            latest = self._latest_score_subquery(session)

            # Single query with JOIN, ORDER BY and LIMIT
            query = (
                session.query(Stock, StockScore)
                .join(StockScore, Stock.id == StockScore.stock_id)
                .join(
                    latest,
                    and_(
                        StockScore.stock_id == latest.c.stock_id,
                        StockScore.calculated_at == latest.c.max_date,
                    ),
                )
                .filter(Stock.sic_code.isnot(None))
                .filter(sic_filter)
            )

            # Sort by metric in SQL
            if metric == "zscore":
                query = query.order_by(StockScore.altman_z_score.desc())
            else:
                query = query.order_by(
                    StockScore.piotroski_score.desc(), StockScore.altman_z_score.desc()
                )

            results_raw = query.limit(limit).all()

            # Build result list with ranks
            results = []
            for i, (stock, score) in enumerate(results_raw, 1):
                sector_info = get_sector_from_sic(stock.sic_code)
                results.append(
                    SectorLeader(
                        ticker=stock.ticker,
                        company_name=stock.company_name,
                        sector=sector,
                        industry=sector_info.industry if sector_info else "",
                        fscore=score.piotroski_score,
                        zscore=score.altman_z_score,
                        zone=score.altman_zone,
                        rank=i,
                    )
                )

            return results

    def filter_by_sector(
        self,
        sector: str,
        min_fscore: Optional[int] = None,
        min_zscore: Optional[float] = None,
        zone: Optional[str] = None,
        limit: int = 50,
    ) -> list[SectorLeader]:
        """
        Filter stocks by sector with optional score filters.

        Args:
            sector: Sector name
            min_fscore: Minimum F-Score
            min_zscore: Minimum Z-Score
            zone: Required zone (Safe, Grey, Distress)
            limit: Maximum results

        Returns:
            List of matching stocks
        """
        with get_session() as session:
            sic_filter = self._build_sic_filter(sector)
            if sic_filter is None:
                return []

            latest = self._latest_score_subquery(session)

            # Single query with JOIN and all filters in SQL
            query = (
                session.query(Stock, StockScore)
                .join(StockScore, Stock.id == StockScore.stock_id)
                .join(
                    latest,
                    and_(
                        StockScore.stock_id == latest.c.stock_id,
                        StockScore.calculated_at == latest.c.max_date,
                    ),
                )
                .filter(Stock.sic_code.isnot(None))
                .filter(sic_filter)
            )

            # Apply filters in SQL
            if min_fscore is not None:
                query = query.filter(StockScore.piotroski_score >= min_fscore)
            if min_zscore is not None:
                query = query.filter(StockScore.altman_z_score >= min_zscore)
            if zone is not None:
                query = query.filter(StockScore.altman_zone == zone)

            # Sort and limit
            query = query.order_by(
                StockScore.piotroski_score.desc(), StockScore.altman_z_score.desc()
            ).limit(limit)

            results_raw = query.all()

            # Build result list with ranks
            results = []
            for i, (stock, score) in enumerate(results_raw, 1):
                sector_info = get_sector_from_sic(stock.sic_code)
                results.append(
                    SectorLeader(
                        ticker=stock.ticker,
                        company_name=stock.company_name,
                        sector=sector,
                        industry=sector_info.industry if sector_info else "",
                        fscore=score.piotroski_score,
                        zscore=score.altman_z_score,
                        zone=score.altman_zone,
                        rank=i,
                    )
                )

            return results

    @staticmethod
    def get_available_sectors() -> list[str]:
        """Get list of available sectors for filtering."""
        return get_all_sectors()

    @staticmethod
    def get_industries_for_sector(sector: str) -> list[str]:
        """Get list of industries within a sector."""
        return get_industries_for_sector(sector)

    @staticmethod
    def get_altman_formula_for_sic(sic_code: str) -> str:
        """Determine Altman formula based on SIC code."""
        return get_altman_formula(sic_code)
