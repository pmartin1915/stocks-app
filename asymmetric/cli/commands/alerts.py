"""Alert management commands for watchlist monitoring."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from asymmetric.cli.formatting import get_score_color, get_zone_color
from asymmetric.core.alerts.checker import AlertChecker


@click.group()
@click.pass_context
def alerts(ctx: click.Context) -> None:
    """
    Manage watchlist alerts.

    Set up alerts to monitor score thresholds and zone changes
    for stocks on your watchlist.

    \b
    Examples:
        asymmetric alerts add AAPL --type fscore_above --threshold 7
        asymmetric alerts add MSFT --type zscore_zone --zone Distress --severity critical
        asymmetric alerts list
        asymmetric alerts check
        asymmetric alerts history
    """
    pass


@alerts.command("add")
@click.argument("ticker")
@click.option(
    "--type",
    "alert_type",
    type=click.Choice(["fscore_above", "fscore_below", "zscore_zone", "zscore_above", "zscore_below"]),
    required=True,
    help="Type of alert",
)
@click.option("--threshold", type=float, help="Numeric threshold (for score alerts)")
@click.option(
    "--zone", type=click.Choice(["Safe", "Grey", "Distress"]), help="Target zone (for zone alerts)"
)
@click.option(
    "--severity",
    type=click.Choice(["info", "warning", "critical"]),
    default="warning",
    help="Alert severity",
)
@click.pass_context
def alerts_add(
    ctx: click.Context, ticker: str, alert_type: str, threshold: float, zone: str, severity: str
) -> None:
    """Create a new alert for a stock."""
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    checker = AlertChecker()

    try:
        alert = checker.create_alert(
            ticker=ticker,
            alert_type=alert_type,
            threshold_value=threshold,
            threshold_zone=zone,
            severity=severity,
        )

        console.print(f"[green]Created alert for {ticker}[/green]")
        console.print(f"  Type: {alert_type}")
        if threshold is not None:
            console.print(f"  Threshold: {threshold}")
        if zone:
            console.print(f"  Zone: {zone}")
        console.print(f"  Severity: {severity}")
        console.print()
        console.print("[dim]Run `asymmetric alerts check` to evaluate alerts[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")


@alerts.command("list")
@click.option("--ticker", default=None, help="Filter by ticker")
@click.option("--active-only", is_flag=True, help="Show only active alerts")
@click.option("--triggered", is_flag=True, help="Show only triggered alerts")
@click.pass_context
def alerts_list(ctx: click.Context, ticker: str, active_only: bool, triggered: bool) -> None:
    """List configured alerts."""
    console: Console = ctx.obj["console"]

    checker = AlertChecker()
    alerts = checker.get_alerts(ticker=ticker, active_only=active_only, triggered_only=triggered)

    if not alerts:
        console.print("[yellow]No alerts configured[/yellow]")
        console.print("[dim]Tip: Run `asymmetric alerts add TICKER --type ...` to create one[/dim]")
        return

    table = Table(title="Configured Alerts")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Ticker", style="cyan")
    table.add_column("Type", style="bold")
    table.add_column("Threshold", justify="center")
    table.add_column("Severity", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Triggers", justify="right")

    for alert, alert_ticker in alerts:
        # Format threshold
        if alert.threshold_value is not None:
            threshold = str(int(alert.threshold_value)) if alert.alert_type.startswith("fscore") else f"{alert.threshold_value:.2f}"
        elif alert.threshold_zone:
            threshold = alert.threshold_zone
        else:
            threshold = "-"

        # Status
        if not alert.is_active:
            status = Text("Inactive", style="dim")
        elif alert.is_triggered:
            status = Text("TRIGGERED", style="red bold")
        else:
            status = Text("Active", style="green")

        # Severity styling
        sev_style = {"info": "blue", "warning": "yellow", "critical": "red"}
        severity_text = Text(alert.severity, style=sev_style.get(alert.severity, "white"))

        table.add_row(
            str(alert.id),
            alert_ticker,
            alert.alert_type,
            threshold,
            severity_text,
            status,
            str(alert.trigger_count),
        )

    console.print(table)


@alerts.command("check")
@click.option("--ticker", default=None, help="Check specific ticker only")
@click.option("--quiet", is_flag=True, help="Only output triggered alerts")
@click.pass_context
def alerts_check(ctx: click.Context, ticker: str, quiet: bool) -> None:
    """Run alert checks against current scores."""
    console: Console = ctx.obj["console"]

    checker = AlertChecker()
    tickers = [ticker] if ticker else None
    triggers = checker.check_all(tickers=tickers)

    if triggers:
        console.print(Panel.fit("[bold red]ALERTS TRIGGERED[/bold red]"))
        console.print()

        for trigger in triggers:
            sev_style = {"info": "blue", "warning": "yellow", "critical": "red bold"}
            style = sev_style.get(trigger.severity, "white")

            console.print(f"[{style}][{trigger.severity.upper()}][/{style}] {trigger.message}")
            console.print(f"  [dim]Triggered at: {trigger.triggered_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
            console.print()

        console.print(f"[bold]{len(triggers)} alert(s) triggered[/bold]")
        console.print("[dim]Run `asymmetric alerts history` to see full history[/dim]")
    elif not quiet:
        console.print("[green]No alerts triggered[/green]")


@alerts.command("history")
@click.option("--ticker", default=None, help="Filter by ticker")
@click.option("--unacknowledged", is_flag=True, help="Show only unacknowledged")
@click.option("--limit", type=int, default=20, help="Maximum results")
@click.pass_context
def alerts_history(ctx: click.Context, ticker: str, unacknowledged: bool, limit: int) -> None:
    """Show alert trigger history."""
    console: Console = ctx.obj["console"]

    checker = AlertChecker()
    history = checker.get_alert_history(ticker=ticker, unacknowledged_only=unacknowledged, limit=limit)

    if not history:
        console.print("[yellow]No alert history found[/yellow]")
        return

    table = Table(title="Alert History")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Ticker", style="cyan")
    table.add_column("Type", style="bold")
    table.add_column("Message", max_width=40)
    table.add_column("When", style="dim")
    table.add_column("Ack", justify="center")

    for record, alert_ticker, alert_type in history:
        ack_status = Text("Yes", style="green") if record.acknowledged else Text("No", style="yellow")

        table.add_row(
            str(record.id),
            alert_ticker,
            alert_type,
            record.message[:40] + ("..." if len(record.message) > 40 else ""),
            record.triggered_at.strftime("%Y-%m-%d %H:%M"),
            ack_status,
        )

    console.print(table)

    # Count unacknowledged
    unack_count = sum(1 for h, _, _ in history if not h.acknowledged)
    if unack_count > 0:
        console.print(f"\n[yellow]{unack_count} unacknowledged alert(s)[/yellow]")
        console.print("[dim]Run `asymmetric alerts ack <id>` to acknowledge[/dim]")


@alerts.command("ack")
@click.argument("alert_history_id", type=int)
@click.pass_context
def alerts_ack(ctx: click.Context, alert_history_id: int) -> None:
    """Acknowledge an alert."""
    console: Console = ctx.obj["console"]

    checker = AlertChecker()
    success = checker.acknowledge_alert(alert_history_id)

    if success:
        console.print(f"[green]Acknowledged alert #{alert_history_id}[/green]")
    else:
        console.print(f"[red]Alert history #{alert_history_id} not found[/red]")


@alerts.command("remove")
@click.argument("alert_id", type=int)
@click.pass_context
def alerts_remove(ctx: click.Context, alert_id: int) -> None:
    """Remove an alert configuration."""
    console: Console = ctx.obj["console"]

    checker = AlertChecker()
    success = checker.remove_alert(alert_id)

    if success:
        console.print(f"[green]Removed alert #{alert_id}[/green]")
    else:
        console.print(f"[red]Alert #{alert_id} not found[/red]")
