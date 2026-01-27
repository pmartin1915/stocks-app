#!/usr/bin/env python
"""
Convenience script to launch the Asymmetric dashboard.

Usage:
    python run_dashboard.py

The dashboard will be available at http://localhost:8501
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Launch the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"

    if not dashboard_path.exists():
        print(f"Error: Dashboard not found at {dashboard_path}")
        sys.exit(1)

    print("Starting Asymmetric Dashboard...")
    print("Dashboard will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
            check=True,
        )
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error running dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
