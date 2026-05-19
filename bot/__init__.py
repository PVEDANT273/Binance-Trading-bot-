"""
trading_bot.bot
~~~~~~~~~~~~~~~
Core bot package — client, order management, validators, and logging.
"""

from bot.client import BinanceClient
from bot.orders import OrderManager

__all__ = ["BinanceClient", "OrderManager"]
