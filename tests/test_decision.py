"""Tests for decision command group."""

import json
import pytest
from click.testing import CliRunner

from asymmetric.cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def existing_thesis(tmp_db):
    """Create a thesis for testing decision linking."""
    from asymmetric.db import get_session, init_db, Thesis
    from asymmetric.db.database import get_or_create_stock

    init_db()

    with get_session() as session:
        stock = get_or_create_stock("AAPL")
        stock = session.merge(stock)
        thesis = Thesis(
            stock_id=stock.id,
            summary="Test thesis for AAPL",
            analysis_text="Test analysis text",
            status="active",
        )
        session.add(thesis)
        session.flush()
        thesis_id = thesis.id

    return thesis_id


@pytest.fixture
def existing_decision(tmp_db, existing_thesis):
    """Create a decision for testing view command."""
    from asymmetric.db import get_session, Decision
    from datetime import datetime

    with get_session() as session:
        decision = Decision(
            thesis_id=existing_thesis,
            decision="buy",
            rationale="Test buy decision",
            confidence=4,
            target_price=150.00,
            stop_loss=120.00,
            decided_at=datetime.utcnow(),
        )
        session.add(decision)
        session.flush()
        decision_id = decision.id

    return decision_id


class TestDecisionCreate:
    """Tests for decision create command."""

    def test_create_buy_decision(self, runner, tmp_db):
        """Test creating a buy decision."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--confidence", "4",
        ])

        assert result.exit_code == 0
        assert "Decision recorded" in result.output
        assert "BUY" in result.output

    def test_create_sell_decision(self, runner, tmp_db):
        """Test creating a sell decision."""
        result = runner.invoke(cli, [
            "decision", "create", "MSFT",
            "--action", "sell",
        ])

        assert result.exit_code == 0
        assert "Decision recorded" in result.output
        assert "SELL" in result.output

    def test_create_hold_decision(self, runner, tmp_db):
        """Test creating a hold decision."""
        result = runner.invoke(cli, [
            "decision", "create", "GOOG",
            "--action", "hold",
        ])

        assert result.exit_code == 0
        assert "HOLD" in result.output

    def test_create_pass_decision(self, runner, tmp_db):
        """Test creating a pass decision."""
        result = runner.invoke(cli, [
            "decision", "create", "META",
            "--action", "pass",
            "--notes", "Not a good fit for portfolio",
        ])

        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_create_with_thesis_link(self, runner, tmp_db, existing_thesis):
        """Test creating decision linked to existing thesis."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--thesis", str(existing_thesis),
        ])

        assert result.exit_code == 0
        assert "Decision recorded" in result.output

    def test_create_with_invalid_thesis(self, runner, tmp_db):
        """Test creating decision with non-existent thesis fails."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--thesis", "99999",
        ])

        assert result.exit_code == 1
        assert "Thesis not found" in result.output

    def test_create_with_target_price(self, runner, tmp_db):
        """Test creating decision with target price."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--target-price", "200.00",
        ])

        assert result.exit_code == 0
        assert "$200.00" in result.output

    def test_create_with_stop_loss(self, runner, tmp_db):
        """Test creating decision with stop loss."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--stop-loss", "150.00",
        ])

        assert result.exit_code == 0
        assert "$150.00" in result.output

    def test_create_with_notes(self, runner, tmp_db):
        """Test creating decision with notes."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--notes", "Strong fundamentals and growth potential",
        ])

        assert result.exit_code == 0
        assert "Strong fundamentals" in result.output

    def test_invalid_confidence_too_high(self, runner, tmp_db):
        """Test confidence validation rejects values > 5."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--confidence", "6",
        ])

        # Click's IntRange validation returns exit code 2 (usage error)
        assert result.exit_code == 2
        assert "6 is not in the range 1<=x<=5" in result.output

    def test_invalid_confidence_too_low(self, runner, tmp_db):
        """Test confidence validation rejects values < 1."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
            "--action", "buy",
            "--confidence", "0",
        ])

        # Click's IntRange validation returns exit code 2 (usage error)
        assert result.exit_code == 2
        assert "0 is not in the range 1<=x<=5" in result.output

    def test_action_required(self, runner, tmp_db):
        """Test that --action is required."""
        result = runner.invoke(cli, [
            "decision", "create", "AAPL",
        ])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_ticker_uppercase(self, runner, tmp_db):
        """Test ticker is converted to uppercase."""
        result = runner.invoke(cli, [
            "decision", "create", "aapl",
            "--action", "buy",
        ])

        assert result.exit_code == 0
        assert "AAPL" in result.output


class TestDecisionList:
    """Tests for decision list command."""

    def test_list_command_works(self, runner, tmp_db):
        """Test listing command runs successfully."""
        result = runner.invoke(cli, ["decision", "list"])

        assert result.exit_code == 0
        # Either shows "No decisions found" or shows a table with decisions
        assert "No decisions found" in result.output or "Investment Decisions" in result.output

    def test_list_shows_decisions(self, runner, tmp_db, existing_decision):
        """Test listing shows existing decisions."""
        result = runner.invoke(cli, ["decision", "list"])

        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "BUY" in result.output

    def test_list_filter_by_action(self, runner, tmp_db, existing_decision):
        """Test filtering by action type."""
        # existing_decision is "buy"
        result = runner.invoke(cli, ["decision", "list", "--action", "buy"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

        # Should not show if filtering for "sell"
        result = runner.invoke(cli, ["decision", "list", "--action", "sell"])
        assert result.exit_code == 0
        # AAPL should not appear since it's a buy decision
        # (but we might still see empty table or "No decisions")

    def test_list_filter_by_ticker(self, runner, tmp_db, existing_decision):
        """Test filtering by ticker."""
        result = runner.invoke(cli, ["decision", "list", "--ticker", "AAPL"])

        assert result.exit_code == 0
        assert "AAPL" in result.output

    def test_list_limit(self, runner, tmp_db, existing_decision):
        """Test limiting results."""
        result = runner.invoke(cli, ["decision", "list", "--limit", "1"])

        assert result.exit_code == 0

    def test_list_json_output(self, runner, tmp_db, existing_decision):
        """Test JSON output format."""
        result = runner.invoke(cli, ["decision", "list", "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) >= 1
        assert output[0]["ticker"] == "AAPL"
        assert output[0]["action"] == "buy"


class TestDecisionView:
    """Tests for decision view command."""

    def test_view_existing(self, runner, tmp_db, existing_decision):
        """Test viewing an existing decision."""
        result = runner.invoke(cli, ["decision", "view", str(existing_decision)])

        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "BUY" in result.output
        assert "$150.00" in result.output  # target price
        assert "$120.00" in result.output  # stop loss

    def test_view_not_found(self, runner, tmp_db):
        """Test viewing non-existent decision."""
        result = runner.invoke(cli, ["decision", "view", "99999"])

        assert result.exit_code == 1
        assert "Decision not found" in result.output

    def test_view_json_output(self, runner, tmp_db, existing_decision):
        """Test JSON output format for view."""
        result = runner.invoke(cli, ["decision", "view", str(existing_decision), "--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == existing_decision
        assert output["ticker"] == "AAPL"
        assert output["action"] == "buy"
        assert output["confidence"] == 4

    def test_view_shows_rationale(self, runner, tmp_db, existing_decision):
        """Test view shows rationale panel."""
        result = runner.invoke(cli, ["decision", "view", str(existing_decision)])

        assert result.exit_code == 0
        assert "Test buy decision" in result.output


class TestDecisionHelp:
    """Tests for decision command help."""

    def test_decision_help(self, runner):
        """Test decision group help."""
        result = runner.invoke(cli, ["decision", "--help"])

        assert result.exit_code == 0
        assert "Track investment decisions" in result.output
        assert "create" in result.output
        assert "list" in result.output
        assert "view" in result.output

    def test_decision_create_help(self, runner):
        """Test decision create help."""
        result = runner.invoke(cli, ["decision", "create", "--help"])

        assert result.exit_code == 0
        assert "--action" in result.output
        assert "--thesis" in result.output
        assert "--target-price" in result.output
        assert "--stop-loss" in result.output
        assert "--confidence" in result.output
        assert "--notes" in result.output
