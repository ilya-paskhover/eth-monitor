import logging
from datetime import datetime, timezone

from .baseline import BaselineStore
from .config import Config
from .formatting import format_money, format_pair
from .notifier import TelegramNotifier
from .price_fetcher import PriceFetchError, PriceFetcher


class PriceMonitor:
    """Orchestrates the price monitoring workflow for the configured asset.

    Workflow for run():
        1. Emit warnings for any missing required config vars.
        2. Load the stored baseline price and timestamp.
        3. Fetch the current price (with retries).
        4. On first run (no baseline): save price as new baseline, exit quietly.
        5. Calculate percentage change from baseline.
        6. If change exceeds threshold: send Telegram alert, update baseline.
    """

    def __init__(
        self,
        config: Config,
        fetcher: PriceFetcher,
        baseline_store: BaselineStore,
        notifier: TelegramNotifier,
        logger: logging.Logger,
    ) -> None:
        self._config = config
        self._fetcher = fetcher
        self._baseline = baseline_store
        self._notifier = notifier
        self._logger = logger

    def run(self) -> None:
        self._logger.debug("=== Starting %s monitor ===", format_pair(self._config))
        self._warn_missing_config()

        last_price, ts_baseline = self._baseline.load()

        try:
            current_price = self._fetcher.fetch()
        except PriceFetchError as exc:
            self._logger.error("Failed to fetch current price after retries: %s", exc)
            return

        if last_price is None:
            self._logger.debug(
                "No valid baseline present. Initializing with current price %.2f (no alert).", current_price
            )
            self._baseline.save(current_price, self._now())
            self._logger.debug("Baseline initialized.")
            return

        diff = current_price - last_price
        percent = (diff / last_price) * 100
        self._logger.debug("Price change: %.2f %s (%.2f%%)", diff, self._config.quote_currency.upper(), percent)

        if abs(percent) >= self._config.threshold:
            self._logger.debug("Threshold exceeded (%.2f%% >= %.2f%%). Sending alert.", abs(percent), self._config.threshold)
            now = self._now()
            message = self._build_message(current_price, diff, percent, ts_baseline, now)
            if self._notifier.send(message):
                self._baseline.save(current_price, now)
                self._logger.debug("Baseline updated to %.2f.", current_price)
            else:
                self._logger.error("Alert not sent. Baseline unchanged.")
        else:
            self._logger.debug("Price change within threshold (%.2f%%). No alert sent.", self._config.threshold)

        self._logger.debug("=== %s monitor finished ===", format_pair(self._config))

    def test(self) -> bool:
        """Send a test Telegram notification. Returns True if it was sent."""
        self._warn_missing_config()
        return self._notifier.test()

    def _warn_missing_config(self) -> None:
        for var in self._config.missing_vars:
            self._logger.warning("Required environment variable %s is not set.", var)

    def _build_message(
        self,
        current_price: float,
        diff: float,
        percent: float,
        ts_baseline: datetime | None,
        now: datetime,
    ) -> str:
        direction = "+" if diff >= 0 else ""
        currency = self._config.quote_currency
        message = (
            f"{format_pair(self._config)} moved {direction}{percent:.2f}%: "
            f"{format_money(current_price - diff, currency)} -> {format_money(current_price, currency)}"
        )
        if ts_baseline:
            elapsed = self._format_elapsed_phrase(started_at=ts_baseline, now=now)
            return f"{message} {elapsed}"
        return message

    @staticmethod
    def _format_elapsed_phrase(started_at: datetime, now: datetime) -> str:
        total_minutes = max(0, int((now - started_at).total_seconds() // 60))
        hours, minutes = divmod(total_minutes, 60)
        parts = [f"{n} {unit}{'' if n == 1 else 's'}" for n, unit in ((hours, "hour"), (minutes, "minute")) if n]
        return f"in last {' and '.join(parts) or '0 hours'}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc).replace(tzinfo=None)
