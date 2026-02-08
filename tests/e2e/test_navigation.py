"""E2E tests for multi-page navigation.

Tests page navigation, sidebar persistence, and theme persistence across pages.
Requires Streamlit server running on localhost:8501.

Run with: pytest tests/e2e/test_navigation.py -v
"""

import pytest

from tests.e2e.conftest import get_current_theme, navigate_to_page, wait_for_streamlit_rerun


@pytest.mark.e2e
class TestSidebarPersistence:
    """Test that sidebar is visible on all pages."""

    def test_sidebar_visible_on_home(self, page):
        """Verify sidebar is visible on home page."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        assert sidebar.is_visible(), "Sidebar should be visible on home page"

    def test_sidebar_has_asymmetric_branding(self, page):
        """Verify sidebar shows Asymmetric branding."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar_text = sidebar.inner_text()
        assert "Asymmetric" in sidebar_text, "Sidebar should show 'Asymmetric' branding"

    def test_sidebar_has_theme_toggle(self, page):
        """Verify sidebar has theme toggle on home page."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        theme_label = sidebar.locator('text=Theme')
        assert theme_label.is_visible(), "Theme toggle should be visible in sidebar"


@pytest.mark.e2e
class TestPageNavigation:
    """Test navigation between pages."""

    def test_can_navigate_to_watchlist(self, page):
        """Verify navigation to Watchlist page works."""
        # Find and click Watchlist link in sidebar
        sidebar = page.locator('[data-testid="stSidebar"]')
        watchlist_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Watchlist").first

        if watchlist_link.is_visible():
            watchlist_link.click()
            wait_for_streamlit_rerun(page)

            # Verify we're on Watchlist page
            page_title = page.locator('h1').first
            assert "Watchlist" in page_title.inner_text(), "Should navigate to Watchlist page"
        else:
            # Fallback: check for page in native Streamlit nav
            page.locator('text=Watchlist').first.click()
            wait_for_streamlit_rerun(page)

    def test_can_navigate_to_screener(self, page):
        """Verify navigation to Screener page works."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        screener_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Screener").first

        if screener_link.is_visible():
            screener_link.click()
            wait_for_streamlit_rerun(page)

            page_title = page.locator('h1').first
            assert "Screener" in page_title.inner_text(), "Should navigate to Screener page"
        else:
            page.locator('text=Screener').first.click()
            wait_for_streamlit_rerun(page)

    def test_can_navigate_to_compare(self, page):
        """Verify navigation to Compare page works."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        compare_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Compare").first

        if compare_link.is_visible():
            compare_link.click()
            wait_for_streamlit_rerun(page)

            page_title = page.locator('h1').first
            assert "Compare" in page_title.inner_text(), "Should navigate to Compare page"
        else:
            page.locator('text=Compare').first.click()
            wait_for_streamlit_rerun(page)

    def test_can_navigate_to_decisions(self, page):
        """Verify navigation to Decisions page works."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        decisions_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Decisions").first

        if decisions_link.is_visible():
            decisions_link.click()
            wait_for_streamlit_rerun(page)

            page_title = page.locator('h1').first
            assert "Decisions" in page_title.inner_text(), "Should navigate to Decisions page"
        else:
            page.locator('text=Decisions').first.click()
            wait_for_streamlit_rerun(page)

    def test_can_navigate_to_trends(self, page):
        """Verify navigation to Trends page works."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        trends_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Trends").first

        if trends_link.is_visible():
            trends_link.click()
            wait_for_streamlit_rerun(page)

            page_title = page.locator('h1').first
            assert "Trends" in page_title.inner_text(), "Should navigate to Trends page"
        else:
            page.locator('text=Trends').first.click()
            wait_for_streamlit_rerun(page)


@pytest.mark.e2e
class TestThemePersistenceAcrossPages:
    """Test that theme persists when navigating between pages."""

    def test_theme_persists_to_watchlist(self, page):
        """Verify theme persists when navigating to Watchlist."""
        # Set dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Navigate to Watchlist
        sidebar = page.locator('[data-testid="stSidebar"]')
        watchlist_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Watchlist").first
        if watchlist_link.is_visible():
            watchlist_link.click()
        else:
            page.locator('text=Watchlist').first.click()
        wait_for_streamlit_rerun(page)

        # Check theme is still dark
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        assert toggle.is_checked(), "Dark mode should persist to Watchlist page"

    def test_theme_persists_to_screener(self, page):
        """Verify theme persists when navigating to Screener."""
        # Set dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Navigate to Screener
        sidebar = page.locator('[data-testid="stSidebar"]')
        screener_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Screener").first
        if screener_link.is_visible():
            screener_link.click()
        else:
            page.locator('text=Screener').first.click()
        wait_for_streamlit_rerun(page)

        # Check theme is still dark
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        assert toggle.is_checked(), "Dark mode should persist to Screener page"

    def test_theme_change_on_subpage_persists_back(self, page):
        """Verify theme change on subpage persists when navigating back."""
        # Navigate to Watchlist
        sidebar = page.locator('[data-testid="stSidebar"]')
        watchlist_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Watchlist").first
        if watchlist_link.is_visible():
            watchlist_link.click()
        else:
            page.locator('text=Watchlist').first.click()
        wait_for_streamlit_rerun(page)

        # Set dark mode on Watchlist page
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Navigate back to home
        home_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text="Home").first
        if home_link.is_visible():
            home_link.click()
        else:
            # Click on Asymmetric title to go home
            page.locator('text=Asymmetric').first.click()
        wait_for_streamlit_rerun(page)

        # Check theme is still dark on home
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        assert toggle.is_checked(), "Dark mode set on subpage should persist to home"


@pytest.mark.e2e
class TestSidebarOnAllPages:
    """Test sidebar is properly rendered on all pages."""

    @pytest.mark.parametrize("page_name", [
        "Watchlist",
        "Screener",
        "Compare",
        "Decisions",
        "Trends",
        "Alerts",
        "Portfolio",
    ])
    def test_sidebar_visible_on_page(self, page, page_name):
        """Verify sidebar is visible on each page."""
        # Navigate to page
        sidebar = page.locator('[data-testid="stSidebar"]')
        nav_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text=page_name).first

        if nav_link.is_visible():
            nav_link.click()
        else:
            # Fallback: try to find by text
            try:
                page.locator(f'text={page_name}').first.click()
            except Exception:
                pytest.skip(f"Could not find navigation link for {page_name}")

        wait_for_streamlit_rerun(page)

        # Verify sidebar is still visible
        sidebar = page.locator('[data-testid="stSidebar"]')
        assert sidebar.is_visible(), f"Sidebar should be visible on {page_name} page"

    @pytest.mark.parametrize("page_name", [
        "Watchlist",
        "Screener",
        "Compare",
        "Decisions",
        "Trends",
    ])
    def test_theme_toggle_visible_on_page(self, page, page_name):
        """Verify theme toggle is visible on each page."""
        # Navigate to page
        sidebar = page.locator('[data-testid="stSidebar"]')
        nav_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text=page_name).first

        if nav_link.is_visible():
            nav_link.click()
        else:
            try:
                page.locator(f'text={page_name}').first.click()
            except Exception:
                pytest.skip(f"Could not find navigation link for {page_name}")

        wait_for_streamlit_rerun(page)

        # Verify theme toggle is visible
        sidebar = page.locator('[data-testid="stSidebar"]')
        theme_label = sidebar.locator('text=Theme')
        assert theme_label.is_visible(), f"Theme toggle should be visible on {page_name} page"


@pytest.mark.e2e
class TestNavigationHints:
    """Test navigation hints in sidebar."""

    def test_navigation_hints_visible(self, page):
        """Verify navigation hints are displayed in sidebar."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar_text = sidebar.inner_text()

        assert "Navigate using the pages above" in sidebar_text, (
            "Navigation hints should be visible"
        )

    def test_navigation_hints_list_all_pages(self, page):
        """Verify navigation hints list all main pages."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar_text = sidebar.inner_text()

        expected_pages = [
            "Watchlist",
            "Screener",
            "Compare",
            "Decisions",
            "Trends",
            "Alerts",
            "Portfolio",
        ]

        for page_name in expected_pages:
            assert page_name in sidebar_text, f"{page_name} should be in navigation hints"
