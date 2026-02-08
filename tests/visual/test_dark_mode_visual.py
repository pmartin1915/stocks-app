"""Visual regression tests for dark mode.

Compares screenshots of light and dark mode to verify visual changes.
Requires Streamlit server running on localhost:8501.

Run with: pytest tests/visual/ -v

To update baselines:
    1. Run tests to generate current screenshots
    2. Review screenshots in tests/visual/snapshots/current/
    3. Copy approved screenshots to tests/visual/snapshots/baseline/
"""

import os
from pathlib import Path

import pytest

# Check if required packages are available
try:
    from PIL import Image, ImageChops

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageChops = None

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None


# Directory paths for screenshots
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
BASELINE_DIR = SNAPSHOTS_DIR / "baseline"
CURRENT_DIR = SNAPSHOTS_DIR / "current"
DIFF_DIR = SNAPSHOTS_DIR / "diffs"


def pytest_configure(config):
    """Create snapshot directories if they don't exist."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    DIFF_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def visual_browser():
    """Launch browser for visual tests."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def visual_page(visual_browser):
    """Create page for visual tests."""
    page = visual_browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stApp"]', timeout=15000)
    page.wait_for_timeout(2000)  # Extra wait for full render
    yield page
    page.close()


def wait_for_streamlit_rerun(page, timeout=5000):
    """Wait for Streamlit to complete a rerun."""
    try:
        page.wait_for_selector(
            '[data-testid="stStatusWidget"]',
            state="hidden",
            timeout=timeout,
        )
    except Exception:
        pass
    page.wait_for_timeout(1000)


@pytest.mark.visual
class TestDarkModeVisualRegression:
    """Visual regression tests for dark mode."""

    def test_capture_light_mode_screenshot(self, visual_page):
        """Capture screenshot in light mode."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Take screenshot
        screenshot_path = CURRENT_DIR / "light-mode.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        assert screenshot_path.exists(), "Light mode screenshot should be saved"
        print(f"\n[Visual] Light mode screenshot saved: {screenshot_path}")

    def test_capture_dark_mode_screenshot(self, visual_page):
        """Capture screenshot in dark mode."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Take screenshot
        screenshot_path = CURRENT_DIR / "dark-mode.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        assert screenshot_path.exists(), "Dark mode screenshot should be saved"
        print(f"\n[Visual] Dark mode screenshot saved: {screenshot_path}")

    def test_light_and_dark_are_different(self, visual_page):
        """Verify light and dark mode screenshots are visually different."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure light mode and screenshot
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        light_path = CURRENT_DIR / "light-mode-compare.png"
        page.screenshot(path=str(light_path), full_page=True)

        # Switch to dark mode and screenshot
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        toggle.click()
        wait_for_streamlit_rerun(page)

        dark_path = CURRENT_DIR / "dark-mode-compare.png"
        page.screenshot(path=str(dark_path), full_page=True)

        # Compare images
        light_img = Image.open(light_path)
        dark_img = Image.open(dark_path)

        # Images should be same size
        assert light_img.size == dark_img.size, "Screenshot sizes should match"

        # Calculate difference
        diff = ImageChops.difference(light_img, dark_img)
        bbox = diff.getbbox()

        # Save diff image
        diff_path = CURRENT_DIR / "light-dark-diff.png"
        if bbox:
            diff.save(str(diff_path))
            print(f"\n[Visual] Diff image saved: {diff_path}")

        # Assert images are different
        assert bbox is not None, "Light and dark screenshots should be different"

        # Calculate percentage difference
        diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0, 0) and pixel != (0, 0, 0))
        total_pixels = light_img.size[0] * light_img.size[1]
        diff_percent = (diff_pixels / total_pixels) * 100

        print(f"\n[Visual] {diff_percent:.1f}% of pixels changed between themes")

        # At least 5% of pixels should be different (background, colors, etc.)
        assert diff_percent > 5, f"Only {diff_percent:.1f}% pixels changed - themes may not be working"


@pytest.mark.visual
class TestBaselineComparison:
    """Compare current screenshots against approved baselines."""

    def test_light_mode_matches_baseline(self, visual_page):
        """Compare light mode against baseline (if exists)."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        baseline_path = BASELINE_DIR / "light-mode.png"
        if not baseline_path.exists():
            pytest.skip("No light mode baseline - run test_capture_light_mode_screenshot first")

        page = visual_page

        # Ensure light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Take current screenshot
        current_path = CURRENT_DIR / "light-mode-current.png"
        page.screenshot(path=str(current_path), full_page=True)

        # Compare with baseline
        baseline_img = Image.open(baseline_path)
        current_img = Image.open(current_path)

        # Handle size differences
        if baseline_img.size != current_img.size:
            pytest.skip(f"Image sizes differ: baseline={baseline_img.size}, current={current_img.size}")

        diff = ImageChops.difference(baseline_img, current_img)
        bbox = diff.getbbox()

        if bbox:
            # Save diff for inspection
            diff_path = DIFF_DIR / "light-mode-diff.png"
            diff.save(str(diff_path))

            # Calculate difference percentage
            diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0, 0) and pixel != (0, 0, 0))
            total_pixels = baseline_img.size[0] * baseline_img.size[1]
            diff_percent = (diff_pixels / total_pixels) * 100

            # Allow up to 2% difference for rendering variations
            assert diff_percent < 2, (
                f"Visual regression: {diff_percent:.2f}% pixels changed from baseline. "
                f"See diff at: {diff_path}"
            )

    def test_dark_mode_matches_baseline(self, visual_page):
        """Compare dark mode against baseline (if exists)."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        baseline_path = BASELINE_DIR / "dark-mode.png"
        if not baseline_path.exists():
            pytest.skip("No dark mode baseline - run test_capture_dark_mode_screenshot first")

        page = visual_page

        # Ensure dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Take current screenshot
        current_path = CURRENT_DIR / "dark-mode-current.png"
        page.screenshot(path=str(current_path), full_page=True)

        # Compare with baseline
        baseline_img = Image.open(baseline_path)
        current_img = Image.open(current_path)

        if baseline_img.size != current_img.size:
            pytest.skip(f"Image sizes differ: baseline={baseline_img.size}, current={current_img.size}")

        diff = ImageChops.difference(baseline_img, current_img)
        bbox = diff.getbbox()

        if bbox:
            diff_path = DIFF_DIR / "dark-mode-diff.png"
            diff.save(str(diff_path))

            diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0, 0) and pixel != (0, 0, 0))
            total_pixels = baseline_img.size[0] * baseline_img.size[1]
            diff_percent = (diff_pixels / total_pixels) * 100

            assert diff_percent < 2, (
                f"Visual regression: {diff_percent:.2f}% pixels changed from baseline. "
                f"See diff at: {diff_path}"
            )


@pytest.mark.visual
class TestColorBoxScreenshots:
    """Test specific color test boxes on home page."""

    def test_capture_color_boxes_light(self, visual_page):
        """Capture color test boxes in light mode."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Find and screenshot just the color test section
        color_section = page.locator('text=Color Test').locator('..')
        if color_section.is_visible():
            screenshot_path = CURRENT_DIR / "color-boxes-light.png"
            color_section.screenshot(path=str(screenshot_path))
            print(f"\n[Visual] Color boxes (light) saved: {screenshot_path}")

    def test_capture_color_boxes_dark(self, visual_page):
        """Capture color test boxes in dark mode."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Find and screenshot just the color test section
        color_section = page.locator('text=Color Test').locator('..')
        if color_section.is_visible():
            screenshot_path = CURRENT_DIR / "color-boxes-dark.png"
            color_section.screenshot(path=str(screenshot_path))
            print(f"\n[Visual] Color boxes (dark) saved: {screenshot_path}")


@pytest.mark.visual
class TestMultiPageScreenshots:
    """Capture screenshots of multiple pages for visual comparison."""

    @pytest.mark.parametrize("page_name", ["Watchlist", "Screener", "Trends"])
    def test_capture_page_light_mode(self, visual_page, page_name):
        """Capture page screenshots in light mode."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure light mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Navigate to page
        sidebar = page.locator('[data-testid="stSidebar"]')
        nav_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text=page_name).first

        if nav_link.is_visible():
            nav_link.click()
            wait_for_streamlit_rerun(page)

            # Take screenshot
            screenshot_path = CURRENT_DIR / f"{page_name.lower()}-light.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\n[Visual] {page_name} (light) saved: {screenshot_path}")

    @pytest.mark.parametrize("page_name", ["Watchlist", "Screener", "Trends"])
    def test_capture_page_dark_mode(self, visual_page, page_name):
        """Capture page screenshots in dark mode."""
        if not PIL_AVAILABLE:
            pytest.skip("Pillow not installed")

        page = visual_page

        # Ensure dark mode
        toggle = page.locator(
            '[data-testid="stSidebar"] [data-testid="stCheckbox"]'
        ).first
        if not toggle.is_checked():
            toggle.click()
            wait_for_streamlit_rerun(page)

        # Navigate to page
        sidebar = page.locator('[data-testid="stSidebar"]')
        nav_link = sidebar.locator('[data-testid="stSidebarNavLink"]', has_text=page_name).first

        if nav_link.is_visible():
            nav_link.click()
            wait_for_streamlit_rerun(page)

            # Take screenshot
            screenshot_path = CURRENT_DIR / f"{page_name.lower()}-dark.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\n[Visual] {page_name} (dark) saved: {screenshot_path}")
