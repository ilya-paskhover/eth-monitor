import argparse
import sys
import textwrap

from eth_monitor.baseline import BaselineStore
from eth_monitor.config import load_config
from eth_monitor.logger import setup_logger
from eth_monitor.monitor import PriceMonitor
from eth_monitor.notifier import TelegramNotifier
from eth_monitor.price_fetcher import create_fetcher


def build_monitor() -> PriceMonitor:
    config = load_config()
    logger = setup_logger(log_file=config.debug_log)
    fetcher = create_fetcher(config=config, logger=logger)
    baseline_store = BaselineStore(path=config.baseline_file, logger=logger)
    notifier = TelegramNotifier(config=config, logger=logger)
    return PriceMonitor(
        config=config,
        fetcher=fetcher,
        baseline_store=baseline_store,
        notifier=notifier,
        logger=logger,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Crypto/stock price monitor — checks CoinGecko, Yahoo Finance or Finnhub and sends Telegram alerts on significant moves.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples (settings can also go in .env):
              python main.py                                  # ETH/USD via CoinGecko (default)
              ASSET=bitcoin QUOTE_CURRENCY=eur python main.py # BTC/EUR via CoinGecko
              ASSET=AAPL python main.py                       # Apple stock via Yahoo, no API key
              ASSET=SAP.DE QUOTE_CURRENCY=eur python main.py  # SAP on Xetra in euros
              ASSET=EURUSD=X SYMBOL=EUR python main.py        # EUR/USD exchange rate
              PROVIDER=finnhub ASSET=AAPL FINNHUB_API_KEY=... python main.py

            Upper-case ASSET (a ticker) uses Yahoo; lower-case (a CoinGecko id) uses CoinGecko.
            Set PROVIDER to override.
        """),
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test Telegram notification and exit.",
    )
    args = parser.parse_args(argv)

    monitor = build_monitor()
    if args.test:
        monitor.test()
    else:
        monitor.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
