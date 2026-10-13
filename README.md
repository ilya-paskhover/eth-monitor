# eth-monitor

Monitors a crypto price (CoinGecko) or a stock / FX price (Yahoo Finance or Finnhub) and sends a Telegram alert when
the price moves more than a configurable threshold from the last alerted price. Defaults to ETH/USD.

## Features

- Retries on transient network failures
- Atomic baseline file writes (safe on crashes)
- Graceful handling of missing Telegram credentials (warns, does not crash)
- All settings configurable via `.env` or environment variables
- `--test` flag to verify Telegram integration before deploying
- Pluggable price providers: CoinGecko (crypto), Yahoo Finance (stocks, FX, no key) and Finnhub (US stocks, free key)
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
| `PROVIDER`            | auto: `yahoo` for tickers, else `coingecko`     | No                | `coingecko` (crypto), `yahoo` or `finnhub` (stocks); see [Price providers](#price-providers) |
| `ASSET`               | `ethereum`                                      | No                | CoinGecko coin id (`bitcoin`), Yahoo symbol (`AAPL`, `SAP.DE`, `EURUSD=X`) or Finnhub ticker (`AAPL`) |
| `QUOTE_CURRENCY`      | `usd`                                           | No                | CoinGecko vs currency (`usd`, `eur`, `btc`); display only for Yahoo and Finnhub (set it to the listing's currency) |
| `SYMBOL`              | derived from `ASSET` (`ethereum` gives `ETH`)   | No                | Short name used in alerts                                 |
| `FINNHUB_API_KEY`     | none                                            | With `finnhub`    | Free key from https://finnhub.io                          |
| `THRESHOLD`           | `2.5`                                           | No                | % change from baseline that triggers alert                |
| `BASELINE_FILE`       | `/tmp/<symbol>_last_price`                      | No                | Path to the baseline persistence file                     |
| `DEBUG_LOG`           | `/tmp/eth_monitor_debug.log`                    | No                | Path to the rotating debug log file                       |
| `MAX_RETRIES`         | `3`                                             | No                | Max price-fetch attempts before giving up                 |
| `RETRY_DELAY`         | `2`                                             | No                | Seconds between retry attempts                            |
| `COINGECKO_API_URL`   | `https://api.coingecko.com/api/v3/simple/price` | No                | CoinGecko endpoint (asset and currency are added as query params) |
| `FINNHUB_API_URL`     | `https://finnhub.io/api/v1/quote`               | No                | Finnhub quote endpoint                                    |
| `YAHOO_API_URL`       | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | No   | Yahoo chart endpoint (`{symbol}` is replaced by `ASSET`)   |

Examples:

```bash
# Bitcoin in euros
ASSET=bitcoin QUOTE_CURRENCY=eur python main.py

# Apple stock (Yahoo is picked automatically, no API key)
ASSET=AAPL python main.py

# SAP on Xetra, priced in euros
ASSET=SAP.DE QUOTE_CURRENCY=eur SYMBOL=SAP python main.py

# EUR/USD exchange rate
ASSET=EURUSD=X SYMBOL=EUR QUOTE_CURRENCY=usd THRESHOLD=0.5 python main.py

# Apple stock via Finnhub instead (official API, free key)
PROVIDER=finnhub ASSET=AAPL FINNHUB_API_KEY=... python main.py
```

To watch several assets, schedule one run per asset with different settings. Each asset
gets its own baseline file by default, so they never interfere.

### Monitoring a stock (Yahoo, no API key)

Put this in `.env` (Telegram settings as usual):

```bash
ASSET=AAPL
THRESHOLD=2.5
```

Check it once by hand, then schedule it. The first run only records the baseline;
later runs alert when the price moves `THRESHOLD`% from it:

```bash
python main.py
```

For a non-US listing, set `QUOTE_CURRENCY` to the listing's currency so alerts show the
right sign (the monitor logs a warning if they differ), and optionally a short `SYMBOL`:

```bash
ASSET=SAP.DE
QUOTE_CURRENCY=eur
SYMBOL=SAP
```

Yahoo symbols: US tickers as-is (`AAPL`, `MSFT`), other exchanges with a suffix
(`SAP.DE` Xetra, `VOD.L` London, `7203.T` Tokyo), FX as `EURUSD=X`, crypto as `BTC-USD`.
Look up a symbol on finance.yahoo.com if unsure.

### Price providers

If `PROVIDER` is not set, it is picked from `ASSET`: a ticker with upper-case letters
(`AAPL`, `SAP.DE`, `EURUSD=X`) uses **Yahoo**, a lower-case CoinGecko id (`ethereum`,
`bitcoin`) uses **CoinGecko**. So stocks only need `ASSET`. Write tickers in upper case,
and set `PROVIDER` explicitly to override (for example `PROVIDER=finnhub`).

| Provider    | Covers                                   | Key           | Notes |
|-------------|------------------------------------------|---------------|-------|
| `coingecko` | Crypto in any CoinGecko vs currency      | No            | Default. Official public API with rate limits. |
| `yahoo`     | Stocks worldwide, FX (`EURUSD=X`), crypto (`BTC-USD`) | No | **Unofficial** endpoint. It can change, rate-limit or start requiring cookies without notice, and Yahoo's terms allow personal use only. |
| `finnhub`   | US stocks                                | Yes, free     | Official, documented API. Use it if Yahoo breaks or for anything beyond personal use. |

**Using Finnhub**

1. Sign up at https://finnhub.io/register and copy the API key from the dashboard.
2. Set `PROVIDER=finnhub`, `ASSET=<ticker>` and `FINNHUB_API_KEY=<key>` in `.env`.
3. The free tier has a per-minute call limit that is far above what a cron job every few minutes
   needs; check https://finnhub.io/pricing for current limits and which exchanges are included.
4. The key is sent in the `X-Finnhub-Token` header, so it never appears in logged URLs.
5. Unknown tickers come back as all zeros; the monitor treats that as a fetch error, not a price of 0.

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

Several assets, each with its own baseline file (the stock only on weekdays; cron uses the
machine's local time, so add an hour range matching the exchange's session if you want one):

```cron
*/5 * * * *   cd /path/to/eth-monitor && /usr/bin/python main.py
*/5 * * * 1-5 cd /path/to/eth-monitor && ASSET=AAPL /usr/bin/python main.py
```

Run `python main.py --help` for more examples.

## Project Structure

```
eth-monitor/
├── eth_monitor/
│   ├── config.py          # Settings dataclass, loaded from .env
│   ├── logger.py          # Logging setup (rotating file + stderr)
│   ├── price_fetcher.py   # Provider clients (CoinGecko, Yahoo, Finnhub) with retries
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
