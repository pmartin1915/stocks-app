#!/usr/bin/env python
"""
Convenience script to launch the Asymmetric dashboard.

Usage:
    python run_dashboard.py

The dashboard will be available at http://localhost:8501
"""

import shutil
import subprocess
import sys
from pathlib import Path


def _clear_streamlit_cache() -> None:
    """Remove Streamlit's __pycache__ and cache dirs so restarted servers
    always pick up the latest code.  Harmless if the dirs don't exist."""
    cache_dir = Path(__file__).parent / ".streamlit" / "cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)

    # Also clear any .pyc bytecache in the dashboard package so Python
    # doesn't serve stale compiled modules.
    for pyc_dir in Path(__file__).parent.joinpath("dashboard").rglob("__pycache__"):
        shutil.rmtree(pyc_dir, ignore_errors=True)


def main() -> None:
    """Launch the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"

    if not dashboard_path.exists():
        print(f"Error: Dashboard not found at {dashboard_path}")
        sys.exit(1)

    _clear_streamlit_cache()

    print("Starting Asymmetric Dashboard...")
    print("Dashboard will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(
            [
                sys.executable, "-m", "streamlit", "run",
                str(dashboard_path),
                "--server.runOnSave", "true",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error running dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
