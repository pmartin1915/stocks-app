"""Decision tracking commands for investment actions."""

import json
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


@click.group()
@click.pass_context
def decision(ctx: click.Context) -> None:
    """
    Track investment decisions.

    Record buy/hold/sell/pass decisions with rationale and price targets.

    \b
    Examples:
        asymmetric decision create AAPL --action buy
        asymmetric decision create MSFT --action hold --thesis 1
        asymmetric decision list
        asymmetric decision view 1
    """
    pass


@decision.command("create")
@click.argument("ticker")
@click.option(
    "--action",
    type=click.Choice(["buy", "hold", "sell", "pass"]),
    required=True,
    help="Investment action",
)
@click.option("--thesis", "thesis_id", type=int, default=None, help="Link to thesis ID")
@click.option("--target-price", type=float, default=None, help="Target price")
@click.option("--stop-loss", type=float, default=None, help="Stop loss price")
@click.option("--confidence", type=int, default=None, help="Confidence level 1-5")
@click.option("--notes", default="", help="Decision rationale/notes")
@click.pass_context
def decision_create(
    ctx: click.Context,
    ticker: str,
    action: str,
    thesis_id: Optional[int],
    target_price: Optional[float],
    stop_loss: Optional[float],
    confidence: Optional[int],
    notes: str,
) -> None:
    """
    Record a new investment decision.

    \b
    Examples:
        asymmetric decision create AAPL --action buy --confidence 4
        asymmetric decision create MSFT --action hold --thesis 1 --target-price 450
    """
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    # Validate confidence
    if confidence is not None and (confidence < 1 or confidence > 5):
        console.print("[red]Confidence must be between 1 and 5[/red]")
        raise SystemExit(1)

    try:
        from asymmetric.db import get_session, init_db, Decision, Thesis
        from asymmetric.db.database import get_or_create_stock

        init_db()

        with get_session() as session:
            # Validate thesis if provided
            if thesis_id:
                thesis = session.query(Thesis).filter(Thesis.id == thesis_id).first()
                if not thesis:
                    console.print(f"[red]Thesis not found: ID {thesis_id}[/red]")
                    raise SystemExit(1)
                # Verify ticker matches thesis
                if thesis.stock and thesis.stock.ticker != ticker:
                    console.print(
                        f"[yellow]Warning: Thesis {thesis_id} is for "
                        f"{thesis.stock.ticker}, not {ticker}[/yellow]"
                    )
            else:
                # Create a default thesis if none provided
                stock = get_or_create_stock(ticker)
                stock = session.merge(stock)

                default_thesis = Thesis(
                    stock_id=stock.id,
                    summary=f"Quick decision for {ticker}",
                    analysis_text=notes or f"Decision: {action}",
                    status="active",
                )
                session.add(default_thesis)
                session.flush()
                thesis_id = default_thesis.id

            # Create decision
            decision_record = Decision(
                thesis_id=thesis_id,
                decision=action,
                rationale=notes or f"{action.title()} decision for {ticker}",
                confidence=confidence,
                target_price=target_price,
                stop_loss=stop_loss,
                decided_at=datetime.utcnow(),
            )
            session.add(decision_record)
            session.flush()
            decision_id = decision_record.id

        console.print()
        console.print(f"[green]Decision recorded![/green]")
        console.print(f"[dim]Decision ID: {decision_id}[/dim]")
        console.print()

        # Summary panel
        summary_lines = [
            f"[bold]{ticker}[/bold]: {action.upper()}",
        ]
        if target_price:
            summary_lines.append(f"Target: ${target_price:.2f}")
        if stop_loss:
            summary_lines.append(f"Stop Loss: ${stop_loss:.2f}")
        if confidence:
            summary_lines.append(f"Confidence: {'*' * confidence}{'.' * (5 - confidence)}")
        if notes:
            summary_lines.append(f"[dim]{notes}[/dim]")

        console.print(Panel(
            "\n".join(summary_lines),
            title="Decision Summary",
            border_style="green",
        ))

    except Exception as e:
        if not isinstance(e, SystemExit):
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        raise


@decision.command("list")
@click.option(
    "--action",
    type=click.Choice(["buy", "hold", "sell", "pass", "all"]),
    default="all",
    help="Filter by action type",
)
@click.option("--ticker", default=None, help="Filter by ticker")
@click.option("--limit", type=int, default=20, help="Maximum results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def decision_list(
    ctx: click.Context,
    action: str,
    ticker: Optional[str],
    limit: int,
    as_json: bool,
) -> None:
    """
    List investment decisions.

    \b
    Examples:
        asymmetric decision list
        asymmetric decision list --action buy
        asymmetric decision list --ticker AAPL
    """
    console: Console = ctx.obj["console"]

    try:
        from asymmetric.db import get_session, init_db, Decision, Thesis, Stock

        init_db()

        with get_session() as session:
            query = session.query(Decision).join(Thesis).join(Stock)

            if action != "all":
                query = query.filter(Decision.decision == action)
            if ticker:
                query = query.filter(Stock.ticker == ticker.upper())

            query = query.order_by(Decision.decided_at.desc()).limit(limit)
            decisions = query.all()

            if as_json:
                output = [
                    {
                        "id": d.id,
                        "ticker": d.thesis.stock.ticker if d.thesis and d.thesis.stock else "?",
                        "action": d.decision,
                        "confidence": d.confidence,
                        "target_price": d.target_price,
                        "stop_loss": d.stop_loss,
                        "rationale": d.rationale,
                        "thesis_id": d.thesis_id,
                        "decided_at": d.decided_at.isoformat() if d.decided_at else None,
                    }
                    for d in decisions
                ]
                console.print(json.dumps(output, indent=2))
            else:
                _display_decision_list(console, decisions)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


def _display_decision_list(console: Console, decisions) -> None:
    """Display decision list with Rich formatting."""
    if not decisions:
        console.print("[yellow]No decisions found.[/yellow]")
        console.print("[dim]Record one with: asymmetric decision create TICKER --action buy[/dim]")
        return

    table = Table(title="Investment Decisions")
    table.add_column("ID", style="cyan")
    table.add_column("Ticker", style="bold")
    table.add_column("Action", justify="center")
    table.add_column("Confidence", justify="center")
    table.add_column("Target", justify="right")
    table.add_column("Decided")

    action_colors = {
        "buy": "green",
        "sell": "red",
        "hold": "yellow",
        "pass": "dim",
    }

    for d in decisions:
        ticker = d.thesis.stock.ticker if d.thesis and d.thesis.stock else "?"
        action_color = action_colors.get(d.decision, "white")
        confidence_str = f"{'*' * d.confidence}" if d.confidence else "-"
        target = f"${d.target_price:.2f}" if d.target_price else "-"
        decided = d.decided_at.strftime("%Y-%m-%d") if d.decided_at else "-"

        table.add_row(
            str(d.id),
            ticker,
            f"[{action_color}]{d.decision.upper()}[/{action_color}]",
            confidence_str,
            target,
            decided,
        )

    console.print()
    console.print(table)
    console.print()


@decision.command("view")
@click.argument("decision_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def decision_view(ctx: click.Context, decision_id: int, as_json: bool) -> None:
    """
    View a specific decision.

    \b
    Examples:
        asymmetric decision view 1
        asymmetric decision view 1 --json
    """
    console: Console = ctx.obj["console"]

    try:
        from asymmetric.db import get_session, init_db, Decision

        init_db()

        with get_session() as session:
            d = session.query(Decision).filter(Decision.id == decision_id).first()

            if not d:
                console.print(f"[red]Decision not found: ID {decision_id}[/red]")
                raise SystemExit(1)

            if as_json:
                output = {
                    "id": d.id,
                    "ticker": d.thesis.stock.ticker if d.thesis and d.thesis.stock else "?",
                    "action": d.decision,
                    "rationale": d.rationale,
                    "confidence": d.confidence,
                    "target_price": d.target_price,
                    "stop_loss": d.stop_loss,
                    "thesis_id": d.thesis_id,
                    "decided_at": d.decided_at.isoformat() if d.decided_at else None,
                }
                console.print(json.dumps(output, indent=2))
            else:
                _display_decision(console, d)

    except Exception as e:
        if not isinstance(e, SystemExit):
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        raise


def _display_decision(console: Console, d) -> None:
    """Display a single decision with Rich formatting."""
    ticker = d.thesis.stock.ticker if d.thesis and d.thesis.stock else "?"

    action_colors = {
        "buy": "green",
        "sell": "red",
        "hold": "yellow",
        "pass": "dim",
    }
    action_color = action_colors.get(d.decision, "white")

    console.print()
    console.print(f"[bold]Decision #{d.id}: {ticker}[/bold]")
    console.print(
        f"Action: [{action_color}][bold]{d.decision.upper()}[/bold][/{action_color}]"
    )
    console.print()

    # Details table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    if d.confidence:
        table.add_row("Confidence", f"{'*' * d.confidence}{'.' * (5 - d.confidence)} ({d.confidence}/5)")
    if d.target_price:
        table.add_row("Target Price", f"${d.target_price:.2f}")
    if d.stop_loss:
        table.add_row("Stop Loss", f"${d.stop_loss:.2f}")
    table.add_row("Thesis ID", str(d.thesis_id))
    table.add_row(
        "Decided",
        d.decided_at.strftime("%Y-%m-%d %H:%M") if d.decided_at else "-"
    )

    console.print(Panel(table, title="Details", border_style="blue"))

    # Rationale
    if d.rationale:
        console.print()
        console.print(Panel(d.rationale, title="Rationale", border_style="cyan"))

    console.print()
