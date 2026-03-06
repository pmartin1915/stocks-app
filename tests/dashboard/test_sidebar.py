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
        from dashboard.utils.sidebar import render_full_sidebar

        assert callable(render_full_sidebar)

    def test_sidebar_has_private_helpers(self):
        """Sidebar module should have private helper functions."""
        from dashboard.utils.sidebar import (
            _render_branding,
            _render_footer,
            _render_navigation,
        )

        assert callable(_render_branding)
        assert callable(_render_footer)
        assert callable(_render_navigation)


class TestRenderBranding:
    """Test branding rendering."""

    def test_render_branding_uses_sidebar(self):
        """_render_branding should use st.sidebar for output."""
        mock_st = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            from dashboard.utils.sidebar import _render_branding

            _render_branding()

            mock_st.sidebar.markdown.assert_called()
            # Branding renders HTML with app name
            call_args = mock_st.sidebar.markdown.call_args_list[0][0][0]
            assert "Asymmetric" in call_args


class TestRenderNavigation:
    """Test navigation rendering."""

    def test_render_navigation_uses_sidebar(self):
        """_render_navigation should render nav items to sidebar."""
        mock_st = MagicMock()

        with patch("dashboard.utils.sidebar.st", mock_st):
            from dashboard.utils.sidebar import _render_navigation

            _render_navigation(current_page="home")

            # Navigation renders section labels and page links
            assert mock_st.sidebar.markdown.called
            assert mock_st.sidebar.page_link.called or mock_st.sidebar.markdown.called


class TestRenderFullSidebar:
    """Test full sidebar rendering."""

    def test_render_full_sidebar_calls_all_components(self):
        """render_full_sidebar should call branding, navigation, and footer."""
        with patch(
            "dashboard.utils.sidebar._render_branding"
        ) as mock_branding:
            with patch(
                "dashboard.utils.sidebar._render_navigation"
            ) as mock_nav:
                with patch(
                    "dashboard.utils.sidebar._render_footer"
                ) as mock_footer:
                    from dashboard.utils.sidebar import render_full_sidebar

                    render_full_sidebar(current_page="home")

                    mock_branding.assert_called_once()
                    mock_nav.assert_called_once_with("home")
                    mock_footer.assert_called_once()


class TestNavigationStructure:
    """Test that all expected pages are in navigation structure."""

    def test_all_pages_in_nav_groups(self):
        """All dashboard pages should be listed in _NAV_GROUPS."""
        from dashboard.utils.sidebar import _NAV_GROUPS

        # Flatten all page labels from nav groups
        all_labels = []
        for _group_label, items in _NAV_GROUPS:
            for label, _path, _icon, _page_id in items:
                all_labels.append(label)

        expected_pages = [
            "Home",
            "Portfolio",
            "Watchlist",
            "Screener",
            "Research",
            "Compare",
            "Decisions",
            "Trends",
            "Alerts",
        ]

        for page in expected_pages:
            assert page in all_labels, f"Missing page: {page}"

    def test_nav_groups_have_correct_sections(self):
        """Navigation should have OVERVIEW, RESEARCH, TRACKING sections."""
        from dashboard.utils.sidebar import _NAV_GROUPS

        group_labels = [label for label, _items in _NAV_GROUPS]
        assert "OVERVIEW" in group_labels
        assert "RESEARCH" in group_labels
        assert "TRACKING" in group_labels

    def test_nav_page_ids_are_unique(self):
        """Each page should have a unique page_id."""
        from dashboard.utils.sidebar import _NAV_GROUPS

        page_ids = []
        for _group_label, items in _NAV_GROUPS:
            for _label, _path, _icon, page_id in items:
                page_ids.append(page_id)

        assert len(page_ids) == len(set(page_ids)), "Duplicate page_ids found"


class TestSidebarColorIntegration:
    """Test sidebar color integration with theme system."""

    def test_semantic_colors_are_available(self):
        """Semantic colors should be available for theme-aware styling."""
        from dashboard.theme import SEMANTIC_COLORS

        assert SEMANTIC_COLORS["green"] == "#10b981"
        assert SEMANTIC_COLORS["blue"] == "#60a5fa"
        assert SEMANTIC_COLORS["red"] == "#f87171"
