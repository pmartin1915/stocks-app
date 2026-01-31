"""Quickstart guide command."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from asymmetric.cli.formatting import BORDER_PRIMARY


@click.command()
@click.pass_context
def quickstart(ctx: click.Context) -> None:
    """
    Get started with Asymmetric in 5 steps.

    Shows the recommended workflow for new users, from database
    initialization to your first stock screen.

    \b
    Examples:
        asymmetric quickstart
    """
    console: Console = ctx.obj["console"]

    console.print()
    console.print(
        Panel.fit(
            "[bold]Asymmetric Quickstart Guide[/bold]",
            border_style=BORDER_PRIMARY,
        )
    )
    console.print()

    # Build steps table
    table = Table(
        show_header=True,
        header_style="bold cyan",
        padding=(0, 2),
        box=None,
    )
    table.add_column("Step", style="bold", width=6)
    table.add_column("Command", style="green", width=40)
    table.add_column("Description", style="dim")

    steps = [
        ("1", "asymmetric db init", "Create local database"),
        ("2", "asymmetric db refresh", "Download SEC bulk data (~500MB)"),
        ("3", "asymmetric lookup AAPL", "Look up company information"),
        ("4", "asymmetric score AAPL", "Calculate F-Score and Z-Score"),
        ("5", "asymmetric screen --piotroski-min 7", "Find financially strong stocks"),
    ]

    for step, cmd, desc in steps:
        table.add_row(step, cmd, desc)

    console.print(table)
    console.print()

    # Additional tips
    console.print("[dim]Tips:[/dim]")
    console.print("  [dim]Add --help to any command for details[/dim]")
    console.print("  [dim]Use --json flag for machine-readable output[/dim]")
    console.print("  [dim]Run 'asymmetric status' to check current state[/dim]")
    console.print()
