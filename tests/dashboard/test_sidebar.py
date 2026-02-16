"""Test sidebar components.

Tests for dashboard/utils/sidebar.py - branding and navigation.
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
        )

        assert callable(render_branding)
        assert callable(render_full_sidebar)
        assert callable(render_navigation)


class TestRenderBranding:
    """Test branding rendering."""

    def test_render_branding_uses_sidebar(self):
        """render_branding should use st.sidebar for output."""
        mock_st = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            from dashboard.utils.sidebar import render_branding

            render_branding()

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
        """render_full_sidebar should call branding and navigation."""
        mock_st = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            with patch(
                "dashboard.utils.sidebar.render_branding"
            ) as mock_branding:
                with patch(
                    "dashboard.utils.sidebar.render_navigation"
                ) as mock_nav:
                    from dashboard.utils import sidebar

                    sidebar.render_full_sidebar()

                    mock_branding.assert_called_once()
                    mock_nav.assert_called_once()


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

        assert SEMANTIC_COLORS["green"] == "#10b981"
        assert SEMANTIC_COLORS["blue"] == "#60a5fa"
        assert SEMANTIC_COLORS["red"] == "#f87171"
