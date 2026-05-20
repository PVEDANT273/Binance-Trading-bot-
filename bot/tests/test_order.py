from bot.client import BinanceClient
from bot.orders import OrderManager

client = BinanceClient()

manager = OrderManager(client)

response = manager.place_order(
    symbol="BTCUSDT",
    side="BUY",
    order_type="MARKET",
    quantity=0.001
)

print(response)