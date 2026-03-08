# eth-monitor

Monitors the ETH/USD price via the CoinGecko API and sends a Telegram alert when
the price moves more than a configurable threshold from the last alerted price.

## Features

- Retries on transient network failures
- Atomic baseline file writes (safe on crashes)
- Graceful handling of missing Telegram credentials (warns, does not crash)
- All settings configurable via `.env` or environment variables
- `--test` flag to verify Telegram integration before deploying
- 40 unit tests, all components independently mockable

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

| Variable              | Default                                                              | Required | Description                                |
|-----------------------|----------------------------------------------------------------------|----------|--------------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | —                                                                    | Yes      | Telegram Bot API token                     |
| `TELEGRAM_CHAT_ID`    | —                                                                    | Yes      | Telegram chat/user ID to send alerts to    |
| `THRESHOLD`           | `1.5`                                                                | No       | % change from baseline that triggers alert |
| `BASELINE_FILE`       | `/tmp/eth_last_price`                                                | No       | Path to the baseline persistence file      |
| `DEBUG_LOG`           | `/tmp/eth_monitor_debug.log`                                         | No       | Path to the rotating debug log file        |
| `MAX_RETRIES`         | `3`                                                                  | No       | Max price-fetch attempts before giving up  |
| `RETRY_DELAY`         | `2`                                                                  | No       | Seconds between retry attempts             |
| `COINGECKO_API_URL`   | `https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd` | No | CoinGecko endpoint |

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
│   ├── price_fetcher.py   # CoinGecko HTTP client with retries
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
