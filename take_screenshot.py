#!/usr/bin/env python
"""Quick screenshot utility for visual testing.

Usage:
    python take_screenshot.py                    # Home page
    python take_screenshot.py /Watchlist         # Specific page
    python take_screenshot.py /Portfolio full    # Full page capture
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8501"
OUTPUT_DIR = Path(__file__).parent


def take_screenshot(
    page_name: str = "",
    full_page: bool = False,
    wait_ms: int = 4000,
) -> Path:
    """Capture a screenshot of a dashboard page.

    Args:
        page_name: Streamlit page name (e.g. "/Portfolio", "/Watchlist").
                   Empty string for the home page.
        full_page: Capture full scrollable page vs viewport only.
        wait_ms: Milliseconds to wait for page to settle.

    Returns:
        Path to the saved screenshot.
    """
    slug = page_name.strip("/").lower() or "home"
    url = f"{BASE_URL}/{page_name.lstrip('/')}" if page_name else BASE_URL
    out_path = OUTPUT_DIR / f"screenshot_{slug}.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=str(out_path), full_page=full_page)
        browser.close()

    print(f"Saved: {out_path}")
    return out_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    full = "full" in sys.argv[2:] if len(sys.argv) > 2 else False
    take_screenshot(name, full_page=full)
