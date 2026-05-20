import httpx

BASE_URL = "https://testnet.binancefuture.com"

response = httpx.get(f"{BASE_URL}/fapi/v1/ping")

print(response.status_code)
print(response.text)