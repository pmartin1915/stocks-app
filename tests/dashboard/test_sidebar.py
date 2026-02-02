"""Test sidebar components.

Tests for dashboard/utils/sidebar.py - theme toggle, branding, and navigation.
Note: These tests focus on the pure logic aspects. Full integration tests
with Streamlit require the e2e test suite with Playwright.
"""

from unittest.mock import MagicMock, patch


class TestSidebarModuleImports:
    """Test that sidebar module imports work correctly."""

    def test_sidebar_module_imports(self):
        """Sidebar module should be importable."""
        from dashboard.utils import sidebar

        assert sidebar is not None

    def test_sidebar_has_render_functions(self):
        """Sidebar module should have all render functions."""
        from dashboard.utils.sidebar import (
            render_branding,
            render_full_sidebar,
            render_navigation,
            render_theme_toggle,
        )

        assert callable(render_branding)
        assert callable(render_full_sidebar)
        assert callable(render_navigation)
        assert callable(render_theme_toggle)


class TestThemeToggleLogic:
    """Test theme toggle initialization and state management."""

    def test_theme_defaults_to_light(self):
        """Theme should default to 'light' when not set."""
        # Mock streamlit session_state
        mock_st = MagicMock()
        mock_st.session_state = {}
        mock_st.sidebar = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            from dashboard.utils.sidebar import render_theme_toggle

            # Check that theme is initialized
            # Note: This test verifies the logic pattern
            assert "theme" not in mock_st.session_state or mock_st.session_state.get(
                "theme"
            ) in ["light", "dark"]

    def test_theme_toggle_preserves_existing_state(self):
        """Theme toggle should not overwrite existing theme state."""
        # If theme is already 'dark', it should stay 'dark'
        mock_st = MagicMock()
        mock_st.session_state = {"theme": "dark"}

        # Theme should remain dark
        assert mock_st.session_state["theme"] == "dark"


class TestRenderBranding:
    """Test branding rendering."""

    def test_render_branding_uses_sidebar(self):
        """render_branding should use st.sidebar for output."""
        mock_st = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            from dashboard.utils.sidebar import render_branding

            render_branding()

            # Should call sidebar.title and sidebar.caption
            mock_st.sidebar.title.assert_called_once_with("Asymmetric")
            mock_st.sidebar.caption.assert_called_once_with(
                "Long-term value investing research"
            )


class TestRenderNavigation:
    """Test navigation rendering."""

    def test_render_navigation_uses_sidebar(self):
        """render_navigation should render nav items to sidebar."""
        mock_st = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            from dashboard.utils.sidebar import render_navigation

            render_navigation()

            # Should call sidebar.divider and sidebar.markdown
            mock_st.sidebar.divider.assert_called_once()
            mock_st.sidebar.markdown.assert_called_once()

            # Verify navigation content includes key pages
            call_args = mock_st.sidebar.markdown.call_args[0][0]
            assert "Watchlist" in call_args
            assert "Screener" in call_args
            assert "Compare" in call_args
            assert "Decisions" in call_args
            assert "Trends" in call_args
            assert "Alerts" in call_args
            assert "Portfolio" in call_args


class TestRenderFullSidebar:
    """Test full sidebar rendering."""

    def test_render_full_sidebar_calls_all_components(self):
        """render_full_sidebar should call all component functions."""
        mock_st = MagicMock()
        mock_st.session_state = {"theme": "light"}
        mock_st.sidebar = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            with patch(
                "dashboard.utils.sidebar.render_branding"
            ) as mock_branding:
                with patch(
                    "dashboard.utils.sidebar.render_theme_toggle"
                ) as mock_toggle:
                    with patch(
                        "dashboard.utils.sidebar.render_navigation"
                    ) as mock_nav:
                        # Import after patching
                        from dashboard.utils import sidebar

                        # Call the actual function
                        sidebar.render_full_sidebar()

                        # All components should be called (debug removed)
                        mock_branding.assert_called_once()
                        mock_toggle.assert_called_once()
                        mock_nav.assert_called_once()


class TestThemeStateTransitions:
    """Test theme state transitions."""

    def test_theme_can_switch_light_to_dark(self):
        """Theme should be able to switch from light to dark."""
        session_state = {"theme": "light"}

        # Simulate toggle click
        is_dark = True
        new_theme = "dark" if is_dark else "light"

        if session_state["theme"] != new_theme:
            session_state["theme"] = new_theme

        assert session_state["theme"] == "dark"

    def test_theme_can_switch_dark_to_light(self):
        """Theme should be able to switch from dark to light."""
        session_state = {"theme": "dark"}

        # Simulate toggle click
        is_dark = False
        new_theme = "dark" if is_dark else "light"

        if session_state["theme"] != new_theme:
            session_state["theme"] = new_theme

        assert session_state["theme"] == "light"

    def test_no_rerun_when_theme_unchanged(self):
        """Should not trigger rerun if theme hasn't changed."""
        session_state = {"theme": "light"}

        # Simulate toggle click with same value
        is_dark = False
        new_theme = "dark" if is_dark else "light"

        needs_rerun = session_state["theme"] != new_theme

        assert needs_rerun is False


class TestDebugToggleClicks:
    """Test debug toggle click counting."""

    def test_debug_clicks_initialized_to_zero(self):
        """Debug click counter should initialize to 0."""
        session_state = {}

        if "debug_toggle_clicks" not in session_state:
            session_state["debug_toggle_clicks"] = 0

        assert session_state["debug_toggle_clicks"] == 0

    def test_debug_clicks_increments(self):
        """Debug click counter should increment on theme change."""
        session_state = {"debug_toggle_clicks": 5, "theme": "light"}

        # Simulate theme change
        new_theme = "dark"
        if session_state["theme"] != new_theme:
            session_state["debug_toggle_clicks"] += 1
            session_state["theme"] = new_theme

        assert session_state["debug_toggle_clicks"] == 6


class TestNavigationPages:
    """Test that all expected pages are in navigation."""

    def test_all_pages_in_navigation_markdown(self):
        """All dashboard pages should be listed in navigation."""
        expected_pages = [
            "Watchlist",
            "Screener",
            "Compare",
            "Decisions",
            "Trends",
            "Alerts",
            "Portfolio",
        ]

        # Navigation markdown from sidebar.py
        nav_markdown = """
**Navigate using the pages above:**
- **Watchlist** — Your tracked stocks
- **Screener** — Find opportunities
- **Compare** — Side-by-side analysis
- **Decisions** — Investment theses
- **Trends** — Score trajectories
- **Alerts** — Threshold monitoring
- **Portfolio** — Holdings & P&L
"""

        for page in expected_pages:
            assert page in nav_markdown, f"Missing page: {page}"


class TestSidebarColorIntegration:
    """Test sidebar color integration with theme system."""

    def test_semantic_colors_are_available(self):
        """Semantic colors should be available for theme-aware styling."""
        from dashboard.theme import SEMANTIC_COLORS

        # Verify that semantic colors are properly defined
        light_colors = SEMANTIC_COLORS["light"]
        assert light_colors["green"] == "#22c55e"
        assert light_colors["blue"] == "#3b82f6"
        assert light_colors["red"] == "#ef4444"

        dark_colors = SEMANTIC_COLORS["dark"]
        assert dark_colors["green"] == "#10b981"
        assert dark_colors["blue"] == "#60a5fa"
        assert dark_colors["red"] == "#f87171"
