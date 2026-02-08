"""Pytest fixtures for E2E tests using Playwright.

This module provides browser automation fixtures for testing the Streamlit dashboard.
Requires: pip install playwright && playwright install chromium

Usage:
    pytest tests/e2e/ -v --headed  # Run with visible browser
    pytest tests/e2e/ -v           # Run headless (default)
"""

import os
import signal
import subprocess
import sys
import time

import pytest

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: End-to-end browser tests")


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests if playwright is not installed."""
    if not PLAYWRIGHT_AVAILABLE:
        skip_marker = pytest.mark.skip(
            reason="Playwright not installed. Run: pip install playwright && playwright install chromium"
        )
        for item in items:
            if "e2e" in item.keywords or "tests/e2e" in str(item.fspath):
                item.add_marker(skip_marker)


# Base URL for Streamlit app
STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "http://localhost:8501")


@pytest.fixture(scope="session")
def streamlit_server():
    """Start Streamlit server for E2E tests.

    This fixture starts the Streamlit server before any e2e tests run,
    and stops it after all tests complete.

    Note: If the server is already running (e.g., in development),
    this fixture will detect it and skip starting a new one.
    """
    import socket

    # Check if server is already running
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    if is_port_in_use(8501):
        print("\n[E2E] Streamlit server already running on port 8501")
        yield STREAMLIT_URL
        return

    print("\n[E2E] Starting Streamlit server...")

    # Start Streamlit in a subprocess
    # Use shell=True on Windows for proper signal handling
    if sys.platform == "win32":
        proc = subprocess.Popen(
            ["streamlit", "run", "dashboard/app.py", "--server.headless=true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        proc = subprocess.Popen(
            ["streamlit", "run", "dashboard/app.py", "--server.headless=true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )

    # Wait for server to start
    max_wait = 30  # seconds
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_port_in_use(8501):
            print(f"[E2E] Streamlit server started on {STREAMLIT_URL}")
            break
        time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError("Streamlit server failed to start within 30 seconds")

    yield STREAMLIT_URL

    # Stop the server
    print("\n[E2E] Stopping Streamlit server...")
    if sys.platform == "win32":
        proc.terminate()
    else:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

    proc.wait(timeout=10)
    print("[E2E] Streamlit server stopped")


@pytest.fixture(scope="module")
def browser(streamlit_server):
    """Launch Playwright browser for E2E tests.

    This fixture is scoped to the module level to avoid repeated
    browser launches, which can be slow.
    """
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed")

    with sync_playwright() as p:
        # Launch Chromium in headless mode by default
        # Set headless=False in the test or via CLI for debugging
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, streamlit_server):
    """Create a fresh browser page for each test.

    Each test gets its own page to ensure isolation.
    The page is pre-loaded with the Streamlit app.
    """
    page = browser.new_page()

    # Navigate to the app
    page.goto(streamlit_server)

    # Wait for Streamlit to fully load
    # The [data-testid="stApp"] selector indicates Streamlit is ready
    page.wait_for_selector('[data-testid="stApp"]', timeout=15000)

    # Additional wait for any dynamic content
    page.wait_for_timeout(1000)

    yield page

    page.close()


@pytest.fixture
def headed_browser(streamlit_server):
    """Launch browser in headed mode for debugging.

    Use this fixture when you want to see the browser during test execution.
    Example: def test_something(headed_browser): ...
    """
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        yield browser
        browser.close()


@pytest.fixture
def headed_page(headed_browser, streamlit_server):
    """Create a page in headed mode with slow motion for debugging."""
    page = headed_browser.new_page()
    page.goto(streamlit_server)
    page.wait_for_selector('[data-testid="stApp"]', timeout=15000)
    page.wait_for_timeout(1000)
    yield page
    page.close()


@pytest.fixture
def screenshot_on_failure(page, request):
    """Capture screenshot on test failure.

    Add this fixture to a test to automatically capture a screenshot
    if the test fails.
    """
    yield

    # Check if test failed
    if request.node.rep_call.failed:
        screenshot_dir = "tests/e2e/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        screenshot_path = os.path.join(
            screenshot_dir, f"{request.node.name}_failure.png"
        )
        page.screenshot(path=screenshot_path)
        print(f"\n[E2E] Screenshot saved: {screenshot_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for screenshot_on_failure fixture."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# Helper functions for common E2E operations


def wait_for_streamlit_rerun(page, timeout=5000):
    """Wait for Streamlit to complete a rerun after an action.

    Streamlit reruns the entire script when state changes.
    This helper waits for the rerun to complete.
    """
    # Streamlit shows a "Running..." indicator during rerun
    # Wait for it to disappear
    try:
        page.wait_for_selector(
            '[data-testid="stStatusWidget"]',
            state="hidden",
            timeout=timeout,
        )
    except Exception:
        pass  # Widget might not appear for fast reruns

    # Additional stabilization wait
    page.wait_for_timeout(500)


def click_theme_toggle(page):
    """Click the dark mode toggle in the sidebar.

    Returns the new toggle state (True for dark, False for light).
    """
    toggle = page.locator('[data-testid="stSidebar"] [data-testid="stCheckbox"]').first
    toggle.click()
    wait_for_streamlit_rerun(page)
    return toggle.is_checked()


def get_current_theme(page):
    """Get the current theme from the debug info in sidebar.

    Returns 'light' or 'dark'.
    """
    # Look for the debug info showing current theme
    debug_text = page.locator('text=Theme:').first
    if debug_text.is_visible():
        text = debug_text.inner_text()
        if "dark" in text.lower():
            return "dark"
        return "light"

    # Fallback: check toggle state
    toggle = page.locator('[data-testid="stSidebar"] [data-testid="stCheckbox"]').first
    return "dark" if toggle.is_checked() else "light"


def navigate_to_page(page, page_name):
    """Navigate to a specific page using the sidebar.

    Args:
        page: Playwright page object
        page_name: Name of the page to navigate to (e.g., "Watchlist", "Screener")
    """
    # Click on the page link in sidebar
    sidebar = page.locator('[data-testid="stSidebar"]')
    link = sidebar.locator(f'text={page_name}').first
    link.click()
    wait_for_streamlit_rerun(page)
