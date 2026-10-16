import json
import logging
import time

import requests

from .config import Config


class PriceFetchError(Exception):
    """Raised when the price cannot be fetched after all retries."""


class PriceFetcher:
    """Base class: fetches the current price of the configured asset, with retries.

    Subclasses implement _request() (one HTTP call) and _parse_price() (extract the price).
    """

    _TIMEOUT = (10, 20)

    def __init__(self, config: Config, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger

    def fetch(self) -> float:
        """Return the current price of the configured asset.

        Retries up to config.max_retries times with config.retry_delay seconds between
        attempts. Raises PriceFetchError if all attempts fail.
        """
        last_error: str = ""
        for attempt in range(1, self._config.max_retries + 1):
            self._logger.debug(
                "Fetching %s price (attempt %d/%d)...", self._config.symbol, attempt, self._config.max_retries
            )
            try:
                price = self._fetch_once()
                self._logger.debug("Successfully fetched price: %s", price)
                return price
            except PriceFetchError as exc:
                last_error = str(exc)
                self._logger.error("Attempt %d failed: %s", attempt, exc)
                if attempt < self._config.max_retries:
                    time.sleep(self._config.retry_delay)

        raise PriceFetchError(f"All {self._config.max_retries} attempts failed. Last error: {last_error}")

    def _fetch_once(self) -> float:
        try:
            response = self._request()
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise PriceFetchError(f"Request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise PriceFetchError(f"HTTP request failed: {exc}") from exc

        try:
            price = self._parse_price(json.loads(response.text))
        except (KeyError, TypeError, ValueError) as exc:
            raise PriceFetchError(f"Price parsing failed. Response body: {response.text!r}") from exc
        # 0 means no quote (Finnhub answers unknown tickers with all zeros); `not > 0` also rejects NaN.
        if not price > 0:
            raise PriceFetchError(f"No valid price for {self._config.asset!r}: {price}")
        return price

    def _request(self) -> requests.Response:
        raise NotImplementedError

    def _parse_price(self, data: dict) -> float:
        raise NotImplementedError


class CoinGeckoFetcher(PriceFetcher):
    """Crypto prices from CoinGecko /simple/price (ASSET = coin id, QUOTE_CURRENCY = vs currency)."""

    def _request(self) -> requests.Response:
        return requests.get(
            self._config.coingecko_api_url,
            params={"ids": self._config.asset, "vs_currencies": self._config.quote_currency},
            timeout=self._TIMEOUT,
        )

    def _parse_price(self, data: dict) -> float:
        return float(data[self._config.asset][self._config.quote_currency])


class FinnhubFetcher(PriceFetcher):
    """Stock prices from Finnhub /quote (ASSET = ticker). Quotes are in the listing's currency."""

    def _request(self) -> requests.Response:
        return requests.get(
            self._config.finnhub_api_url,
            params={"symbol": self._config.asset},
            headers={"X-Finnhub-Token": self._config.finnhub_api_key or ""},
            timeout=self._TIMEOUT,
        )

    def _parse_price(self, data: dict) -> float:
        return float(data["c"])


class YahooFetcher(PriceFetcher):
    """Stocks, FX and crypto from Yahoo Finance's chart endpoint (ASSET = Yahoo symbol, e.g. "AAPL", "EURUSD=X").

    No API key needed, but the endpoint is unofficial and may change or rate-limit without notice.
    """

    # Yahoo answers requests without a browser-like User-Agent with HTTP 429.
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; eth-monitor)"}
    # Yahoo quotes some listings in the minor unit: London in pence, Johannesburg in cents, Tel Aviv in agorot.
    _MINOR_UNITS = {"GBp": "GBP", "ZAc": "ZAR", "ILA": "ILS"}

    def _request(self) -> requests.Response:
        return requests.get(
            self._config.yahoo_api_url.format(symbol=self._config.asset),
            params={"range": "1d", "interval": "1d"},
            headers=self._HEADERS,
            timeout=self._TIMEOUT,
        )

    def _parse_price(self, data: dict) -> float:
        meta = data["chart"]["result"][0]["meta"]
        price = float(meta["regularMarketPrice"])
        currency = meta.get("currency")
        if currency in self._MINOR_UNITS:
            currency, price = self._MINOR_UNITS[currency], price / 100
        if currency and currency.lower() != self._config.quote_currency:
            self._logger.warning(
                "%s is quoted in %s but QUOTE_CURRENCY is %s; alerts will show the wrong currency.",
                self._config.asset, currency, self._config.quote_currency.upper(),
            )
        return price


_FETCHERS: dict[str, type[PriceFetcher]] = {
    "coingecko": CoinGeckoFetcher,
    "finnhub": FinnhubFetcher,
    "yahoo": YahooFetcher,
}


def create_fetcher(config: Config, logger: logging.Logger) -> PriceFetcher:
    """Return the fetcher for config.provider. Raises ValueError for an unknown provider."""
    try:
        fetcher_cls = _FETCHERS[config.provider]
    except KeyError:
        raise ValueError(
            f"Unknown PROVIDER {config.provider!r}. Supported: {', '.join(sorted(_FETCHERS))}."
        ) from None
    return fetcher_cls(config=config, logger=logger)
