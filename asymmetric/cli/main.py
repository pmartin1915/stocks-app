"""
Asymmetric CLI - Investment Research Workstation.

Entry point for the command-line interface. Provides commands for:
- Company lookup
- Financial scoring (Piotroski F-Score, Altman Z-Score)
- Stock comparison (side-by-side)
- Watchlist management
- Portfolio tracking (transactions, holdings, P&L)
- Alerts (score threshold monitoring)
- Historical trends (score trajectory analysis)
- Sector analysis (peer comparison)
- AI-powered filing analysis
- Thesis management
- MCP server for Claude Code integration
- Database management (bulk data refresh)

Usage:
    asymmetric --help
    asymmetric lookup AAPL
    asymmetric score MSFT
    asymmetric score AAPL --detail
    asymmetric compare AAPL MSFT GOOG
    asymmetric watchlist add AAPL
    asymmetric watchlist review
    asymmetric portfolio add AAPL -q 10 -p 150
    asymmetric portfolio summary
    asymmetric alerts add AAPL --type fscore_above --threshold 7
    asymmetric history show AAPL
    asymmetric trends improving
    asymmetric sectors list
    asymmetric analyze AAPL
    asymmetric thesis create MSFT --auto
    asymmetric mcp start
    asymmetric db init
"""

from collections import OrderedDict

import click
from rich.console import Console

from asymmetric import __version__
from asymmetric.cli.commands import (
    alerts,
    analyze,
    compare,
    db,
    decision,
    history,
    launch,
    lookup,
    mcp_cmd,
    portfolio,
    quickstart,
    score,
    screen,
    sectors,
    status,
    thesis,
    watchlist,
)


class OrderedGroup(click.Group):
    """Custom group that displays commands in organized categories."""

    COMMAND_GROUPS: OrderedDict[str, list[str]] = OrderedDict([
        ("Research", ["lookup", "score", "compare", "analyze"]),
        ("Screening", ["screen", "trends"]),
        ("Tracking", ["watchlist", "portfolio", "thesis", "decision"]),
        ("Monitoring", ["alerts", "history", "sectors"]),
        ("Setup", ["db", "mcp", "quickstart", "status", "launch"]),
    ])

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Write commands in organized groups."""
        for group_name, cmd_names in self.COMMAND_GROUPS.items():
            commands = []
            for cmd_name in cmd_names:
                cmd = self.get_command(ctx, cmd_name)
                if cmd:
                    help_text = cmd.get_short_help_str(limit=formatter.width)
                    commands.append((cmd_name, help_text))

            if commands:
                with formatter.section(group_name):
                    formatter.write_dl(commands)

# Global console for rich output
console = Console()


@click.group(cls=OrderedGroup)
@click.version_option(version=__version__, prog_name="asymmetric")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Asymmetric - CLI-first investment research workstation.

    Screen stocks using quantitative criteria (Piotroski F-Score,
    Altman Z-Score) and AI-powered qualitative analysis.

    \b
    Examples:
        asymmetric lookup AAPL           # Look up company info
        asymmetric score MSFT            # Calculate financial scores
        asymmetric score AAPL --json     # Output as JSON
        asymmetric analyze AAPL          # AI analysis (Flash)
        asymmetric analyze MSFT --deep   # AI analysis (Pro)
        asymmetric thesis create AAPL    # Create investment thesis
        asymmetric thesis list           # List all theses
        asymmetric mcp start             # Start MCP server
        asymmetric db init               # Initialize database
        asymmetric db refresh            # Download bulk SEC data
    """
    ctx.ensure_object(dict)
    ctx.obj["console"] = console


# Register command groups
cli.add_command(lookup.lookup)
cli.add_command(score.score)
cli.add_command(screen.screen)
cli.add_command(compare.compare)
cli.add_command(watchlist.watchlist)
cli.add_command(portfolio.portfolio)
cli.add_command(alerts.alerts)
cli.add_command(history.history)
cli.add_command(history.trends)
cli.add_command(sectors.sectors)
cli.add_command(analyze.analyze)
cli.add_command(thesis.thesis)
cli.add_command(decision.decision)
cli.add_command(mcp_cmd.mcp)
cli.add_command(db.db)
cli.add_command(quickstart.quickstart)
cli.add_command(status.status)
cli.add_command(launch.launch)


def main() -> None:
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
