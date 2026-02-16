"""Tests for CLI input validation utilities."""

import pytest
import click

from asymmetric.cli.validators import (
    TICKER_PATTERN,
    _validate_ticker_format,
    validate_ticker,
    validate_positive_float,
    validate_price_relationship,
    validate_text_length,
    TickerType,
    TICKER,
)


class TestTickerPattern:
    """Tests for ticker regex pattern."""

    @pytest.mark.parametrize("ticker", [
        "A", "AA", "AAPL", "GOOGL", "BRK.A", "BRK.B",
        "BRK-B", "A1", "123", "BF.B",
    ])
    def test_valid_tickers(self, ticker):
        assert TICKER_PATTERN.match(ticker)

    @pytest.mark.parametrize("ticker", [
        "", "TOOLONGXXXX1", "aapl", "$AAPL", "AA PL",
    ])
    def test_invalid_tickers(self, ticker):
        assert not TICKER_PATTERN.match(ticker)


class TestValidateTickerFormat:
    """Tests for _validate_ticker_format()."""

    def test_valid_standard_ticker(self):
        assert _validate_ticker_format("AAPL") == "AAPL"
        assert _validate_ticker_format("MSFT") == "MSFT"

    def test_valid_class_ticker(self):
        assert _validate_ticker_format("BRK.A") == "BRK.A"
        assert _validate_ticker_format("BRK.B") == "BRK.B"

    def test_single_letter_ticker(self):
        assert _validate_ticker_format("A") == "A"

    def test_valid_hyphenated_ticker(self):
        assert _validate_ticker_format("BRK-B") == "BRK-B"

    def test_valid_numeric_ticker(self):
        assert _validate_ticker_format("3M") == "3M"

    def test_invalid_too_long(self):
        with pytest.raises(ValueError, match="Invalid ticker format"):
            _validate_ticker_format("TOOLONGXXXX1")

    def test_invalid_lowercase(self):
        with pytest.raises(ValueError, match="Invalid ticker format"):
            _validate_ticker_format("aapl")

    def test_invalid_special_chars(self):
        with pytest.raises(ValueError, match="Invalid ticker format"):
            _validate_ticker_format("$AAPL")


class TestValidateTicker:
    """Tests for validate_ticker() Click callback."""

    def test_normalizes_to_uppercase(self):
        # Create minimal click context
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--ticker"])
        result = validate_ticker(ctx, param, "aapl")
        assert result == "AAPL"

    def test_strips_whitespace(self):
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--ticker"])
        result = validate_ticker(ctx, param, "  AAPL  ")
        assert result == "AAPL"

    def test_empty_raises_bad_parameter(self):
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--ticker"])
        with pytest.raises(click.BadParameter, match="required"):
            validate_ticker(ctx, param, "")

    def test_invalid_format_raises_bad_parameter(self):
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--ticker"])
        with pytest.raises(click.BadParameter, match="Invalid ticker"):
            validate_ticker(ctx, param, "TOOLONGXXXX1")


class TestValidatePositiveFloat:
    """Tests for validate_positive_float() factory."""

    def test_none_passthrough(self):
        validator = validate_positive_float("price")
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--price"])
        assert validator(ctx, param, None) is None

    def test_positive_value_accepted(self):
        validator = validate_positive_float("price")
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--price"])
        assert validator(ctx, param, 100.0) == 100.0

    def test_zero_rejected(self):
        validator = validate_positive_float("price")
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--price"])
        with pytest.raises(click.BadParameter, match="greater than 0"):
            validator(ctx, param, 0.0)

    def test_negative_rejected(self):
        validator = validate_positive_float("price")
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--price"])
        with pytest.raises(click.BadParameter, match="greater than 0"):
            validator(ctx, param, -5.0)

    def test_min_val_enforced(self):
        validator = validate_positive_float("price", min_val=10.0)
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--price"])
        with pytest.raises(click.BadParameter, match="at least 10"):
            validator(ctx, param, 5.0)
        assert validator(ctx, param, 10.0) == 10.0

    def test_max_val_enforced(self):
        validator = validate_positive_float("price", max_val=100.0)
        ctx = click.Context(click.Command("test"))
        param = click.Option(["--price"])
        with pytest.raises(click.BadParameter, match="at most 100"):
            validator(ctx, param, 150.0)
        assert validator(ctx, param, 100.0) == 100.0


class TestValidatePriceRelationship:
    """Tests for validate_price_relationship()."""

    def test_none_values_allowed(self):
        # No error when either value is None
        validate_price_relationship(None, 100.0, "buy")
        validate_price_relationship(150.0, None, "buy")
        validate_price_relationship(None, None, "buy")

    def test_buy_target_above_stop(self):
        # Valid: target > stop_loss
        validate_price_relationship(150.0, 140.0, "buy")

    def test_buy_target_below_stop_raises(self):
        with pytest.raises(click.BadParameter, match="must be greater"):
            validate_price_relationship(140.0, 150.0, "buy")

    def test_hold_target_above_stop(self):
        validate_price_relationship(200.0, 180.0, "hold")

    def test_hold_target_below_stop_raises(self):
        with pytest.raises(click.BadParameter, match="must be greater"):
            validate_price_relationship(180.0, 200.0, "hold")

    def test_sell_any_relationship_allowed(self):
        # For sell/pass, relationship doesn't matter
        validate_price_relationship(100.0, 150.0, "sell")
        validate_price_relationship(100.0, 150.0, "pass")


class TestValidateTextLength:
    """Tests for validate_text_length()."""

    def test_none_passthrough(self):
        result, truncated = validate_text_length(None, 100, "notes")
        assert result is None
        assert truncated is False

    def test_short_text_unchanged(self):
        result, truncated = validate_text_length("short", 100, "notes")
        assert result == "short"
        assert truncated is False

    def test_long_text_truncated(self):
        long_text = "x" * 150
        result, truncated = validate_text_length(long_text, 100, "notes", truncate=True)
        assert len(result) == 100
        assert truncated is True

    def test_long_text_raises_when_no_truncate(self):
        long_text = "x" * 150
        with pytest.raises(click.BadParameter, match="exceeds maximum"):
            validate_text_length(long_text, 100, "notes", truncate=False)


class TestTickerType:
    """Tests for TickerType custom Click param type."""

    def test_name_attribute(self):
        assert TICKER.name == "ticker"

    def test_convert_valid(self):
        result = TICKER.convert("aapl", None, None)
        assert result == "AAPL"

    def test_convert_with_whitespace(self):
        result = TICKER.convert("  msft  ", None, None)
        assert result == "MSFT"
