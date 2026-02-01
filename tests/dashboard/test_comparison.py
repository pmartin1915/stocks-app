"""Test comparison utility functions.

Tests for dashboard/components/comparison.py - find_winner_index() and calculate_combined_score().
"""

import pytest

from dashboard.components.comparison import calculate_combined_score, find_winner_index


class TestFindWinnerIndex:
    """Tests for find_winner_index()."""

    def test_higher_is_better_finds_max(self):
        """Should find index of maximum value when higher_is_better=True."""
        assert find_winner_index([3, 7, 5], higher_is_better=True) == 1

    def test_lower_is_better_finds_min(self):
        """Should find index of minimum value when higher_is_better=False."""
        assert find_winner_index([3, 7, 5], higher_is_better=False) == 0

    def test_all_none_returns_none(self):
        """All None values should return None."""
        assert find_winner_index([None, None, None], higher_is_better=True) is None

    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        assert find_winner_index([], higher_is_better=True) is None

    def test_mixed_none_finds_valid(self):
        """Should find winner among valid values, ignoring None."""
        assert find_winner_index([None, 5, None], higher_is_better=True) == 1
        assert find_winner_index([None, 5, None], higher_is_better=False) == 1

    def test_mixed_values_higher(self):
        """Should correctly pick max from mixed valid/None values."""
        assert find_winner_index([3, None, 8, None, 5], higher_is_better=True) == 2

    def test_mixed_values_lower(self):
        """Should correctly pick min from mixed valid/None values."""
        assert find_winner_index([3, None, 8, None, 5], higher_is_better=False) == 0

    def test_single_value(self):
        """Single non-None value should be the winner."""
        assert find_winner_index([None, 42, None], higher_is_better=True) == 1

    def test_negative_values(self):
        """Should handle negative values correctly."""
        assert find_winner_index([-5, -2, -8], higher_is_better=True) == 1  # -2 is max
        assert find_winner_index([-5, -2, -8], higher_is_better=False) == 2  # -8 is min

    def test_decimal_values(self):
        """Should handle decimal values correctly."""
        assert find_winner_index([1.5, 2.5, 1.8], higher_is_better=True) == 1
        assert find_winner_index([1.5, 2.5, 1.8], higher_is_better=False) == 0

    def test_first_wins_tie(self):
        """On tie, first occurrence should win (max behavior)."""
        result = find_winner_index([5, 5, 3], higher_is_better=True)
        # Python's max returns first occurrence for ties
        assert result == 0

    def test_zero_values(self):
        """Should handle zero correctly."""
        assert find_winner_index([0, 1, -1], higher_is_better=True) == 1
        assert find_winner_index([0, 1, -1], higher_is_better=False) == 2


class TestCalculateCombinedScore:
    """Tests for calculate_combined_score()."""

    def test_safe_zone_adds_two(self):
        """Safe zone should add +2 bonus to F-Score."""
        data = {"piotroski": {"score": 8}, "altman": {"zone": "Safe"}}
        assert calculate_combined_score(data) == 10  # 8 + 2

    def test_grey_zone_adds_one(self):
        """Grey zone should add +1 bonus to F-Score."""
        data = {"piotroski": {"score": 6}, "altman": {"zone": "Grey"}}
        assert calculate_combined_score(data) == 7  # 6 + 1

    def test_distress_zone_no_bonus(self):
        """Distress zone should add +0 bonus to F-Score."""
        data = {"piotroski": {"score": 4}, "altman": {"zone": "Distress"}}
        assert calculate_combined_score(data) == 4  # 4 + 0

    def test_none_fscore_returns_none(self):
        """Missing F-Score should return None."""
        data = {"piotroski": {}, "altman": {"zone": "Safe"}}
        assert calculate_combined_score(data) is None

    def test_none_zone_no_bonus(self):
        """Missing zone should not add bonus."""
        data = {"piotroski": {"score": 7}, "altman": {}}
        assert calculate_combined_score(data) == 7  # 7 + 0

    def test_missing_piotroski_key(self):
        """Missing piotroski key should return None."""
        data = {"altman": {"zone": "Safe"}}
        assert calculate_combined_score(data) is None

    def test_missing_altman_key(self):
        """Missing altman key should just use F-Score."""
        data = {"piotroski": {"score": 5}}
        assert calculate_combined_score(data) == 5

    def test_empty_data(self):
        """Empty dict should return None."""
        assert calculate_combined_score({}) is None

    def test_max_combined_score(self):
        """Max F-Score (9) + Safe (+2) should equal 11."""
        data = {"piotroski": {"score": 9}, "altman": {"zone": "Safe"}}
        assert calculate_combined_score(data) == 11

    def test_zero_fscore_safe(self):
        """F-Score of 0 with Safe zone should return 2."""
        data = {"piotroski": {"score": 0}, "altman": {"zone": "Safe"}}
        assert calculate_combined_score(data) == 2

    def test_zone_case_sensitivity(self):
        """Zone matching should be case-sensitive per implementation."""
        # "safe" (lowercase) should not match "Safe"
        data = {"piotroski": {"score": 5}, "altman": {"zone": "safe"}}
        # Implementation uses exact match, so lowercase "safe" gets no bonus
        assert calculate_combined_score(data) == 5
