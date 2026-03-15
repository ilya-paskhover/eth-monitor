import logging

import pytest
import requests

from eth_monitor.config import Config
from eth_monitor.notifier import TelegramNotifier

_LOGGER = logging.getLogger("test_notifier")


def _notifier(token: str | None = "tok", chat_id: str | None = "123") -> TelegramNotifier:
    cfg = Config(telegram_bot_token=token, telegram_chat_id=chat_id)
    return TelegramNotifier(config=cfg, logger=_LOGGER)


def test_send_returns_false_when_no_token():
    notifier = _notifier(token=None, chat_id="123")
    assert notifier.send("hello") is False


def test_send_returns_false_when_no_chat_id():
    notifier = _notifier(token="tok", chat_id=None)
    assert notifier.send("hello") is False


def test_send_returns_true_on_success(mocker):
    notifier = _notifier()
    mock_resp = mocker.Mock()
    mock_resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.post", return_value=mock_resp)

    assert notifier.send("hello") is True


def test_send_returns_false_on_http_error(mocker):
    notifier = _notifier()
    mocker.patch("requests.post", side_effect=requests.exceptions.HTTPError("bad"))
    assert notifier.send("hello") is False


def test_send_returns_false_on_connection_error(mocker):
    notifier = _notifier()
    mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("down"))
    assert notifier.send("hello") is False


def test_test_calls_send(mocker):
    notifier = _notifier()
    mocker.patch.object(notifier, "send", return_value=True)
    result = notifier.test()
    assert result is True
    notifier.send.assert_called_once_with("TEST - ETH/USD moved +9.99%: $9,999.99 -> $9,999.99 in last 9 hours")


def test_test_returns_false_when_send_fails(mocker):
    notifier = _notifier()
    mocker.patch.object(notifier, "send", return_value=False)
    assert notifier.test() is False
