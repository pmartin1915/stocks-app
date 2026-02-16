"""Watchlist command for saving and reviewing stock picks."""

import json
import logging

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import get_score_color, get_zone_color
from asymmetric.core.data.edgar_client import EdgarClient
from asymmetric.core.data.exceptions import InsufficientDataError
from asymmetric.core.scoring import AltmanScorer, PiotroskiScorer

# Default watchlist location
WATCHLIST_FILE = Path.home() / ".asymmetric" / "watchlist.json"


def _ensure_watchlist_dir() -> None:
    """Ensure the watchlist directory exists."""
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_watchlist() -> dict:
    """Load watchlist from file."""
    if not WATCHLIST_FILE.exists():
        return {"stocks": {}}

    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"stocks": {}}


def _save_watchlist(watchlist: dict) -> None:
    """Save watchlist to file."""
    _ensure_watchlist_dir()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


@click.group()
@click.pass_context
def watchlist(ctx: click.Context) -> None:
    """
    Manage your stock watchlist.

    Save interesting stocks for later review. The watchlist persists
    between sessions.

    \b
    Examples:
        asymmetric watchlist add AAPL
        asymmetric watchlist add MSFT --note "Great cloud growth"
        asymmetric watchlist review
        asymmetric watchlist remove AAPL
        asymmetric watchlist clear
    """
    pass


@watchlist.command()
@click.argument("ticker")
@click.option("--note", "-n", default="", help="Optional note about why you're watching")
@click.pass_context
def add(ctx: click.Context, ticker: str, note: str) -> None:
    """Add a stock to your watchlist."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    wl = _load_watchlist()

    if ticker in wl["stocks"]:
        console.print(f"[yellow]{ticker} is already on your watchlist[/yellow]")
        if note:
            wl["stocks"][ticker]["note"] = note
            wl["stocks"][ticker]["updated"] = datetime.now(timezone.utc).isoformat()
            _save_watchlist(wl)
            console.print(f"[dim]Updated note for {ticker}[/dim]")
        return

    wl["stocks"][ticker] = {
        "added": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    _save_watchlist(wl)

    console.print(f"[green]Added {ticker} to watchlist[/green]")
    if note:
        console.print(f"[dim]Note: {note}[/dim]")

    console.print()
    console.print(f"[dim]Next: Run `asymmetric watchlist review` to see all stocks[/dim]")


@watchlist.command()
@click.argument("ticker")
@click.pass_context
def remove(ctx: click.Context, ticker: str) -> None:
    """Remove a stock from your watchlist."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    wl = _load_watchlist()

    if ticker not in wl["stocks"]:
        console.print(f"[yellow]{ticker} is not on your watchlist[/yellow]")
        return

    del wl["stocks"][ticker]
    _save_watchlist(wl)

    console.print(f"[green]Removed {ticker} from watchlist[/green]")


@watchlist.command()
@click.pass_context
def clear(ctx: click.Context) -> None:
    """Clear all stocks from your watchlist."""
    console: Console = ctx.obj["console"]

    wl = _load_watchlist()
    count = len(wl["stocks"])

    if count == 0:
        console.print("[dim]Watchlist is already empty[/dim]")
        return

    wl["stocks"] = {}
    _save_watchlist(wl)

    console.print(f"[green]Cleared {count} stocks from watchlist[/green]")


@watchlist.command("list")
@click.pass_context
def list_stocks(ctx: click.Context) -> None:
    """List all stocks on your watchlist (without scores)."""
    console: Console = ctx.obj["console"]

    wl = _load_watchlist()

    if not wl["stocks"]:
        console.print("[dim]Your watchlist is empty[/dim]")
        console.print()
        console.print("[dim]Add stocks with: asymmetric watchlist add AAPL[/dim]")
        return

    console.print()
    console.print(f"[bold]Watchlist ({len(wl['stocks'])} stocks)[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Ticker", style="bold")
    table.add_column("Added")
    table.add_column("Note", style="dim")

    for ticker, data in sorted(wl["stocks"].items()):
        added = data.get("added", "")
        if added:
            try:
                added_dt = datetime.fromisoformat(added)
                added = added_dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        note = data.get("note", "")
        table.add_row(ticker, added, note[:40] + "..." if len(note) > 40 else note)

    console.print(table)
    console.print()
    console.print("[dim]Run `asymmetric watchlist review` to see scores[/dim]")


@watchlist.command()
@click.option("--refresh", is_flag=True, help="Fetch fresh scores from SEC")
@click.pass_context
def review(ctx: click.Context, refresh: bool) -> None:
    """
    Review your watchlist with current scores.

    Shows F-Score and Z-Score for each stock. Use --refresh to fetch
    the latest data from SEC (rate limited).
    """
    console: Console = ctx.obj["console"]

    wl = _load_watchlist()

    if not wl["stocks"]:
        console.print("[dim]Your watchlist is empty[/dim]")
        console.print()
        console.print("[dim]Add stocks with: asymmetric watchlist add AAPL[/dim]")
        return

    tickers = list(wl["stocks"].keys())

    # Fetch scores
    results = {}
    if refresh:
        client = EdgarClient()
        with console.status("[bold blue]Fetching scores...[/bold blue]") as status:
            for ticker in tickers:
                status.update(f"[bold blue]Fetching {ticker}...[/bold blue]")
                try:
                    financials = client.get_financials(ticker, periods=2)
                    if financials.get("periods"):
                        current = financials["periods"][0]
                        prior = financials["periods"][1] if len(financials["periods"]) > 1 else {}

                        result = {"piotroski": None, "altman": None}

                        try:
                            p = PiotroskiScorer()
                            f_result = p.calculate_from_dict(current, prior)
                            result["piotroski"] = f_result.score
                        except InsufficientDataError:
                            pass

                        try:
                            a = AltmanScorer()
                            z_result = a.calculate_from_dict(current)
                            result["altman"] = {"z_score": z_result.z_score, "zone": z_result.zone}
                        except InsufficientDataError:
                            pass

                        results[ticker] = result

                        # Update cached scores
                        wl["stocks"][ticker]["cached_scores"] = result
                        wl["stocks"][ticker]["cached_at"] = datetime.now(timezone.utc).isoformat()
                except Exception as e:
                    logger.debug("Score cache miss for %s: %s", ticker, e)

        _save_watchlist(wl)
    else:
        # Use cached scores if available
        for ticker in tickers:
            if "cached_scores" in wl["stocks"][ticker]:
                results[ticker] = wl["stocks"][ticker]["cached_scores"]

    # Display results
    console.print()
    console.print(f"[bold]Watchlist Review ({len(tickers)} stocks)[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Ticker", style="bold")
    table.add_column("F-Score", justify="center")
    table.add_column("Z-Score", justify="center")
    table.add_column("Zone", justify="center")
    table.add_column("Note", style="dim")

    for ticker in sorted(tickers):
        data = wl["stocks"][ticker]
        note = data.get("note", "")[:30]

        if ticker in results:
            r = results[ticker]

            # F-Score
            if r.get("piotroski") is not None:
                f_score = r["piotroski"]
                f_color = get_score_color(f_score, 9)
                f_text = Text(f"{f_score}/9", style=f"bold {f_color}")
            else:
                f_text = Text("N/A", style="dim")

            # Z-Score
            if r.get("altman"):
                z_score = r["altman"]["z_score"]
                zone = r["altman"]["zone"]
                z_color = get_zone_color(zone)
                z_text = Text(f"{z_score:.2f}", style=f"bold {z_color}")
                zone_text = Text(zone, style=z_color)
            else:
                z_text = Text("N/A", style="dim")
                zone_text = Text("-", style="dim")

            table.add_row(ticker, f_text, z_text, zone_text, note)
        else:
            table.add_row(
                ticker,
                Text("?", style="dim"),
                Text("?", style="dim"),
                Text("-", style="dim"),
                note,
            )

    console.print(table)

    if not refresh and not any("cached_scores" in wl["stocks"][t] for t in tickers):
        console.print()
        console.print("[dim]No cached scores. Run with --refresh to fetch from SEC[/dim]")

    # Next actions
    console.print()
    console.print("[dim]Next steps:[/dim]")
    if tickers:
        console.print(f"  [dim]Compare:[/dim]  asymmetric compare {' '.join(tickers[:3])}")
        console.print(f"  [dim]Score:[/dim]  asymmetric score {tickers[0]}")
    console.print()
