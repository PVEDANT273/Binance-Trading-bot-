"""
bot/client.py
~~~~~~~~~~~~~
Low-level HMAC-SHA256 signed REST client for the Binance Futures Testnet.

Responsibilities
----------------
- Load credentials from environment / .env
- Sign every authenticated request with HMAC-SHA256
- Handle HTTP-level errors and wrap them in typed exceptions
- Expose thin get() / post() helpers plus convenience endpoints
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from bot.logging_config import get_logger

load_dotenv()

log = get_logger(__name__)

# ── Custom exceptions ────────────────────────────────────────────────────────

class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error code."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[Binance API {code}] {message}")


class NetworkError(Exception):
    """Raised on connection timeouts or DNS failures."""


# ── Client ───────────────────────────────────────────────────────────────────

class BinanceClient:
    """
    Authenticated httpx wrapper for Binance Futures USDT-M REST API.

    Usage
    -----
    >>> client = BinanceClient()
    >>> client.ping()
    >>> info = client.get_exchange_info("BTCUSDT")
    """

    DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
    TIMEOUT = 10.0  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
        self._base_url = (
            base_url
            or os.environ.get("BINANCE_BASE_URL", self.DEFAULT_BASE_URL)
        ).rstrip("/")

        if not self._api_key or not self._api_secret:
            raise EnvironmentError(
                "BINANCE_API_KEY and BINANCE_API_SECRET must be set "
                "(copy .env.example → .env and fill in your testnet credentials)."
            )

        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=self.TIMEOUT,
            headers={
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        log.debug("BinanceClient initialised | base_url=%s", self._base_url)

    # ── Signing ──────────────────────────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        """Add timestamp + HMAC-SHA256 signature to *params* dict (in-place + return)."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    # ── Low-level HTTP helpers ────────────────────────────────────────────────

    def _handle_response(self, response: httpx.Response) -> Any:
        """Parse JSON and raise BinanceAPIError on non-2xx or API error body."""
        log.debug(
            "HTTP %s %s → %d | body=%s",
            response.request.method,
            response.request.url,
            response.status_code,
            response.text[:500],
        )
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            return response.text

        # Binance returns {"code": <negative int>, "msg": "..."} for API errors
        if isinstance(data, dict) and data.get("code", 0) < 0:
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        if response.status_code >= 400:
            raise BinanceAPIError(response.status_code, str(data))

        return data

    def get(self, endpoint: str, params: Optional[dict] = None, signed: bool = True) -> Any:
        """Send a signed GET request."""
        params = params or {}
        if signed:
            self._sign(params)
        log.debug("GET %s | params=%s", endpoint, {k: v for k, v in params.items() if k != "signature"})
        try:
            resp = self._http.get(endpoint, params=params)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error: {exc}") from exc
        return self._handle_response(resp)

    def post(self, endpoint: str, data: Optional[dict] = None, signed: bool = True) -> Any:
        """Send a signed POST request."""
        data = data or {}
        if signed:
            self._sign(data)
        log.debug("POST %s | data=%s", endpoint, {k: v for k, v in data.items() if k != "signature"})
        try:
            resp = self._http.post(endpoint, data=data)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error: {exc}") from exc
        return self._handle_response(resp)

    # ── Convenience endpoints ─────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if the exchange is reachable."""
        try:
            self._http.get("/fapi/v1/ping")
            log.debug("Ping successful")
            return True
        except Exception as exc:
            log.warning("Ping failed: %s", exc)
            return False

    def get_server_time(self) -> int:
        """Return exchange server time in milliseconds."""
        data = self.get("/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_exchange_info(self, symbol: str) -> dict:
        """
        Fetch symbol metadata including filters (LOT_SIZE, PRICE_FILTER, etc.).

        Returns the first matching symbol dict from exchangeInfo.
        """
        data = self.get("/fapi/v1/exchangeInfo", params={}, signed=False)
        for s in data.get("symbols", []):
            if s["symbol"] == symbol:
                log.debug("exchange info fetched for %s", symbol)
                return s
        raise BinanceAPIError(-1, f"Symbol '{symbol}' not found on Binance Futures Testnet.")

    def close(self) -> None:
        """Close the underlying httpx session."""
        self._http.close()

    # Context-manager support
    def __enter__(self) -> "BinanceClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
