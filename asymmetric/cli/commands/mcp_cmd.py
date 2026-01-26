"""MCP server management commands."""

import click
from rich.console import Console

from asymmetric.config import config


def _get_default_port() -> int:
    """Get default MCP port from central config."""
    return config.mcp_default_port


@click.group(name="mcp")
@click.pass_context
def mcp(ctx: click.Context) -> None:
    """
    MCP server management.

    Start the Model Context Protocol server for integration with
    Claude Code and other MCP clients.

    \b
    Examples:
        asymmetric mcp start                       # STDIO mode
        asymmetric mcp start --transport http      # HTTP mode
        asymmetric mcp start --port 9000           # Custom port
    """
    pass


@mcp.command("start")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport mode: stdio (dev) or http (prod)",
)
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
    help="Host to bind for HTTP mode",
)
@click.option(
    "--port",
    type=int,
    default=None,  # Loaded from central config
    help="Port for HTTP mode (default from ASYMMETRIC_MCP_PORT)",
)
@click.option(
    "--auto-port",
    is_flag=True,
    default=False,
    help="Automatically find available port if specified port is in use",
)
@click.pass_context
def mcp_start(
    ctx: click.Context,
    transport: str,
    host: str,
    port: int | None,
    auto_port: bool,
) -> None:
    """
    Start the MCP server.

    STDIO mode (default): For development and Claude Code integration.
    HTTP mode: For production deployment with persistent connections.

    \b
    STDIO Mode (Development):
        asymmetric mcp start

    \b
    HTTP Mode (Production):
        asymmetric mcp start --transport http --port 8000

    \b
    Claude Code Integration:
        claude mcp add asymmetric -- poetry run asymmetric mcp start

    \b
    Available Tools:
        - lookup_company: Get company metadata
        - get_financials_summary: Condensed financial data
        - calculate_scores: Piotroski + Altman scores
        - get_filing_section: Lazy-load filing section
        - analyze_filing_with_ai: Gemini analysis with caching
        - screen_universe: Filter stocks by criteria
        - extract_custom_metrics: LLM-aided XBRL parsing
    """
    console: Console = ctx.obj["console"]

    # Use central config default if port not specified
    if port is None:
        port = config.mcp_default_port

    try:
        from asymmetric.mcp.server import run_server
        from asymmetric.core.data.exceptions import PortInUseError

        # Check configuration
        if not config.gemini_api_key:
            console.print(
                "[yellow]Warning: GEMINI_API_KEY not set. "
                "AI tools will be disabled.[/yellow]"
            )

        if transport == "http":
            if auto_port:
                console.print(
                    f"[green]Starting MCP server on http://{host}:{port} "
                    f"(auto-port enabled)[/green]"
                )
            else:
                console.print(f"[green]Starting MCP server on http://{host}:{port}[/green]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
        else:
            console.print("[green]Starting MCP server in STDIO mode[/green]")
            console.print("[dim]Ready for MCP client connection[/dim]")

        # Run server (blocks until stopped)
        run_server(transport=transport, host=host, port=port, auto_port=auto_port)

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")

    except PortInUseError as e:
        console.print(f"[red]Port conflict:[/red] {e}")
        if not auto_port:
            console.print(
                "[yellow]Tip: Use --auto-port to automatically find an available port[/yellow]"
            )
        raise SystemExit(1)

    except ImportError as e:
        console.print(f"[red]Missing dependency:[/red] {e}")
        console.print("[yellow]Run: poetry install[/yellow]")
        raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@mcp.command("info")
@click.pass_context
def mcp_info(ctx: click.Context) -> None:
    """
    Show MCP server information and configuration.
    """
    console: Console = ctx.obj["console"]

    from rich.table import Table
    from rich.panel import Panel
    from asymmetric.config import config

    console.print()
    console.print("[bold]Asymmetric MCP Server[/bold]")
    console.print()

    # Configuration table
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value")

    config_table.add_row(
        "Gemini API",
        "[green]Configured[/green]" if config.gemini_api_key else "[red]Not configured[/red]"
    )
    config_table.add_row(
        "SEC Identity",
        config.sec_identity[:50] + "..." if len(config.sec_identity) > 50 else config.sec_identity
    )
    config_table.add_row("Database Path", str(config.db_path))
    config_table.add_row("Bulk Data Dir", str(config.bulk_dir))

    console.print(Panel(config_table, title="Configuration", border_style="blue"))

    # Tools table
    tools = [
        ("lookup_company", "Get company metadata by ticker"),
        ("get_financials_summary", "Condensed financial data"),
        ("calculate_scores", "Piotroski F-Score + Altman Z-Score"),
        ("get_filing_section", "Lazy-load specific filing section"),
        ("analyze_filing_with_ai", "Gemini analysis with caching"),
        ("screen_universe", "Filter stocks by criteria"),
        ("extract_custom_metrics", "LLM-aided XBRL parsing"),
    ]

    tools_table = Table(show_header=True, header_style="bold")
    tools_table.add_column("Tool")
    tools_table.add_column("Description")

    for name, desc in tools:
        tools_table.add_row(name, desc)

    console.print()
    console.print(Panel(tools_table, title="Available Tools", border_style="green"))

    # Usage examples
    console.print()
    console.print("[bold]Usage Examples:[/bold]")
    console.print()
    console.print("  [cyan]# Start in STDIO mode (development)[/cyan]")
    console.print("  asymmetric mcp start")
    console.print()
    console.print("  [cyan]# Start in HTTP mode (production)[/cyan]")
    console.print("  asymmetric mcp start --transport http --port 8000")
    console.print()
    console.print("  [cyan]# Add to Claude Code[/cyan]")
    console.print("  claude mcp add asymmetric -- poetry run asymmetric mcp start")
    console.print()
