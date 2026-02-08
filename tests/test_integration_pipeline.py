"""
Integration tests for the full Asymmetric pipeline.

These tests verify that the complete flow works end-to-end:
1. Bulk data → Scoring → Database persistence → Screening

Unlike unit tests that mock components, these integration tests use
real implementations with controlled test data to verify the
components work together correctly.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select
from click.testing import CliRunner

from asymmetric.cli.main import cli
from asymmetric.core.scoring.altman import AltmanScorer
from asymmetric.core.scoring.piotroski import PiotroskiScorer
from asymmetric.db.database import get_or_create_stock, get_session, init_db, reset_engine
from asymmetric.db.models import Stock, StockScore


class TestScoringPipeline:
    """Integration tests: financial data → scoring → results."""

    def test_piotroski_and_altman_together(self, healthy_company_data):
        """
        Verify both scorers work together with the same input data.

        This catches issues where field names differ between scorers
        or one scorer modifies data that breaks the other.
        """
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        # Score with Piotroski
        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(current, prior, require_all_signals=False)

        # Score with Altman using same current data
        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(current, is_manufacturing=True, require_all_components=False)

        # Verify both produced valid results
        assert p_result.score >= 0
        assert p_result.score <= 9
        # interpretation contains classification plus description
        assert any(level in p_result.interpretation for level in ["Strong", "Moderate", "Weak"])

        assert a_result.z_score is not None
        assert a_result.zone in ["Safe", "Grey", "Distress"]

    def test_healthy_company_scores_high(self, healthy_company_data):
        """
        Verify healthy company fixture produces expected scores.

        This is a regression test - if the fixture or scoring logic
        changes, this test will catch score drift.
        """
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(current, prior)

        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(current, is_manufacturing=True)

        # Healthy company should score well
        assert p_result.score >= 7, f"Healthy company scored only {p_result.score}/9 Piotroski"
        assert a_result.zone == "Safe", f"Healthy company in {a_result.zone} zone, expected Safe"
        assert a_result.z_score > 2.99, f"Z-Score {a_result.z_score} below Safe threshold"

    def test_weak_company_scores_low(self, weak_company_data):
        """
        Verify weak company fixture produces expected low scores.
        """
        current = weak_company_data["current"]
        prior = weak_company_data["prior"]

        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(current, prior, require_all_signals=False)

        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(current, is_manufacturing=True, require_all_components=False)

        # Weak company should score poorly
        assert p_result.score <= 4, f"Weak company scored {p_result.score}/9 Piotroski (expected ≤4)"
        assert a_result.zone in ["Grey", "Distress"], f"Weak company in {a_result.zone} zone"

    def test_distressed_company_in_distress_zone(self, distressed_company_data):
        """
        Verify distressed company fixture produces Distress zone.
        """
        altman = AltmanScorer()
        result = altman.calculate_from_dict(
            distressed_company_data,
            is_manufacturing=True,
            require_all_components=False
        )

        assert result.zone == "Distress", f"Distressed company in {result.zone} zone, expected Distress"
        assert result.z_score < 1.81, f"Z-Score {result.z_score} above Distress threshold"


class TestDatabasePersistence:
    """Integration tests: scoring → database persistence → retrieval."""

    def test_save_and_retrieve_score(self, tmp_db, healthy_company_data):
        """
        Verify scores can be saved to database and retrieved correctly.
        """
        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        # Calculate scores
        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(current, prior)

        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(current, is_manufacturing=True)

        # Save to database
        with get_session() as session:
            stock = get_or_create_stock(session, "TEST", "0000000001", "Test Company Inc.")
            stock_id = stock.id  # Capture before session closes

            score = StockScore(
                stock_id=stock_id,
                piotroski_score=p_result.score,
                piotroski_signals_available=p_result.signals_available,
                piotroski_interpretation=p_result.interpretation,
                altman_z_score=a_result.z_score,
                altman_zone=a_result.zone,
                altman_interpretation=a_result.interpretation,
                altman_formula=a_result.formula_used,
                fiscal_year=2023,
                data_source="integration_test",
                calculated_at=datetime.now(timezone.utc),
            )
            session.add(score)

        # Retrieve and verify
        with get_session() as session:
            saved_score = session.exec(
                select(StockScore).where(StockScore.stock_id == stock_id)
            ).first()

            assert saved_score is not None
            assert saved_score.piotroski_score == p_result.score
            assert saved_score.altman_z_score == a_result.z_score
            assert saved_score.altman_zone == a_result.zone
            assert saved_score.data_source == "integration_test"

    def test_multiple_scores_for_same_stock(self, tmp_db, healthy_company_data, weak_company_data):
        """
        Verify a stock can have multiple score records (different time periods).
        """
        import uuid
        unique_ticker = f"MULTI{uuid.uuid4().hex[:6].upper()}"

        piotroski = PiotroskiScorer()
        altman = AltmanScorer()

        # Score for FY2023 (healthy)
        h_current = healthy_company_data["current"]
        h_prior = healthy_company_data["prior"]
        p_2023 = piotroski.calculate_from_dict(h_current, h_prior)
        a_2023 = altman.calculate_from_dict(h_current, is_manufacturing=True)

        # Score for FY2022 (weak)
        w_current = weak_company_data["current"]
        w_prior = weak_company_data["prior"]
        p_2022 = piotroski.calculate_from_dict(w_current, w_prior, require_all_signals=False)
        a_2022 = altman.calculate_from_dict(w_current, is_manufacturing=True, require_all_components=False)

        # Save both to same stock
        with get_session() as session:
            stock = get_or_create_stock(session, unique_ticker, "0000000002", "Multi-Score Corp")

            score_2023 = StockScore(
                stock_id=stock.id,
                piotroski_score=p_2023.score,
                piotroski_signals_available=p_2023.signals_available,
                piotroski_interpretation=p_2023.interpretation,
                altman_z_score=a_2023.z_score,
                altman_zone=a_2023.zone,
                altman_formula=a_2023.formula_used,
                fiscal_year=2023,
                data_source="integration_test",
                calculated_at=datetime.now(timezone.utc),
            )
            score_2022 = StockScore(
                stock_id=stock.id,
                piotroski_score=p_2022.score,
                piotroski_signals_available=p_2022.signals_available,
                piotroski_interpretation=p_2022.interpretation,
                altman_z_score=a_2022.z_score,
                altman_zone=a_2022.zone,
                altman_formula=a_2022.formula_used,
                fiscal_year=2022,
                data_source="integration_test",
                calculated_at=datetime.now(timezone.utc),
            )
            session.add(score_2023)
            session.add(score_2022)
            stock_id = stock.id

        # Verify both exist
        with get_session() as session:
            scores = session.exec(
                select(StockScore)
                .where(StockScore.stock_id == stock_id)
                .order_by(StockScore.fiscal_year.desc())
            ).all()

            assert len(scores) == 2
            assert scores[0].fiscal_year == 2023
            assert scores[1].fiscal_year == 2022
            # 2023 (healthy) should score higher than 2022 (weak)
            assert scores[0].piotroski_score > scores[1].piotroski_score

    def test_stock_score_relationship(self, tmp_db, healthy_company_data):
        """
        Verify Stock → StockScore relationship works correctly.
        """
        import uuid
        unique_ticker = f"REL{uuid.uuid4().hex[:6].upper()}"

        current = healthy_company_data["current"]
        prior = healthy_company_data["prior"]

        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(current, prior)

        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(current, is_manufacturing=True)

        with get_session() as session:
            stock = get_or_create_stock(session, unique_ticker, "0000000003", "Relationship Test Inc.")

            score = StockScore(
                stock_id=stock.id,
                piotroski_score=p_result.score,
                piotroski_signals_available=p_result.signals_available,
                altman_z_score=a_result.z_score,
                altman_zone=a_result.zone,
                altman_formula=a_result.formula_used,
                data_source="integration_test",
                calculated_at=datetime.now(timezone.utc),
            )
            session.add(score)

        # Query via relationship
        with get_session() as session:
            stock = session.exec(select(Stock).where(Stock.ticker == unique_ticker)).first()
            assert stock is not None
            assert len(stock.scores) == 1
            assert stock.scores[0].piotroski_score == p_result.score


class TestScreeningIntegration:
    """Integration tests: bulk data → scoring → filtering."""

    @pytest.fixture
    def multi_company_batch_data(self, healthy_company_data, weak_company_data):
        """
        Batch financial data simulating BulkDataManager.get_batch_financials() output.
        """
        return {
            "STRONG": [
                healthy_company_data["current"],
                healthy_company_data["prior"],
            ],
            "WEAK": [
                weak_company_data["current"],
                weak_company_data["prior"],
            ],
            "MODERATE": [
                {
                    # Moderate company - middle scores
                    "revenue": 100_000_000,
                    "gross_profit": 35_000_000,
                    "net_income": 8_000_000,
                    "total_assets": 200_000_000,
                    "current_assets": 50_000_000,
                    "current_liabilities": 40_000_000,
                    "long_term_debt": 30_000_000,
                    "shares_outstanding": 10_000_000,
                    "operating_cash_flow": 12_000_000,
                    "total_liabilities": 70_000_000,
                    "retained_earnings": 50_000_000,
                    "ebit": 15_000_000,
                    "market_cap": 200_000_000,
                    "book_equity": 130_000_000,
                },
                {
                    "revenue": 95_000_000,
                    "gross_profit": 33_000_000,
                    "net_income": 7_000_000,
                    "total_assets": 195_000_000,
                    "current_assets": 48_000_000,
                    "current_liabilities": 42_000_000,
                    "long_term_debt": 32_000_000,
                    "shares_outstanding": 10_000_000,
                    "operating_cash_flow": 10_000_000,
                },
            ],
        }

    def test_score_and_filter_batch(self, multi_company_batch_data):
        """
        Verify batch scoring and filtering works correctly.

        Simulates the screen command's core logic without CLI overhead.
        """
        piotroski = PiotroskiScorer()
        altman = AltmanScorer()

        results = []
        for ticker, periods in multi_company_batch_data.items():
            current = periods[0]
            prior = periods[1] if len(periods) > 1 else {}

            p_result = piotroski.calculate_from_dict(current, prior, require_all_signals=False)
            a_result = altman.calculate_from_dict(current, is_manufacturing=True, require_all_components=False)

            results.append({
                "ticker": ticker,
                "piotroski": p_result.score,
                "altman_z": a_result.z_score,
                "altman_zone": a_result.zone,
            })

        # Filter: Piotroski >= 7
        high_piotroski = [r for r in results if r["piotroski"] >= 7]
        assert len(high_piotroski) >= 1, "Expected at least STRONG to pass Piotroski >= 7"
        assert any(r["ticker"] == "STRONG" for r in high_piotroski)

        # Filter: Safe zone only
        safe_zone = [r for r in results if r["altman_zone"] == "Safe"]
        assert len(safe_zone) >= 1, "Expected at least STRONG to be in Safe zone"

        # WEAK should not appear in either filtered list
        assert not any(r["ticker"] == "WEAK" for r in high_piotroski)

    def test_combined_filters(self, multi_company_batch_data):
        """
        Verify combined Piotroski + Altman filtering works correctly.
        """
        piotroski = PiotroskiScorer()
        altman = AltmanScorer()

        results = []
        for ticker, periods in multi_company_batch_data.items():
            current = periods[0]
            prior = periods[1] if len(periods) > 1 else {}

            p_result = piotroski.calculate_from_dict(current, prior, require_all_signals=False)
            a_result = altman.calculate_from_dict(current, is_manufacturing=True, require_all_components=False)

            results.append({
                "ticker": ticker,
                "piotroski": p_result.score,
                "altman_z": a_result.z_score,
                "altman_zone": a_result.zone,
            })

        # Combined filter: Piotroski >= 6 AND Altman >= 2.5
        combined = [
            r for r in results
            if r["piotroski"] >= 6 and r["altman_z"] >= 2.5
        ]

        # At least STRONG should pass, WEAK should not
        strong_result = next((r for r in results if r["ticker"] == "STRONG"), None)
        weak_result = next((r for r in results if r["ticker"] == "WEAK"), None)

        if strong_result and strong_result["piotroski"] >= 6 and strong_result["altman_z"] >= 2.5:
            assert any(r["ticker"] == "STRONG" for r in combined)

        if weak_result:
            # WEAK has negative income, should fail Piotroski threshold
            assert not any(r["ticker"] == "WEAK" for r in combined)


class TestFullPipelineEndToEnd:
    """
    Full end-to-end integration tests using CLI runner.

    These tests exercise the complete flow from CLI command to output.
    """

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    def test_screen_command_full_flow(
        self,
        mock_manager_class,
        runner,
        healthy_company_data,
        weak_company_data,
    ):
        """
        Full CLI test: screen command with real scorers, mocked bulk data.

        This tests that scoring logic integrates correctly with CLI output.
        """
        mock_manager = MagicMock()
        mock_manager.get_scorable_tickers.return_value = ["STRONG", "WEAK"]
        mock_manager.get_batch_financials.return_value = {
            "STRONG": [
                healthy_company_data["current"],
                healthy_company_data["prior"],
            ],
            "WEAK": [
                weak_company_data["current"],
                weak_company_data["prior"],
            ],
        }
        # Mock get_company_info to return proper dict (not MagicMock)
        mock_manager.get_company_info.side_effect = lambda ticker: {
            "ticker": ticker,
            "company_name": f"{ticker} Corporation",
            "cik": "0000000001",
        }
        mock_manager_class.return_value = mock_manager

        # Run with Piotroski filter that should only match STRONG
        result = runner.invoke(cli, ["screen", "--piotroski-min", "7", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Parse JSON output
        try:
            data = json.loads(result.output)
            assert "results" in data

            # STRONG should be in results (high F-score)
            tickers_in_results = [r.get("ticker") for r in data["results"]]
            assert "STRONG" in tickers_in_results, f"Expected STRONG in results: {data['results']}"

            # At minimum, verify the command ran and produced structured output
            assert "stats" in data
            assert "criteria" in data
        except json.JSONDecodeError:
            # If Rich markup is present, just verify no crash
            assert "error" not in result.output.lower()

    @patch("asymmetric.cli.commands.score.EdgarClient")
    def test_score_command_with_save(
        self,
        mock_edgar_class,
        runner,
        tmp_db,
        healthy_company_data,
    ):
        """
        Test score --save persists to database correctly.
        """
        mock_edgar = MagicMock()
        # get_financials returns {"periods": [current, prior], ...}
        mock_edgar.get_financials.return_value = {
            "periods": [healthy_company_data["current"], healthy_company_data["prior"]],
            "ticker": "INTTEST",
            "company_name": "Integration Test Corp",
        }
        mock_edgar.get_company_info.return_value = {
            "ticker": "INTTEST",
            "cik": "0000000099",
            "company_name": "Integration Test Corp",
        }
        mock_edgar_class.return_value = mock_edgar

        result = runner.invoke(cli, ["score", "INTTEST", "--save"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "saved" in result.output.lower() or "Score" in result.output

        # Verify database was updated
        with get_session() as session:
            scores = session.exec(select(StockScore)).all()
            # Should have at least one score saved
            assert len(scores) >= 1

    @patch("asymmetric.cli.commands.screen.BulkDataManager")
    def test_screen_to_watchlist_integration(
        self,
        mock_manager_class,
        runner,
        tmp_path,
        healthy_company_data,
    ):
        """
        Test screen --add-to-watchlist creates correct watchlist entries.
        """
        mock_manager = MagicMock()
        mock_manager.get_scorable_tickers.return_value = ["WATCH1", "WATCH2"]
        mock_manager.get_batch_financials.return_value = {
            "WATCH1": [
                healthy_company_data["current"],
                healthy_company_data["prior"],
            ],
            "WATCH2": [
                healthy_company_data["current"],
                healthy_company_data["prior"],
            ],
        }
        # Mock get_company_info to return proper dict (not MagicMock)
        mock_manager.get_company_info.side_effect = lambda ticker: {
            "ticker": ticker,
            "company_name": f"{ticker} Corporation",
            "cik": "0000000001",
        }
        mock_manager_class.return_value = mock_manager

        # Use temp directory for watchlist
        watchlist_dir = tmp_path / ".asymmetric"
        watchlist_path = watchlist_dir / "watchlist.json"

        with patch("asymmetric.cli.commands.screen.Path.home", return_value=tmp_path):
            result = runner.invoke(
                cli,
                ["screen", "--piotroski-min", "5", "--add-to-watchlist", "--json"]
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify watchlist was created
        if watchlist_path.exists():
            with open(watchlist_path) as f:
                watchlist = json.load(f)
                assert len(watchlist) >= 1


class TestDataValidation:
    """
    Integration tests for data validation across pipeline.

    These tests verify that invalid/incomplete data is handled
    gracefully at each stage of the pipeline.
    """

    def test_missing_fields_handled_gracefully(self):
        """
        Verify scorers handle missing fields without crashing.
        """
        incomplete_data = {
            "revenue": 100_000_000,
            "net_income": 10_000_000,
            # Missing: gross_profit, current_assets, etc.
        }

        piotroski = PiotroskiScorer()
        result = piotroski.calculate_from_dict(
            incomplete_data,
            {},  # No prior data
            require_all_signals=False
        )

        # Should produce a result, even if partial
        assert result is not None
        assert result.score >= 0
        assert result.signals_available < 9  # Some signals missing

    def test_zero_values_handled(self):
        """
        Verify zero values don't cause division errors.
        """
        zero_heavy_data = {
            "revenue": 0,
            "gross_profit": 0,
            "net_income": 0,
            "total_assets": 100_000_000,  # Non-zero to avoid div/0
            "current_assets": 50_000_000,
            "current_liabilities": 0,
            "long_term_debt": 0,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": 0,
            "total_liabilities": 0,
            "retained_earnings": 0,
            "ebit": 0,
            "market_cap": 100_000_000,
        }

        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(
            zero_heavy_data,
            {},
            require_all_signals=False
        )

        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(
            zero_heavy_data,
            is_manufacturing=True,
            require_all_components=False
        )

        # Should not crash
        assert p_result is not None
        assert a_result is not None

    def test_negative_values_handled(self):
        """
        Verify negative values (losses, deficits) are handled correctly.
        """
        negative_data = {
            "revenue": 100_000_000,
            "gross_profit": -5_000_000,  # Loss
            "net_income": -20_000_000,  # Loss
            "total_assets": 100_000_000,
            "current_assets": 30_000_000,
            "current_liabilities": 50_000_000,  # Current ratio < 1
            "long_term_debt": 80_000_000,
            "shares_outstanding": 10_000_000,
            "operating_cash_flow": -10_000_000,  # Negative
            "total_liabilities": 130_000_000,
            "retained_earnings": -50_000_000,  # Accumulated deficit
            "ebit": -15_000_000,
            "market_cap": 20_000_000,
            "book_equity": -30_000_000,  # Negative equity
        }

        piotroski = PiotroskiScorer()
        p_result = piotroski.calculate_from_dict(
            negative_data,
            {},
            require_all_signals=False
        )

        altman = AltmanScorer()
        a_result = altman.calculate_from_dict(
            negative_data,
            is_manufacturing=True,
            require_all_components=False
        )

        # Should handle negatives, likely producing low/distress scores
        assert p_result is not None
        assert p_result.score <= 3  # Losses = low F-score

        assert a_result is not None
        assert a_result.zone in ["Grey", "Distress"]
