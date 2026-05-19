# 🤖 Binance Futures Testnet Trading Bot

A clean, production-quality Python CLI bot for placing orders on the **Binance Futures USDT-M Testnet**.  
Built with direct REST calls (no SDK), HMAC-signed requests, structured logging, and a rich interactive CLI.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Order Types** | MARKET, LIMIT, STOP_MARKET (bonus) |
| **Sides** | BUY and SELL |
| **CLI Modes** | Flag-based (`place-order`) + guided interactive (`interactive`) |
| **Logging** | Rotating log file (`logs/trading_bot.log`) + colour console |
| **Validation** | Symbol, side, type, quantity, price, stop price — respects exchange filters |
| **Dry Run** | Preview & validate orders without sending to the exchange |
| **Error Handling** | Typed exceptions for API errors, network failures, invalid input |

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # HMAC-signed REST client (BinanceClient)
│   ├── orders.py            # Order placement logic (OrderManager)
│   ├── validators.py        # Input validation helpers
│   └── logging_config.py   # Rotating file + Rich console logging
├── cli.py                   # Typer CLI entry point
├── logs/
│   ├── trading_bot.log      # Live rotating log (auto-created)
│   ├── market_order.log     # Sample MARKET order log
│   └── limit_order.log      # Sample LIMIT order log
├── .env.example             # Credential template
├── .env                     # Your credentials (git-ignored)
├── .gitignore
├── README.md
└── requirements.txt
```

---

## ⚙️ Setup

### 1 — Get Testnet Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in with GitHub (no KYC required)
3. Navigate to **API Management** → generate a new API key
4. Copy your **API Key** and **Secret Key**

### 2 — Clone & Install

```bash
# Clone the repo
git clone <your-repo-url>
cd trading_bot

# Create and activate a virtual environment (recommended)
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3 — Configure Credentials

```bash
# Copy the template
copy .env.example .env      # Windows
cp .env.example .env        # macOS/Linux
```

Open `.env` and fill in your keys:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

> ⚠️ **Never commit `.env` to version control.** It is already in `.gitignore`.

---

## 🚀 How to Run

### Command: `place-order` (flag-based)

```bash
python cli.py place-order --help
```

```
 --symbol  -s    TEXT   Trading pair, e.g. BTCUSDT       [required]
 --side          TEXT   BUY or SELL                       [required]
 --type    -t    TEXT   MARKET | LIMIT | STOP_MARKET      [required]
 --qty     -q    FLOAT  Quantity (base asset)             [required]
 --price   -p    FLOAT  Limit price (LIMIT orders only)
 --stop          FLOAT  Stop trigger price (STOP_MARKET)
 --dry-run       FLAG   Validate without sending
```

#### Examples

```bash
# MARKET BUY — buy 0.001 BTC at best available price
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# LIMIT SELL — sell 0.01 ETH when price reaches 4000 USDT
python cli.py place-order --symbol ETHUSDT --side SELL --type LIMIT --qty 0.01 --price 4000

# STOP_MARKET SELL — trigger a market sell if BTC drops to 60000 (bonus)
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop 60000

# Dry run — validate everything without sending to the exchange
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 --dry-run
```

### Command: `interactive` (guided menus)

```bash
python cli.py interactive
```

Walks you through symbol → side → type → quantity → price → confirmation step by step, with colour-coded prompts and a preview table before sending.

---

## 📊 Sample Output

### MARKET Order

```
╭──────────── 📋 Order Request ─────────────╮
│  Symbol      BTCUSDT                      │
│  Side        BUY                          │
│  Type        MARKET                       │
│  Quantity    0.001                        │
╰───────────────────────────────────────────╯

╭──────────── ✅ Exchange Response ──────────╮
│  Order ID    3427651982                   │
│  Symbol      BTCUSDT                      │
│  Side        BUY                          │
│  Type        MARKET                       │
│  Status      FILLED                       │
│  Executed    0.001                        │
│  Avg Price   67423.50                     │
╰───────────────────────────────────────────╯

🎉 Order placed successfully!
```

---

## 📝 Logging

All activity is logged to `logs/trading_bot.log` in this format:

```
2026-05-19T12:00:01 | DEBUG    | bot.client | GET /fapi/v1/exchangeInfo | params={symbol: BTCUSDT}
2026-05-19T12:00:02 | INFO     | bot.orders | Order request | symbol=BTCUSDT side=BUY type=MARKET qty=0.001
2026-05-19T12:00:02 | DEBUG    | bot.client | HTTP POST /fapi/v1/order → 200 | body={...}
2026-05-19T12:00:02 | INFO     | bot.orders | Order response | {orderId: 123, status: FILLED, ...}
```

The log file rotates automatically at **5 MB** and keeps **3 backups**.

---

## 🔧 Assumptions & Limitations

1. **Testnet only** — the `BINANCE_BASE_URL` defaults to `https://testnet.binancefuture.com`. Change it in `.env` for mainnet (not recommended for automated bots without extensive testing).
2. **USDT-M Perpetuals only** — all symbols must end with `USDT`.
3. **No position management** — the bot only places orders; it does not track open positions or PnL.
4. **GTC time-in-force** — LIMIT orders are placed as Good-Till-Cancelled.
5. **Clock sync** — Binance requires the request timestamp to be within 5 seconds of server time. If you see `-1021` errors, check your system clock.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `httpx` | Async-capable HTTP client for REST calls |
| `typer[all]` | CLI framework with auto-help and type checking |
| `rich` | Colour terminal output, panels, tables |
| `python-dotenv` | Load `.env` credentials at runtime |

Install all with:
```bash
pip install -r requirements.txt
```

---

## 🐛 Troubleshooting

| Error | Fix |
|---|---|
| `EnvironmentError: BINANCE_API_KEY...` | Copy `.env.example` → `.env` and fill in credentials |
| `BinanceAPIError [-1021]` | System clock out of sync — sync your OS clock |
| `BinanceAPIError [-2019]` | Margin insufficient — add funds on the testnet dashboard |
| `BinanceAPIError [-1111]` | Quantity precision wrong — use a smaller decimal (e.g. `0.001` not `0.0001`) |
| `NetworkError: Request timed out` | Check internet connection or testnet status |
