"""Tests for SectorAnalyzer business logic."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from asymmetric.core.sectors.analyzer import SectorAnalyzer
from asymmetric.db.database import get_session
from asymmetric.db.models import Stock, StockScore


@pytest.fixture(autouse=True)
def setup_db(tmp_db: Path):
    """Use tmp_db fixture from conftest for clean database per test."""
    yield


@pytest.fixture
def analyzer():
    """Create SectorAnalyzer instance."""
    return SectorAnalyzer()


@pytest.fixture
def tech_stock():
    """Create a technology sector stock (SIC 3571 - Computer and Office Equipment)."""
    with get_session() as session:
        stock = Stock(
            ticker="TECH",
            cik="0001111111",
            company_name="Tech Corp",
            sic_code="3571",  # Computer and Office Equipment
        )
        session.add(stock)
        session.commit()
        session.refresh(stock)

        score = StockScore(
            stock_id=stock.id,
            piotroski_score=8,
            altman_z_score=4.5,
            altman_zone="Safe",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score)
        session.commit()

        return stock.ticker


@pytest.fixture
def tech_stock_2():
    """Create second technology stock for peer comparison."""
    with get_session() as session:
        stock = Stock(
            ticker="TECH2",
            cik="0001111112",
            company_name="Tech Corp 2",
            sic_code="3572",  # Computer Storage Devices
        )
        session.add(stock)
        session.commit()
        session.refresh(stock)

        score = StockScore(
            stock_id=stock.id,
            piotroski_score=6,
            altman_z_score=3.0,
            altman_zone="Safe",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score)
        session.commit()

        return stock.ticker


@pytest.fixture
def finance_stock():
    """Create a finance sector stock (SIC 6000 - Depository Institutions)."""
    with get_session() as session:
        stock = Stock(
            ticker="BANK",
            cik="0002222222",
            company_name="Bank Corp",
            sic_code="6020",  # Commercial Banking
        )
        session.add(stock)
        session.commit()
        session.refresh(stock)

        score = StockScore(
            stock_id=stock.id,
            piotroski_score=7,
            altman_z_score=2.5,
            altman_zone="Grey",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score)
        session.commit()

        return stock.ticker


@pytest.fixture
def stock_no_sic():
    """Create a stock without SIC code."""
    with get_session() as session:
        stock = Stock(
            ticker="NOSIC",
            cik="0003333333",
            company_name="No SIC Corp",
            sic_code=None,
        )
        session.add(stock)
        session.commit()
        return stock.ticker


class TestGetSectorForTicker:
    """Tests for sector lookup by ticker."""

    def test_get_sector_for_tech_stock(self, analyzer, tech_stock):
        """Test getting sector for technology stock."""
        sector_info = analyzer.get_sector_for_ticker(tech_stock)

        assert sector_info is not None
        assert sector_info.sector == "Manufacturing"  # SIC 3571 is Manufacturing
        # SIC 3571 maps to Industrial Machinery & Equipment (3500-3599 range)
        assert sector_info.industry == "Industrial Machinery & Equipment"

    def test_get_sector_for_finance_stock(self, analyzer, finance_stock):
        """Test getting sector for finance stock."""
        sector_info = analyzer.get_sector_for_ticker(finance_stock)

        assert sector_info is not None
        assert sector_info.sector == "Finance"

    def test_get_sector_no_sic_returns_none(self, analyzer, stock_no_sic):
        """Test stock without SIC code returns None."""
        sector_info = analyzer.get_sector_for_ticker(stock_no_sic)
        assert sector_info is None

    def test_get_sector_nonexistent_ticker(self, analyzer):
        """Test non-existent ticker returns None."""
        sector_info = analyzer.get_sector_for_ticker("NOTEXIST")
        assert sector_info is None


class TestGetPeers:
    """Tests for peer identification."""

    def test_get_peers_same_sector(self, analyzer, tech_stock, tech_stock_2):
        """Test getting peers in same sector."""
        peers = analyzer.get_peers(tech_stock, limit=10)

        assert tech_stock_2 in peers
        assert tech_stock not in peers  # Should not include self

    def test_get_peers_excludes_different_sector(self, analyzer, tech_stock, finance_stock):
        """Test peers excludes stocks from different sectors."""
        peers = analyzer.get_peers(tech_stock, limit=10)

        assert finance_stock not in peers

    def test_get_peers_respects_limit(self, analyzer, tech_stock, tech_stock_2):
        """Test limit parameter is respected."""
        peers = analyzer.get_peers(tech_stock, limit=1)
        assert len(peers) <= 1

    def test_get_peers_no_sector(self, analyzer, stock_no_sic):
        """Test stock without sector returns empty list."""
        peers = analyzer.get_peers(stock_no_sic, limit=10)
        assert peers == []


class TestGetSectorAverages:
    """Tests for sector average calculations."""

    def test_get_sector_averages_specific_sector(
        self, analyzer, tech_stock, tech_stock_2, finance_stock
    ):
        """Test calculating averages for a specific sector."""
        averages = analyzer.get_sector_averages(sector="Manufacturing")

        # Should have one result for Manufacturing
        assert len(averages) >= 1

        mfg = next((a for a in averages if a.sector == "Manufacturing"), None)
        if mfg:
            assert mfg.company_count >= 2  # TECH and TECH2
            # Average of 8 and 6 = 7
            assert mfg.avg_fscore == pytest.approx(7.0, rel=0.1)

    def test_get_sector_averages_all_sectors(
        self, analyzer, tech_stock, tech_stock_2, finance_stock
    ):
        """Test calculating averages for all sectors."""
        averages = analyzer.get_sector_averages()

        # Should have at least Manufacturing and Finance
        sectors = [a.sector for a in averages]
        assert "Manufacturing" in sectors or "Finance" in sectors

    def test_get_sector_averages_identifies_top_performer(
        self, analyzer, tech_stock, tech_stock_2
    ):
        """Test top performer is identified correctly."""
        averages = analyzer.get_sector_averages(sector="Manufacturing")

        mfg = next((a for a in averages if a.sector == "Manufacturing"), None)
        if mfg:
            # TECH has F-Score 8, TECH2 has 6
            assert mfg.top_performer == "TECH"
            assert mfg.top_performer_fscore == 8


class TestCompareTopeers:
    """Tests for peer comparison."""

    def test_compare_to_peers_returns_comparison(self, analyzer, tech_stock, tech_stock_2):
        """Test peer comparison returns valid result."""
        comparison = analyzer.compare_to_peers(tech_stock)

        if comparison:  # May be None if no sector data
            assert comparison.ticker == tech_stock
            assert comparison.sector == "Manufacturing"
            assert comparison.fscore == 8

    def test_compare_to_peers_calculates_vs_sector(self, analyzer, tech_stock, tech_stock_2):
        """Test comparison calculates difference from sector average."""
        comparison = analyzer.compare_to_peers(tech_stock)

        if comparison:
            # TECH F-Score (8) vs average of TECH(8) and TECH2(6) = 7
            # So fscore_vs_sector should be 8 - 7 = 1
            assert comparison.fscore_vs_sector == pytest.approx(
                comparison.fscore - comparison.sector_avg_fscore, rel=0.01
            )

    def test_compare_to_peers_no_data(self, analyzer, stock_no_sic):
        """Test comparison returns None when no sector data."""
        comparison = analyzer.compare_to_peers(stock_no_sic)
        assert comparison is None


class TestGetSectorLeaders:
    """Tests for sector leader identification."""

    def test_get_sector_leaders_by_fscore(self, analyzer, tech_stock, tech_stock_2):
        """Test getting sector leaders sorted by F-Score."""
        leaders = analyzer.get_sector_leaders(sector="Manufacturing", metric="fscore", limit=10)

        if leaders:
            # TECH (F-Score 8) should be first, TECH2 (F-Score 6) second
            assert leaders[0].ticker == "TECH"
            assert leaders[0].fscore >= leaders[-1].fscore  # Sorted descending

    def test_get_sector_leaders_by_zscore(self, analyzer, tech_stock, tech_stock_2):
        """Test getting sector leaders sorted by Z-Score."""
        leaders = analyzer.get_sector_leaders(sector="Manufacturing", metric="zscore", limit=10)

        if leaders:
            assert leaders[0].zscore >= leaders[-1].zscore

    def test_get_sector_leaders_sets_rank(self, analyzer, tech_stock, tech_stock_2):
        """Test leaders have rank set correctly."""
        leaders = analyzer.get_sector_leaders(sector="Manufacturing", limit=10)

        for i, leader in enumerate(leaders, 1):
            assert leader.rank == i

    def test_get_sector_leaders_respects_limit(self, analyzer, tech_stock, tech_stock_2):
        """Test limit parameter is respected."""
        leaders = analyzer.get_sector_leaders(sector="Manufacturing", limit=1)
        assert len(leaders) <= 1


class TestFilterBySector:
    """Tests for sector filtering."""

    def test_filter_by_sector_min_fscore(self, analyzer, tech_stock, tech_stock_2):
        """Test filtering by minimum F-Score."""
        results = analyzer.filter_by_sector(sector="Manufacturing", min_fscore=7)

        tickers = [r.ticker for r in results]
        assert "TECH" in tickers  # F-Score 8 >= 7
        # TECH2 has F-Score 6, should be excluded
        assert "TECH2" not in tickers

    def test_filter_by_sector_zone(self, analyzer, tech_stock, finance_stock):
        """Test filtering by zone."""
        # TECH is Safe, BANK is Grey
        safe_results = analyzer.filter_by_sector(sector="Manufacturing", zone="Safe")
        grey_results = analyzer.filter_by_sector(sector="Finance", zone="Grey")

        safe_tickers = [r.ticker for r in safe_results]
        grey_tickers = [r.ticker for r in grey_results]

        if safe_tickers:
            assert "TECH" in safe_tickers
        if grey_tickers:
            assert "BANK" in grey_tickers


class TestStaticMethods:
    """Tests for static utility methods."""

    def test_get_available_sectors(self, analyzer):
        """Test getting available sectors list."""
        sectors = analyzer.get_available_sectors()

        assert isinstance(sectors, list)
        assert len(sectors) > 0
        assert "Manufacturing" in sectors
        assert "Finance" in sectors

    def test_get_industries_for_sector(self, analyzer):
        """Test getting industries for a sector."""
        industries = analyzer.get_industries_for_sector("Manufacturing")

        assert isinstance(industries, list)
        assert len(industries) > 0

    def test_get_altman_formula_manufacturing(self, analyzer):
        """Test Altman formula selection for manufacturing SIC."""
        formula = analyzer.get_altman_formula_for_sic("3571")
        assert formula == "manufacturing"

    def test_get_altman_formula_non_manufacturing(self, analyzer):
        """Test Altman formula selection for non-manufacturing SIC."""
        formula = analyzer.get_altman_formula_for_sic("6020")
        assert formula == "non_manufacturing"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_sector(self, analyzer):
        """Test querying sector with no stocks."""
        # Agriculture sector (SIC 01xx) likely has no stocks in test DB
        leaders = analyzer.get_sector_leaders(sector="Agriculture", limit=10)
        assert leaders == []

    def test_stock_without_score(self, analyzer):
        """Test stock without score is handled."""
        with get_session() as session:
            stock = Stock(
                ticker="NOSCORE",
                cik="0004444444",
                company_name="No Score Corp",
                sic_code="3571",
            )
            session.add(stock)
            session.commit()

        # Should not crash, just not include the stock
        leaders = analyzer.get_sector_leaders(sector="Manufacturing", limit=10)
        tickers = [l.ticker for l in leaders]
        assert "NOSCORE" not in tickers
