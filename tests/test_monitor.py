import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from eth_monitor.baseline import BaselineStore
from eth_monitor.config import Config
from eth_monitor.monitor import ETHMonitor
from eth_monitor.notifier import TelegramNotifier
from eth_monitor.price_fetcher import PriceFetchError, PriceFetcher

_LOGGER = logging.getLogger("test_monitor")
_TS = datetime(2026, 3, 9, 12, 0, 0)
_NOW = datetime(2026, 3, 9, 13, 0, 0)


def _make_monitor(
    *,
    threshold: float = 1.5,
    last_price: float | None = 3000.0,
    last_ts: datetime | None = _TS,
    current_price: float = 3000.0,
    fetch_error: bool = False,
    notify_result: bool = True,
    missing_vars: list[str] | None = None,
) -> ETHMonitor:
    config = Config(threshold=threshold, missing_vars=missing_vars or [])

    fetcher = MagicMock(spec=PriceFetcher)
    if fetch_error:
        fetcher.fetch.side_effect = PriceFetchError("network down")
    else:
        fetcher.fetch.return_value = current_price

    baseline = MagicMock(spec=BaselineStore)
    baseline.load.return_value = (last_price, last_ts)
    baseline.save.return_value = True

    notifier = MagicMock(spec=TelegramNotifier)
    notifier.send.return_value = notify_result

    return ETHMonitor(
        config=config,
        fetcher=fetcher,
        baseline_store=baseline,
        notifier=notifier,
        logger=_LOGGER,
    )


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_first_run_initializes_baseline(_now_mock):
    """On first run (no baseline), saves price without sending alert."""
    monitor = _make_monitor(last_price=None, last_ts=None, current_price=3000.0)
    monitor.run()

    monitor._baseline.save.assert_called_once_with(3000.0, _NOW)
    monitor._notifier.send.assert_not_called()


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_no_alert_within_threshold(_now_mock):
    """No alert when price change is below threshold."""
    monitor = _make_monitor(last_price=3000.0, current_price=3040.0, threshold=1.5)
    monitor.run()

    monitor._notifier.send.assert_not_called()
    monitor._baseline.save.assert_not_called()


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_alert_sent_on_upward_move(_now_mock):
    """Alert sent when price rises beyond threshold."""
    monitor = _make_monitor(last_price=3000.0, current_price=3100.0, threshold=1.5)
    monitor.run()

    monitor._notifier.send.assert_called_once()
    message = monitor._notifier.send.call_args[0][0]
    assert message == "ETH/USD moved +3.33%: $3,000.00 -> $3,100.00 in last 1 hour"


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_alert_sent_on_downward_move(_now_mock):
    """Alert sent when price drops beyond threshold."""
    monitor = _make_monitor(last_price=3000.0, current_price=2900.0, threshold=1.5)
    monitor.run()

    monitor._notifier.send.assert_called_once()


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_baseline_updated_after_successful_alert(_now_mock):
    """Baseline is updated only when alert is successfully sent."""
    monitor = _make_monitor(last_price=3000.0, current_price=3100.0, notify_result=True)
    monitor.run()

    monitor._baseline.save.assert_called_once_with(3100.0, _NOW)


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_baseline_not_updated_when_alert_fails(_now_mock):
    """Baseline is NOT updated if the Telegram alert fails."""
    monitor = _make_monitor(last_price=3000.0, current_price=3100.0, notify_result=False)
    monitor.run()

    monitor._baseline.save.assert_not_called()


def test_run_handles_fetch_error():
    """run() does not raise if price fetch fails entirely."""
    monitor = _make_monitor(fetch_error=True)
    monitor.run()  # must not raise

    monitor._notifier.send.assert_not_called()
    monitor._baseline.save.assert_not_called()


def test_missing_vars_warns(caplog):
    """Warnings are emitted for each missing required config var."""
    monitor = _make_monitor(
        last_price=None, last_ts=None, current_price=1000.0,
        missing_vars=["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    )
    with caplog.at_level(logging.WARNING, logger="test_monitor"):
        monitor.run()

    assert "TELEGRAM_BOT_TOKEN" in caplog.text
    assert "TELEGRAM_CHAT_ID" in caplog.text


def test_test_delegates_to_notifier():
    monitor = _make_monitor()
    monitor._notifier.test = MagicMock(return_value=True)
    monitor.test()
    monitor._notifier.test.assert_called_once()


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_message_includes_baseline_timestamp(_now_mock):
    """Alert message includes the baseline timestamp when available."""
    monitor = _make_monitor(last_price=3000.0, last_ts=_TS, current_price=3100.0)
    monitor.run()

    message = monitor._notifier.send.call_args[0][0]
    assert "in last 1 hour" in message


@patch("eth_monitor.monitor.ETHMonitor._now", return_value=_NOW)
def test_message_no_baseline_timestamp(_now_mock):
    """Alert message works without a baseline timestamp."""
    monitor = _make_monitor(last_price=3000.0, last_ts=None, current_price=3100.0)
    monitor.run()

    message = monitor._notifier.send.call_args[0][0]
    assert message == "ETH/USD moved +3.33%: $3,000.00 -> $3,100.00"
