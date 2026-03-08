import json
import logging
import time

import requests

from .config import Config


class PriceFetchError(Exception):
    """Raised when the ETH price cannot be fetched after all retries."""


class PriceFetcher:
    """Fetches the current ETH/USD price from the CoinGecko API."""

    _CONNECT_TIMEOUT = 10
    _READ_TIMEOUT = 20

    def __init__(self, config: Config, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger

    def fetch(self) -> float:
        """Return the current ETH/USD price.

        Retries up to config.max_retries times with config.retry_delay seconds between
        attempts. Raises PriceFetchError if all attempts fail.
        """
        last_error: str = ""
        for attempt in range(1, self._config.max_retries + 1):
            self._logger.debug("Fetching ETH price (attempt %d/%d)...", attempt, self._config.max_retries)
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
            response = requests.get(
                self._config.coingecko_api_url,
                timeout=(self._CONNECT_TIMEOUT, self._READ_TIMEOUT),
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise PriceFetchError(f"Request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise PriceFetchError(f"HTTP request failed: {exc}") from exc

        return self._parse_price(response.text)

    def _parse_price(self, body: str) -> float:
        try:
            data = json.loads(body)
            price = data["ethereum"]["usd"]
            return float(price)
        except (KeyError, TypeError, ValueError) as exc:
            raise PriceFetchError(f"Price parsing failed. Response body: {body!r}") from exc
