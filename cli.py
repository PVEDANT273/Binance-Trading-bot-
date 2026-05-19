"""
cli.py
~~~~~~
Typer-powered CLI entry point for the Binance Futures Testnet Trading Bot.

Two commands:
  place-order   — single order via flags (scriptable / CI friendly)
  interactive   — guided interactive mode with rich menus & confirmation

Usage:
  python cli.py --help
  python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
  python cli.py interactive
"""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from rich import box

from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceClient, BinanceAPIError, NetworkError
from bot.orders import OrderManager
from bot.validators import VALID_SIDES, VALID_ORDER_TYPES

# ── Bootstrap logging before anything else ───────────────────────────────────
setup_logging()
log = get_logger(__name__)

# ── Typer app ─────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="trading-bot",
    help="[bold cyan]Binance Futures Testnet[/bold cyan] — simple order placer",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

# ── Shared display helpers ────────────────────────────────────────────────────

def _print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    qty: float,
    price: Optional[float],
    stop_price: Optional[float],
    dry_run: bool,
) -> None:
    """Print a rich panel summarising the order about to be placed."""
    side_color = "green" if side.upper() == "BUY" else "red"
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("Field", style="bold dim", no_wrap=True)
    t.add_column("Value", style="white")

    t.add_row("Symbol",     f"[bold]{symbol}[/bold]")
    t.add_row("Side",       f"[bold {side_color}]{side}[/bold {side_color}]")
    t.add_row("Type",       order_type)
    t.add_row("Quantity",   str(qty))
    if price is not None:
        t.add_row("Price",  str(price))
    if stop_price is not None:
        t.add_row("Stop",   str(stop_price))
    if dry_run:
        t.add_row("Mode",   "[yellow bold]DRY RUN — order will NOT be sent[/yellow bold]")

    console.print(
        Panel(t, title="[bold blue]📋 Order Request[/bold blue]", border_style="blue")
    )


def _print_response(result: dict) -> None:
    """Print a rich panel with the exchange response."""
    if result.get("dry_run"):
        console.print(
            Panel(
                "[yellow]Dry-run complete — no order was sent to the exchange.[/yellow]\n"
                f"[dim]Payload: {result['payload']}[/dim]",
                title="[bold yellow]🔍 Dry Run Result[/bold yellow]",
                border_style="yellow",
            )
        )
        return

    status = result.get("status", "UNKNOWN")
    status_color = "green" if status in ("FILLED", "NEW", "PARTIALLY_FILLED") else "red"

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("Field", style="bold dim", no_wrap=True)
    t.add_column("Value", style="white")

    t.add_row("Order ID",     str(result.get("orderId", "—")))
    t.add_row("Symbol",       str(result.get("symbol", "—")))
    t.add_row("Side",         str(result.get("side", "—")))
    t.add_row("Type",         str(result.get("type", "—")))
    t.add_row(
        "Status",
        f"[bold {status_color}]{status}[/bold {status_color}]",
    )
    t.add_row("Executed Qty", str(result.get("executedQty", "0")))
    t.add_row("Avg Price",    str(result.get("avgPrice", "0")))
    t.add_row("Orig Qty",     str(result.get("origQty", "0")))

    console.print(
        Panel(t, title="[bold green]✅ Exchange Response[/bold green]", border_style="green")
    )


def _run_order(
    symbol: str,
    side: str,
    order_type: str,
    qty: float,
    price: Optional[float],
    stop_price: Optional[float],
    dry_run: bool,
) -> None:
    """Common execution path for both CLI commands."""
    _print_request_summary(symbol, side, order_type, qty, price, stop_price, dry_run)

    try:
        with BinanceClient() as client:
            manager = OrderManager(client, dry_run=dry_run)
            result = manager.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=qty,
                price=price,
                stop_price=stop_price,
            )
    except EnvironmentError as exc:
        console.print(f"\n[bold red]❌ Configuration error:[/bold red] {exc}")
        log.error("Configuration error: %s", exc)
        raise typer.Exit(code=1)
    except ValueError as exc:
        console.print(f"\n[bold red]❌ Validation error:[/bold red] {exc}")
        log.error("Validation error: %s", exc)
        raise typer.Exit(code=1)
    except BinanceAPIError as exc:
        console.print(f"\n[bold red]❌ Binance API error [{exc.code}]:[/bold red] {exc.message}")
        log.error("BinanceAPIError code=%s message=%s", exc.code, exc.message)
        raise typer.Exit(code=1)
    except NetworkError as exc:
        console.print(f"\n[bold red]❌ Network error:[/bold red] {exc}")
        log.error("NetworkError: %s", exc)
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"\n[bold red]❌ Unexpected error:[/bold red] {exc}")
        log.exception("Unexpected error during order placement")
        raise typer.Exit(code=1)

    _print_response(result)

    if not result.get("dry_run"):
        console.print(
            "\n[bold green]🎉 Order placed successfully![/bold green]"
        )
        log.info("Order placed successfully. orderId=%s", result.get("orderId"))


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("place-order")
def place_order(
    symbol: str = typer.Option(
        ..., "--symbol", "-s",
        help="Trading pair, e.g. [bold]BTCUSDT[/bold]",
        show_default=False,
    ),
    side: str = typer.Option(
        ..., "--side",
        help="Order side: [green]BUY[/green] or [red]SELL[/red]",
        show_default=False,
    ),
    order_type: str = typer.Option(
        ..., "--type", "-t",
        help="Order type: MARKET | LIMIT | STOP_MARKET",
        show_default=False,
    ),
    qty: float = typer.Option(
        ..., "--qty", "-q",
        help="Order quantity (base asset)",
        show_default=False,
    ),
    price: Optional[float] = typer.Option(
        None, "--price", "-p",
        help="Limit price (required for LIMIT orders)",
    ),
    stop_price: Optional[float] = typer.Option(
        None, "--stop",
        help="Stop trigger price (required for STOP_MARKET orders)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Validate and preview without sending to exchange",
        is_flag=True,
    ),
) -> None:
    """
    Place a [bold]single order[/bold] on Binance Futures Testnet via command-line flags.

    Examples:

      [dim]# Market BUY[/dim]
      python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

      [dim]# Limit SELL[/dim]
      python cli.py place-order --symbol ETHUSDT --side SELL --type LIMIT --qty 0.01 --price 4000

      [dim]# Stop-Market SELL (bonus)[/dim]
      python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop 60000

      [dim]# Dry run (no order sent)[/dim]
      python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 --dry-run
    """
    _run_order(
        symbol=symbol.upper(),
        side=side.upper(),
        order_type=order_type.upper(),
        qty=qty,
        price=price,
        stop_price=stop_price,
        dry_run=dry_run,
    )


@app.command("interactive")
def interactive() -> None:
    """
    Launch [bold cyan]guided interactive mode[/bold cyan] — step-by-step prompts with validation.

    Great for exploring the bot without memorising flags.
    """
    console.rule("[bold cyan]🤖 Binance Futures Testnet — Interactive Order Placer[/bold cyan]")
    console.print()

    # ── Symbol ────────────────────────────────────────────────────────────
    while True:
        symbol = Prompt.ask(
            "[bold]Symbol[/bold] (e.g. BTCUSDT, ETHUSDT)",
            default="BTCUSDT",
        ).strip().upper()
        if symbol.endswith("USDT") and len(symbol) >= 5:
            break
        console.print("[red]  ✗ Symbol must end with USDT (e.g. BTCUSDT).[/red]")

    # ── Side ──────────────────────────────────────────────────────────────
    while True:
        side = Prompt.ask(
            "[bold]Side[/bold]",
            choices=["BUY", "SELL"],
            default="BUY",
        ).strip().upper()
        if side in VALID_SIDES:
            break

    # ── Order type ────────────────────────────────────────────────────────
    console.print()
    console.print("[bold]Order types available:[/bold]")
    console.print("  [cyan]1[/cyan] — MARKET       (execute immediately at best price)")
    console.print("  [cyan]2[/cyan] — LIMIT         (execute at a specific price or better)")
    console.print("  [cyan]3[/cyan] — STOP_MARKET   (trigger a market order at a stop price)")
    console.print()

    type_map = {"1": "MARKET", "2": "LIMIT", "3": "STOP_MARKET"}
    while True:
        choice = Prompt.ask(
            "[bold]Choose order type[/bold]",
            choices=["1", "2", "3"],
            default="1",
        )
        order_type = type_map[choice]
        break

    # ── Quantity ──────────────────────────────────────────────────────────
    while True:
        try:
            qty = float(Prompt.ask("[bold]Quantity[/bold] (base asset, e.g. 0.001)"))
            if qty > 0:
                break
            console.print("[red]  ✗ Quantity must be greater than 0.[/red]")
        except ValueError:
            console.print("[red]  ✗ Please enter a valid number.[/red]")

    # ── Price (LIMIT only) ────────────────────────────────────────────────
    price: Optional[float] = None
    if order_type == "LIMIT":
        while True:
            try:
                price = float(Prompt.ask("[bold]Limit price[/bold] (USDT)"))
                if price > 0:
                    break
                console.print("[red]  ✗ Price must be greater than 0.[/red]")
            except ValueError:
                console.print("[red]  ✗ Please enter a valid number.[/red]")

    # ── Stop price (STOP_MARKET only) ─────────────────────────────────────
    stop_price: Optional[float] = None
    if order_type == "STOP_MARKET":
        while True:
            try:
                stop_price = float(Prompt.ask("[bold]Stop trigger price[/bold] (USDT)"))
                if stop_price > 0:
                    break
                console.print("[red]  ✗ Stop price must be greater than 0.[/red]")
            except ValueError:
                console.print("[red]  ✗ Please enter a valid number.[/red]")

    # ── Dry-run option ────────────────────────────────────────────────────
    dry_run = Confirm.ask(
        "\n[yellow]Dry run?[/yellow] (preview without sending to exchange)",
        default=False,
    )

    console.print()

    # ── Confirmation table ────────────────────────────────────────────────
    _print_request_summary(symbol, side, order_type, qty, price, stop_price, dry_run)

    confirmed = Confirm.ask(
        "[bold]Send this order?[/bold]",
        default=True,
    )

    if not confirmed:
        console.print("[yellow]Order cancelled.[/yellow]")
        log.info("User cancelled order in interactive mode.")
        raise typer.Exit()

    console.print()
    _run_order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        qty=qty,
        price=price,
        stop_price=stop_price,
        dry_run=dry_run,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
