"""Scoring commands for Piotroski F-Score and Altman Z-Score."""

import json
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import (
    get_fscore_verdict,
    get_quick_signals,
    get_score_color,
    get_zone_color,
    get_zscore_verdict,
    make_progress_bar,
)
from asymmetric.core.data.edgar_client import EdgarClient
from asymmetric.core.data.exceptions import (
    InsufficientDataError,
    SECEmptyResponseError,
    SECIdentityError,
    SECRateLimitError,
)
from asymmetric.core.scoring import AltmanScorer, PiotroskiScorer


@click.command()
@click.argument("ticker")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--detail", is_flag=True, help="Show detailed signal breakdown")
@click.option("--piotroski-only", is_flag=True, help="Only calculate Piotroski F-Score")
@click.option("--altman-only", is_flag=True, help="Only calculate Altman Z-Score")
@click.option("--save", is_flag=True, help="Save scores to database")
@click.pass_context
def score(
    ctx: click.Context,
    ticker: str,
    as_json: bool,
    detail: bool,
    piotroski_only: bool,
    altman_only: bool,
    save: bool,
) -> None:
    """
    Calculate financial health scores for a company.

    Shows a simplified summary by default. Use --detail for full breakdown.

    \b
    Examples:
        asymmetric score AAPL           # Quick summary
        asymmetric score AAPL --detail  # Full signal breakdown
        asymmetric score MSFT --json    # JSON output
    """
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    try:
        with console.status(f"[bold blue]Fetching financial data for {ticker}...[/bold blue]"):
            client = EdgarClient()
            financials = client.get_financials(ticker, periods=2)

        if not financials.get("periods") or len(financials["periods"]) < 1:
            console.print(f"[red]No financial data available for {ticker}[/red]")
            raise SystemExit(1)

        results: dict = {
            "ticker": ticker,
            "piotroski": None,
            "altman": None,
        }

        current_period = financials["periods"][0]
        prior_period = financials["periods"][1] if len(financials["periods"]) > 1 else {}

        # Calculate Piotroski F-Score
        if not altman_only:
            try:
                piotroski = PiotroskiScorer()
                f_result = piotroski.calculate_from_dict(current_period, prior_period)
                results["piotroski"] = {
                    "score": f_result.score,
                    "max_score": 9,
                    "signals_available": f_result.signals_available,
                    "interpretation": f_result.interpretation,
                    "profitability_score": f_result.profitability_score,
                    "leverage_score": f_result.leverage_score,
                    "efficiency_score": f_result.efficiency_score,
                    "missing_signals": f_result.missing_signals,
                }
            except InsufficientDataError as e:
                results["piotroski"] = {"error": str(e)}

        # Calculate Altman Z-Score
        if not piotroski_only:
            try:
                altman = AltmanScorer()
                z_result = altman.calculate_from_dict(current_period)
                results["altman"] = {
                    "z_score": round(z_result.z_score, 2),
                    "zone": z_result.zone,
                    "interpretation": z_result.interpretation,
                    "formula_used": z_result.formula_used,
                    "components_calculated": z_result.components_calculated,
                    "missing_inputs": z_result.missing_inputs,
                }
            except InsufficientDataError as e:
                results["altman"] = {"error": str(e)}

        # Save to database if requested
        if save:
            p = results.get("piotroski", {})
            if p and "error" not in p:
                _save_score_to_db(ticker, results)
                if not as_json:
                    console.print("[green]Score saved to database[/green]")
                    console.print()

        # Output
        if as_json:
            console.print(json.dumps(results, indent=2))
        else:
            _display_scores(console, ticker, results, detail=detail)

    except SECIdentityError as e:
        console.print(f"[red]SEC Identity Error:[/red] {e}")
        console.print("[yellow]Set SEC_IDENTITY environment variable.[/yellow]")
        raise SystemExit(1)

    except SECRateLimitError as e:
        console.print(f"[red]SEC Rate Limit Hit:[/red] {e}")
        console.print("[yellow]Wait a few minutes and try again.[/yellow]")
        raise SystemExit(1)

    except SECEmptyResponseError as e:
        console.print(f"[red]SEC Empty Response:[/red] {e}")
        raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


def _display_scores(console: Console, ticker: str, results: dict, detail: bool = False) -> None:
    """Display scores using Rich formatting."""
    console.print()

    p = results.get("piotroski", {})
    a = results.get("altman", {})

    # Handle errors
    if "error" in p and "error" in a:
        console.print(f"[red]Could not calculate scores for {ticker}[/red]")
        if "error" in p:
            console.print(f"[dim]Piotroski: {p['error']}[/dim]")
        if "error" in a:
            console.print(f"[dim]Altman: {a['error']}[/dim]")
        return

    if detail:
        _display_detailed_scores(console, ticker, results)
    else:
        _display_simple_scores(console, ticker, results)


def _display_simple_scores(console: Console, ticker: str, results: dict) -> None:
    """Display simplified score summary with plain English verdict."""
    p = results.get("piotroski", {})
    a = results.get("altman", {})

    # Build the verdict line
    verdicts = []
    if p and "error" not in p:
        f_verdict, f_color = get_fscore_verdict(p["score"])
        verdicts.append(f"[bold {f_color}]{f_verdict}[/bold {f_color}]")
    if a and "error" not in a:
        z_verdict, z_color = get_zscore_verdict(a["zone"])
        verdicts.append(f"[bold {z_color}]{z_verdict}[/bold {z_color}]")

    verdict_line = " with ".join(verdicts) if verdicts else "Insufficient data"

    # Build content
    lines = []
    lines.append(f"[bold]{ticker}[/bold] is {verdict_line}")
    lines.append("")

    # Score bars
    if p and "error" not in p:
        score = p["score"]
        color = get_score_color(score, 9)
        bar = make_progress_bar(score, 9)
        lines.append(f"  Piotroski F-Score   [{color}]{bar}[/{color}]  [bold]{score}/9[/bold]")

    if a and "error" not in a:
        # Z-Score bar (capped at 10 for display)
        z_score = a["z_score"]
        color = get_zone_color(a["zone"])
        bar = make_progress_bar(min(z_score, 10), 10)
        lines.append(f"  Altman Z-Score      [{color}]{bar}[/{color}]  [bold]{z_score:.2f}[/bold] {a['zone']}")

    # Quick signals
    signals = get_quick_signals(p, a)
    if signals:
        lines.append("")
        signal_parts = []
        for sym, text, color in signals:
            signal_parts.append(f"[{color}]{sym}[/{color}] {text}")
        lines.append("  " + "  ".join(signal_parts))

    console.print(Panel(
        "\n".join(lines),
        border_style="blue",
        padding=(1, 2),
    ))

    # Next action hints
    console.print()
    console.print(f"[dim]Next steps:[/dim]")
    console.print(f"  [dim]Details:[/dim]  asymmetric score {ticker} --detail")
    console.print(f"  [dim]AI Analysis:[/dim]  asymmetric analyze {ticker}")
    console.print()


def _display_detailed_scores(console: Console, ticker: str, results: dict) -> None:
    """Display detailed score breakdown with all signals."""
    console.print(f"[bold]Detailed Scores for {ticker}[/bold]")
    console.print()

    # Piotroski F-Score detailed
    p = results.get("piotroski", {})
    if p and "error" not in p:
        score = p["score"]
        color = get_score_color(score, 9)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        table.add_row(
            "Score",
            Text(f"{score}/9", style=f"bold {color}")
        )
        table.add_row("Interpretation", p["interpretation"])
        table.add_row("Signals Available", f"{p['signals_available']}/9")
        table.add_row("", "")
        table.add_row(
            "[bold]PROFITABILITY[/bold]",
            Text(f"{p['profitability_score']}/4", style="bold")
        )
        table.add_row("Leverage/Liquidity", f"{p['leverage_score']}/3")
        table.add_row("Operating Efficiency", f"{p['efficiency_score']}/2")

        if p.get("missing_signals"):
            table.add_row("", "")
            missing = p["missing_signals"]
            table.add_row(
                "[dim]Missing Signals[/dim]",
                f"[dim]{', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}[/dim]"
            )

        console.print(Panel(table, title="Piotroski F-Score", border_style=color))

    # Altman Z-Score detailed
    a = results.get("altman", {})
    if a and "error" not in a:
        zone = a["zone"]
        color = get_zone_color(zone)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        table.add_row(
            "Z-Score",
            Text(f"{a['z_score']:.2f}", style=f"bold {color}")
        )
        table.add_row(
            "Zone",
            Text(zone, style=f"bold {color}")
        )
        table.add_row("Interpretation", a["interpretation"])
        table.add_row("Formula", a["formula_used"].replace("_", " ").title())
        table.add_row("Components", f"{a['components_calculated']}/5")

        if a.get("missing_inputs"):
            table.add_row("", "")
            table.add_row(
                "[dim]Missing Inputs[/dim]",
                f"[dim]{len(a['missing_inputs'])} inputs[/dim]"
            )

        console.print(Panel(table, title="Altman Z-Score", border_style=color))

    # Next action hints
    console.print()
    console.print(f"[dim]Next steps:[/dim]")
    console.print(f"  [dim]AI Analysis:[/dim]  asymmetric analyze {ticker}")
    console.print(f"  [dim]Compare:[/dim]  asymmetric compare {ticker} MSFT GOOG")
    console.print()


def _save_score_to_db(ticker: str, results: dict) -> None:
    """Save calculated scores to SQLite database."""
    from asymmetric.db import get_session, init_db, StockScore
    from asymmetric.db.database import get_or_create_stock

    init_db()

    p = results.get("piotroski", {})
    a = results.get("altman", {})

    with get_session() as session:
        stock = get_or_create_stock(ticker)
        stock = session.merge(stock)

        score_record = StockScore(
            stock_id=stock.id,
            piotroski_score=p.get("score", 0),
            piotroski_signals_available=p.get("signals_available", 9),
            piotroski_interpretation=p.get("interpretation"),
            piotroski_profitability=p.get("profitability_score"),
            piotroski_leverage=p.get("leverage_score"),
            piotroski_efficiency=p.get("efficiency_score"),
            altman_z_score=a.get("z_score", 0.0) if a and "error" not in a else 0.0,
            altman_zone=a.get("zone", "Unknown") if a and "error" not in a else "Unknown",
            altman_interpretation=a.get("interpretation") if a and "error" not in a else None,
            altman_formula=a.get("formula_used", "manufacturing") if a else "manufacturing",
            data_source="live_api",
            calculated_at=datetime.now(timezone.utc),
        )
        session.add(score_record)
