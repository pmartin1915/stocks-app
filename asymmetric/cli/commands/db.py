"""Database management commands."""

import logging

import click
from rich.console import Console

logger = logging.getLogger(__name__)
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from asymmetric.cli.error_handler import handle_cli_errors
from asymmetric.config import config
from asymmetric.core.data.bulk_manager import BulkDataManager


@click.group()
def db() -> None:
    """Database management commands.

    Initialize and manage the local database for bulk SEC data.
    """
    pass


@db.command()
@click.pass_context
@handle_cli_errors
def init(ctx: click.Context) -> None:
    """
    Initialize the local database.

    Creates the DuckDB database schema for storing bulk SEC data.
    This is required before running 'db refresh'.

    \b
    Example:
        asymmetric db init
    """
    console: Console = ctx.obj["console"]

    # Ensure directories exist
    config.ensure_directories()

    with console.status("[bold blue]Initializing database...[/bold blue]"):
        bulk = BulkDataManager()
        bulk.initialize_schema()
        bulk.close()

    console.print("[green]Database initialized successfully![/green]")
    console.print(f"[dim]Database path: {config.bulk_dir / 'sec_data.duckdb'}[/dim]")


@db.command()
@click.option("--full", is_flag=True, help="Force full re-download of bulk data")
@click.option(
    "--precompute/--no-precompute",
    default=True,
    help="Auto-precompute scores after refresh (default: enabled)"
)
@click.option("--limit", type=int, default=None, help="Max companies to import (default: all)")
@click.pass_context
@handle_cli_errors
def refresh(ctx: click.Context, full: bool, precompute: bool, limit: int) -> None:
    """
    Download/update SEC bulk data.

    Downloads companyfacts.zip from SEC EDGAR for zero-API-call
    historical queries. File size is approximately 500MB.

    By default, automatically precomputes scores after refresh for
    instant screening performance.

    \b
    Note: This can take several minutes on first run.

    \b
    Examples:
        asymmetric db refresh                   # Incremental update with auto-precompute
        asymmetric db refresh --full            # Full re-download with auto-precompute
        asymmetric db refresh --no-precompute   # Skip precomputation
    """
    console: Console = ctx.obj["console"]

    bulk = BulkDataManager()
    bulk.initialize_schema()

    # Check if we need to refresh
    stats = bulk.get_stats()
    if not full and stats.get("last_refresh"):
        console.print(f"[dim]Last refresh: {stats['last_refresh']}[/dim]")

    if full:
        console.print("[yellow]Performing full refresh (this may take a while)...[/yellow]")
    else:
        console.print("[blue]Checking for updates...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading bulk data...", total=100)

        def update_progress(pct: int) -> None:
            progress.update(task, completed=pct)
            if pct < 10:
                progress.update(task, description="Preparing...")
            elif pct < 50:
                progress.update(task, description="Downloading companyfacts.zip...")
            elif pct < 100:
                progress.update(task, description="Importing to database...")
            else:
                progress.update(task, description="Complete!")

        bulk.refresh(full=full, progress_callback=update_progress, max_companies=limit if limit else None)

    # Show stats
    stats = bulk.get_stats()

    console.print()
    console.print("[green]Bulk data refresh complete![/green]")

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")
    table.add_row("Companies", f"{stats['ticker_count']:,}")
    table.add_row("Facts", f"{stats['fact_count']:,}")
    table.add_row("Database Size", f"{stats['db_size_mb']:.1f} MB")
    table.add_row("Last Refresh", stats['last_refresh'] or "N/A")

    console.print(table)

    # Auto-precompute scores after successful refresh
    if precompute and stats['ticker_count'] > 0:
        console.print()
        console.print("[bold blue]Precomputing scores for instant screening...[/bold blue]")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task("Calculating scores...", total=100)

                def progress_callback(pct: int):
                    progress.update(task, completed=pct)

                count = bulk.precompute_scores(progress_callback=progress_callback)

            console.print(f"[green]✓ Precomputed {count} scores[/green]")
            console.print("[dim]Screening will now be instant with cached scores[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Score precomputation failed: {e}[/yellow]")
            console.print("[dim]You can run 'asymmetric db precompute' manually[/dim]")

    bulk.close()


@db.command()
@click.pass_context
@handle_cli_errors
def stats(ctx: click.Context) -> None:
    """
    Show database statistics.

    Displays information about the bulk data cache including
    number of companies, facts, and last refresh time.

    \b
    Example:
        asymmetric db stats
    """
    console: Console = ctx.obj["console"]

    bulk = BulkDataManager()
    bulk.initialize_schema()
    db_stats = bulk.get_stats()
    bulk.close()

    table = Table(title="Database Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Companies", f"{db_stats['ticker_count']:,}")
    table.add_row("Financial Facts", f"{db_stats['fact_count']:,}")
    table.add_row("Database Size", f"{db_stats['db_size_mb']:.1f} MB")
    table.add_row("Database Path", db_stats['db_path'])
    table.add_row(
        "Last Refresh",
        db_stats['last_refresh'] or "[yellow]Never[/yellow]"
    )

    console.print(table)

    if db_stats['ticker_count'] == 0:
        console.print()
        console.print("[yellow]Database is empty. Run 'asymmetric db refresh' to download data.[/yellow]")


@db.command()
@click.option("--limit", type=click.IntRange(1, 100000), default=10000, help="Maximum companies to score (1-100000)")
@click.pass_context
@handle_cli_errors
def precompute(ctx: click.Context, limit: int) -> None:
    """
    Precompute F-Scores and Z-Scores for all companies.

    Calculates Piotroski F-Score and Altman Z-Score for all companies
    with sufficient data. Results are stored in DuckDB for instant
    screening queries.

    \b
    Note: This uses local bulk data only (zero SEC API calls).

    \b
    Examples:
        asymmetric db precompute
        asymmetric db precompute --limit 5000
    """
    import time

    console: Console = ctx.obj["console"]

    bulk = BulkDataManager()
    bulk.initialize_schema()

    # Check if we have data
    stats = bulk.get_stats()
    if stats["ticker_count"] == 0:
        console.print("[yellow]No bulk data available.[/yellow]")
        console.print("Run [cyan]asymmetric db refresh[/cyan] first.")
        bulk.close()
        raise SystemExit(1)

    console.print(f"[bold blue]Precomputing scores for up to {limit:,} companies...[/bold blue]")
    console.print(f"[dim]Using bulk data with {stats['ticker_count']:,} companies[/dim]")
    console.print()

    start_time = time.perf_counter()
    scores_computed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Computing scores...", total=100)

        def update_progress(pct: int) -> None:
            nonlocal scores_computed
            scores_computed = pct
            progress.update(task, completed=pct, description=f"Computing scores... {pct}%")

        tickers = bulk.get_scorable_tickers(limit=limit)
        bulk.precompute_scores(tickers=tickers, progress_callback=update_progress)
        progress.update(task, completed=100, description="Complete!")

    elapsed = time.perf_counter() - start_time

    # Get final stats
    score_stats = bulk.get_scores_stats()
    bulk.close()

    console.print()
    console.print("[green]Precomputation complete![/green]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")
    table.add_row("Scores Computed", f"{score_stats.get('total_scores', scores_computed):,}")
    table.add_row("Time Elapsed", f"{elapsed:.1f} seconds")
    table.add_row("Last Computed", score_stats.get("last_computed", "N/A"))

    console.print(table)
    console.print()
    console.print("[dim]Run 'asymmetric screen' for instant results using precomputed scores.[/dim]")
