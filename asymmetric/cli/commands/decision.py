"""Decision tracking commands for investment actions."""

import json
import re
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from asymmetric.cli.validators import TICKER, validate_price_relationship


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
@click.argument("ticker", type=TICKER)
@click.option(
    "--action",
    type=click.Choice(["buy", "hold", "sell", "pass"]),
    required=True,
    help="Investment action",
)
@click.option("--thesis", "thesis_id", type=click.IntRange(min=1), default=None, help="Link to thesis ID")
@click.option("--target-price", type=click.FloatRange(min=0.01), default=None, help="Target price in USD")
@click.option("--stop-loss", type=click.FloatRange(min=0.01), default=None, help="Stop loss price in USD")
@click.option("--confidence", type=click.IntRange(1, 5), default=None, help="Confidence level 1-5")
@click.option("--notes", default="", help="Decision rationale/notes (max 500 chars)")
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
    # Ticker is already validated and uppercased by TICKER type

    # Validate price relationship
    try:
        validate_price_relationship(target_price, stop_loss, action)
    except click.BadParameter as e:
        console.print(f"[red]{e.message}[/red]")
        raise SystemExit(1)

    # Truncate notes if too long
    if len(notes) > 500:
        console.print("[yellow]Note truncated to 500 characters[/yellow]")
        notes = notes[:500]

    # Warn on suspicious decisions
    if action == "buy" and confidence is not None and confidence < 2:
        console.print("[yellow]Warning: Low confidence for BUY action[/yellow]")

    try:
        from asymmetric.db import get_session, init_db, Decision, Thesis
        from asymmetric.db.database import get_or_create_stock

        init_db()

        with get_session() as session:
            # Validate thesis if provided
            if thesis_id:
                thesis = session.exec(select(Thesis).where(Thesis.id == thesis_id)).first()
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
                decided_at=datetime.now(timezone.utc),
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
            stmt = select(Decision).join(Thesis).join(Stock)

            if action != "all":
                stmt = stmt.where(Decision.decision == action)
            if ticker:
                stmt = stmt.where(Stock.ticker == ticker.upper())

            stmt = stmt.order_by(Decision.decided_at.desc()).limit(limit)
            decisions = session.exec(stmt).all()

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
            d = session.exec(select(Decision).where(Decision.id == decision_id)).first()

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


@decision.command("update")
@click.argument("decision_id", type=int)
@click.option(
    "--action",
    type=click.Choice(["buy", "hold", "sell", "pass"]),
    default=None,
    help="Update investment action",
)
@click.option("--target-price", type=click.FloatRange(min=0.01), default=None, help="Update target price in USD")
@click.option("--stop-loss", type=click.FloatRange(min=0.01), default=None, help="Update stop loss price in USD")
@click.option("--confidence", type=click.IntRange(1, 5), default=None, help="Update confidence level 1-5")
@click.option("--notes", default=None, help="Update decision rationale/notes")
@click.pass_context
def decision_update(
    ctx: click.Context,
    decision_id: int,
    action: Optional[str],
    target_price: Optional[float],
    stop_loss: Optional[float],
    confidence: Optional[int],
    notes: Optional[str],
) -> None:
    """
    Update an existing decision.

    \b
    Examples:
        asymmetric decision update 1 --confidence 5
        asymmetric decision update 1 --action sell --target-price 200
    """
    console: Console = ctx.obj["console"]

    # Check if any updates provided
    if all(v is None for v in [action, target_price, stop_loss, confidence, notes]):
        console.print("[yellow]No updates provided. Use --action, --target-price, --stop-loss, --confidence, or --notes[/yellow]")
        raise SystemExit(1)

    try:
        from asymmetric.db import get_session, init_db, Decision

        init_db()

        with get_session() as session:
            d = session.exec(select(Decision).where(Decision.id == decision_id)).first()

            if not d:
                console.print(f"[red]Decision not found: ID {decision_id}[/red]")
                raise SystemExit(1)

            # Apply updates
            updates = []
            if action is not None:
                d.decision = action
                updates.append(f"action → {action}")
            if target_price is not None:
                d.target_price = target_price
                updates.append(f"target_price → ${target_price:.2f}")
            if stop_loss is not None:
                d.stop_loss = stop_loss
                updates.append(f"stop_loss → ${stop_loss:.2f}")
            if confidence is not None:
                d.confidence = confidence
                updates.append(f"confidence → {confidence}")
            if notes is not None:
                d.rationale = notes
                updates.append("rationale updated")

            session.add(d)
            session.commit()

            console.print(f"[green]+[/green] Decision #{decision_id} updated:")
            for u in updates:
                console.print(f"  • {u}")

    except Exception as e:
        if not isinstance(e, SystemExit):
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        raise


@decision.command("delete")
@click.argument("decision_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def decision_delete(ctx: click.Context, decision_id: int, yes: bool) -> None:
    """
    Delete a decision.

    \b
    Examples:
        asymmetric decision delete 1
        asymmetric decision delete 1 --yes
    """
    console: Console = ctx.obj["console"]

    try:
        from asymmetric.db import get_session, init_db, Decision

        init_db()

        with get_session() as session:
            d = session.exec(select(Decision).where(Decision.id == decision_id)).first()

            if not d:
                console.print(f"[red]Decision not found: ID {decision_id}[/red]")
                raise SystemExit(1)

            ticker = d.thesis.stock.ticker if d.thesis and d.thesis.stock else "?"

            if not yes:
                confirm = click.confirm(
                    f"Delete decision #{decision_id} ({d.decision.upper()} on {ticker})?",
                    default=False,
                )
                if not confirm:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise SystemExit(0)

            session.delete(d)
            session.commit()

            console.print(f"[green]+[/green] Decision #{decision_id} deleted")

    except Exception as e:
        if not isinstance(e, SystemExit):
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        raise
