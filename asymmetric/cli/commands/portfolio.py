"""Portfolio management commands for transaction and holdings tracking."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import get_score_color, get_zone_color
from asymmetric.core.portfolio.manager import PortfolioManager
from asymmetric.core.portfolio.snapshot_service import (
    get_last_snapshot_date,
    should_take_snapshot,
    take_daily_snapshot,
)


@click.group()
@click.pass_context
def portfolio(ctx: click.Context) -> None:
    """
    Manage your investment portfolio.

    Track buy/sell transactions, view holdings, and calculate
    portfolio-level scores and P&L.

    \b
    Examples:
        asymmetric portfolio add AAPL -q 10 -p 150.00
        asymmetric portfolio sell AAPL -q 5 -p 175.00
        asymmetric portfolio summary
        asymmetric portfolio holdings
        asymmetric portfolio scores --weighted
    """
    pass


@portfolio.command("add")
@click.argument("ticker")
@click.option("--quantity", "-q", type=float, required=True, help="Number of shares")
@click.option("--price", "-p", type=float, required=True, help="Price per share in USD")
@click.option("--date", "-d", default=None, help="Transaction date (YYYY-MM-DD)")
@click.option("--fees", type=float, default=0.0, help="Brokerage fees")
@click.option("--notes", default="", help="Transaction notes")
@click.pass_context
def portfolio_add(
    ctx: click.Context, ticker: str, quantity: float, price: float, date: str, fees: float, notes: str
) -> None:
    """Record a stock purchase."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    # Parse date if provided
    transaction_date = None
    if date:
        try:
            transaction_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            return

    manager = PortfolioManager()

    try:
        transaction = manager.add_buy(
            ticker=ticker,
            quantity=quantity,
            price_per_share=price,
            transaction_date=transaction_date,
            fees=fees,
            notes=notes or None,
        )

        console.print(f"[green]Recorded purchase of {ticker}[/green]")
        console.print(f"  Shares: {quantity}")
        console.print(f"  Price: ${price:.2f}")
        console.print(f"  Total Cost: ${transaction.total_cost:.2f}")
        if fees > 0:
            console.print(f"  Fees: ${fees:.2f}")
        console.print()
        console.print("[dim]Run `asymmetric portfolio holdings` to see your positions[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")


@portfolio.command("sell")
@click.argument("ticker")
@click.option("--quantity", "-q", type=float, required=True, help="Shares to sell")
@click.option("--price", "-p", type=float, required=True, help="Sale price per share in USD")
@click.option("--date", "-d", default=None, help="Sale date (YYYY-MM-DD)")
@click.option("--fees", type=float, default=0.0, help="Brokerage fees")
@click.pass_context
def portfolio_sell(
    ctx: click.Context, ticker: str, quantity: float, price: float, date: str, fees: float
) -> None:
    """Record a stock sale with realized gain calculation."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    # Parse date if provided
    transaction_date = None
    if date:
        try:
            transaction_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            return

    manager = PortfolioManager()

    try:
        transaction = manager.add_sell(
            ticker=ticker,
            quantity=quantity,
            price_per_share=price,
            transaction_date=transaction_date,
            fees=fees,
        )

        console.print(f"[green]Recorded sale of {ticker}[/green]")
        console.print(f"  Shares: {quantity}")
        console.print(f"  Price: ${price:.2f}")
        console.print(f"  Proceeds: ${transaction.total_proceeds:.2f}")
        if fees > 0:
            console.print(f"  Fees: ${fees:.2f}")

        # Show realized gain/loss
        if transaction.realized_gain is not None:
            gain_style = "green" if transaction.realized_gain >= 0 else "red"
            console.print(f"  [{gain_style}]Realized Gain: ${transaction.realized_gain:.2f}[/{gain_style}]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")


@portfolio.command("summary")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def portfolio_summary(ctx: click.Context, as_json: bool) -> None:
    """Show portfolio summary with total value, P&L, allocation."""
    console: Console = ctx.obj["console"]

    manager = PortfolioManager()
    summary = manager.get_portfolio_summary()

    if as_json:
        import json

        data = {
            "total_cost_basis": summary.total_cost_basis,
            "realized_pnl_total": summary.realized_pnl_total,
            "realized_pnl_ytd": summary.realized_pnl_ytd,
            "position_count": summary.position_count,
            "cash_invested": summary.cash_invested,
            "cash_received": summary.cash_received,
        }
        console.print(json.dumps(data, indent=2))
        return

    if summary.position_count == 0:
        console.print("[yellow]No positions in portfolio[/yellow]")
        console.print("[dim]Run `asymmetric portfolio add TICKER -q ... -p ...` to add a position[/dim]")
        return

    console.print(Panel.fit("[bold]Portfolio Summary[/bold]"))
    console.print()

    # Cost basis
    console.print(f"[cyan]Total Cost Basis:[/cyan] ${summary.total_cost_basis:,.2f}")
    console.print(f"[cyan]Positions:[/cyan] {summary.position_count}")
    console.print()

    # Cash flow
    console.print(f"[cyan]Cash Invested:[/cyan] ${summary.cash_invested:,.2f}")
    console.print(f"[cyan]Cash Received:[/cyan] ${summary.cash_received:,.2f}")
    console.print()

    # Realized P&L
    ytd_style = "green" if summary.realized_pnl_ytd >= 0 else "red"
    total_style = "green" if summary.realized_pnl_total >= 0 else "red"
    console.print(f"[cyan]Realized P&L (YTD):[/cyan] [{ytd_style}]${summary.realized_pnl_ytd:,.2f}[/{ytd_style}]")
    console.print(f"[cyan]Realized P&L (Total):[/cyan] [{total_style}]${summary.realized_pnl_total:,.2f}[/{total_style}]")


@portfolio.command("holdings")
@click.option(
    "--sort-by",
    type=click.Choice(["ticker", "value", "fscore"]),
    default="value",
    help="Sort field",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def portfolio_holdings(ctx: click.Context, sort_by: str, as_json: bool) -> None:
    """List all current holdings with scores and P&L."""
    console: Console = ctx.obj["console"]

    manager = PortfolioManager()
    holdings = manager.get_holdings(sort_by=sort_by)

    if not holdings:
        console.print("[yellow]No holdings in portfolio[/yellow]")
        return

    if as_json:
        import json

        data = [
            {
                "ticker": h.ticker,
                "company_name": h.company_name,
                "quantity": h.quantity,
                "cost_basis_total": h.cost_basis_total,
                "cost_basis_per_share": h.cost_basis_per_share,
                "allocation_percent": h.allocation_percent,
                "fscore": h.fscore,
                "zscore": h.zscore,
                "zone": h.zone,
            }
            for h in holdings
        ]
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="Portfolio Holdings")
    table.add_column("Ticker", style="cyan")
    table.add_column("Company", max_width=25)
    table.add_column("Shares", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Avg Cost", justify="right")
    table.add_column("Alloc %", justify="right")
    table.add_column("F-Score", justify="center")
    table.add_column("Zone", justify="center")

    for h in holdings:
        fscore_text = (
            Text(str(h.fscore), style=get_score_color(h.fscore, 9)) if h.fscore is not None else Text("-", style="dim")
        )
        zone_text = (
            Text(h.zone, style=get_zone_color(h.zone)) if h.zone else Text("-", style="dim")
        )

        table.add_row(
            h.ticker,
            h.company_name[:25],
            f"{h.quantity:,.2f}",
            f"${h.cost_basis_total:,.2f}",
            f"${h.cost_basis_per_share:.2f}",
            f"{h.allocation_percent:.1f}%",
            fscore_text,
            zone_text,
        )

    console.print(table)

    # Total
    total = sum(h.cost_basis_total for h in holdings)
    console.print(f"\n[bold]Total Cost Basis: ${total:,.2f}[/bold]")


@portfolio.command("history")
@click.argument("ticker", required=False)
@click.option("--limit", type=int, default=20, help="Maximum results")
@click.pass_context
def portfolio_history(ctx: click.Context, ticker: str, limit: int) -> None:
    """Show transaction history for a ticker or entire portfolio."""
    console: Console = ctx.obj["console"]

    manager = PortfolioManager()
    transactions = manager.get_transaction_history(ticker=ticker, limit=limit)

    if not transactions:
        console.print("[yellow]No transactions found[/yellow]")
        return

    title = f"Transaction History: {ticker.upper()}" if ticker else "Transaction History"
    table = Table(title=title)
    table.add_column("Date", style="dim")
    table.add_column("Ticker", style="cyan")
    table.add_column("Type", justify="center")
    table.add_column("Shares", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Gain", justify="right")

    for t in transactions:
        type_style = "green" if t.transaction_type == "buy" else "red"
        type_text = Text(t.transaction_type.upper(), style=type_style)

        total = t.total_cost if t.transaction_type == "buy" else t.total_proceeds
        gain_text = "-"
        if t.realized_gain is not None:
            gain_style = "green" if t.realized_gain >= 0 else "red"
            gain_text = Text(f"${t.realized_gain:,.2f}", style=gain_style)

        table.add_row(
            t.transaction_date.strftime("%Y-%m-%d"),
            t.ticker,
            type_text,
            f"{t.quantity:,.2f}",
            f"${t.price_per_share:.2f}",
            f"${total:,.2f}",
            gain_text,
        )

    console.print(table)


@portfolio.command("scores")
@click.option("--weighted", is_flag=True, help="Show position-weighted portfolio scores")
@click.pass_context
def portfolio_scores(ctx: click.Context, weighted: bool) -> None:
    """Calculate portfolio-level F-Score and Z-Score metrics."""
    console: Console = ctx.obj["console"]

    manager = PortfolioManager()
    scores = manager.get_weighted_scores()

    if scores.holdings_with_scores == 0:
        console.print("[yellow]No holdings with scores found[/yellow]")
        console.print("[dim]Run `asymmetric score TICKER` for your holdings to add score data[/dim]")
        return

    console.print(Panel.fit("[bold]Portfolio Scores[/bold]"))
    console.print()

    if weighted:
        console.print("[cyan]Position-Weighted Scores:[/cyan]")
        console.print(f"  F-Score: {scores.weighted_fscore:.1f}")
        console.print(f"  Z-Score: {scores.weighted_zscore:.2f}")
        console.print()

    console.print("[cyan]Zone Allocation:[/cyan]")
    console.print(f"  [green]Safe:[/green] {scores.safe_allocation:.1f}%")
    console.print(f"  [yellow]Grey:[/yellow] {scores.grey_allocation:.1f}%")
    console.print(f"  [red]Distress:[/red] {scores.distress_allocation:.1f}%")
    console.print()

    console.print(f"[dim]Holdings with scores: {scores.holdings_with_scores}[/dim]")
    if scores.holdings_without_scores > 0:
        console.print(f"[dim yellow]Holdings missing scores: {scores.holdings_without_scores}[/dim yellow]")


@portfolio.command("snapshot")
@click.option("--auto", is_flag=True, help="Automatic mode (only take snapshot if conditions met)")
@click.option("--force", is_flag=True, help="Force snapshot even if one already exists today")
@click.pass_context
def portfolio_snapshot(ctx: click.Context, auto: bool, force: bool) -> None:
    """
    Take a portfolio snapshot with current market prices.

    Snapshots capture portfolio state over time for performance tracking.
    In --auto mode, only creates snapshot if:
    - No snapshot exists today
    - After market close (4 PM ET / 9 PM UTC)
    - Portfolio has holdings

    \b
    Examples:
        asymmetric portfolio snapshot           # Manual snapshot
        asymmetric portfolio snapshot --auto    # Automated (for cron jobs)
        asymmetric portfolio snapshot --force   # Force even if exists today
    """
    console: Console = ctx.obj["console"]

    # Check last snapshot
    last_snapshot = get_last_snapshot_date()
    if last_snapshot:
        console.print(f"[dim]Last snapshot: {last_snapshot.strftime('%Y-%m-%d %H:%M UTC')}[/dim]")
        console.print()

    # Auto mode - check conditions
    if auto:
        if not force and not should_take_snapshot():
            console.print("[yellow]Snapshot conditions not met (already exists today or before market close)[/yellow]")
            console.print("[dim]Run without --auto flag to force manual snapshot[/dim]")
            return

    # Take snapshot
    manager = PortfolioManager()

    try:
        snapshot = manager.take_snapshot(auto=auto)

        console.print("[green]Portfolio snapshot created successfully[/green]")
        console.print()
        console.print(f"[cyan]Snapshot Date:[/cyan] {snapshot.snapshot_date.strftime('%Y-%m-%d %H:%M UTC')}")
        console.print(f"[cyan]Market Value:[/cyan] ${snapshot.total_value:,.2f}")
        console.print(f"[cyan]Cost Basis:[/cyan] ${snapshot.total_cost_basis:,.2f}")

        # Show unrealized P&L with color
        pnl_style = "green" if snapshot.unrealized_pnl >= 0 else "red"
        console.print(
            f"[cyan]Unrealized P&L:[/cyan] [{pnl_style}]${snapshot.unrealized_pnl:,.2f} "
            f"({snapshot.unrealized_pnl_percent:+.2f}%)[/{pnl_style}]"
        )

        console.print(f"[cyan]Positions:[/cyan] {snapshot.position_count}")
        console.print()

        # Show weighted scores
        if snapshot.weighted_fscore and snapshot.weighted_zscore:
            console.print(f"[cyan]Weighted F-Score:[/cyan] {snapshot.weighted_fscore:.1f}/9")
            console.print(f"[cyan]Weighted Z-Score:[/cyan] {snapshot.weighted_zscore:.2f}")

        console.print()
        console.print("[dim]View snapshot history in the dashboard Portfolio page[/dim]")

    except Exception as e:
        logger.exception("Unexpected error creating snapshot")
        console.print(f"[red]Unexpected error creating snapshot: {e}[/red]")
