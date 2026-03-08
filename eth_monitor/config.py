import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

_REQUIRED_VARS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
_DEFAULTS: dict[str, str] = {
    "COINGECKO_API_URL": "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
    "THRESHOLD": "1.5",
    "BASELINE_FILE": "/tmp/eth_last_price",
    "DEBUG_LOG": "/tmp/eth_monitor_debug.log",
    "MAX_RETRIES": "3",
    "RETRY_DELAY": "2",
}


@dataclass
class Config:
    coingecko_api_url: str = _DEFAULTS["COINGECKO_API_URL"]
    threshold: float = float(_DEFAULTS["THRESHOLD"])
    baseline_file: str = _DEFAULTS["BASELINE_FILE"]
    debug_log: str = _DEFAULTS["DEBUG_LOG"]
    max_retries: int = int(_DEFAULTS["MAX_RETRIES"])
    retry_delay: float = float(_DEFAULTS["RETRY_DELAY"])
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    # Names of required vars that were absent at load time (used for deferred warnings)
    missing_vars: list[str] = field(default_factory=list, repr=False)


def load_config(env_file: str = ".env") -> Config:
    """Load configuration from environment variables, optionally from an .env file.

    Warns (does not raise) if required Telegram variables are missing.
    Unknown or extra variables are silently ignored.
    """
    load_dotenv(dotenv_path=env_file, override=False)

    missing: list[str] = []
    for var in _REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)

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

    return Config(
        coingecko_api_url=_get("COINGECKO_API_URL"),
        threshold=_float("THRESHOLD"),
        baseline_file=_get("BASELINE_FILE"),
        debug_log=_get("DEBUG_LOG"),
        max_retries=_int("MAX_RETRIES"),
        retry_delay=_float("RETRY_DELAY"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        missing_vars=missing,
    )
