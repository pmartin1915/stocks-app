"""Status command showing current Asymmetric state."""

import json
import logging

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from asymmetric.cli.formatting import (
    BORDER_PRIMARY,
    MISSING,
)
from asymmetric.config import config

# Watchlist file location (same as watchlist.py)
WATCHLIST_FILE = Path.home() / ".asymmetric" / "watchlist.json"


def _get_db_status() -> tuple[bool, str]:
    """Check database initialization status."""
    db_path = config.db_path
    if not db_path.exists():
        return False, "Not initialized"

    # Get file modification time
    mtime = datetime.fromtimestamp(db_path.stat().st_mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - mtime

    if age.days > 0:
        age_str = f"{age.days}d ago"
    elif age.seconds > 3600:
        age_str = f"{age.seconds // 3600}h ago"
    else:
        age_str = f"{age.seconds // 60}m ago"

    return True, f"Updated {age_str}"


def _get_watchlist_count() -> int:
    """Get number of stocks in watchlist."""
    if not WATCHLIST_FILE.exists():
        return 0

    try:
        with open(WATCHLIST_FILE, "r") as f:
            data = json.load(f)
            return len(data.get("stocks", {}))
    except (json.JSONDecodeError, IOError):
        return 0


def _get_portfolio_count() -> int:
    """Get number of positions in portfolio."""
    try:
        from sqlmodel import select

        from asymmetric.db.database import get_session
        from asymmetric.db.portfolio_models import Holding

        with get_session() as session:
            stmt = select(Holding).where(Holding.quantity > 0)
            holdings = session.exec(stmt).all()
            return len(holdings)
    except Exception:  # Intentional: status helpers should not crash on missing data
        return 0


def _get_alerts_count() -> int:
    """Get number of active alerts."""
    try:
        from sqlmodel import select

        from asymmetric.db.alert_models import Alert
        from asymmetric.db.database import get_session

        with get_session() as session:
            stmt = select(Alert).where(Alert.active == True)  # noqa: E712
            alerts = session.exec(stmt).all()
            return len(alerts)
    except Exception:  # Intentional: status helpers should not crash on missing data
        return 0


def _get_recent_decisions_count() -> int:
    """Get number of decisions in the last 30 days."""
    try:
        from datetime import timedelta

        from sqlmodel import select

        from asymmetric.db.database import get_session
        from asymmetric.db.models import Decision

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        with get_session() as session:
            stmt = select(Decision).where(Decision.created_at >= cutoff)
            decisions = session.exec(stmt).all()
            return len(decisions)
    except Exception:  # Intentional: status helpers should not crash on missing data
        return 0


def _get_theses_count() -> int:
    """Get total number of theses."""
    try:
        from sqlmodel import select

        from asymmetric.db.database import get_session
        from asymmetric.db.models import Thesis

        with get_session() as session:
            stmt = select(Thesis)
            theses = session.exec(stmt).all()
            return len(theses)
    except Exception:  # Intentional: status helpers should not crash on missing data
        return 0


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """
    Show current Asymmetric status.

    Displays database status, watchlist count, portfolio positions,
    and recent activity at a glance.

    \b
    Examples:
        asymmetric status
    """
    console: Console = ctx.obj["console"]

    console.print()
    console.print(
        Panel.fit(
            "[bold]Asymmetric Status[/bold]",
            border_style=BORDER_PRIMARY,
        )
    )
    console.print()

    # Build status table
    table = Table(
        show_header=False,
        padding=(0, 2),
        box=None,
    )
    table.add_column("Item", style="cyan", width=24)
    table.add_column("Value", width=30)

    # Database status
    db_ok, db_status = _get_db_status()
    db_indicator = "[green]OK[/green]" if db_ok else "[red]--[/red]"
    table.add_row("Database", f"{db_indicator}  {db_status}")

    # Watchlist
    wl_count = _get_watchlist_count()
    wl_text = f"{wl_count} stocks" if wl_count > 0 else MISSING
    table.add_row("Watchlist", wl_text)

    # Portfolio
    port_count = _get_portfolio_count()
    port_text = f"{port_count} positions" if port_count > 0 else MISSING
    table.add_row("Portfolio", port_text)

    # Alerts
    alerts_count = _get_alerts_count()
    alerts_text = f"{alerts_count} active" if alerts_count > 0 else MISSING
    table.add_row("Alerts", alerts_text)

    # Theses
    theses_count = _get_theses_count()
    theses_text = str(theses_count) if theses_count > 0 else MISSING
    table.add_row("Theses", theses_text)

    # Recent decisions
    decisions_count = _get_recent_decisions_count()
    decisions_text = f"{decisions_count} (last 30d)" if decisions_count > 0 else MISSING
    table.add_row("Recent Decisions", decisions_text)

    console.print(table)
    console.print()

    # Show quick hints if not set up
    if not db_ok:
        console.print("[yellow]Get started:[/yellow]")
        console.print("  asymmetric db init")
        console.print("  asymmetric db refresh")
        console.print()
    elif wl_count == 0 and port_count == 0:
        console.print("[dim]Try: asymmetric screen --piotroski-min 7[/dim]")
        console.print()
