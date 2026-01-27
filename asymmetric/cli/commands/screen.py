"""Screen command for filtering stocks by quantitative criteria."""

import json
import logging
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import get_score_color, get_zone_color
from asymmetric.core.data.bulk_manager import BulkDataManager
from asymmetric.core.data.exceptions import (
    InsufficientDataError,
    SECRateLimitError,
)
from asymmetric.core.scoring import AltmanScorer, PiotroskiScorer

# Watchlist file location
WATCHLIST_FILE = Path.home() / ".asymmetric" / "watchlist.json"

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--piotroski-min",
    type=click.IntRange(0, 9),
    default=None,
    help="Minimum Piotroski F-Score (0-9)",
)
@click.option(
    "--altman-min",
    type=click.FloatRange(min=-10.0, max=50.0),
    default=None,
    help="Minimum Altman Z-Score (typically 1.81-3.0)",
)
@click.option(
    "--altman-zone",
    type=click.Choice(["Safe", "Grey", "Distress"], case_sensitive=False),
    default=None,
    help="Required Altman zone",
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Update bulk data before screening",
)
@click.option(
    "--limit",
    type=click.IntRange(1, 10000),
    default=50,
    help="Maximum results to return (1-10000)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["piotroski", "altman", "ticker"]),
    default="piotroski",
    help="Field to sort by",
)
@click.option(
    "--sort-order",
    type=click.Choice(["asc", "desc"]),
    default="desc",
    help="Sort order",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON",
)
@click.option(
    "--add-to-watchlist",
    is_flag=True,
    help="Add passing stocks to watchlist",
)
@click.pass_context
def screen(
    ctx: click.Context,
    piotroski_min: int | None,
    altman_min: float | None,
    altman_zone: str | None,
    refresh: bool,
    limit: int,
    sort_by: str,
    sort_order: str,
    as_json: bool,
    add_to_watchlist: bool,
) -> None:
    """
    Screen stocks by quantitative criteria.

    Filter the stock universe using Piotroski F-Score and Altman Z-Score
    criteria. Uses bulk SEC data from DuckDB for zero API calls during
    screening.

    \b
    Piotroski F-Score (0-9):
        7-9: Strong - Financially healthy
        4-6: Moderate - Mixed signals
        0-3: Weak - Financial concerns

    \b
    Altman Z-Score Zones:
        Safe: > 2.99 - Low bankruptcy risk
        Grey: 1.81-2.99 - Uncertain
        Distress: < 1.81 - High bankruptcy risk

    \b
    Examples:
        asymmetric screen --piotroski-min 7
        asymmetric screen --altman-zone Safe --limit 25
        asymmetric screen --piotroski-min 6 --altman-min 2.99
        asymmetric screen --refresh --limit 100
        asymmetric screen --json
    """
    console: Console = ctx.obj["console"]

    try:
        bulk = BulkDataManager()

        # Handle --refresh flag
        if refresh:
            console.print("[bold blue]Refreshing bulk data...[/bold blue]")
            try:
                bulk.refresh()
                console.print("[green]Bulk data updated.[/green]\n")
            except SECRateLimitError as e:
                console.print(f"[red]SEC Rate Limit Hit:[/red] {e}")
                console.print("[yellow]Wait a few minutes and try again.[/yellow]")
                raise SystemExit(1)

        # Use optimized batch approach: get pre-filtered scorable tickers
        console.print("[dim]Finding scorable companies...[/dim]")
        tickers = bulk.get_scorable_tickers(
            require_piotroski=True,
            require_altman=True,
            limit=1000,
        )

        if not tickers:
            # Fall back to all tickers if scorable query fails
            tickers = bulk.get_all_tickers(limit=1000)

        if not tickers:
            console.print("[yellow]No bulk data available.[/yellow]")
            console.print("Run [cyan]asymmetric db refresh[/cyan] to download SEC data.")
            raise SystemExit(1)

        # Initialize scorers
        piotroski_scorer = PiotroskiScorer()
        altman_scorer = AltmanScorer()

        results = []
        skipped_count = 0

        # Use batch query for better performance
        console.print(f"[dim]Fetching financial data for {len(tickers)} companies...[/dim]")
        batch_data = bulk.get_batch_financials(tickers, periods=2)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Scoring {len(batch_data)} companies...",
                total=len(batch_data),
            )

            for ticker, periods_data in batch_data.items():
                progress.update(task, advance=1)

                try:
                    if not periods_data:
                        skipped_count += 1
                        continue

                    # Current period is first (newest), prior is second
                    current_financials = periods_data[0]
                    prior_financials = periods_data[1] if len(periods_data) > 1 else {}

                    # Calculate scores
                    try:
                        piotroski_result = piotroski_scorer.calculate_from_dict(
                            current_financials, prior_financials
                        )
                    except InsufficientDataError:
                        skipped_count += 1
                        continue

                    try:
                        altman_result = altman_scorer.calculate_from_dict(current_financials)
                    except InsufficientDataError:
                        skipped_count += 1
                        continue

                    # Apply filters
                    if piotroski_min is not None and piotroski_result.score < piotroski_min:
                        continue
                    # Case-insensitive zone comparison (user might pass "safe" instead of "Safe")
                    if altman_zone is not None and altman_result.zone.lower() != altman_zone.lower():
                        continue
                    if altman_min is not None and altman_result.z_score < altman_min:
                        continue

                    # Get company info for display
                    company_info = bulk.get_company_info(ticker)
                    company_name = company_info.get("company_name", "") if company_info else ""

                    results.append({
                        "ticker": ticker,
                        "company_name": company_name[:30] if company_name else "",
                        "piotroski_score": piotroski_result.score,
                        "piotroski_interpretation": piotroski_result.interpretation,
                        "altman_z_score": round(altman_result.z_score, 2),
                        "altman_zone": altman_result.zone,
                    })

                except Exception as e:
                    logger.debug(f"Skipping {ticker}: {e}")
                    skipped_count += 1
                    continue

        # Sort results
        sort_keys = {
            "piotroski": lambda x: x["piotroski_score"],
            "altman": lambda x: x["altman_z_score"],
            "ticker": lambda x: x["ticker"],
        }
        reverse = sort_order == "desc"
        results.sort(key=sort_keys[sort_by], reverse=reverse)

        # Apply limit
        results = results[:limit]

        # Build output
        criteria = {}
        if piotroski_min is not None:
            criteria["piotroski_min"] = piotroski_min
        if altman_min is not None:
            criteria["altman_min"] = altman_min
        if altman_zone is not None:
            criteria["altman_zone"] = altman_zone

        output = {
            "criteria": criteria,
            "stats": {
                "total_tickers": len(tickers),
                "total_scored": len(tickers) - skipped_count,
                "skipped": skipped_count,
                "matches": len(results),
            },
            "results": results,
        }

        # Add to watchlist if requested
        if add_to_watchlist and results:
            added_count = _add_results_to_watchlist(results, criteria)
            if not as_json:
                console.print(f"[green]Added {added_count} stocks to watchlist[/green]")
                console.print()

        if as_json:
            console.print(json.dumps(output, indent=2))
        else:
            _display_results(console, output)

    except Exception as e:
        if not isinstance(e, SystemExit):
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        raise


def _display_results(console: Console, output: dict) -> None:
    """Display screening results using Rich formatting."""
    stats = output["stats"]
    criteria = output["criteria"]
    results = output["results"]

    console.print()
    console.print(
        f"[bold]Screening Results[/bold] "
        f"({stats['matches']} matches from {stats['total_scored']} companies)"
    )
    console.print()

    if not results:
        console.print("[yellow]No stocks match the specified criteria.[/yellow]")
    else:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Ticker", style="cyan", width=8)
        table.add_column("Company", width=25)
        table.add_column("Piotroski", justify="center", width=12)
        table.add_column("Altman Z", justify="right", width=10)
        table.add_column("Zone", justify="center", width=10)

        for r in results:
            score = r["piotroski_score"]
            score_color = get_score_color(score, 9)
            zone = r["altman_zone"]
            zone_color = get_zone_color(zone)

            table.add_row(
                r["ticker"],
                r["company_name"],
                Text(f"{score}/9", style=score_color),
                f"{r['altman_z_score']:.2f}",
                Text(zone, style=zone_color),
            )

        console.print(table)

    console.print()

    # Show criteria if any were specified
    if criteria:
        criteria_parts = []
        if "piotroski_min" in criteria:
            criteria_parts.append(f"piotroski_min={criteria['piotroski_min']}")
        if "altman_min" in criteria:
            criteria_parts.append(f"altman_min={criteria['altman_min']}")
        if "altman_zone" in criteria:
            criteria_parts.append(f"altman_zone={criteria['altman_zone']}")
        console.print(f"[dim]Criteria: {', '.join(criteria_parts)}[/dim]")

    if stats["skipped"] > 0:
        console.print(f"[dim]Skipped (insufficient data): {stats['skipped']}[/dim]")

    console.print()


def _add_results_to_watchlist(results: list[dict], criteria: dict) -> int:
    """
    Add screening results to watchlist.

    Args:
        results: List of screening result dicts with ticker, scores, etc.
        criteria: Screening criteria used (for notes)

    Returns:
        Number of stocks added to watchlist
    """
    # Ensure directory exists
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing watchlist
    if WATCHLIST_FILE.exists():
        try:
            with open(WATCHLIST_FILE, "r") as f:
                watchlist = json.load(f)
        except (json.JSONDecodeError, IOError):
            watchlist = {"stocks": {}}
    else:
        watchlist = {"stocks": {}}

    # Build note from criteria
    criteria_parts = []
    if criteria.get("piotroski_min"):
        criteria_parts.append(f"F>={criteria['piotroski_min']}")
    if criteria.get("altman_min"):
        criteria_parts.append(f"Z>={criteria['altman_min']}")
    if criteria.get("altman_zone"):
        criteria_parts.append(f"Zone={criteria['altman_zone']}")
    criteria_note = f"Screen: {', '.join(criteria_parts)}" if criteria_parts else "Screen result"

    # Add each result
    now = datetime.now().isoformat()
    added_count = 0

    for r in results:
        ticker = r["ticker"]
        if ticker not in watchlist["stocks"]:
            watchlist["stocks"][ticker] = {
                "added": now,
                "note": criteria_note,
                "source": "screen",
            }
            added_count += 1
        else:
            # Update existing entry with screen info
            watchlist["stocks"][ticker]["last_screened"] = now
            watchlist["stocks"][ticker]["screen_note"] = criteria_note

        # Cache the scores
        watchlist["stocks"][ticker]["cached_scores"] = {
            "piotroski": r.get("piotroski_score"),
            "altman": {
                "z_score": r.get("altman_z_score"),
                "zone": r.get("altman_zone"),
            } if r.get("altman_z_score") else None,
        }
        watchlist["stocks"][ticker]["cached_at"] = now

    # Save watchlist
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)

    return added_count
