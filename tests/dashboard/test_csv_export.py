"""Tests for CSV export sanitization utility."""

import pandas as pd
import pytest

from dashboard.utils.csv_export import sanitize_csv_dataframe


class TestSanitizeCsvDataframe:
    """Tests for CSV injection protection."""

    def test_escapes_equals_prefix(self):
        df = pd.DataFrame({"name": ["=cmd('calc')", "Normal"]})
        result = sanitize_csv_dataframe(df)
        assert result["name"].iloc[0] == "'=cmd('calc')"
        assert result["name"].iloc[1] == "Normal"

    def test_escapes_plus_prefix(self):
        df = pd.DataFrame({"name": ["+cmd('calc')"]})
        result = sanitize_csv_dataframe(df)
        assert result["name"].iloc[0] == "'+cmd('calc')"

    def test_escapes_minus_prefix(self):
        df = pd.DataFrame({"name": ["-1+1"]})
        result = sanitize_csv_dataframe(df)
        assert result["name"].iloc[0] == "'-1+1"

    def test_escapes_at_prefix(self):
        df = pd.DataFrame({"name": ["@SUM(A1:A10)"]})
        result = sanitize_csv_dataframe(df)
        assert result["name"].iloc[0] == "'@SUM(A1:A10)"

    def test_does_not_modify_safe_strings(self):
        df = pd.DataFrame({"name": ["Apple Inc.", "Microsoft Corp", "AAPL"]})
        result = sanitize_csv_dataframe(df)
        assert list(result["name"]) == ["Apple Inc.", "Microsoft Corp", "AAPL"]

    def test_preserves_numeric_columns(self):
        df = pd.DataFrame({"price": [150.0, -20.5], "name": ["=BAD", "OK"]})
        result = sanitize_csv_dataframe(df)
        assert result["price"].iloc[0] == 150.0
        assert result["price"].iloc[1] == -20.5
        assert result["name"].iloc[0] == "'=BAD"

    def test_handles_empty_dataframe(self):
        df = pd.DataFrame({"name": pd.Series([], dtype=str)})
        result = sanitize_csv_dataframe(df)
        assert len(result) == 0

    def test_handles_none_values(self):
        df = pd.DataFrame({"name": [None, "=BAD", "OK"]})
        result = sanitize_csv_dataframe(df)
        assert result["name"].iloc[0] is None
        assert result["name"].iloc[1] == "'=BAD"

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"name": ["=BAD"]})
        sanitize_csv_dataframe(df)
        assert df["name"].iloc[0] == "=BAD"
