from bot.client import BinanceClient

client = BinanceClient()

# print(client.get_server_time())



data = client.get_account_info()
print(data)