# AI-Automated Testing Setup for Asymmetric Dashboard

**Purpose:** Enable fully automated testing of Streamlit dashboard functionality, including visual regression testing for dark mode.

---

## Quick Start

```bash
# 1. Install testing dependencies
pip install pytest playwright streamlit[testing] Pillow pytest-html

# 2. Install browser drivers
playwright install chromium

# 3. Run all tests
pytest tests/ -v --html=reports/test-report.html

# 4. Run specific test suites
pytest tests/e2e/ -v              # Browser-based E2E tests
pytest tests/unit/ -v             # Fast unit tests
pytest tests/visual/ -v           # Visual regression tests
```

---

## Testing Architecture

```
tests/
├── e2e/                    # End-to-end browser tests (Playwright)
│   ├── test_dark_mode.py
│   ├── test_navigation.py
│   └── test_watchlist.py
│
├── unit/                   # Fast unit tests (Streamlit testing)
│   ├── test_theme.py
│   ├── test_sidebar.py
│   └── test_components.py
│
├── visual/                 # Visual regression tests
│   ├── test_dark_mode_visual.py
│   ├── snapshots/
│   │   ├── baseline/
│   │   │   ├── light-mode.png
│   │   │   └── dark-mode.png
│   │   └── current/
│   │       ├── light-mode.png
│   │       └── dark-mode.png
│   └── diffs/
│
├── fixtures/               # Test data
│   ├── sample_stocks.json
│   └── sample_theses.json
│
└── conftest.py            # Shared fixtures
```

---

## 1. End-to-End Tests (Playwright)

### Installation

```bash
pip install pytest playwright
playwright install chromium
```

### Example Test: `tests/e2e/test_dark_mode.py`

```python
import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.fixture(scope="module")
def browser():
    """Launch browser once per module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set True for CI
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create fresh page for each test."""
    page = browser.new_page()
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stApp"]', timeout=10000)
    yield page
    page.close()


def test_dark_mode_toggle_exists(page):
    """Verify dark mode toggle is visible."""
    toggle = page.locator('text=Theme').locator('..')
    expect(toggle).to_be_visible()


def test_dark_mode_toggle_state_changes(page):
    """Verify toggle changes state when clicked."""
    # Find moon emoji toggle
    toggle = page.locator('[data-testid="basewidget-toggle"]').first

    # Get initial state
    initial_checked = toggle.is_checked()

    # Click toggle
    toggle.click()

    # Wait for rerun
    page.wait_for_timeout(2000)

    # Get new state
    new_checked = toggle.is_checked()

    # Assert state changed
    assert initial_checked != new_checked, "Toggle state didn't change"


def test_dark_mode_colors_change(page):
    """Verify colors actually change when toggle is clicked."""
    # Get initial green color box
    green_box = page.locator('text=GREEN').locator('..')
    initial_bg = green_box.evaluate('el => getComputedStyle(el).backgroundColor')

    # Click dark mode toggle
    toggle = page.locator('[data-testid="basewidget-toggle"]').first
    toggle.click()

    # Wait for rerun and rerender
    page.wait_for_timeout(2000)

    # Get new green color
    new_bg = green_box.evaluate('el => getComputedStyle(el).backgroundColor')

    # Assert colors are different
    assert initial_bg != new_bg, f"Color didn't change. Before: {initial_bg}, After: {new_bg}"

    # Verify specific color values
    # Light mode green: rgb(34, 197, 94) = #22c55e
    # Dark mode green: rgb(16, 185, 129) = #10b981
    assert initial_bg == "rgb(34, 197, 94)", f"Initial color wrong: {initial_bg}"
    assert new_bg == "rgb(16, 185, 129)", f"Dark color wrong: {new_bg}"


def test_debug_info_shows_correct_theme(page):
    """Verify debug info matches toggle state."""
    # Check initial debug info
    debug_text = page.locator('text=Theme:').locator('..')
    initial_theme = debug_text.inner_text()
    assert "light" in initial_theme.lower(), f"Initial theme wrong: {initial_theme}"

    # Click toggle
    toggle = page.locator('[data-testid="basewidget-toggle"]').first
    toggle.click()
    page.wait_for_timeout(2000)

    # Check updated debug info
    new_theme = debug_text.inner_text()
    assert "dark" in new_theme.lower(), f"New theme wrong: {new_theme}"
```

### Run E2E Tests

```bash
# Run with visible browser (debugging)
pytest tests/e2e/test_dark_mode.py -v -s

# Run headless (CI mode)
pytest tests/e2e/test_dark_mode.py -v

# Generate HTML report
pytest tests/e2e/ --html=reports/e2e-report.html
```

---

## 2. Unit Tests (Streamlit Testing)

### Installation

```bash
pip install streamlit[testing]
```

### Example Test: `tests/unit/test_theme.py`

```python
import pytest
from streamlit.testing.v1 import AppTest


def test_theme_initialization():
    """Test theme initializes to light mode."""
    app = AppTest.from_file("dashboard/app.py")
    app.run()

    assert app.session_state.theme == "light"


def test_theme_toggle_updates_state():
    """Test clicking toggle updates session state."""
    app = AppTest.from_file("dashboard/app.py")
    app.run()

    # Initial state
    assert app.session_state.theme == "light"

    # Simulate toggle click
    app.toggle[0].set_value(True).run()

    # Verify state changed
    assert app.session_state.theme == "dark"


def test_get_semantic_color_returns_correct_values():
    """Test color function returns theme-specific values."""
    from dashboard.theme import get_semantic_color
    import streamlit as st

    # Mock light theme
    st.session_state.theme = "light"
    assert get_semantic_color("green") == "#22c55e"
    assert get_semantic_color("red") == "#ef4444"
    assert get_semantic_color("blue") == "#3b82f6"

    # Mock dark theme
    st.session_state.theme = "dark"
    assert get_semantic_color("green") == "#10b981"
    assert get_semantic_color("red") == "#f87171"
    assert get_semantic_color("blue") == "#60a5fa"


def test_sidebar_renders_on_all_pages():
    """Test that sidebar is rendered on every page."""
    pages = [
        "dashboard/app.py",
        "dashboard/pages/1_Watchlist.py",
        "dashboard/pages/2_Screener.py",
        "dashboard/pages/5_Trends.py",
    ]

    for page_path in pages:
        app = AppTest.from_file(page_path)
        app.run()

        # Check sidebar title exists
        assert any("Asymmetric" in str(element) for element in app.sidebar)
```

### Run Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_theme.py -v

# Run with coverage
pytest tests/unit/ --cov=dashboard --cov-report=html
```

---

## 3. Visual Regression Tests

### Installation

```bash
pip install Pillow playwright
```

### Example Test: `tests/visual/test_dark_mode_visual.py`

```python
import pytest
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
import os


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


def test_dark_mode_visual_regression(browser):
    """Compare light mode vs dark mode screenshots."""
    page = browser.new_page()
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stApp"]', timeout=10000)

    # Ensure snapshots directory exists
    os.makedirs("tests/visual/snapshots/current", exist_ok=True)

    # Screenshot light mode
    light_path = "tests/visual/snapshots/current/light-mode.png"
    page.screenshot(path=light_path, full_page=True)

    # Click dark mode toggle
    toggle = page.locator('[data-testid="basewidget-toggle"]').first
    toggle.click()
    page.wait_for_timeout(2000)

    # Screenshot dark mode
    dark_path = "tests/visual/snapshots/current/dark-mode.png"
    page.screenshot(path=dark_path, full_page=True)

    page.close()

    # Compare images
    light_img = Image.open(light_path)
    dark_img = Image.open(dark_path)

    # Images should be different sizes (same) but different colors
    assert light_img.size == dark_img.size, "Screenshot sizes don't match"

    # Calculate difference
    diff = ImageChops.difference(light_img, dark_img)
    bbox = diff.getbbox()

    # Save diff image for debugging
    if bbox:
        diff_path = "tests/visual/snapshots/current/diff.png"
        diff.save(diff_path)

    # Assert images are different
    assert bbox is not None, "Light and dark mode screenshots are identical"

    # Calculate percentage difference
    diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0))
    total_pixels = light_img.size[0] * light_img.size[1]
    diff_percent = (diff_pixels / total_pixels) * 100

    # At least 10% of pixels should be different
    assert diff_percent > 10, f"Only {diff_percent:.1f}% pixels changed"


def test_compare_against_baseline(browser):
    """Compare current screenshots against approved baseline."""
    baseline_dir = "tests/visual/snapshots/baseline"
    current_dir = "tests/visual/snapshots/current"

    # Skip if no baseline exists
    if not os.path.exists(f"{baseline_dir}/light-mode.png"):
        pytest.skip("No baseline screenshots found")

    page = browser.new_page()
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stApp"]')

    # Take current screenshot
    current_path = f"{current_dir}/light-mode.png"
    page.screenshot(path=current_path, full_page=True)
    page.close()

    # Compare with baseline
    baseline_img = Image.open(f"{baseline_dir}/light-mode.png")
    current_img = Image.open(current_path)

    diff = ImageChops.difference(baseline_img, current_img)
    bbox = diff.getbbox()

    # If different, save diff
    if bbox:
        diff.save(f"{current_dir}/diff-from-baseline.png")

    # Assert no unexpected changes (allow <1% pixel difference for anti-aliasing)
    if bbox:
        diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0))
        total_pixels = baseline_img.size[0] * baseline_img.size[1]
        diff_percent = (diff_pixels / total_pixels) * 100

        assert diff_percent < 1, f"Visual regression detected: {diff_percent:.2f}% pixels changed"
```

### Update Baseline Screenshots

```bash
# Take new baseline screenshots (after approving visual changes)
pytest tests/visual/test_dark_mode_visual.py -v
cp tests/visual/snapshots/current/*.png tests/visual/snapshots/baseline/
```

---

## 4. Configuration Files

### `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    e2e: End-to-end browser tests (slow)
    unit: Fast unit tests
    visual: Visual regression tests

addopts =
    -v
    --strict-markers
    --tb=short
    --html=reports/test-report.html
    --self-contained-html

filterwarnings =
    ignore::DeprecationWarning
```

### `requirements-test.txt`

```
pytest==7.4.3
playwright==1.40.0
Pillow==10.1.0
pytest-html==4.1.1
pytest-cov==4.1.0
```

### `conftest.py` (Shared Fixtures)

```python
import pytest
import subprocess
import time
import signal
import os


@pytest.fixture(scope="session", autouse=True)
def start_streamlit():
    """Start Streamlit server before tests, stop after."""
    # Start Streamlit in background
    proc = subprocess.Popen(
        ["streamlit", "run", "dashboard/app.py", "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if os.name != 'nt' else None
    )

    # Wait for server to start
    time.sleep(10)

    yield

    # Stop server after tests
    if os.name == 'nt':
        proc.terminate()
    else:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

    proc.wait()


@pytest.fixture
def clean_session_state():
    """Reset session state between tests."""
    import streamlit as st
    st.session_state.clear()
    st.session_state.theme = "light"
```

---

## 5. CI/CD Integration

### GitHub Actions: `.github/workflows/test-dashboard.yml`

```yaml
name: Dashboard Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
          playwright install chromium

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=dashboard --cov-report=xml

      - name: Start Streamlit
        run: |
          streamlit run dashboard/app.py --server.headless=true &
          sleep 10

      - name: Run E2E tests
        run: pytest tests/e2e/ -v

      - name: Run visual regression tests
        run: pytest tests/visual/ -v

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: reports/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: failure-screenshots
          path: tests/visual/snapshots/current/
```

---

## 6. Running Tests Locally

### Full Test Suite

```bash
# Run all tests
pytest tests/ -v --html=reports/test-report.html

# View report
open reports/test-report.html  # macOS
start reports/test-report.html  # Windows
xdg-open reports/test-report.html  # Linux
```

### Specific Test Categories

```bash
# Fast unit tests only
pytest tests/unit/ -v

# Slow E2E tests only
pytest tests/e2e/ -v -m e2e

# Visual regression only
pytest tests/visual/ -v -m visual

# Skip slow tests
pytest tests/ -v -m "not e2e"
```

### Debug Mode

```bash
# Run with visible browser
pytest tests/e2e/test_dark_mode.py -v -s --headed

# Stop on first failure
pytest tests/ -v -x

# Run specific test function
pytest tests/e2e/test_dark_mode.py::test_dark_mode_colors_change -v
```

### Coverage Report

```bash
# Generate coverage report
pytest tests/ --cov=dashboard --cov-report=html

# View coverage
open htmlcov/index.html
```

---

## 7. Debugging Failed Tests

### Check Streamlit Logs

```bash
# Run Streamlit with verbose logging
streamlit run dashboard/app.py --logger.level=debug
```

### Save Screenshots on Failure

Add to `conftest.py`:
```python
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed:
        # Save screenshot
        if hasattr(item, 'funcargs') and 'page' in item.funcargs:
            page = item.funcargs['page']
            screenshot_path = f"tests/failures/{item.name}.png"
            page.screenshot(path=screenshot_path)
```

### Browser DevTools Inspection

```python
# In test, pause to inspect
def test_dark_mode_debug(page):
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stApp"]')

    # Open DevTools and pause
    page.pause()  # Opens interactive inspector

    # Continue test after manual inspection
    toggle = page.locator('[data-testid="basewidget-toggle"]')
    toggle.click()
```

---

## 8. AI Agent Integration

### Running Tests via Claude Code

```bash
# In Claude Code session
/test dark-mode  # Runs pytest tests/e2e/test_dark_mode.py -v
```

### Automated Test Generation

Ask Claude Code to generate tests:
```
"Generate Playwright test for verifying the Screener page loads with correct filters"
```

### Test Result Analysis

Claude Code can analyze test failures:
```
"Analyze the test failure in tests/e2e/test_dark_mode.py and suggest fixes"
```

---

## Success Metrics

- ✅ All tests pass in CI/CD
- ✅ Visual regression tests detect theme changes
- ✅ Coverage > 80% for theme-related code
- ✅ E2E tests verify user-facing functionality
- ✅ Tests run in < 5 minutes total

---

## Next Steps

1. Create test files from examples above
2. Run initial test suite locally
3. Fix any failures
4. Set up GitHub Actions
5. Add test badges to README
6. Document test results

---

**Last Updated:** 2026-02-01
**Maintainer:** AI-assisted development
