import argparse
import sys

from eth_monitor.baseline import BaselineStore
from eth_monitor.config import load_config
from eth_monitor.logger import setup_logger
from eth_monitor.monitor import ETHMonitor
from eth_monitor.notifier import TelegramNotifier
from eth_monitor.price_fetcher import PriceFetcher


def build_monitor() -> ETHMonitor:
    config = load_config()
    logger = setup_logger(log_file=config.debug_log)
    fetcher = PriceFetcher(config=config, logger=logger)
    baseline_store = BaselineStore(path=config.baseline_file, logger=logger)
    notifier = TelegramNotifier(config=config, logger=logger)
    return ETHMonitor(
        config=config,
        fetcher=fetcher,
        baseline_store=baseline_store,
        notifier=notifier,
        logger=logger,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ETH/USD price monitor — checks CoinGecko and sends Telegram alerts on significant moves."
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
