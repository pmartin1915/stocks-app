"""Compare command for side-by-side stock comparison."""

import json
import logging

import click

logger = logging.getLogger(__name__)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.error_handler import handle_cli_errors
from asymmetric.cli.formatting import (
    Signals,
    get_zone_color,
    highlight_winner,
)
from asymmetric.core.data.edgar_client import EdgarClient
from asymmetric.core.data.exceptions import (
    InsufficientDataError,
    SECEmptyResponseError,
    SECIdentityError,
    SECRateLimitError,
)
from asymmetric.core.scoring import AltmanScorer, PiotroskiScorer


def _calculate_scores(client: EdgarClient, ticker: str) -> dict:
    """Calculate scores for a single ticker."""
    result = {
        "ticker": ticker,
        "piotroski": None,
        "altman": None,
        "error": None,
    }

    try:
        financials = client.get_financials(ticker, periods=2)

        if not financials.get("periods") or len(financials["periods"]) < 1:
            result["error"] = "No financial data available"
            return result

        current_period = financials["periods"][0]
        prior_period = financials["periods"][1] if len(financials["periods"]) > 1 else {}

        # Piotroski F-Score
        try:
            piotroski = PiotroskiScorer()
            f_result = piotroski.calculate_from_dict(current_period, prior_period)
            result["piotroski"] = {
                "score": f_result.score,
                "profitability": f_result.profitability_score,
                "leverage": f_result.leverage_score,
                "efficiency": f_result.efficiency_score,
                "interpretation": f_result.interpretation,
            }
        except InsufficientDataError:
            pass

        # Altman Z-Score
        try:
            altman = AltmanScorer()
            z_result = altman.calculate_from_dict(current_period)
            result["altman"] = {
                "z_score": round(z_result.z_score, 2),
                "zone": z_result.zone,
            }
        except InsufficientDataError:
            pass

    except (SECEmptyResponseError, SECRateLimitError, SECIdentityError) as e:
        result["error"] = str(e)

    return result


@click.command()
@click.argument("tickers", nargs=-1, required=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
@handle_cli_errors
def compare(
    ctx: click.Context,
    tickers: tuple[str, ...],
    as_json: bool,
) -> None:
    """
    Compare financial health scores across multiple stocks.

    Provide 2-5 tickers to compare side-by-side. The best value in each
    category is highlighted in green.

    \b
    Examples:
        asymmetric compare AAPL MSFT
        asymmetric compare AAPL MSFT GOOG AMZN
        asymmetric compare AAPL MSFT --json
    """
    console: Console = ctx.obj["console"]

    # Validate ticker count
    if len(tickers) < 2:
        console.print("[red]Error:[/red] Please provide at least 2 tickers to compare")
        raise SystemExit(1)

    if len(tickers) > 5:
        console.print("[red]Error:[/red] Maximum 5 tickers for comparison")
        raise SystemExit(1)

    # Normalize tickers
    tickers = tuple(t.upper() for t in tickers)

    client = EdgarClient()
    results = []

    with console.status("[bold blue]Fetching financial data...[/bold blue]") as status:
        for ticker in tickers:
            status.update(f"[bold blue]Fetching {ticker}...[/bold blue]")
            result = _calculate_scores(client, ticker)
            results.append(result)

    if as_json:
        console.print(json.dumps(results, indent=2))
    else:
        _display_comparison(console, results)


def _display_comparison(console: Console, results: list[dict]) -> None:
    """Display side-by-side comparison with winner highlighting."""
    console.print()

    # Check for any successful results
    valid_results = [r for r in results if not r.get("error")]
    if not valid_results:
        console.print("[red]No valid data for any ticker[/red]")
        for r in results:
            if r.get("error"):
                console.print(f"  [dim]{r['ticker']}: {r['error']}[/dim]")
        return

    # Build comparison table
    table = Table(
        title="Side-by-Side Comparison",
        show_header=True,
        header_style="bold cyan",
        padding=(0, 2),
    )

    # Add columns - first is metric name, rest are tickers
    table.add_column("Metric", style="cyan")
    for r in results:
        table.add_column(r["ticker"], justify="center")

    # F-Score row
    f_scores = [r.get("piotroski", {}).get("score") if r.get("piotroski") else None for r in results]
    f_colors = highlight_winner(f_scores, higher_is_better=True)

    f_cells = []
    for i, r in enumerate(results):
        if r.get("error"):
            f_cells.append(Text("Error", style="dim"))
        elif r.get("piotroski"):
            score = r["piotroski"]["score"]
            f_cells.append(Text(f"{score}/9", style=f"bold {f_colors[i]}"))
        else:
            f_cells.append(Text("N/A", style="dim"))

    table.add_row("F-Score", *f_cells)

    # Z-Score row
    z_scores = [r.get("altman", {}).get("z_score") if r.get("altman") else None for r in results]
    z_colors = highlight_winner(z_scores, higher_is_better=True)

    z_cells = []
    for i, r in enumerate(results):
        if r.get("error"):
            z_cells.append(Text("Error", style="dim"))
        elif r.get("altman"):
            z_score = r["altman"]["z_score"]
            z_cells.append(Text(f"{z_score:.2f}", style=f"bold {z_colors[i]}"))
        else:
            z_cells.append(Text("N/A", style="dim"))

    table.add_row("Z-Score", *z_cells)

    # Zone row
    zone_cells = []
    for r in results:
        if r.get("error"):
            zone_cells.append(Text("Error", style="dim"))
        elif r.get("altman"):
            zone = r["altman"]["zone"]
            color = get_zone_color(zone)
            zone_cells.append(Text(zone, style=color))
        else:
            zone_cells.append(Text("N/A", style="dim"))

    table.add_row("Zone", *zone_cells)

    # Separator
    table.add_section()

    # Component breakdown
    # Profitability
    prof_scores = [r.get("piotroski", {}).get("profitability") if r.get("piotroski") else None for r in results]
    prof_colors = highlight_winner(prof_scores, higher_is_better=True)

    prof_cells = []
    for i, r in enumerate(results):
        if r.get("error") or not r.get("piotroski"):
            prof_cells.append(Text("-", style="dim"))
        else:
            score = r["piotroski"]["profitability"]
            prof_cells.append(Text(f"{score}/4", style=prof_colors[i]))

    table.add_row("Profitability", *prof_cells)

    # Leverage
    lev_scores = [r.get("piotroski", {}).get("leverage") if r.get("piotroski") else None for r in results]
    lev_colors = highlight_winner(lev_scores, higher_is_better=True)

    lev_cells = []
    for i, r in enumerate(results):
        if r.get("error") or not r.get("piotroski"):
            lev_cells.append(Text("-", style="dim"))
        else:
            score = r["piotroski"]["leverage"]
            lev_cells.append(Text(f"{score}/3", style=lev_colors[i]))

    table.add_row("Leverage", *lev_cells)

    # Efficiency
    eff_scores = [r.get("piotroski", {}).get("efficiency") if r.get("piotroski") else None for r in results]
    eff_colors = highlight_winner(eff_scores, higher_is_better=True)

    eff_cells = []
    for i, r in enumerate(results):
        if r.get("error") or not r.get("piotroski"):
            eff_cells.append(Text("-", style="dim"))
        else:
            score = r["piotroski"]["efficiency"]
            eff_cells.append(Text(f"{score}/2", style=eff_colors[i]))

    table.add_row("Efficiency", *eff_cells)

    console.print(Panel(table, border_style="blue"))

    # Find the best overall candidate
    best_ticker = None
    best_score = -1
    for r in results:
        if r.get("piotroski") and r.get("altman"):
            # Simple heuristic: F-Score + (Z-Score > 2.99 ? 2 : 0)
            combined = r["piotroski"]["score"]
            if r["altman"]["zone"] == "Safe":
                combined += 2
            elif r["altman"]["zone"] == "Grey":
                combined += 1
            if combined > best_score:
                best_score = combined
                best_ticker = r["ticker"]

    # Next action hints
    console.print()
    if best_ticker:
        console.print(f"[dim]Best candidate: [bold green]{best_ticker}[/bold green] {Signals.WINNER}[/dim]")
    console.print(f"[dim]Next steps:[/dim]")
    if best_ticker:
        console.print(f"  [dim]Deep dive:[/dim]  asymmetric score {best_ticker} --detail")
        console.print(f"  [dim]AI Analysis:[/dim]  asymmetric analyze {best_ticker}")
    console.print()
