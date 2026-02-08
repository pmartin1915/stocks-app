"""E2E tests for dark mode functionality.

Tests the dark mode toggle, color changes, and theme persistence.
Requires Streamlit server running on localhost:8501.

Run with: pytest tests/e2e/test_dark_mode.py -v
"""

import pytest

from tests.e2e.conftest import click_theme_toggle, get_current_theme, wait_for_streamlit_rerun


@pytest.mark.e2e
class TestDarkModeToggle:
    """Test dark mode toggle visibility and functionality."""

    def test_dark_mode_toggle_exists(self, page):
        """Verify dark mode toggle is visible in sidebar."""
        # Look for the theme toggle in sidebar
        sidebar = page.locator('[data-testid="stSidebar"]')
        assert sidebar.is_visible(), "Sidebar should be visible"

        # Look for Theme label
        theme_label = sidebar.locator('text=Theme')
        assert theme_label.is_visible(), "Theme label should be visible"

    def test_dark_mode_toggle_is_interactive(self, page):
        """Verify toggle can be clicked."""
        # Find the toggle widget
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first

        # Should be visible and enabled
        assert toggle.is_visible(), "Toggle should be visible"
        assert toggle.is_enabled(), "Toggle should be enabled"

    def test_dark_mode_toggle_state_changes(self, page):
        """Verify toggle changes state when clicked."""
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first

        # Get initial state
        initial_checked = toggle.is_checked()

        # Click toggle
        toggle.click()

        # Wait for Streamlit rerun
        wait_for_streamlit_rerun(page)

        # Get new state - need to re-query after rerun
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        new_checked = toggle.is_checked()

        # Assert state changed
        assert initial_checked != new_checked, "Toggle state should change after click"

    def test_can_toggle_back_to_original_state(self, page):
        """Verify toggle can switch back to original state."""
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first

        initial_state = toggle.is_checked()

        # Toggle twice
        toggle.click()
        wait_for_streamlit_rerun(page)

        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        toggle.click()
        wait_for_streamlit_rerun(page)

        # Should be back to initial state
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        final_state = toggle.is_checked()

        assert final_state == initial_state, "Should return to original state after two toggles"


@pytest.mark.e2e
class TestDarkModeColors:
    """Test that colors actually change when theme switches."""

    def test_color_test_boxes_exist(self, page):
        """Verify color test boxes are visible on home page."""
        # The home page has color test boxes (GREEN, RED, BLUE)
        green_box = page.locator('text=GREEN').first
        assert green_box.is_visible(), "GREEN color test box should be visible"

    def test_colors_change_when_toggled(self, page):
        """Verify colors change when dark mode is toggled."""
        # Get initial green color
        green_box = page.locator('text=GREEN').locator('..')
        initial_style = green_box.evaluate(
            "el => window.getComputedStyle(el).backgroundColor"
        )

        # Toggle dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        toggle.click()
        wait_for_streamlit_rerun(page)

        # Get new green color
        green_box = page.locator('text=GREEN').locator('..')
        new_style = green_box.evaluate(
            "el => window.getComputedStyle(el).backgroundColor"
        )

        # Colors should be different
        assert initial_style != new_style, (
            f"Color should change. Before: {initial_style}, After: {new_style}"
        )

    def test_light_mode_green_is_correct(self, page):
        """Verify light mode green matches spec (#22c55e)."""
        # Ensure we're in light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Get green box background color
        green_box = page.locator('text=GREEN').locator('..')
        bg_color = green_box.evaluate(
            "el => window.getComputedStyle(el).backgroundColor"
        )

        # #22c55e = rgb(34, 197, 94)
        expected = "rgb(34, 197, 94)"
        assert bg_color == expected, f"Light mode green should be {expected}, got {bg_color}"

    def test_dark_mode_green_is_correct(self, page):
        """Verify dark mode green matches spec (#10b981)."""
        # Ensure we're in dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Get green box background color
        green_box = page.locator('text=GREEN').locator('..')
        bg_color = green_box.evaluate(
            "el => window.getComputedStyle(el).backgroundColor"
        )

        # #10b981 = rgb(16, 185, 129)
        expected = "rgb(16, 185, 129)"
        assert bg_color == expected, f"Dark mode green should be {expected}, got {bg_color}"


@pytest.mark.e2e
class TestDebugInfo:
    """Test debug info shows correct theme state."""

    def test_debug_info_shows_theme(self, page):
        """Verify debug info displays current theme."""
        sidebar = page.locator('[data-testid="stSidebar"]')

        # Look for debug info section
        debug_section = sidebar.locator('text=Debug Info')
        assert debug_section.is_visible(), "Debug Info section should be visible"

    def test_debug_info_updates_on_toggle(self, page):
        """Verify debug info updates when theme changes."""
        sidebar = page.locator('[data-testid="stSidebar"]')

        # Get initial theme from debug info
        initial_theme = get_current_theme(page)

        # Toggle theme
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        toggle.click()
        wait_for_streamlit_rerun(page)

        # Get new theme from debug info
        new_theme = get_current_theme(page)

        # Theme should have changed
        assert initial_theme != new_theme, (
            f"Theme should change. Before: {initial_theme}, After: {new_theme}"
        )

    def test_debug_colors_match_expected_light(self, page):
        """Verify debug color values match expected for light mode."""
        # Ensure light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        sidebar = page.locator('[data-testid="stSidebar"]')

        # Check for expected light mode colors in debug info
        sidebar_text = sidebar.inner_text()
        assert "#22c55e" in sidebar_text, "Light green (#22c55e) should be in debug info"
        assert "#3b82f6" in sidebar_text, "Light blue (#3b82f6) should be in debug info"
        assert "#ef4444" in sidebar_text, "Light red (#ef4444) should be in debug info"

    def test_debug_colors_match_expected_dark(self, page):
        """Verify debug color values match expected for dark mode."""
        # Ensure dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        sidebar = page.locator('[data-testid="stSidebar"]')

        # Check for expected dark mode colors in debug info
        sidebar_text = sidebar.inner_text()
        assert "#10b981" in sidebar_text, "Dark green (#10b981) should be in debug info"
        assert "#60a5fa" in sidebar_text, "Dark blue (#60a5fa) should be in debug info"
        assert "#f87171" in sidebar_text, "Dark red (#f87171) should be in debug info"


@pytest.mark.e2e
class TestDarkModeIndicator:
    """Test the dark mode ON/OFF indicator on home page."""

    def test_dark_mode_indicator_exists(self, page):
        """Verify Dark Mode indicator is visible."""
        indicator = page.locator('text=Dark Mode:')
        assert indicator.is_visible(), "Dark Mode indicator should be visible"

    def test_dark_mode_indicator_shows_off_in_light(self, page):
        """Verify indicator shows OFF in light mode."""
        # Ensure light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Check indicator
        page_text = page.locator('[data-testid="stApp"]').inner_text()
        assert "Dark Mode: OFF" in page_text, "Should show 'Dark Mode: OFF' in light mode"

    def test_dark_mode_indicator_shows_on_in_dark(self, page):
        """Verify indicator shows ON in dark mode."""
        # Ensure dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Check indicator
        page_text = page.locator('[data-testid="stApp"]').inner_text()
        assert "Dark Mode: ON" in page_text, "Should show 'Dark Mode: ON' in dark mode"


@pytest.mark.e2e
class TestColorSwatches:
    """Test the visual color swatches in debug info."""

    def test_color_swatches_exist(self, page):
        """Verify color swatches are rendered in sidebar."""
        sidebar = page.locator('[data-testid="stSidebar"]')

        # Look for div elements with specific background colors
        # The swatches are 30x30px divs with colored backgrounds
        swatches = sidebar.locator('div[style*="border-radius:4px"]')

        # Should have at least the 3 color swatches (green, blue, red)
        assert swatches.count() >= 3, "Should have at least 3 color swatches"

    def test_swatches_change_color_on_toggle(self, page):
        """Verify swatch colors change when theme toggles."""
        sidebar = page.locator('[data-testid="stSidebar"]')

        # Get first swatch's background color
        swatch = sidebar.locator('div[style*="border-radius:4px"]').first
        initial_bg = swatch.evaluate("el => el.style.background")

        # Toggle theme
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        toggle.click()
        wait_for_streamlit_rerun(page)

        # Get new background color
        swatch = page.locator('[data-testid="stSidebar"]').locator(
            'div[style*="border-radius:4px"]'
        ).first
        new_bg = swatch.evaluate("el => el.style.background")

        # Colors should be different
        assert initial_bg != new_bg, "Swatch colors should change with theme"
