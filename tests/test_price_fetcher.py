import json
import logging

import pytest
import requests

from eth_monitor.config import Config
from eth_monitor.price_fetcher import PriceFetchError, PriceFetcher

_LOGGER = logging.getLogger("test_price_fetcher")


def _fetcher(max_retries: int = 3, retry_delay: float = 0) -> PriceFetcher:
    cfg = Config(max_retries=max_retries, retry_delay=retry_delay)
    return PriceFetcher(config=cfg, logger=_LOGGER)


def _mock_response(mocker, json_body: dict, status_code: int = 200):
    mock_resp = mocker.Mock()
    mock_resp.status_code = status_code
    mock_resp.text = json.dumps(json_body)
    mock_resp.raise_for_status = mocker.Mock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)
    return mock_resp


def test_fetch_returns_price(mocker):
    fetcher = _fetcher()
    mocker.patch("requests.get", return_value=_mock_response(mocker, {"ethereum": {"usd": 3456.78}}))

    assert fetcher.fetch() == 3456.78


def test_fetch_retries_on_failure(mocker):
    fetcher = _fetcher(max_retries=3, retry_delay=0)
    fail = mocker.Mock(side_effect=requests.exceptions.ConnectionError("down"))
    success = _mock_response(mocker, {"ethereum": {"usd": 2000.0}})
    mocker.patch("requests.get", side_effect=[fail.side_effect, fail.side_effect, success])

    price = fetcher.fetch()
    assert price == 2000.0


def test_fetch_raises_after_all_retries(mocker):
    fetcher = _fetcher(max_retries=2, retry_delay=0)
    mocker.patch("requests.get", side_effect=requests.exceptions.ConnectionError("down"))

    with pytest.raises(PriceFetchError):
        fetcher.fetch()


def test_fetch_raises_on_bad_json(mocker):
    fetcher = _fetcher(max_retries=1, retry_delay=0)
    bad_resp = mocker.Mock()
    bad_resp.text = '{"unexpected": "format"}'
    bad_resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", return_value=bad_resp)

    with pytest.raises(PriceFetchError):
        fetcher.fetch()


def test_fetch_raises_on_timeout(mocker):
    fetcher = _fetcher(max_retries=1, retry_delay=0)
    mocker.patch("requests.get", side_effect=requests.exceptions.Timeout())

    with pytest.raises(PriceFetchError):
        fetcher.fetch()
