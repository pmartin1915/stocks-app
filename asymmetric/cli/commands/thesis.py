"""Thesis management commands for investment decision tracking."""

import json
from datetime import datetime

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from asymmetric.core.ai.exceptions import AIError, GeminiConfigError
from asymmetric.core.data.exceptions import SECRateLimitError


@click.group()
@click.pass_context
def thesis(ctx: click.Context) -> None:
    """
    Manage investment theses.

    Create, view, and track investment theses with optional AI generation.

    \b
    Examples:
        asymmetric thesis create AAPL
        asymmetric thesis create MSFT --auto
        asymmetric thesis list
        asymmetric thesis view 1
    """
    pass


@thesis.command("create")
@click.argument("ticker")
@click.option(
    "--auto",
    is_flag=True,
    help="Auto-generate thesis using AI",
)
@click.option(
    "--status",
    type=click.Choice(["draft", "active", "archived"]),
    default="draft",
    help="Initial thesis status",
)
@click.pass_context
def thesis_create(
    ctx: click.Context,
    ticker: str,
    auto: bool,
    status: str,
) -> None:
    """
    Create a new investment thesis.

    Use --auto to generate thesis using AI analysis of recent filings.

    \b
    Examples:
        asymmetric thesis create AAPL
        asymmetric thesis create MSFT --auto
    """
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    try:
        from asymmetric.db import get_session, init_db, Thesis, Stock
        from asymmetric.db.database import get_or_create_stock

        # Initialize database if needed
        init_db()

        if auto:
            _create_auto_thesis(console, ticker, status)
        else:
            _create_manual_thesis(console, ticker, status)

    except GeminiConfigError as e:
        console.print(f"[red]Gemini not configured:[/red] {e}")
        console.print("[yellow]Set GEMINI_API_KEY to use --auto.[/yellow]")
        raise SystemExit(1)

    except AIError as e:
        console.print(f"[red]AI Error:[/red] {e}")
        raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


def _create_auto_thesis(console: Console, ticker: str, status: str) -> None:
    """Create thesis using AI generation."""
    from asymmetric.core.ai.gemini_client import GeminiModel, get_gemini_client
    from asymmetric.core.data.edgar_client import EdgarClient
    from asymmetric.db import get_session, Thesis
    from asymmetric.db.database import get_or_create_stock

    # Get filing text
    with console.status(f"[bold blue]Fetching 10-K for {ticker}...[/bold blue]"):
        edgar = EdgarClient()
        text = edgar.get_filing_text(ticker, filing_type="10-K")

    if not text:
        console.print(f"[red]No 10-K filing found for {ticker}[/red]")
        raise SystemExit(1)

    # Generate thesis with AI
    prompt = """Based on this SEC 10-K filing, generate an investment thesis with:

1. **Summary** (1-2 sentences): A concise investment thesis statement
2. **Bull Case**: Key reasons this could be a good investment
3. **Bear Case**: Key risks and concerns
4. **Key Metrics to Monitor**: Specific metrics to track going forward

Format your response with clear section headers."""

    with console.status("[bold blue]Generating thesis with AI...[/bold blue]"):
        client = get_gemini_client()
        result = client.analyze_with_cache(
            context=text,
            prompt=prompt,
            model=GeminiModel.PRO,  # Use Pro for better quality
        )

    # Parse response to extract sections
    content = result.content
    summary = _extract_section(content, "Summary", 500) or content[:500]

    # Save to database
    with get_session() as session:
        stock = get_or_create_stock(ticker)
        stock = session.merge(stock)

        thesis = Thesis(
            stock_id=stock.id,
            summary=summary[:500],
            analysis_text=content,
            bull_case=_extract_section(content, "Bull Case"),
            bear_case=_extract_section(content, "Bear Case"),
            key_metrics=_extract_section(content, "Key Metrics"),
            ai_model=result.model,
            ai_cost_usd=result.estimated_cost_usd,
            ai_tokens_input=result.token_count_input,
            ai_tokens_output=result.token_count_output,
            cached=result.cached,
            status=status,
        )
        session.add(thesis)
        session.flush()
        thesis_id = thesis.id

    console.print()
    console.print(f"[green]Thesis created successfully![/green]")
    console.print(f"[dim]Thesis ID: {thesis_id}[/dim]")
    console.print()

    # Display preview
    console.print(Panel(
        Markdown(summary),
        title=f"Investment Thesis: {ticker}",
        border_style="green",
    ))

    console.print()
    console.print(f"[dim]View full thesis: asymmetric thesis view {thesis_id}[/dim]")


def _create_manual_thesis(console: Console, ticker: str, status: str) -> None:
    """Create thesis with manual input."""
    from asymmetric.db import get_session, Thesis
    from asymmetric.db.database import get_or_create_stock

    console.print(f"[bold]Creating manual thesis for {ticker}[/bold]")
    console.print()

    # Get user input
    summary = click.prompt("Summary (1-2 sentences)")
    analysis = click.prompt("Full analysis (press Enter for multiline)", default="")

    if not analysis:
        console.print("[dim]Enter your analysis (end with Ctrl+D or Ctrl+Z):[/dim]")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        analysis = "\n".join(lines)

    bull_case = click.prompt("Bull case (optional)", default="")
    bear_case = click.prompt("Bear case (optional)", default="")

    # Save to database
    with get_session() as session:
        stock = get_or_create_stock(ticker)
        stock = session.merge(stock)

        thesis = Thesis(
            stock_id=stock.id,
            summary=summary[:500],
            analysis_text=analysis,
            bull_case=bull_case if bull_case else None,
            bear_case=bear_case if bear_case else None,
            status=status,
        )
        session.add(thesis)
        session.flush()
        thesis_id = thesis.id

    console.print()
    console.print(f"[green]Thesis created successfully![/green]")
    console.print(f"[dim]Thesis ID: {thesis_id}[/dim]")


def _extract_section(text: str, section_name: str, max_length: int = None) -> str:
    """Extract a section from markdown-formatted text."""
    import re

    # Try to find section by header
    patterns = [
        rf"\*\*{section_name}\*\*[:\s]*([^*]+?)(?=\*\*|\Z)",
        rf"#{1,3}\s*{section_name}[:\s]*(.+?)(?=#{1,3}|\Z)",
        rf"{section_name}[:\s]*([^\n]+(?:\n(?![A-Z][a-z]+:)[^\n]+)*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            if max_length and len(content) > max_length:
                content = content[:max_length] + "..."
            return content

    return ""


@thesis.command("list")
@click.option(
    "--status",
    type=click.Choice(["draft", "active", "archived", "all"]),
    default="all",
    help="Filter by status",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def thesis_list(ctx: click.Context, status: str, as_json: bool) -> None:
    """
    List investment theses.

    \b
    Examples:
        asymmetric thesis list
        asymmetric thesis list --status active
        asymmetric thesis list --json
    """
    console: Console = ctx.obj["console"]

    try:
        from asymmetric.db import get_session, init_db, Thesis, Stock

        init_db()

        with get_session() as session:
            query = session.query(Thesis).join(Stock)

            if status != "all":
                query = query.filter(Thesis.status == status)

            query = query.order_by(Thesis.created_at.desc())
            theses = query.all()

            if as_json:
                output = [
                    {
                        "id": t.id,
                        "ticker": t.stock.ticker if t.stock else "Unknown",
                        "summary": t.summary,
                        "status": t.status,
                        "ai_generated": bool(t.ai_model),
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                    }
                    for t in theses
                ]
                console.print(json.dumps(output, indent=2))
            else:
                _display_thesis_list(console, theses)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


def _display_thesis_list(console: Console, theses) -> None:
    """Display thesis list with Rich formatting."""
    if not theses:
        console.print("[yellow]No theses found.[/yellow]")
        console.print("[dim]Create one with: asymmetric thesis create TICKER[/dim]")
        return

    table = Table(title="Investment Theses")
    table.add_column("ID", style="cyan")
    table.add_column("Ticker", style="bold")
    table.add_column("Summary")
    table.add_column("Status")
    table.add_column("AI", justify="center")
    table.add_column("Created")

    status_colors = {
        "draft": "yellow",
        "active": "green",
        "archived": "dim",
    }

    for t in theses:
        ticker = t.stock.ticker if t.stock else "Unknown"
        summary = (t.summary[:50] + "...") if len(t.summary) > 50 else t.summary
        status_color = status_colors.get(t.status, "white")
        ai_marker = "[green]Y[/green]" if t.ai_model else "[dim]-[/dim]"
        created = t.created_at.strftime("%Y-%m-%d") if t.created_at else "-"

        table.add_row(
            str(t.id),
            ticker,
            summary,
            f"[{status_color}]{t.status}[/{status_color}]",
            ai_marker,
            created,
        )

    console.print()
    console.print(table)
    console.print()


@thesis.command("view")
@click.argument("thesis_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def thesis_view(ctx: click.Context, thesis_id: int, as_json: bool) -> None:
    """
    View a specific thesis.

    \b
    Examples:
        asymmetric thesis view 1
        asymmetric thesis view 1 --json
    """
    console: Console = ctx.obj["console"]

    try:
        from asymmetric.db import get_session, init_db, Thesis

        init_db()

        with get_session() as session:
            thesis = session.query(Thesis).filter(Thesis.id == thesis_id).first()

            if not thesis:
                console.print(f"[red]Thesis not found: ID {thesis_id}[/red]")
                raise SystemExit(1)

            if as_json:
                output = {
                    "id": thesis.id,
                    "ticker": thesis.stock.ticker if thesis.stock else "Unknown",
                    "summary": thesis.summary,
                    "analysis_text": thesis.analysis_text,
                    "bull_case": thesis.bull_case,
                    "bear_case": thesis.bear_case,
                    "key_metrics": thesis.key_metrics,
                    "status": thesis.status,
                    "ai_model": thesis.ai_model,
                    "ai_cost_usd": thesis.ai_cost_usd,
                    "created_at": thesis.created_at.isoformat() if thesis.created_at else None,
                    "updated_at": thesis.updated_at.isoformat() if thesis.updated_at else None,
                }
                console.print(json.dumps(output, indent=2))
            else:
                _display_thesis(console, thesis)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


def _display_thesis(console: Console, thesis) -> None:
    """Display a single thesis with Rich formatting."""
    ticker = thesis.stock.ticker if thesis.stock else "Unknown"

    console.print()

    # Header
    status_colors = {"draft": "yellow", "active": "green", "archived": "dim"}
    status_color = status_colors.get(thesis.status, "white")

    console.print(f"[bold]Investment Thesis: {ticker}[/bold]")
    console.print(f"[dim]ID: {thesis.id} | Status: [{status_color}]{thesis.status}[/{status_color}][/dim]")
    console.print()

    # Summary
    console.print(Panel(thesis.summary, title="Summary", border_style="blue"))

    # Full analysis
    if thesis.analysis_text:
        console.print()
        console.print(Panel(
            Markdown(thesis.analysis_text),
            title="Analysis",
            border_style="cyan",
        ))

    # Bull/Bear cases
    if thesis.bull_case or thesis.bear_case:
        console.print()
        cols = Table.grid(expand=True)
        cols.add_column()
        cols.add_column()

        bull_panel = Panel(
            Markdown(thesis.bull_case or "[dim]Not specified[/dim]"),
            title="[green]Bull Case[/green]",
            border_style="green",
        )
        bear_panel = Panel(
            Markdown(thesis.bear_case or "[dim]Not specified[/dim]"),
            title="[red]Bear Case[/red]",
            border_style="red",
        )

        cols.add_row(bull_panel, bear_panel)
        console.print(cols)

    # Metadata
    console.print()
    meta_table = Table(show_header=False, box=None, padding=(0, 1))
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value")

    if thesis.ai_model:
        meta_table.add_row("AI Model", thesis.ai_model)
        meta_table.add_row("AI Cost", f"${thesis.ai_cost_usd:.4f}" if thesis.ai_cost_usd else "-")

    meta_table.add_row(
        "Created",
        thesis.created_at.strftime("%Y-%m-%d %H:%M") if thesis.created_at else "-"
    )
    meta_table.add_row(
        "Updated",
        thesis.updated_at.strftime("%Y-%m-%d %H:%M") if thesis.updated_at else "-"
    )

    console.print(Panel(meta_table, title="[dim]Metadata[/dim]", border_style="dim"))
    console.print()
