"""Test AI feedback database operations.

Tests for dashboard/utils/ai_feedback.py - recording and querying feedback.
Uses the tmp_db fixture from the main conftest.py for database isolation.
"""

import time

import pytest


class TestRecordFeedback:
    """Tests for recording AI feedback."""

    def test_record_new_feedback(self, tmp_db):
        """Should create new feedback record."""
        from dashboard.utils.ai_feedback import record_ai_feedback

        result = record_ai_feedback(
            content_hash="abc123",
            content_type="analysis",
            ticker="AAPL",
            model="flash",
            helpful=True,
        )

        assert result is True

    def test_record_feedback_not_helpful(self, tmp_db):
        """Should record not helpful feedback."""
        from dashboard.utils.ai_feedback import record_ai_feedback

        result = record_ai_feedback(
            content_hash="xyz789",
            content_type="analysis",
            ticker="MSFT",
            model="pro",
            helpful=False,
        )

        assert result is True

    def test_update_existing_feedback(self, tmp_db):
        """Should update existing feedback for same hash."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_recent_feedback

        # Create initial feedback as helpful
        record_ai_feedback(
            content_hash="update_test",
            content_type="analysis",
            ticker="AAPL",
            model="flash",
            helpful=True,
        )

        # Update to not helpful
        result = record_ai_feedback(
            content_hash="update_test",
            content_type="analysis",
            ticker="AAPL",
            model="flash",
            helpful=False,
        )

        assert result is True

        # Verify the update
        recent = get_recent_feedback(limit=10)
        record = next(r for r in recent if r["content_hash"] == "update_test")
        assert record["helpful"] is False

    def test_feedback_with_text(self, tmp_db):
        """Should store optional feedback text."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_recent_feedback

        record_ai_feedback(
            content_hash="text_test",
            content_type="thesis",
            ticker="GOOGL",
            model="pro",
            helpful=False,
            feedback_text="Analysis missed key risk factors",
        )

        recent = get_recent_feedback(limit=1)
        assert len(recent) == 1
        assert recent[0]["feedback_text"] == "Analysis missed key risk factors"

    def test_feedback_with_prompt_summary(self, tmp_db):
        """Should store prompt summary if provided."""
        from dashboard.utils.ai_feedback import record_ai_feedback

        long_prompt = "Analyze this company's financial health based on their latest 10-K filing..."
        result = record_ai_feedback(
            content_hash="prompt_test",
            content_type="analysis",
            ticker="NVDA",
            model="flash",
            helpful=True,
            prompt_summary=long_prompt,
        )

        assert result is True


class TestFeedbackStats:
    """Tests for feedback statistics."""

    def test_empty_stats(self, tmp_db):
        """Should return zero counts for empty database."""
        from dashboard.utils.ai_feedback import get_feedback_stats

        stats = get_feedback_stats()
        assert stats["total"] == 0
        assert stats["helpful"] == 0
        assert stats["not_helpful"] == 0
        assert stats["helpful_rate"] == 0

    def test_stats_calculation(self, tmp_db):
        """Should calculate correct statistics."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_feedback_stats

        # Create mixed feedback: 2 helpful, 1 not helpful
        record_ai_feedback("h1", "analysis", "AAPL", "flash", helpful=True)
        record_ai_feedback("h2", "analysis", "MSFT", "flash", helpful=True)
        record_ai_feedback("h3", "analysis", "GOOGL", "flash", helpful=False)

        stats = get_feedback_stats()
        assert stats["total"] == 3
        assert stats["helpful"] == 2
        assert stats["not_helpful"] == 1
        assert stats["helpful_rate"] == pytest.approx(2 / 3)

    def test_stats_by_model_flash(self, tmp_db):
        """Should filter stats by flash model."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_feedback_stats

        record_ai_feedback("m1", "analysis", "AAPL", "flash", helpful=True)
        record_ai_feedback("m2", "analysis", "AAPL", "pro", helpful=False)
        record_ai_feedback("m3", "analysis", "AAPL", "flash", helpful=True)

        flash_stats = get_feedback_stats(model="flash")
        assert flash_stats["total"] == 2
        assert flash_stats["helpful"] == 2
        assert flash_stats["not_helpful"] == 0

    def test_stats_by_model_pro(self, tmp_db):
        """Should filter stats by pro model."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_feedback_stats

        record_ai_feedback("p1", "analysis", "AAPL", "flash", helpful=True)
        record_ai_feedback("p2", "analysis", "MSFT", "pro", helpful=False)
        record_ai_feedback("p3", "analysis", "GOOGL", "pro", helpful=True)

        pro_stats = get_feedback_stats(model="pro")
        assert pro_stats["total"] == 2
        assert pro_stats["helpful"] == 1
        assert pro_stats["not_helpful"] == 1
        assert pro_stats["helpful_rate"] == pytest.approx(0.5)

    def test_stats_all_helpful(self, tmp_db):
        """Should handle 100% helpful rate."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_feedback_stats

        record_ai_feedback("all1", "analysis", "AAPL", "flash", helpful=True)
        record_ai_feedback("all2", "analysis", "MSFT", "flash", helpful=True)

        stats = get_feedback_stats()
        assert stats["helpful_rate"] == 1.0

    def test_stats_none_helpful(self, tmp_db):
        """Should handle 0% helpful rate."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_feedback_stats

        record_ai_feedback("none1", "analysis", "AAPL", "flash", helpful=False)
        record_ai_feedback("none2", "analysis", "MSFT", "flash", helpful=False)

        stats = get_feedback_stats()
        assert stats["helpful_rate"] == 0.0


class TestRecentFeedback:
    """Tests for recent feedback retrieval."""

    def test_empty_recent(self, tmp_db):
        """Should return empty list for no feedback."""
        from dashboard.utils.ai_feedback import get_recent_feedback

        recent = get_recent_feedback()
        assert recent == []

    def test_recent_ordering(self, tmp_db):
        """Should return most recent first."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_recent_feedback

        record_ai_feedback("old_hash", "analysis", "AAPL", "flash", helpful=True)
        time.sleep(0.1)  # Ensure different timestamps
        record_ai_feedback("new_hash", "analysis", "MSFT", "flash", helpful=False)

        recent = get_recent_feedback(limit=2)
        assert len(recent) == 2
        assert recent[0]["content_hash"] == "new_hash"
        assert recent[1]["content_hash"] == "old_hash"

    def test_recent_limit(self, tmp_db):
        """Should respect limit parameter."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_recent_feedback

        for i in range(10):
            record_ai_feedback(f"limit_{i}", "analysis", "AAPL", "flash", helpful=True)

        recent = get_recent_feedback(limit=5)
        assert len(recent) == 5

    def test_recent_default_limit(self, tmp_db):
        """Should use default limit of 20."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_recent_feedback

        for i in range(25):
            record_ai_feedback(f"default_{i}", "analysis", "AAPL", "flash", helpful=True)

        recent = get_recent_feedback()
        assert len(recent) == 20

    def test_recent_includes_all_fields(self, tmp_db):
        """Should return all expected fields."""
        from dashboard.utils.ai_feedback import record_ai_feedback, get_recent_feedback

        record_ai_feedback(
            content_hash="fields_test",
            content_type="thesis",
            ticker="NVDA",
            model="pro",
            helpful=True,
            feedback_text="Great analysis",
        )

        recent = get_recent_feedback(limit=1)
        assert len(recent) == 1

        record = recent[0]
        assert record["content_hash"] == "fields_test"
        assert record["content_type"] == "thesis"
        assert record["ticker"] == "NVDA"
        assert record["model"] == "pro"
        assert record["helpful"] is True
        assert record["feedback_text"] == "Great analysis"
        assert "feedback_at" in record


class TestDatabaseUnavailable:
    """Tests for graceful degradation when DB is unavailable."""

    def test_record_returns_false_without_db(self, monkeypatch):
        """Should return False when database is unavailable."""
        # Temporarily disable DB
        monkeypatch.setattr("dashboard.utils.ai_feedback.DB_AVAILABLE", False)

        from dashboard.utils.ai_feedback import record_ai_feedback

        result = record_ai_feedback(
            content_hash="no_db",
            content_type="analysis",
            ticker="AAPL",
            model="flash",
            helpful=True,
        )

        assert result is False

    def test_stats_returns_error_without_db(self, monkeypatch):
        """Should return error dict when database is unavailable."""
        monkeypatch.setattr("dashboard.utils.ai_feedback.DB_AVAILABLE", False)

        from dashboard.utils.ai_feedback import get_feedback_stats

        stats = get_feedback_stats()
        assert "error" in stats

    def test_recent_returns_empty_without_db(self, monkeypatch):
        """Should return empty list when database is unavailable."""
        monkeypatch.setattr("dashboard.utils.ai_feedback.DB_AVAILABLE", False)

        from dashboard.utils.ai_feedback import get_recent_feedback

        recent = get_recent_feedback()
        assert recent == []
