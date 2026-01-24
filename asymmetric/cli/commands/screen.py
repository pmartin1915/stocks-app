"""Screen command for filtering stocks by quantitative criteria."""

import json
import logging

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text

from asymmetric.core.data.bulk_manager import BulkDataManager
from asymmetric.core.data.exceptions import (
    InsufficientDataError,
    SECRateLimitError,
)
from asymmetric.core.scoring import AltmanScorer, PiotroskiScorer

logger = logging.getLogger(__name__)


def _get_score_color(score: int, max_score: int) -> str:
    """Get color based on score percentage."""
    pct = score / max_score
    if pct >= 0.7:
        return "green"
    elif pct >= 0.4:
        return "yellow"
    else:
        return "red"


def _get_zone_color(zone: str) -> str:
    """Get color based on Altman zone."""
    colors = {
        "Safe": "green",
        "Grey": "yellow",
        "Distress": "red",
    }
    return colors.get(zone, "white")


@click.command()
@click.option(
    "--piotroski-min",
    type=int,
    default=None,
    help="Minimum Piotroski F-Score (0-9)",
)
@click.option(
    "--altman-min",
    type=float,
    default=None,
    help="Minimum Altman Z-Score",
)
@click.option(
    "--altman-zone",
    type=click.Choice(["Safe", "Grey", "Distress"]),
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
    type=int,
    default=50,
    help="Maximum results to return",
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

        # Get all tickers from bulk data
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

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Screening {len(tickers)} companies...",
                total=len(tickers),
            )

            for ticker in tickers:
                progress.update(task, advance=1)

                try:
                    # Get 2 periods of financial data for Piotroski comparison
                    periods_data = bulk.get_financials_periods(ticker, periods=2)
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
                    if altman_zone is not None and altman_result.zone != altman_zone:
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
            score_color = _get_score_color(score, 9)
            zone = r["altman_zone"]
            zone_color = _get_zone_color(zone)

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
