"""
bot/validators.py
~~~~~~~~~~~~~~~~~
Input validation helpers for order parameters.

All public functions raise `ValueError` with a human-readable message on
failure, so the CLI / caller can display the error without importing
exchange-specific types.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_DOWN
from typing import Optional

# ── Valid enumerations ──────────────────────────────────────────────────────
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


# ── Helpers ─────────────────────────────────────────────────────────────────
def _round_step(value: float, step: str) -> Decimal:
    """Round *value* down to the precision implied by *step* string (e.g. '0.001')."""
    step_dec = Decimal(step)
    val_dec = Decimal(str(value))
    return (val_dec / step_dec).to_integral_value(rounding=ROUND_DOWN) * step_dec


def _count_decimals(step: str) -> int:
    """Return the number of decimal places in a step string."""
    if "." in step:
        return len(step.rstrip("0").split(".")[1])
    return 0


# ── Public validators ────────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """
    Normalise and do a basic sanity check on the trading symbol.

    Rules:
      - Must be a non-empty string
      - Uppercased automatically
      - Must end with 'USDT' (USDT-M futures)
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Symbol must be a non-empty string (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not symbol.endswith("USDT"):
        raise ValueError(
            f"Symbol '{symbol}' does not end with 'USDT'. "
            "Only USDT-M perpetual futures are supported (e.g. BTCUSDT, ETHUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Validate and normalise order side (BUY/SELL)."""
    if not isinstance(side, str):
        raise ValueError("Side must be a string.")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate and normalise order type."""
    if not isinstance(order_type, str):
        raise ValueError("Order type must be a string.")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(
    qty: float,
    symbol_info: Optional[dict] = None,
) -> Decimal:
    """
    Validate quantity against exchange lot-size rules.

    If *symbol_info* is provided (from /fapi/v1/exchangeInfo), the quantity
    is rounded to stepSize and checked against minQty / maxQty.
    Returns a Decimal rounded to the correct precision.
    """
    if qty is None:
        raise ValueError("Quantity is required.")
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity must be a positive number, got: '{qty}'.")

    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0, got: {qty}.")
    if not math.isfinite(qty):
        raise ValueError("Quantity must be a finite number.")

    if symbol_info is None:
        return Decimal(str(qty))

    # Extract LOT_SIZE filter
    lot_filter = _get_filter(symbol_info, "LOT_SIZE")
    if lot_filter:
        min_qty = float(lot_filter["minQty"])
        max_qty = float(lot_filter["maxQty"])
        step_size = lot_filter["stepSize"]

        if qty < min_qty:
            raise ValueError(
                f"Quantity {qty} is below the minimum allowed ({min_qty})."
            )
        if qty > max_qty:
            raise ValueError(
                f"Quantity {qty} exceeds the maximum allowed ({max_qty})."
            )

        rounded = _round_step(qty, step_size)
        decimals = _count_decimals(step_size)
        return rounded.quantize(Decimal(10) ** -decimals)

    return Decimal(str(qty))


def validate_price(
    price: Optional[float],
    order_type: str,
    symbol_info: Optional[dict] = None,
) -> Optional[Decimal]:
    """
    Validate limit price.

    - Required when order_type is LIMIT.
    - Rounded to the exchange tickSize.
    - Returns None for MARKET orders.
    """
    if order_type == "MARKET":
        return None  # price is ignored for market orders

    if order_type in ("LIMIT",) and price is None:
        raise ValueError("Price is required for LIMIT orders.")

    if price is None:
        return None

    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValueError(f"Price must be a positive number, got: '{price}'.")

    if price <= 0:
        raise ValueError(f"Price must be greater than 0, got: {price}.")
    if not math.isfinite(price):
        raise ValueError("Price must be a finite number.")

    if symbol_info is None:
        return Decimal(str(price))

    # Extract PRICE_FILTER
    price_filter = _get_filter(symbol_info, "PRICE_FILTER")
    if price_filter:
        min_price = float(price_filter["minPrice"])
        max_price = float(price_filter["maxPrice"])
        tick_size = price_filter["tickSize"]

        if price < min_price:
            raise ValueError(
                f"Price {price} is below the minimum allowed ({min_price})."
            )
        if max_price > 0 and price > max_price:
            raise ValueError(
                f"Price {price} exceeds the maximum allowed ({max_price})."
            )

        rounded = _round_step(price, tick_size)
        decimals = _count_decimals(tick_size)
        return rounded.quantize(Decimal(10) ** -decimals)

    return Decimal(str(price))


def validate_stop_price(
    stop_price: Optional[float],
    order_type: str,
    symbol_info: Optional[dict] = None,
) -> Optional[Decimal]:
    """
    Validate stop trigger price.

    Required when order_type is STOP_MARKET.
    """
    if order_type != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValueError("Stop price (--stop) is required for STOP_MARKET orders.")

    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValueError(f"Stop price must be a positive number, got: '{stop_price}'.")

    if stop_price <= 0:
        raise ValueError(f"Stop price must be greater than 0, got: {stop_price}.")

    if symbol_info is None:
        return Decimal(str(stop_price))

    price_filter = _get_filter(symbol_info, "PRICE_FILTER")
    if price_filter:
        tick_size = price_filter["tickSize"]
        rounded = _round_step(stop_price, tick_size)
        decimals = _count_decimals(tick_size)
        return rounded.quantize(Decimal(10) ** -decimals)

    return Decimal(str(stop_price))


# ── Internal utility ─────────────────────────────────────────────────────────

def _get_filter(symbol_info: dict, filter_type: str) -> Optional[dict]:
    """Extract a specific filter dict from symbol_info['filters']."""
    for f in symbol_info.get("filters", []):
        if f.get("filterType") == filter_type:
            return f
    return None
