"""Sector analysis commands for peer comparison and filtering."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import get_score_color, get_zone_color
from asymmetric.core.sectors.analyzer import SectorAnalyzer


@click.group()
@click.pass_context
def sectors(ctx: click.Context) -> None:
    """
    Sector and industry analysis.

    Compare stocks to sector peers, view sector averages,
    and find top performers by sector.

    \b
    Examples:
        asymmetric sectors list
        asymmetric sectors top --sector Manufacturing
        asymmetric sectors compare AAPL
        asymmetric sectors averages
    """
    pass


@sectors.command("list")
@click.option("--show-counts", is_flag=True, help="Show company counts per sector")
@click.pass_context
def sectors_list(ctx: click.Context, show_counts: bool) -> None:
    """List available sectors with optional company counts."""
    console: Console = ctx.obj["console"]

    available = SectorAnalyzer.get_available_sectors()

    if show_counts:
        analyzer = SectorAnalyzer()
        averages = analyzer.get_sector_averages()

        table = Table(title="Sectors by Company Count")
        table.add_column("Sector", style="cyan")
        table.add_column("Companies", justify="right")
        table.add_column("Avg F-Score", justify="center")
        table.add_column("Avg Z-Score", justify="right")
        table.add_column("Safe %", justify="right", style="green")

        for avg in sorted(averages, key=lambda x: x.company_count, reverse=True):
            safe_pct = (avg.safe_count / avg.company_count * 100) if avg.company_count > 0 else 0
            table.add_row(
                avg.sector,
                str(avg.company_count),
                f"{avg.avg_fscore:.1f}",
                f"{avg.avg_zscore:.2f}",
                f"{safe_pct:.0f}%",
            )

        console.print(table)
    else:
        console.print(Panel.fit("[bold]Available Sectors[/bold]"))
        for sector in available:
            industries = SectorAnalyzer.get_industries_for_sector(sector)
            console.print(f"  [cyan]{sector}[/cyan] ({len(industries)} industries)")


@sectors.command("top")
@click.option("--sector", required=True, help="Sector to analyze")
@click.option(
    "--metric", type=click.Choice(["fscore", "zscore"]), default="fscore", help="Ranking metric"
)
@click.option("--limit", type=int, default=10, help="Maximum results")
@click.pass_context
def sectors_top(ctx: click.Context, sector: str, metric: str, limit: int) -> None:
    """Show top performers in a sector."""
    console: Console = ctx.obj["console"]

    analyzer = SectorAnalyzer()
    leaders = analyzer.get_sector_leaders(sector, metric=metric, limit=limit)

    if not leaders:
        console.print(f"[yellow]No stocks found in sector: {sector}[/yellow]")
        console.print("[dim]Tip: Run `asymmetric sectors list` to see available sectors[/dim]")
        return

    metric_label = "F-Score" if metric == "fscore" else "Z-Score"
    table = Table(title=f"Top {limit} in {sector} by {metric_label}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Ticker", style="cyan")
    table.add_column("Company", max_width=30)
    table.add_column("Industry", max_width=25)
    table.add_column("F-Score", justify="center")
    table.add_column("Z-Score", justify="right")
    table.add_column("Zone", justify="center")

    for leader in leaders:
        table.add_row(
            str(leader.rank),
            leader.ticker,
            leader.company_name[:30],
            leader.industry[:25] if leader.industry else "",
            Text(str(leader.fscore), style=get_score_color(leader.fscore, 9)),
            f"{leader.zscore:.2f}",
            Text(leader.zone, style=get_zone_color(leader.zone)),
        )

    console.print(table)


@sectors.command("compare")
@click.argument("ticker")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def sectors_compare(ctx: click.Context, ticker: str, as_json: bool) -> None:
    """Compare a stock to its sector peers."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    analyzer = SectorAnalyzer()
    comparison = analyzer.compare_to_peers(ticker)

    if not comparison:
        console.print(f"[yellow]Could not compare {ticker} - insufficient data[/yellow]")
        console.print("[dim]The stock may not have SIC code classification or score data[/dim]")
        return

    if as_json:
        import json

        data = {
            "ticker": comparison.ticker,
            "company_name": comparison.company_name,
            "sector": comparison.sector,
            "industry": comparison.industry,
            "fscore": comparison.fscore,
            "zscore": comparison.zscore,
            "zone": comparison.zone,
            "sector_avg_fscore": comparison.sector_avg_fscore,
            "sector_avg_zscore": comparison.sector_avg_zscore,
            "fscore_vs_sector": comparison.fscore_vs_sector,
            "zscore_vs_sector": comparison.zscore_vs_sector,
            "sector_rank": comparison.sector_rank,
            "sector_total": comparison.sector_total,
            "percentile": comparison.percentile,
        }
        console.print(json.dumps(data, indent=2))
        return

    # Display comparison
    console.print(Panel.fit(f"[bold]{ticker}[/bold] vs Sector Peers"))
    console.print()

    console.print(f"[cyan]Company:[/cyan] {comparison.company_name}")
    console.print(f"[cyan]Sector:[/cyan] {comparison.sector}")
    console.print(f"[cyan]Industry:[/cyan] {comparison.industry}")
    console.print()

    # Scores comparison
    table = Table(show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column(ticker, justify="center")
    table.add_column("Sector Avg", justify="center")
    table.add_column("Difference", justify="center")

    # F-Score
    fscore_diff = comparison.fscore_vs_sector
    fscore_style = "green" if fscore_diff > 0 else "red" if fscore_diff < 0 else "yellow"
    table.add_row(
        "F-Score",
        Text(str(comparison.fscore), style=get_score_color(comparison.fscore, 9)),
        f"{comparison.sector_avg_fscore:.1f}",
        Text(f"{fscore_diff:+.1f}", style=fscore_style),
    )

    # Z-Score
    zscore_diff = comparison.zscore_vs_sector
    zscore_style = "green" if zscore_diff > 0 else "red" if zscore_diff < 0 else "yellow"
    table.add_row(
        "Z-Score",
        f"{comparison.zscore:.2f}",
        f"{comparison.sector_avg_zscore:.2f}",
        Text(f"{zscore_diff:+.2f}", style=zscore_style),
    )

    # Zone
    table.add_row("Zone", Text(comparison.zone, style=get_zone_color(comparison.zone)), "-", "-")

    console.print(table)
    console.print()

    # Ranking
    rank_style = "green" if comparison.percentile >= 75 else "yellow" if comparison.percentile >= 50 else "red"
    console.print(
        f"[bold]Sector Rank:[/bold] [{rank_style}]#{comparison.sector_rank} of {comparison.sector_total}[/{rank_style}] "
        f"([dim]{comparison.percentile:.0f}th percentile[/dim])"
    )


@sectors.command("averages")
@click.option("--sector", default=None, help="Specific sector (all if not specified)")
@click.pass_context
def sectors_averages(ctx: click.Context, sector: str) -> None:
    """Show average scores by sector."""
    console: Console = ctx.obj["console"]

    analyzer = SectorAnalyzer()
    averages = analyzer.get_sector_averages(sector)

    if not averages:
        console.print("[yellow]No sector data available[/yellow]")
        return

    table = Table(title="Sector Averages")
    table.add_column("Sector", style="cyan")
    table.add_column("Companies", justify="right")
    table.add_column("Avg F", justify="center")
    table.add_column("Avg Z", justify="right")
    table.add_column("Safe", justify="right", style="green")
    table.add_column("Grey", justify="right", style="yellow")
    table.add_column("Distress", justify="right", style="red")
    table.add_column("Top Performer", style="bold")

    for avg in sorted(averages, key=lambda x: x.avg_fscore, reverse=True):
        table.add_row(
            avg.sector,
            str(avg.company_count),
            f"{avg.avg_fscore:.1f}",
            f"{avg.avg_zscore:.2f}",
            str(avg.safe_count),
            str(avg.grey_count),
            str(avg.distress_count),
            f"{avg.top_performer} ({avg.top_performer_fscore})" if avg.top_performer else "-",
        )

    console.print(table)
