"""Launch command for starting the dashboard and MCP server."""

import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console

from asymmetric.cli.formatting import print_next_steps
from asymmetric.config import config


def find_available_port(start: int = 8501, end: int = 8520) -> int:
    """Find an available port in the given range."""
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available ports in range {start}-{end}")


@click.command()
@click.option(
    "--no-browser",
    is_flag=True,
    help="Don't auto-open browser",
)
@click.option(
    "--with-mcp",
    is_flag=True,
    help="Also start MCP server (port 8765)",
)
@click.option(
    "--port",
    default=0,
    type=int,
    help="Dashboard port (0 = auto-detect available port)",
)
@click.pass_context
def launch(ctx: click.Context, no_browser: bool, with_mcp: bool, port: int) -> None:
    """
    Launch the Asymmetric dashboard.

    Performs pre-flight checks and starts the Streamlit dashboard.
    Optionally starts the MCP server in parallel for Claude Code integration.

    \b
    Examples:
        asymmetric launch              # Start dashboard, open browser
        asymmetric launch --with-mcp   # Start dashboard + MCP server
        asymmetric launch --no-browser # Headless mode (for servers)
        asymmetric launch --port 8080  # Custom port
    """
    console: Console = ctx.obj["console"]

    console.print("[bold]Pre-flight checks...[/bold]")
    console.print()

    # Check database
    if not config.db_path.exists():
        console.print("[yellow]![/yellow] Database not initialized")

        if click.confirm("Initialize database now?", default=True):
            from asymmetric.db import init_db

            init_db()
            console.print("[green]+[/green] Database initialized")
            console.print()
            console.print(
                "[dim]TIP: Run 'asymmetric db refresh' to download SEC bulk data[/dim]"
            )
            console.print()
        else:
            console.print("[red]x[/red] Cannot proceed without database")
            raise SystemExit(1)
    else:
        console.print("[green]+[/green] Database found")

    # Check SEC_IDENTITY
    sec_identity = config.sec_identity
    if not sec_identity or "your-email" in sec_identity.lower():
        console.print("[yellow]![/yellow] SEC_IDENTITY not configured in .env")
        console.print("[dim]Some features may not work without valid SEC identity[/dim]")
    else:
        console.print("[green]+[/green] SEC_IDENTITY configured")

    console.print()

    # Start MCP server if requested
    mcp_process = None
    if with_mcp:
        console.print("[cyan]Starting MCP server on port 8765...[/cyan]")
        try:
            # Windows-specific: create new console window
            if sys.platform == "win32":
                mcp_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "asymmetric.cli.main",
                        "mcp",
                        "start",
                        "--transport",
                        "http",
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                # Unix: run in background
                mcp_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "asymmetric.cli.main",
                        "mcp",
                        "start",
                        "--transport",
                        "http",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            console.print("[green]+[/green] MCP server starting")
        except Exception as e:
            console.print(f"[yellow]![/yellow] Failed to start MCP server: {e}")

    # Find dashboard path
    dashboard_path = Path(__file__).parent.parent.parent.parent / "dashboard" / "app.py"
    if not dashboard_path.exists():
        console.print(f"[red]x[/red] Dashboard not found at {dashboard_path}")
        raise SystemExit(1)

    # Auto-detect port if not specified
    if port == 0:
        console.print("[cyan]Finding available port...[/cyan]")
        try:
            port = find_available_port()
            console.print(f"[green]+[/green] Using port {port}")
        except RuntimeError as e:
            console.print(f"[red]x[/red] {e}")
            raise SystemExit(1)

    url = f"http://localhost:{port}"

    # Open browser
    if not no_browser:
        console.print(f"[cyan]Opening browser to {url}...[/cyan]")
        webbrowser.open(url)

    console.print()
    console.print("[bold green]Dashboard starting...[/bold green]")
    console.print()
    console.print(f"  Dashboard: {url}")
    if with_mcp:
        console.print("  MCP Server: http://localhost:8765")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    try:
        # Run streamlit
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard_path),
                "--server.port",
                str(port),
                "--server.headless",
                "true" if no_browser else "false",
            ]
        )
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Dashboard stopped[/yellow]")
    finally:
        if mcp_process and sys.platform != "win32":
            # On Unix, terminate the background MCP process
            mcp_process.terminate()
            console.print("[dim]MCP server stopped[/dim]")
        elif mcp_process and sys.platform == "win32":
            console.print(
                "[dim]Note: MCP server may still be running in separate window[/dim]"
            )

    print_next_steps(
        console,
        [
            ("Check status", "asymmetric status"),
            ("View quickstart", "asymmetric quickstart"),
        ],
    )
