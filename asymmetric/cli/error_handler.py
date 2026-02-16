"""Shared CLI error handling decorator.

Eliminates duplicate exception handling across CLI commands by catching
common SEC and AI errors in a single decorator. Commands can still handle
command-specific exceptions internally before the decorator catches the rest.

Usage:
    @click.command()
    @click.pass_context
    @handle_cli_errors
    def my_command(ctx, ...):
        ...
"""

import functools
import logging

import click
from rich.console import Console

from asymmetric.core.data.exceptions import (
    SECEmptyResponseError,
    SECIdentityError,
    SECRateLimitError,
)

logger = logging.getLogger(__name__)


def handle_cli_errors(f):
    """Decorator that catches common CLI exceptions with Rich-formatted output.

    Handles SEC errors (identity, rate limit, empty response) and unexpected
    exceptions with consistent formatting and exit codes.

    Must be applied AFTER @click.pass_context so the first positional arg
    is the Click context (which provides the console via ctx.obj["console"]).
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # Get console from Click context if available
        ctx = click.get_current_context(silent=True)
        console = ctx.obj["console"] if ctx and ctx.obj and "console" in ctx.obj else Console()

        try:
            return f(*args, **kwargs)
        except SystemExit:
            raise  # Don't intercept explicit exits
        except SECIdentityError as e:
            console.print(f"[red]SEC Identity Error:[/red] {e}")
            console.print(
                "[yellow]Set SEC_IDENTITY environment variable to a valid User-Agent string.[/yellow]"
            )
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
        except click.exceptions.Exit:
            raise  # Don't intercept Click exits
        except Exception as e:
            logger.exception("Unexpected error in %s command", f.__name__)
            console.print(f"[red]Unexpected error:[/red] {e}")
            raise SystemExit(1)

    return wrapper
