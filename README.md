# eth-monitor

Monitors a crypto price (CoinGecko) or stock price (Finnhub) and sends a Telegram alert when
the price moves more than a configurable threshold from the last alerted price. Defaults to ETH/USD.

## Features

- Retries on transient network failures
- Atomic baseline file writes (safe on crashes)
- Graceful handling of missing Telegram credentials (warns, does not crash)
- All settings configurable via `.env` or environment variables
- `--test` flag to verify Telegram integration before deploying
- Pluggable price providers: CoinGecko (crypto, any quote currency) and Finnhub (stocks)
- Unit tests for every component, all independently mockable

## Requirements

```
Python 3.10+
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable              | Default                                         | Required          | Description                                               |
|-----------------------|-------------------------------------------------|-------------------|-----------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | none                                            | Yes               | Telegram Bot API token                                    |
| `TELEGRAM_CHAT_ID`    | none                                            | Yes               | Telegram chat/user ID to send alerts to                   |
| `PROVIDER`            | `coingecko`                                     | No                | `coingecko` (crypto) or `finnhub` (stocks)                |
| `ASSET`               | `ethereum`                                      | No                | CoinGecko coin id (`bitcoin`, `solana`) or stock ticker (`AAPL`) |
| `QUOTE_CURRENCY`      | `usd`                                           | No                | CoinGecko vs currency (`usd`, `eur`, `btc`); display only for Finnhub |
| `SYMBOL`              | derived from `ASSET` (`ethereum` gives `ETH`)   | No                | Short name used in alerts                                 |
| `FINNHUB_API_KEY`     | none                                            | With `finnhub`    | Free key from https://finnhub.io                          |
| `THRESHOLD`           | `2.5`                                           | No                | % change from baseline that triggers alert                |
| `BASELINE_FILE`       | `/tmp/<symbol>_last_price`                      | No                | Path to the baseline persistence file                     |
| `DEBUG_LOG`           | `/tmp/eth_monitor_debug.log`                    | No                | Path to the rotating debug log file                       |
| `MAX_RETRIES`         | `3`                                             | No                | Max price-fetch attempts before giving up                 |
| `RETRY_DELAY`         | `2`                                             | No                | Seconds between retry attempts                            |
| `COINGECKO_API_URL`   | `https://api.coingecko.com/api/v3/simple/price` | No                | CoinGecko endpoint (asset and currency are added as query params) |
| `FINNHUB_API_URL`     | `https://finnhub.io/api/v1/quote`               | No                | Finnhub quote endpoint                                    |

Examples:

```bash
# Bitcoin in euros
ASSET=bitcoin QUOTE_CURRENCY=eur python main.py

# Apple stock
PROVIDER=finnhub ASSET=AAPL FINNHUB_API_KEY=... python main.py
```

To watch several assets, schedule one run per asset with different settings. Each asset
gets its own baseline file by default, so they never interfere.

Missing required variables emit a `WARNING` log — the script continues running but
Telegram notifications will be skipped.

## Usage

**Normal run** (fetch price, compare with baseline, alert if needed):

```bash
python main.py
```

**Test Telegram integration** (sends a test message, does not touch the baseline):

```bash
python main.py --test
```

**Scheduled execution** (cron example, every 5 minutes):

```cron
*/5 * * * * /usr/bin/python /path/to/eth-monitor/main.py
```

## Project Structure

```
eth-monitor/
├── eth_monitor/
│   ├── config.py          # Settings dataclass, loaded from .env
│   ├── logger.py          # Logging setup (rotating file + stderr)
│   ├── price_fetcher.py   # Provider clients (CoinGecko, Finnhub) with retries
│   ├── formatting.py      # Pair and currency formatting for alerts
│   ├── baseline.py        # Atomic read/write of baseline file
│   ├── notifier.py        # Telegram alert sender
│   └── monitor.py         # Orchestration: fetch → compare → alert
├── tests/                 # Unit tests (pytest)
├── main.py                # CLI entry point
├── .env.example           # Config template
└── requirements.txt
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Behaviour Notes

- **First run**: no baseline file exists → current price is saved as baseline, no alert sent.
- **Subsequent runs**: if `|change %| >= THRESHOLD`, an alert is sent and the baseline is updated.
  If the alert fails to send, the baseline is left unchanged so the next run retries.
- **Post-reboot** (e.g. `/tmp` cleared): behaves identically to a first run.
- **Stocks**: outside market hours the price does not change, so runs are no-ops. A gap at the
  open shows up as a single alert on the first run after the open.
