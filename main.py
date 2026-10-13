import argparse
import sys

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
        description="Crypto/stock price monitor — checks CoinGecko or Finnhub and sends Telegram alerts on significant moves."
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
