"""
bot/orders.py
~~~~~~~~~~~~~
Order placement business logic for Binance Futures USDT-M Testnet.

This module sits between the CLI layer and the raw HTTP client.
It validates inputs (using validators.py), builds the correct API
payload, calls the client, and returns a clean normalised response.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from bot.client import BinanceClient, BinanceAPIError, NetworkError
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)
from bot.logging_config import get_logger

log = get_logger(__name__)

ORDER_ENDPOINT = "/fapi/v1/order"


class OrderManager:
    """
    High-level interface for placing Binance Futures orders.

    Parameters
    ----------
    client : BinanceClient
        Authenticated REST client instance.
    dry_run : bool
        If True, validate everything but do NOT send the order.
    """

    def __init__(self, client: BinanceClient, dry_run: bool = False) -> None:
        self._client = client
        self._dry_run = dry_run

    #Public API        
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> dict:
        """
        Validate inputs, build the payload, place the order and return a
        normalised response dict.

        Raises
        ------
        ValueError
            On invalid user input (symbol, side, qty, price, etc.)
        BinanceAPIError
            On exchange-level rejection.
        NetworkError
            On connectivity problems.
        """
        #Validate & normalise inputs                                 
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_order_type(order_type)

        # Fetch exchange constraints (best-effort; skip on network error)
        symbol_info: Optional[dict] = None
        try:
            symbol_info = self._client.get_exchange_info(symbol)
        except (BinanceAPIError, NetworkError) as exc:
            log.warning(
                "Could not fetch exchange info for %s (%s). "
                "Skipping server-side filter validation.",
                symbol, exc,
            )

        qty_dec: Decimal = validate_quantity(quantity, symbol_info)
        price_dec: Optional[Decimal] = validate_price(price, order_type, symbol_info)
        stop_dec: Optional[Decimal] = validate_stop_price(stop_price, order_type, symbol_info)

        #Build payload                                               
        payload: dict = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(qty_dec),
        }

        if order_type == "LIMIT":
            payload["price"] = str(price_dec)
            payload["timeInForce"] = "GTC"  # Good-Till-Cancelled

        if order_type == "STOP_MARKET":
            payload["stopPrice"] = str(stop_dec)

        log.info(
            "Order request | symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s dry_run=%s",
            symbol, side, order_type, qty_dec, price_dec, stop_dec, self._dry_run,
        )

        #Dry-run short-circuit                                       
        if self._dry_run:
            log.info("DRY RUN — order not sent. Payload: %s", payload)
            return {
                "dry_run": True,
                "payload": payload,
                "orderId": None,
                "status": "DRY_RUN",
                "executedQty": "0",
                "avgPrice": "0",
            }

        #Send order                                                 
        try:
            raw = self._client.post(ORDER_ENDPOINT, data=payload)
        except BinanceAPIError:
            log.exception("API rejected the order | payload=%s", payload)
            raise
        except NetworkError:
            log.exception("Network error while placing order | payload=%s", payload)
            raise

        log.info("Order response | %s", raw)
        return self._normalise(raw)

    #Internal helpers  
    @staticmethod
    def _normalise(raw: dict) -> dict:
        """
        Extract and return the key fields from the raw Binance response.

        Always returns the same keys regardless of order type so callers
        don't need to branch on response shape.
        """
        return {
            "orderId":     raw.get("orderId"),
            "symbol":      raw.get("symbol"),
            "side":        raw.get("side"),
            "type":        raw.get("type"),
            "status":      raw.get("status"),
            "executedQty": raw.get("executedQty", "0"),
            "avgPrice":    raw.get("avgPrice") or raw.get("price", "0"),
            "origQty":     raw.get("origQty", "0"),
            "timeInForce": raw.get("timeInForce", "—"),
            "updateTime":  raw.get("updateTime"),
            "_raw":        raw,   # keep full response for logging / debugging
        }
