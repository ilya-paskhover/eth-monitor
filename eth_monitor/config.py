import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

_REQUIRED_VARS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
# Extra variables required only by a specific price provider.
_PROVIDER_REQUIRED_VARS: dict[str, tuple[str, ...]] = {
    "finnhub": ("FINNHUB_API_KEY",),
}
# These are fallback values used when no environment variable or .env file entry is present.
# To override any of these, set the corresponding variable in your .env file — no code change needed.
_DEFAULTS: dict[str, str] = {
    "ASSET": "ethereum",
    "QUOTE_CURRENCY": "usd",
    "COINGECKO_API_URL": "https://api.coingecko.com/api/v3/simple/price",
    "FINNHUB_API_URL": "https://finnhub.io/api/v1/quote",
    "YAHOO_API_URL": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
    "THRESHOLD": "2.5",
    "DEBUG_LOG": "/tmp/eth_monitor_debug.log",
    "MAX_RETRIES": "3",
    "RETRY_DELAY": "2",
}
# Display symbols for common CoinGecko ids; anything else falls back to ASSET upper-cased.
_KNOWN_SYMBOLS: dict[str, str] = {
    "ethereum": "ETH",
    "bitcoin": "BTC",
    "solana": "SOL",
}


def default_provider(asset: str) -> str:
    """Pick a provider when PROVIDER is unset.

    CoinGecko ids are lower-case ("ethereum", "usd-coin"); tickers have upper-case letters
    ("AAPL", "SAP.DE", "EURUSD=X"), so anything with an upper-case letter goes to Yahoo.
    """
    return "yahoo" if any(c.isupper() for c in asset) else "coingecko"


def default_symbol(asset: str) -> str:
    return _KNOWN_SYMBOLS.get(asset.lower(), asset.upper())


def default_baseline_file(symbol: str) -> str:
    return f"/tmp/{symbol.lower()}_last_price"


@dataclass
class Config:
    provider: str = "coingecko"
    # CoinGecko coin id (e.g. "ethereum"), Finnhub ticker (e.g. "AAPL") or Yahoo symbol (e.g. "SAP.DE", "EURUSD=X").
    asset: str = _DEFAULTS["ASSET"]
    quote_currency: str = _DEFAULTS["QUOTE_CURRENCY"]
    # Short name shown in alerts and used for the default baseline file name.
    symbol: str = default_symbol(_DEFAULTS["ASSET"])
    coingecko_api_url: str = _DEFAULTS["COINGECKO_API_URL"]
    finnhub_api_url: str = _DEFAULTS["FINNHUB_API_URL"]
    finnhub_api_key: str | None = field(default=None, repr=False)
    yahoo_api_url: str = _DEFAULTS["YAHOO_API_URL"]
    threshold: float = float(_DEFAULTS["THRESHOLD"])
    baseline_file: str = default_baseline_file(default_symbol(_DEFAULTS["ASSET"]))
    debug_log: str = _DEFAULTS["DEBUG_LOG"]
    max_retries: int = int(_DEFAULTS["MAX_RETRIES"])
    retry_delay: float = float(_DEFAULTS["RETRY_DELAY"])
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    # Names of required vars that were absent at load time (used for deferred warnings)
    missing_vars: list[str] = field(default_factory=list, repr=False)


def load_config(env_file: str = ".env") -> Config:
    """Load configuration from environment variables, optionally from an .env file.

    Warns (does not raise) if required Telegram or provider variables are missing.
    Unknown or extra variables are silently ignored.
    """
    load_dotenv(dotenv_path=env_file, override=False)

    def _get(key: str) -> str:
        return os.getenv(key, _DEFAULTS.get(key, ""))

    def _float(key: str) -> float:
        try:
            return float(_get(key))
        except ValueError:
            logging.warning("Config: %s has non-numeric value '%s', using default %s.", key, _get(key), _DEFAULTS.get(key))
            return float(_DEFAULTS.get(key, "0"))

    def _int(key: str) -> int:
        try:
            return int(_get(key))
        except ValueError:
            logging.warning("Config: %s has non-integer value '%s', using default %s.", key, _get(key), _DEFAULTS.get(key))
            return int(_DEFAULTS.get(key, "0"))

    asset = _get("ASSET").strip()
    provider = (os.getenv("PROVIDER") or default_provider(asset)).strip().lower()
    symbol = os.getenv("SYMBOL") or default_symbol(asset)

    missing: list[str] = []
    for var in _REQUIRED_VARS + _PROVIDER_REQUIRED_VARS.get(provider, ()):
        if not os.getenv(var):
            missing.append(var)

    return Config(
        provider=provider,
        asset=asset,
        quote_currency=_get("QUOTE_CURRENCY").strip().lower(),
        symbol=symbol,
        coingecko_api_url=_get("COINGECKO_API_URL"),
        finnhub_api_url=_get("FINNHUB_API_URL"),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY") or None,
        yahoo_api_url=_get("YAHOO_API_URL"),
        threshold=_float("THRESHOLD"),
        baseline_file=os.getenv("BASELINE_FILE") or default_baseline_file(symbol),
        debug_log=_get("DEBUG_LOG"),
        max_retries=_int("MAX_RETRIES"),
        retry_delay=_float("RETRY_DELAY"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        missing_vars=missing,
    )
