"""AI analysis commands for SEC filing analysis."""

import json

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from asymmetric.cli.formatting import print_next_steps
from asymmetric.core.ai.exceptions import (
    AIError,
    GeminiConfigError,
    GeminiContextTooLargeError,
    GeminiRateLimitError,
)
from asymmetric.core.data.exceptions import (
    SECEmptyResponseError,
    SECIdentityError,
    SECRateLimitError,
)


@click.command()
@click.argument("ticker")
@click.option(
    "--deep",
    is_flag=True,
    help="Use Pro model for deep analysis (more expensive)",
)
@click.option(
    "--section",
    type=str,
    help="Analyze specific section (e.g., 'Item 1A' for risk factors)",
)
@click.option(
    "--prompt",
    type=str,
    default="Provide a comprehensive investment analysis of this company.",
    help="Custom analysis prompt",
)
@click.option(
    "--filing-type",
    type=click.Choice(["10-K", "10-Q", "8-K"]),
    default="10-K",
    help="Filing type to analyze",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def analyze(
    ctx: click.Context,
    ticker: str,
    deep: bool,
    section: str,
    prompt: str,
    filing_type: str,
    as_json: bool,
) -> None:
    """
    Analyze SEC filings with AI (Gemini).

    Uses context caching for 10x cost reduction on follow-up queries.
    By default uses Flash model (fast/cheap). Use --deep for Pro model.

    \b
    Common sections:
        Item 1    - Business description
        Item 1A   - Risk factors
        Item 7    - Management's Discussion & Analysis (MD&A)
        Item 8    - Financial statements

    \b
    Examples:
        asymmetric analyze AAPL
        asymmetric analyze MSFT --deep
        asymmetric analyze GOOG --section "Item 1A"
        asymmetric analyze AAPL --prompt "What are the key risks?"
    """
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    try:
        # Import here to check dependencies
        from asymmetric.core.ai.gemini_client import GeminiModel, get_gemini_client
        from asymmetric.core.data.edgar_client import EdgarClient

        # Get filing text
        with console.status(f"[bold blue]Fetching {filing_type} for {ticker}...[/bold blue]"):
            edgar = EdgarClient()
            text = edgar.get_filing_text(
                ticker, filing_type=filing_type, section=section
            )

        if not text:
            if section:
                console.print(
                    f"[red]Section '{section}' not found in {ticker} {filing_type}[/red]"
                )
            else:
                console.print(f"[red]No {filing_type} filing found for {ticker}[/red]")
            raise SystemExit(1)

        console.print(f"[dim]Retrieved {len(text):,} characters of text[/dim]")

        # Analyze with Gemini
        model = GeminiModel.PRO if deep else GeminiModel.FLASH
        model_name = "Pro" if deep else "Flash"

        with console.status(f"[bold blue]Analyzing with Gemini {model_name}...[/bold blue]"):
            client = get_gemini_client()
            result = client.analyze_with_cache(
                context=text,
                prompt=prompt,
                model=model,
            )

        # Output results
        if as_json:
            output = {
                "ticker": ticker,
                "filing_type": filing_type,
                "section": section,
                "prompt": prompt,
                "analysis": result.content,
                "model": result.model,
                "cached": result.cached,
                "token_count_input": result.token_count_input,
                "token_count_output": result.token_count_output,
                "estimated_cost_usd": round(result.estimated_cost_usd, 4),
                "latency_ms": result.latency_ms,
            }
            console.print(json.dumps(output, indent=2))
        else:
            _display_analysis(console, ticker, section, result)

    except GeminiConfigError as e:
        console.print(f"[red]Gemini Configuration Error:[/red] {e}")
        console.print("[yellow]Set GEMINI_API_KEY in your .env file.[/yellow]")
        raise SystemExit(1)

    except GeminiContextTooLargeError as e:
        console.print(f"[red]Context Too Large:[/red] {e}")
        console.print("[yellow]Try using --section to analyze a specific section.[/yellow]")
        raise SystemExit(1)

    except GeminiRateLimitError as e:
        console.print(f"[red]Gemini Rate Limit:[/red] {e}")
        console.print("[yellow]Wait a few minutes and try again.[/yellow]")
        raise SystemExit(1)

    except SECIdentityError as e:
        console.print(f"[red]SEC Identity Error:[/red] {e}")
        raise SystemExit(1)

    except SECRateLimitError as e:
        console.print(f"[red]SEC Rate Limit:[/red] {e}")
        raise SystemExit(1)

    except SECEmptyResponseError as e:
        console.print(f"[red]SEC Empty Response:[/red] {e}")
        raise SystemExit(1)

    except AIError as e:
        console.print(f"[red]AI Error:[/red] {e}")
        raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


def _display_analysis(console: Console, ticker: str, section: str, result) -> None:
    """Display analysis results with Rich formatting."""
    console.print()

    # Metadata
    meta_table = Table(show_header=False, box=None, padding=(0, 1))
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value")

    meta_table.add_row("Model", result.model)
    meta_table.add_row("Cached", "[green]Yes[/green]" if result.cached else "[yellow]No[/yellow]")
    meta_table.add_row("Input Tokens", f"{result.token_count_input:,}")
    meta_table.add_row("Output Tokens", f"{result.token_count_output:,}")
    meta_table.add_row("Estimated Cost", f"${result.estimated_cost_usd:.4f}")
    meta_table.add_row("Latency", f"{result.latency_ms:,}ms")

    title = f"AI Analysis: {ticker}"
    if section:
        title += f" ({section})"

    console.print(Panel(meta_table, title="[dim]Analysis Metadata[/dim]", border_style="dim"))
    console.print()

    # Analysis content
    console.print(Panel(
        Markdown(result.content),
        title=title,
        border_style="blue",
    ))

    # Next steps
    print_next_steps(
        console,
        [
            ("Create thesis", f"asymmetric thesis create {ticker} --auto"),
            ("Record decision", f"asymmetric decision create {ticker} --action buy"),
        ],
    )
