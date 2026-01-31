"""History and trends commands for score trajectory analysis."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import get_score_color, get_zone_color, print_next_steps
from asymmetric.core.trends.analyzer import TrendAnalyzer


@click.group()
@click.pass_context
def history(ctx: click.Context) -> None:
    """
    View historical score trends.

    Track F-Score and Z-Score changes over time to identify
    improving, declining, or consistently strong performers.

    \b
    Examples:
        asymmetric history show AAPL
        asymmetric history show AAPL --years 3
        asymmetric history compare AAPL MSFT GOOG
    """
    pass


@history.command("show")
@click.argument("ticker")
@click.option("--years", type=int, default=5, help="Years of history to show")
@click.option("--chart", is_flag=True, help="Show ASCII chart (coming soon)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def history_show(ctx: click.Context, ticker: str, years: int, chart: bool, as_json: bool) -> None:
    """Show score history for a ticker."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    analyzer = TrendAnalyzer()
    records = analyzer.get_score_history(ticker, years=years)

    if not records:
        console.print(f"[yellow]No score history found for {ticker}[/yellow]")
        console.print("[dim]Tip: Run `asymmetric score {ticker}` to calculate and save scores[/dim]")
        return

    if as_json:
        import json

        data = [
            {
                "fiscal_year": r.fiscal_year,
                "fiscal_period": r.fiscal_period,
                "piotroski_score": r.piotroski_score,
                "altman_z_score": r.altman_z_score,
                "altman_zone": r.altman_zone,
            }
            for r in records
        ]
        console.print(json.dumps(data, indent=2))
        return

    # Display table
    table = Table(title=f"Score History: {ticker}")
    table.add_column("Period", style="cyan")
    table.add_column("F-Score", justify="center")
    table.add_column("Z-Score", justify="right")
    table.add_column("Zone", justify="center")
    table.add_column("Change", justify="center")

    prev_fscore = None
    for i, r in enumerate(records):
        # Calculate change from previous period
        change = ""
        if prev_fscore is not None:
            diff = r.piotroski_score - prev_fscore
            if diff > 0:
                change = f"[green]+{diff}[/green]"
            elif diff < 0:
                change = f"[red]{diff}[/red]"
            else:
                change = "[dim]=[/dim]"

        table.add_row(
            f"{r.fiscal_year} {r.fiscal_period}",
            Text(str(r.piotroski_score), style=get_score_color(r.piotroski_score, 9)),
            f"{r.altman_z_score:.2f}",
            Text(r.altman_zone, style=get_zone_color(r.altman_zone)),
            change,
        )
        prev_fscore = r.piotroski_score

    console.print(table)

    # Summary
    if len(records) >= 2:
        trend = analyzer.calculate_trend(ticker, periods=len(records))
        if trend:
            console.print()
            direction_style = (
                "green"
                if trend.trend_direction == "improving"
                else "red" if trend.trend_direction == "declining" else "yellow"
            )
            console.print(
                f"Trend: [{direction_style}]{trend.trend_direction.upper()}[/{direction_style}] "
                f"(F-Score {trend.fscore_change:+d} over {trend.periods_analyzed} periods)"
            )

    # Next steps
    print_next_steps(
        console,
        [
            ("Score details", f"asymmetric score {ticker} --detail"),
            ("Compare", f"asymmetric compare {ticker} ..."),
        ],
    )


@history.command("compare")
@click.argument("tickers", nargs=-1, required=True)
@click.option("--years", type=int, default=3, help="Years of history to compare")
@click.pass_context
def history_compare(ctx: click.Context, tickers: tuple, years: int) -> None:
    """Compare historical trends across tickers."""
    console: Console = ctx.obj["console"]

    if len(tickers) < 2:
        console.print("[red]Please provide at least 2 tickers to compare[/red]")
        return

    analyzer = TrendAnalyzer()

    table = Table(title=f"Trend Comparison ({years} years)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Current F", justify="center")
    table.add_column("Change", justify="center")
    table.add_column("Trend", justify="center")
    table.add_column("Current Z", justify="right")
    table.add_column("Zone", justify="center")

    for ticker in tickers:
        ticker = ticker.upper()
        trend = analyzer.calculate_trend(ticker, periods=years * 4)  # Assume quarterly

        if not trend:
            table.add_row(ticker, "[dim]N/A[/dim]", "-", "-", "-", "-")
            continue

        change_style = "green" if trend.fscore_change > 0 else "red" if trend.fscore_change < 0 else "yellow"
        direction_style = (
            "green"
            if trend.trend_direction == "improving"
            else "red" if trend.trend_direction == "declining" else "yellow"
        )

        table.add_row(
            ticker,
            Text(str(trend.current_fscore), style=get_score_color(trend.current_fscore, 9)),
            Text(f"{trend.fscore_change:+d}", style=change_style),
            Text(trend.trend_direction, style=direction_style),
            f"{trend.current_zscore:.2f}",
            Text(trend.current_zone, style=get_zone_color(trend.current_zone)),
        )

    console.print(table)


@click.group()
@click.pass_context
def trends(ctx: click.Context) -> None:
    """
    Find stocks by trend patterns.

    Discover stocks with improving, declining, or consistently
    strong scores over time.

    \b
    Examples:
        asymmetric trends improving
        asymmetric trends declining --min-decline 3
        asymmetric trends consistent --min-score 7
        asymmetric trends turnaround
    """
    pass


@trends.command("improving")
@click.option("--min-improvement", type=int, default=2, help="Minimum F-Score improvement")
@click.option("--periods", type=int, default=4, help="Number of periods to check")
@click.option("--limit", type=int, default=25, help="Maximum results")
@click.pass_context
def trends_improving(ctx: click.Context, min_improvement: int, periods: int, limit: int) -> None:
    """Find stocks with improving F-Scores."""
    console: Console = ctx.obj["console"]

    analyzer = TrendAnalyzer()
    results = analyzer.find_improving(min_improvement=min_improvement, periods=periods, limit=limit)

    if not results:
        console.print("[yellow]No improving stocks found with current criteria[/yellow]")
        return

    table = Table(title=f"Improving Stocks (F-Score +{min_improvement}+ over {periods} periods)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Company", max_width=30)
    table.add_column("Current F", justify="center")
    table.add_column("Change", justify="center")
    table.add_column("Current Z", justify="right")
    table.add_column("Zone", justify="center")

    for r in results:
        table.add_row(
            r.ticker,
            r.company_name[:30],
            Text(str(r.current_fscore), style=get_score_color(r.current_fscore, 9)),
            Text(f"+{r.fscore_change}", style="green"),
            f"{r.current_zscore:.2f}",
            Text(r.current_zone, style=get_zone_color(r.current_zone)),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} improving stocks[/dim]")


@trends.command("declining")
@click.option("--min-decline", type=int, default=2, help="Minimum F-Score decline")
@click.option("--periods", type=int, default=4, help="Number of periods to check")
@click.option("--limit", type=int, default=25, help="Maximum results")
@click.pass_context
def trends_declining(ctx: click.Context, min_decline: int, periods: int, limit: int) -> None:
    """Find stocks with declining F-Scores."""
    console: Console = ctx.obj["console"]

    analyzer = TrendAnalyzer()
    results = analyzer.find_declining(min_decline=min_decline, periods=periods, limit=limit)

    if not results:
        console.print("[yellow]No declining stocks found with current criteria[/yellow]")
        return

    table = Table(title=f"Declining Stocks (F-Score -{min_decline}+ over {periods} periods)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Company", max_width=30)
    table.add_column("Current F", justify="center")
    table.add_column("Change", justify="center")
    table.add_column("Current Z", justify="right")
    table.add_column("Zone", justify="center")

    for r in results:
        table.add_row(
            r.ticker,
            r.company_name[:30],
            Text(str(r.current_fscore), style=get_score_color(r.current_fscore, 9)),
            Text(str(r.fscore_change), style="red"),
            f"{r.current_zscore:.2f}",
            Text(r.current_zone, style=get_zone_color(r.current_zone)),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} declining stocks[/dim]")


@trends.command("consistent")
@click.option("--min-score", type=int, default=7, help="Minimum consistent F-Score")
@click.option("--periods", type=int, default=8, help="Consecutive periods required")
@click.option("--limit", type=int, default=25, help="Maximum results")
@click.pass_context
def trends_consistent(ctx: click.Context, min_score: int, periods: int, limit: int) -> None:
    """Find stocks with consistently high F-Scores."""
    console: Console = ctx.obj["console"]

    analyzer = TrendAnalyzer()
    results = analyzer.find_consistent(min_score=min_score, periods=periods, limit=limit)

    if not results:
        console.print("[yellow]No consistent performers found with current criteria[/yellow]")
        return

    table = Table(title=f"Consistent Performers (F-Score {min_score}+ for {periods} periods)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Company", max_width=30)
    table.add_column("Avg F", justify="center")
    table.add_column("Range", justify="center")
    table.add_column("Periods", justify="center")
    table.add_column("Zone", justify="center")

    for r in results:
        table.add_row(
            r.ticker,
            r.company_name[:30],
            f"{r.average_fscore:.1f}",
            f"{r.min_fscore}-{r.max_fscore}",
            str(r.consecutive_periods),
            Text(r.current_zone, style=get_zone_color(r.current_zone)),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} consistent performers[/dim]")


@trends.command("turnaround")
@click.option("--limit", type=int, default=25, help="Maximum results")
@click.pass_context
def trends_turnaround(ctx: click.Context, limit: int) -> None:
    """Find stocks transitioning from Distress zone."""
    console: Console = ctx.obj["console"]

    analyzer = TrendAnalyzer()
    results = analyzer.find_turnaround(limit=limit)

    if not results:
        console.print("[yellow]No turnaround candidates found[/yellow]")
        return

    table = Table(title="Turnaround Candidates (Exited Distress Zone)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Company", max_width=30)
    table.add_column("Prev Zone", justify="center")
    table.add_column("Current", justify="center")
    table.add_column("Z Improve", justify="right")
    table.add_column("F-Score", justify="center")

    for r in results:
        table.add_row(
            r.ticker,
            r.company_name[:30],
            Text(r.previous_zone, style="red"),
            Text(r.current_zone, style=get_zone_color(r.current_zone)),
            f"+{r.zscore_improvement:.2f}",
            Text(str(r.current_fscore), style=get_score_color(r.current_fscore, 9)),
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} turnaround candidates[/dim]")
