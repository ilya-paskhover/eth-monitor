import json
import logging

import pytest
import requests

from eth_monitor.config import Config
from eth_monitor.price_fetcher import (
    CoinGeckoFetcher,
    FinnhubFetcher,
    PriceFetchError,
    PriceFetcher,
    YahooFetcher,
    create_fetcher,
)

_LOGGER = logging.getLogger("test_price_fetcher")


def _fetcher(max_retries: int = 3, retry_delay: float = 0) -> PriceFetcher:
    cfg = Config(max_retries=max_retries, retry_delay=retry_delay)
    return CoinGeckoFetcher(config=cfg, logger=_LOGGER)


def _finnhub(asset: str = "AAPL") -> PriceFetcher:
    cfg = Config(provider="finnhub", asset=asset, symbol=asset, finnhub_api_key="key123", max_retries=1, retry_delay=0)
    return FinnhubFetcher(config=cfg, logger=_LOGGER)


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


def test_coingecko_uses_configured_asset_and_currency(mocker):
    cfg = Config(asset="bitcoin", quote_currency="eur", max_retries=1, retry_delay=0)
    fetcher = CoinGeckoFetcher(config=cfg, logger=_LOGGER)
    get = mocker.patch("requests.get", return_value=_mock_response(mocker, {"bitcoin": {"eur": 51000.5}}))

    assert fetcher.fetch() == 51000.5
    assert get.call_args.kwargs["params"] == {"ids": "bitcoin", "vs_currencies": "eur"}


def test_finnhub_returns_current_price(mocker):
    fetcher = _finnhub()
    get = mocker.patch("requests.get", return_value=_mock_response(mocker, {"c": 187.25, "pc": 185.0}))

    assert fetcher.fetch() == 187.25
    assert get.call_args.kwargs["params"] == {"symbol": "AAPL"}
    assert get.call_args.kwargs["headers"] == {"X-Finnhub-Token": "key123"}


def test_finnhub_unknown_symbol_raises(mocker):
    """Finnhub returns 200 with zeroes for unknown tickers; that must not be treated as a price of 0."""
    fetcher = _finnhub(asset="NOPE")
    mocker.patch("requests.get", return_value=_mock_response(mocker, {"c": 0, "d": None, "pc": 0}))

    with pytest.raises(PriceFetchError):
        fetcher.fetch()


def test_create_fetcher_selects_provider():
    assert isinstance(create_fetcher(Config(provider="coingecko"), _LOGGER), CoinGeckoFetcher)
    assert isinstance(create_fetcher(Config(provider="finnhub"), _LOGGER), FinnhubFetcher)
    assert isinstance(create_fetcher(Config(provider="yahoo"), _LOGGER), YahooFetcher)


def test_create_fetcher_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown PROVIDER"):
        create_fetcher(Config(provider="nasdaq"), _LOGGER)


def _yahoo(asset: str = "AAPL", quote_currency: str = "usd") -> PriceFetcher:
    cfg = Config(provider="yahoo", asset=asset, symbol=asset, quote_currency=quote_currency, max_retries=1, retry_delay=0)
    return YahooFetcher(config=cfg, logger=_LOGGER)


def _yahoo_body(price: float, currency: str = "USD") -> dict:
    return {"chart": {"result": [{"meta": {"currency": currency, "regularMarketPrice": price}}], "error": None}}


def test_yahoo_returns_price(mocker):
    fetcher = _yahoo()
    get = mocker.patch("requests.get", return_value=_mock_response(mocker, _yahoo_body(341.27)))

    assert fetcher.fetch() == 341.27
    assert get.call_args.args[0] == "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
    assert "User-Agent" in get.call_args.kwargs["headers"]


def test_yahoo_unknown_symbol_raises(mocker):
    fetcher = _yahoo(asset="NOPE")
    body = {"chart": {"result": None, "error": {"code": "Not Found", "description": "No data found"}}}
    mocker.patch("requests.get", return_value=_mock_response(mocker, body))

    with pytest.raises(PriceFetchError):
        fetcher.fetch()


def test_yahoo_warns_on_currency_mismatch(mocker, caplog):
    fetcher = _yahoo(asset="SAP.DE", quote_currency="usd")
    mocker.patch("requests.get", return_value=_mock_response(mocker, _yahoo_body(180.0, currency="EUR")))

    with caplog.at_level("WARNING", logger="test_price_fetcher"):
        assert fetcher.fetch() == 180.0
    assert "quoted in EUR" in caplog.text
