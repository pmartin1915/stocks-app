"""Stop command for terminating background dashboard process."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

# PID file location (must match launch.py)
PID_FILE = Path(__file__).parent.parent.parent.parent / ".dashboard.pid"


@click.command()
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress output (only show errors)",
)
@click.pass_context
def stop(ctx: click.Context, quiet: bool) -> None:
    """
    Stop the background dashboard process.

    Reads the PID from .dashboard.pid and terminates the process.
    Use this after starting the dashboard with 'asymmetric launch --background'.

    \b
    Examples:
        asymmetric stop       # Stop the background dashboard
        asymmetric stop -q    # Stop quietly (for scripts)
    """
    console: Console = ctx.obj["console"]

    def log(msg: str) -> None:
        """Print message unless quiet mode is enabled."""
        if not quiet:
            console.print(msg)

    if not PID_FILE.exists():
        if not quiet:
            console.print("[yellow]No dashboard process found[/yellow]")
            console.print("[dim]Hint: Start with 'asymmetric launch --background'[/dim]")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError) as e:
        console.print(f"[red]x[/red] Invalid PID file: {e}")
        PID_FILE.unlink(missing_ok=True)
        raise SystemExit(1)

    log(f"[cyan]Stopping dashboard (PID: {pid})...[/cyan]")

    try:
        if sys.platform == "win32":
            # Windows: use taskkill
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                # Process may already be dead
                if "not found" in result.stderr.lower():
                    log("[yellow]Process already stopped[/yellow]")
                else:
                    console.print(f"[red]x[/red] Failed to stop: {result.stderr.strip()}")
                    raise SystemExit(1)
            else:
                log(f"[green]+[/green] Dashboard stopped (PID: {pid})")
        else:
            # Unix: use kill
            import os
            import signal

            try:
                os.kill(pid, signal.SIGTERM)
                log(f"[green]+[/green] Dashboard stopped (PID: {pid})")
            except ProcessLookupError:
                log("[yellow]Process already stopped[/yellow]")
            except PermissionError:
                console.print("[red]x[/red] Permission denied - try running as admin")
                raise SystemExit(1)

    finally:
        # Always clean up PID file
        PID_FILE.unlink(missing_ok=True)
