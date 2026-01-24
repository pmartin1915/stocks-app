"""
Asymmetric CLI - Investment Research Workstation.

Entry point for the command-line interface. Provides commands for:
- Company lookup
- Financial scoring (Piotroski F-Score, Altman Z-Score)
- Stock comparison (side-by-side)
- Watchlist management
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
    asymmetric analyze AAPL
    asymmetric thesis create MSFT --auto
    asymmetric mcp start
    asymmetric db init
"""

import click
from rich.console import Console

from asymmetric import __version__
from asymmetric.cli.commands import (
    analyze,
    compare,
    db,
    lookup,
    mcp_cmd,
    score,
    screen,
    thesis,
    watchlist,
)

# Global console for rich output
console = Console()


@click.group()
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
cli.add_command(analyze.analyze)
cli.add_command(thesis.thesis)
cli.add_command(mcp_cmd.mcp)
cli.add_command(db.db)


def main() -> None:
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
