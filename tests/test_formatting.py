"""
Tests for the CLI formatting module.

Tests cover:
- Score color functions (F-Score, Altman zone, actions)
- Verdict functions (plain English interpretations)
- Signal indicators (unicode symbols)
- Quick signals (profitability, leverage, efficiency)
- Progress bar rendering
- Winner highlighting for comparisons
"""

import pytest

from asymmetric.cli.formatting import (
    get_score_color,
    get_zone_color,
    get_action_color,
    get_fscore_verdict,
    get_zscore_verdict,
    Signals,
    signal_indicator,
    get_profitability_signal,
    get_leverage_signal,
    get_efficiency_signal,
    get_quick_signals,
    make_progress_bar,
    highlight_winner,
    winner_indicator,
)


class TestGetScoreColor:
    """Tests for get_score_color function."""

    def test_high_score_returns_green(self):
        """Test that scores >= 70% return green."""
        assert get_score_color(7, 10) == "green"
        assert get_score_color(8, 10) == "green"
        assert get_score_color(9, 10) == "green"
        assert get_score_color(10, 10) == "green"

    def test_medium_score_returns_yellow(self):
        """Test that scores 40-69% return yellow."""
        assert get_score_color(5, 10) == "yellow"
        assert get_score_color(6, 10) == "yellow"

    def test_low_score_returns_red(self):
        """Test that scores < 40% return red."""
        assert get_score_color(3, 10) == "red"
        assert get_score_color(2, 10) == "red"
        assert get_score_color(1, 10) == "red"
        assert get_score_color(0, 10) == "red"

    def test_boundary_at_70_percent(self):
        """Test exact 70% boundary returns green."""
        assert get_score_color(7, 10) == "green"

    def test_boundary_at_40_percent(self):
        """Test exact 40% boundary returns yellow."""
        assert get_score_color(4, 10) == "yellow"

    def test_just_under_40_percent(self):
        """Test 39% returns red."""
        assert get_score_color(39, 100) == "red"

    def test_perfect_fscore(self):
        """Test perfect F-Score (9/9) returns green."""
        assert get_score_color(9, 9) == "green"

    def test_zero_score(self):
        """Test zero score returns red."""
        assert get_score_color(0, 9) == "red"


class TestGetZoneColor:
    """Tests for get_zone_color function."""

    def test_safe_zone_returns_green(self):
        """Test Safe zone returns green."""
        assert get_zone_color("Safe") == "green"

    def test_grey_zone_returns_yellow(self):
        """Test Grey zone returns yellow."""
        assert get_zone_color("Grey") == "yellow"

    def test_distress_zone_returns_red(self):
        """Test Distress zone returns red."""
        assert get_zone_color("Distress") == "red"

    def test_unknown_zone_returns_white(self):
        """Test unknown zone returns white (fallback)."""
        assert get_zone_color("Unknown") == "white"

    def test_empty_string_returns_white(self):
        """Test empty string returns white (fallback)."""
        assert get_zone_color("") == "white"


class TestGetActionColor:
    """Tests for get_action_color function."""

    def test_buy_returns_green(self):
        """Test buy action returns green."""
        assert get_action_color("buy") == "green"

    def test_hold_returns_yellow(self):
        """Test hold action returns yellow."""
        assert get_action_color("hold") == "yellow"

    def test_sell_returns_red(self):
        """Test sell action returns red."""
        assert get_action_color("sell") == "red"

    def test_pass_returns_dim(self):
        """Test pass action returns dim."""
        assert get_action_color("pass") == "dim"

    def test_case_insensitive(self):
        """Test action matching is case insensitive."""
        assert get_action_color("BUY") == "green"
        assert get_action_color("Buy") == "green"
        assert get_action_color("HOLD") == "yellow"
        assert get_action_color("SELL") == "red"
        assert get_action_color("PASS") == "dim"

    def test_unknown_action_returns_white(self):
        """Test unknown action returns white (fallback)."""
        assert get_action_color("watch") == "white"
        assert get_action_color("") == "white"


class TestGetFscoreVerdict:
    """Tests for get_fscore_verdict function."""

    def test_strong_score_7(self):
        """Test F-Score 7 returns Financially Strong."""
        text, color = get_fscore_verdict(7)
        assert text == "Financially Strong"
        assert color == "green"

    def test_strong_score_8(self):
        """Test F-Score 8 returns Financially Strong."""
        text, color = get_fscore_verdict(8)
        assert text == "Financially Strong"
        assert color == "green"

    def test_strong_score_9(self):
        """Test F-Score 9 returns Financially Strong."""
        text, color = get_fscore_verdict(9)
        assert text == "Financially Strong"
        assert color == "green"

    def test_moderate_score_5(self):
        """Test F-Score 5 returns Moderate Health."""
        text, color = get_fscore_verdict(5)
        assert text == "Moderate Health"
        assert color == "yellow"

    def test_moderate_boundary_4(self):
        """Test F-Score 4 boundary returns Moderate Health."""
        text, color = get_fscore_verdict(4)
        assert text == "Moderate Health"
        assert color == "yellow"

    def test_moderate_boundary_6(self):
        """Test F-Score 6 boundary returns Moderate Health."""
        text, color = get_fscore_verdict(6)
        assert text == "Moderate Health"
        assert color == "yellow"

    def test_concerns_score_3(self):
        """Test F-Score 3 returns Financial Concerns."""
        text, color = get_fscore_verdict(3)
        assert text == "Financial Concerns"
        assert color == "red"

    def test_concerns_score_0(self):
        """Test F-Score 0 returns Financial Concerns."""
        text, color = get_fscore_verdict(0)
        assert text == "Financial Concerns"
        assert color == "red"


class TestGetZscoreVerdict:
    """Tests for get_zscore_verdict function."""

    def test_safe_zone(self):
        """Test Safe zone returns Low Bankruptcy Risk."""
        text, color = get_zscore_verdict("Safe")
        assert text == "Low Bankruptcy Risk"
        assert color == "green"

    def test_grey_zone(self):
        """Test Grey zone returns Uncertain Risk."""
        text, color = get_zscore_verdict("Grey")
        assert text == "Uncertain Risk"
        assert color == "yellow"

    def test_distress_zone(self):
        """Test Distress zone returns High Bankruptcy Risk."""
        text, color = get_zscore_verdict("Distress")
        assert text == "High Bankruptcy Risk"
        assert color == "red"

    def test_unknown_zone(self):
        """Test unknown zone returns Unknown."""
        text, color = get_zscore_verdict("Other")
        assert text == "Unknown"
        assert color == "white"


class TestSignals:
    """Tests for Signals class constants."""

    def test_check_symbol_exists(self):
        """Test CHECK symbol is defined."""
        assert Signals.CHECK is not None
        assert len(Signals.CHECK) > 0

    def test_cross_symbol_exists(self):
        """Test CROSS symbol is defined."""
        assert Signals.CROSS is not None
        assert len(Signals.CROSS) > 0

    def test_tilde_symbol_exists(self):
        """Test TILDE symbol is defined."""
        assert Signals.TILDE is not None
        assert len(Signals.TILDE) > 0

    def test_warning_symbol_exists(self):
        """Test WARNING symbol is defined."""
        assert Signals.WARNING is not None
        assert len(Signals.WARNING) > 0

    def test_winner_symbol_exists(self):
        """Test WINNER symbol is defined."""
        assert Signals.WINNER is not None
        assert len(Signals.WINNER) > 0

    def test_star_symbol_exists(self):
        """Test STAR symbol is defined."""
        assert Signals.STAR is not None
        assert len(Signals.STAR) > 0


class TestSignalIndicator:
    """Tests for signal_indicator function."""

    def test_passed_returns_check_green(self):
        """Test True returns check symbol in green."""
        symbol, color = signal_indicator(True)
        assert symbol == Signals.CHECK
        assert color == "green"

    def test_failed_returns_cross_red(self):
        """Test False returns cross symbol in red."""
        symbol, color = signal_indicator(False)
        assert symbol == Signals.CROSS
        assert color == "red"

    def test_none_returns_tilde_dim(self):
        """Test None returns tilde symbol in dim."""
        symbol, color = signal_indicator(None)
        assert symbol == Signals.TILDE
        assert color == "dim"


class TestProfitabilitySignal:
    """Tests for get_profitability_signal function."""

    def test_high_score_3(self):
        """Test score 3 returns Profitable in green."""
        symbol, text, color = get_profitability_signal(3)
        assert text == "Profitable"
        assert color == "green"
        assert symbol == Signals.CHECK

    def test_high_score_4(self):
        """Test score 4 returns Profitable in green."""
        symbol, text, color = get_profitability_signal(4)
        assert text == "Profitable"
        assert color == "green"

    def test_medium_score_2(self):
        """Test score 2 returns Marginally profitable in yellow."""
        symbol, text, color = get_profitability_signal(2)
        assert text == "Marginally profitable"
        assert color == "yellow"
        assert symbol == Signals.TILDE

    def test_low_score_1(self):
        """Test score 1 returns Unprofitable in red."""
        symbol, text, color = get_profitability_signal(1)
        assert text == "Unprofitable"
        assert color == "red"
        assert symbol == Signals.CROSS

    def test_low_score_0(self):
        """Test score 0 returns Unprofitable in red."""
        symbol, text, color = get_profitability_signal(0)
        assert text == "Unprofitable"
        assert color == "red"


class TestLeverageSignal:
    """Tests for get_leverage_signal function."""

    def test_low_debt_score_2(self):
        """Test score 2 returns Low debt in green."""
        symbol, text, color = get_leverage_signal(2)
        assert text == "Low debt"
        assert color == "green"
        assert symbol == Signals.CHECK

    def test_low_debt_score_3(self):
        """Test score 3 returns Low debt in green."""
        symbol, text, color = get_leverage_signal(3)
        assert text == "Low debt"
        assert color == "green"

    def test_moderate_debt_score_1(self):
        """Test score 1 returns Moderate debt in yellow."""
        symbol, text, color = get_leverage_signal(1)
        assert text == "Moderate debt"
        assert color == "yellow"
        assert symbol == Signals.TILDE

    def test_high_debt_score_0(self):
        """Test score 0 returns High debt in red."""
        symbol, text, color = get_leverage_signal(0)
        assert text == "High debt"
        assert color == "red"
        assert symbol == Signals.WARNING


class TestEfficiencySignal:
    """Tests for get_efficiency_signal function.

    Note: This verifies the bug fix where declining efficiency (score 0)
    now correctly returns red instead of yellow.
    """

    def test_efficient_score_2(self):
        """Test score 2 returns Efficient operations in green."""
        symbol, text, color = get_efficiency_signal(2)
        assert text == "Efficient operations"
        assert color == "green"
        assert symbol == Signals.CHECK

    def test_mixed_efficiency_score_1(self):
        """Test score 1 returns Mixed efficiency in yellow."""
        symbol, text, color = get_efficiency_signal(1)
        assert text == "Mixed efficiency"
        assert color == "yellow"
        assert symbol == Signals.TILDE

    def test_declining_efficiency_score_0(self):
        """Test score 0 returns Declining efficiency in red (bug fix verified)."""
        symbol, text, color = get_efficiency_signal(0)
        assert text == "Declining efficiency"
        assert color == "red"  # This was incorrectly yellow before the fix
        assert symbol == Signals.WARNING


class TestGetQuickSignals:
    """Tests for get_quick_signals function."""

    def test_full_data_returns_three_signals(self):
        """Test valid data returns list of 3 signal tuples."""
        piotroski = {
            "profitability_score": 3,
            "leverage_score": 2,
            "efficiency_score": 2,
        }
        altman = {"zone": "Safe"}

        signals = get_quick_signals(piotroski, altman)

        assert len(signals) == 3
        # Each signal is a tuple of (symbol, text, color)
        for signal in signals:
            assert len(signal) == 3

    def test_error_in_result_returns_empty(self):
        """Test dict with error key returns empty list."""
        piotroski = {"error": "No data available"}
        altman = {}

        signals = get_quick_signals(piotroski, altman)

        assert signals == []

    def test_empty_result_returns_empty(self):
        """Test empty dict returns empty list (falsy in Python)."""
        piotroski = {}
        altman = {}

        signals = get_quick_signals(piotroski, altman)

        # Empty dict is falsy in Python, so returns empty list
        assert signals == []

    def test_none_result_returns_empty(self):
        """Test None result returns empty list."""
        signals = get_quick_signals(None, None)

        assert signals == []

    def test_missing_subscores_use_zero(self):
        """Test missing subscores default to 0."""
        piotroski = {"profitability_score": 3}  # Missing leverage and efficiency
        altman = {}

        signals = get_quick_signals(piotroski, altman)

        assert len(signals) == 3
        # Profitability should be "Profitable"
        assert signals[0][1] == "Profitable"
        # Leverage defaults to 0 = "High debt"
        assert signals[1][1] == "High debt"
        # Efficiency defaults to 0 = "Declining efficiency"
        assert signals[2][1] == "Declining efficiency"


class TestMakeProgressBar:
    """Tests for make_progress_bar function."""

    def test_full_bar(self):
        """Test 100% filled bar."""
        bar = make_progress_bar(10, 10, 10)
        assert len(bar) == 10
        assert bar.count("\u2588") == 10  # All filled
        assert bar.count("\u2591") == 0  # None empty

    def test_empty_bar(self):
        """Test 0% filled bar."""
        bar = make_progress_bar(0, 10, 10)
        assert len(bar) == 10
        assert bar.count("\u2588") == 0  # None filled
        assert bar.count("\u2591") == 10  # All empty

    def test_half_bar(self):
        """Test 50% filled bar."""
        bar = make_progress_bar(5, 10, 10)
        assert len(bar) == 10
        assert bar.count("\u2588") == 5
        assert bar.count("\u2591") == 5

    def test_custom_width(self):
        """Test custom width parameter."""
        bar = make_progress_bar(5, 10, 20)
        assert len(bar) == 20
        assert bar.count("\u2588") == 10
        assert bar.count("\u2591") == 10

    def test_fractional_value(self):
        """Test fractional percentage (30%)."""
        bar = make_progress_bar(3, 10, 10)
        assert len(bar) == 10
        assert bar.count("\u2588") == 3
        assert bar.count("\u2591") == 7

    def test_default_width(self):
        """Test default width is 10."""
        bar = make_progress_bar(5, 10)
        assert len(bar) == 10


class TestHighlightWinner:
    """Tests for highlight_winner function.

    Note: Basic tests exist in test_compare_command.py.
    These cover additional edge cases.
    """

    def test_empty_list_returns_empty(self):
        """Test empty list returns empty list."""
        colors = highlight_winner([])
        assert colors == []

    def test_single_element_is_winner(self):
        """Test single element is always the winner."""
        colors = highlight_winner([5])
        assert colors == ["green"]

    def test_negative_values(self):
        """Test negative values are handled correctly."""
        values = [-5, -3, -8]
        colors = highlight_winner(values, higher_is_better=True)
        assert colors[1] == "green"  # -3 is highest

    def test_negative_values_lower_is_better(self):
        """Test negative values with lower_is_better."""
        values = [-5, -3, -8]
        colors = highlight_winner(values, higher_is_better=False)
        assert colors[2] == "green"  # -8 is lowest

    def test_float_values(self):
        """Test float values are handled correctly."""
        values = [1.5, 2.5, 1.8]
        colors = highlight_winner(values, higher_is_better=True)
        assert colors[1] == "green"  # 2.5 is highest

    def test_mixed_int_float(self):
        """Test mixed int and float values."""
        values = [2, 2.5, 1]
        colors = highlight_winner(values, higher_is_better=True)
        assert colors[1] == "green"  # 2.5 is highest


class TestWinnerIndicator:
    """Tests for winner_indicator function."""

    def test_winner_returns_diamond(self):
        """Test is_winner=True returns winner diamond symbol."""
        result = winner_indicator(True)
        assert Signals.WINNER in result

    def test_not_winner_returns_empty(self):
        """Test is_winner=False returns empty string."""
        result = winner_indicator(False)
        assert result == ""
