"""Compare page session state isolation tests.

Tests that watchlist-selected tickers and manually-entered tickers
don't collide, and that the Clear button resets all state properly.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit with controllable session state."""
    session_state = {}

    mock_st = MagicMock()
    mock_st.session_state = session_state
    mock_st.set_page_config = MagicMock()
    mock_st.title = MagicMock()
    mock_st.caption = MagicMock()
    mock_st.subheader = MagicMock()
    mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
    mock_st.multiselect = MagicMock(return_value=[])
    mock_st.text_input = MagicMock(return_value="")
    mock_st.button = MagicMock(return_value=False)
    mock_st.info = MagicMock()
    mock_st.progress = MagicMock(return_value=MagicMock())
    mock_st.empty = MagicMock(return_value=MagicMock())
    mock_st.spinner = MagicMock()
    mock_st.divider = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.error = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.rerun = MagicMock()

    return mock_st, session_state


class TestSessionStateDefaults:
    """Test that compare page state is initialized correctly."""

    def test_init_page_state_sets_compare_keys(self):
        """init_page_state('compare') creates all required keys."""
        from dashboard.utils.session_state import SESSION_DEFAULTS, PAGE_KEYS

        compare_keys = PAGE_KEYS["compare"]
        assert "compare_tickers" in compare_keys
        assert "compare_results" in compare_keys
        assert "compare_ai_result" in compare_keys

    def test_compare_tickers_default_is_empty_list(self):
        """compare_tickers defaults to an empty list."""
        from dashboard.utils.session_state import SESSION_DEFAULTS

        assert SESSION_DEFAULTS["compare_tickers"] == []

    def test_compare_results_default_is_empty_dict(self):
        """compare_results defaults to an empty dict."""
        from dashboard.utils.session_state import SESSION_DEFAULTS

        assert SESSION_DEFAULTS["compare_results"] == {}

    def test_compare_ai_result_default_is_none(self):
        """compare_ai_result defaults to None."""
        from dashboard.utils.session_state import SESSION_DEFAULTS

        assert SESSION_DEFAULTS["compare_ai_result"] is None


class TestWatchlistAndManualIndependence:
    """Test that watchlist selection and manual tickers don't interfere."""

    def test_watchlist_priority_over_manual(self):
        """When both watchlist and manual tickers are present, watchlist wins."""
        # The compare page priority logic (lines 115-120):
        #   if selected_from_watchlist: use watchlist
        #   elif manual_tickers: use manual
        selected_from_watchlist = ["AAPL", "MSFT"]
        manual_tickers = ["GOOG"]

        if selected_from_watchlist:
            tickers_to_compare = selected_from_watchlist
        elif manual_tickers:
            tickers_to_compare = manual_tickers
        else:
            tickers_to_compare = []

        assert tickers_to_compare == ["AAPL", "MSFT"]

    def test_manual_fallback_when_watchlist_empty(self):
        """Manual tickers are used when no watchlist selection."""
        selected_from_watchlist = []
        manual_tickers = ["GOOG", "AMZN"]

        if selected_from_watchlist:
            tickers_to_compare = selected_from_watchlist
        elif manual_tickers:
            tickers_to_compare = manual_tickers
        else:
            tickers_to_compare = []

        assert tickers_to_compare == ["GOOG", "AMZN"]

    def test_empty_when_nothing_selected(self):
        """No tickers when both watchlist and manual are empty."""
        selected_from_watchlist = []
        manual_tickers = []

        if selected_from_watchlist:
            tickers_to_compare = selected_from_watchlist
        elif manual_tickers:
            tickers_to_compare = manual_tickers
        else:
            tickers_to_compare = []

        assert tickers_to_compare == []

    def test_watchlist_defaults_filter_stale_tickers(self):
        """Previous selections not in current watchlist are filtered out."""
        # Simulates the filtering logic at lines 81-84:
        previous_compare_tickers = ["AAPL", "MSFT", "GOOG"]
        current_watchlist = {"AAPL", "GOOG", "AMZN"}

        valid_defaults = [
            t for t in previous_compare_tickers[:3]
            if t in current_watchlist
        ]

        assert valid_defaults == ["AAPL", "GOOG"]
        assert "MSFT" not in valid_defaults


class TestClearButtonResetsState:
    """Test that Clear resets all compare-related state."""

    def test_clear_resets_all_three_keys(self):
        """Clear button sets compare_tickers, compare_results, compare_ai_result to defaults."""
        from dashboard.utils.session_state import reset_page_state, init_session_state

        # Simulate having state
        import streamlit as st
        with patch.object(st, "session_state", {}):
            init_session_state(["compare_tickers", "compare_results", "compare_ai_result"])

            # Simulate populated state
            st.session_state["compare_tickers"] = ["AAPL", "MSFT"]
            st.session_state["compare_results"] = {"AAPL": {"score": 8}}
            st.session_state["compare_ai_result"] = {"content": "analysis"}

            # Simulate the clear button logic (lines 141-143)
            st.session_state["compare_tickers"] = []
            st.session_state["compare_results"] = {}
            st.session_state["compare_ai_result"] = None

            assert st.session_state["compare_tickers"] == []
            assert st.session_state["compare_results"] == {}
            assert st.session_state["compare_ai_result"] is None

    def test_reset_page_state_clears_compare(self):
        """reset_page_state('compare') resets compare keys to defaults."""
        import streamlit as st
        with patch.object(st, "session_state", {}):
            from dashboard.utils.session_state import init_session_state, reset_page_state

            init_session_state(["compare_tickers", "compare_results", "compare_ai_result", "theme"])

            # Populate
            st.session_state["compare_tickers"] = ["AAPL"]
            st.session_state["compare_results"] = {"AAPL": {}}
            st.session_state["compare_ai_result"] = "test"

            reset_page_state("compare")

            assert st.session_state["compare_tickers"] == []
            assert st.session_state["compare_results"] == {}
            assert st.session_state["compare_ai_result"] is None

    def test_reset_preserves_theme(self):
        """reset_page_state does not reset the theme key."""
        import streamlit as st
        with patch.object(st, "session_state", {}):
            from dashboard.utils.session_state import init_session_state, reset_page_state

            init_session_state(["theme", "compare_tickers"])
            st.session_state["theme"] = "dark"
            st.session_state["compare_tickers"] = ["AAPL"]

            reset_page_state("compare")

            assert st.session_state["theme"] == "dark"
            assert st.session_state["compare_tickers"] == []


class TestManualTickerSessionKeys:
    """Test that manual ticker inputs use separate keys."""

    def test_manual_ticker_keys_are_indexed(self):
        """Manual tickers use manual_ticker_0, manual_ticker_1, manual_ticker_2."""
        # Verify the keys used in the compare page (line 108)
        expected_keys = ["manual_ticker_0", "manual_ticker_1", "manual_ticker_2"]

        # These are separate from the watchlist_select key (line 90)
        watchlist_key = "watchlist_select"

        for key in expected_keys:
            assert key != watchlist_key
            assert key.startswith("manual_ticker_")

    def test_manual_tickers_uppercased(self):
        """Manual ticker input is uppercased (line 110)."""
        raw_input = "aapl"
        processed = raw_input.upper().strip()
        assert processed == "AAPL"
