"""Company lookup command."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from asymmetric.cli.formatting import print_next_steps
from asymmetric.core.data.edgar_client import EdgarClient
from asymmetric.core.data.exceptions import (
    SECEmptyResponseError,
    SECIdentityError,
    SECRateLimitError,
)


@click.command()
@click.argument("ticker")
@click.option("--full", is_flag=True, help="Show full company details including recent filings")
@click.pass_context
def lookup(ctx: click.Context, ticker: str, full: bool) -> None:
    """
    Look up company information by ticker symbol.

    Retrieves company metadata from SEC EDGAR including CIK,
    company name, and optionally recent filing information.

    \b
    Examples:
        asymmetric lookup AAPL
        asymmetric lookup MSFT --full
    """
    console: Console = ctx.obj["console"]
    ticker = ticker.upper()

    try:
        with console.status(f"[bold blue]Looking up {ticker}...[/bold blue]"):
            client = EdgarClient()
            company = client.get_company(ticker)

        if not company:
            console.print(f"[red]Company not found: {ticker}[/red]")
            raise SystemExit(1)

        # Build output table
        table = Table(
            title=f"[bold]{company.name}[/bold]",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Field", style="cyan", width=20)
        table.add_column("Value", style="green")

        # Basic info
        table.add_row("Ticker", ticker)
        table.add_row("CIK", str(company.cik))
        table.add_row("Name", company.name)

        # Try to get additional attributes if available
        if hasattr(company, "sic") and company.sic:
            table.add_row("SIC Code", str(company.sic))
        if hasattr(company, "sic_description") and company.sic_description:
            table.add_row("Industry", company.sic_description)
        if hasattr(company, "state_of_incorporation") and company.state_of_incorporation:
            table.add_row("State", company.state_of_incorporation)

        if full:
            # Get recent filings info
            table.add_section()
            table.add_row("[bold]Recent Filings[/bold]", "")

            try:
                filings = company.get_filings(form=["10-K", "10-Q"]).head(5)
                for filing in filings:
                    form = getattr(filing, "form", "N/A")
                    filed = getattr(filing, "filing_date", "N/A")
                    table.add_row(f"  {form}", str(filed))
            except Exception:
                table.add_row("  [dim]Unable to fetch filings[/dim]", "")

        console.print(table)

        # Next steps
        print_next_steps(
            console,
            [
                ("Calculate scores", f"asymmetric score {ticker}"),
                ("AI analysis", f"asymmetric analyze {ticker}"),
            ],
        )

    except SECIdentityError as e:
        console.print(f"[red]SEC Identity Error:[/red] {e}")
        console.print("[yellow]Set SEC_IDENTITY environment variable to a valid User-Agent string.[/yellow]")
        console.print("[dim]Example: SEC_IDENTITY='Asymmetric/1.0 (your@email.com)'[/dim]")
        raise SystemExit(1)

    except SECRateLimitError as e:
        console.print(f"[red]SEC Rate Limit Hit:[/red] {e}")
        console.print("[yellow]Wait a few minutes and try again.[/yellow]")
        raise SystemExit(1)

    except SECEmptyResponseError as e:
        console.print(f"[red]SEC Empty Response:[/red] {e}")
        console.print("[yellow]The SEC may be throttling requests. Wait a few minutes.[/yellow]")
        raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
