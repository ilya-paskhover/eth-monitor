import os

import pytest

from eth_monitor.config import Config, load_config


def test_defaults_when_no_env(monkeypatch, tmp_path):
    """load_config uses defaults when no .env file exists and env vars are unset."""
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "THRESHOLD", "BASELINE_FILE",
                "DEBUG_LOG", "MAX_RETRIES", "RETRY_DELAY", "COINGECKO_API_URL",
                "PROVIDER", "ASSET", "QUOTE_CURRENCY", "SYMBOL", "FINNHUB_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.threshold == 2.5
    assert cfg.max_retries == 3
    assert cfg.retry_delay == 2.0
    assert cfg.telegram_bot_token is None
    assert cfg.telegram_chat_id is None
    assert cfg.provider == "coingecko"
    assert cfg.asset == "ethereum"
    assert cfg.quote_currency == "usd"
    assert cfg.symbol == "ETH"
    assert cfg.baseline_file == "/tmp/eth_last_price"


def test_missing_vars_recorded(monkeypatch, tmp_path):
    """Missing required vars are listed in missing_vars (no exception)."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert "TELEGRAM_BOT_TOKEN" in cfg.missing_vars
    assert "TELEGRAM_CHAT_ID" in cfg.missing_vars


def test_values_loaded_from_env(monkeypatch, tmp_path):
    """Environment variables override defaults."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("THRESHOLD", "2.5")
    monkeypatch.setenv("MAX_RETRIES", "5")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.telegram_bot_token == "tok123"
    assert cfg.telegram_chat_id == "999"
    assert cfg.threshold == 2.5
    assert cfg.max_retries == 5
    assert cfg.missing_vars == []


def test_env_file_loaded(tmp_path, monkeypatch):
    """Values from a .env file are picked up."""
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "THRESHOLD"):
        monkeypatch.delenv(var, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_BOT_TOKEN=file_tok\nTELEGRAM_CHAT_ID=111\nTHRESHOLD=3.0\n")

    cfg = load_config(env_file=str(env_file))

    assert cfg.telegram_bot_token == "file_tok"
    assert cfg.telegram_chat_id == "111"
    assert cfg.threshold == 3.0
    assert cfg.missing_vars == []


def test_invalid_threshold_falls_back_to_default(monkeypatch, tmp_path):
    """Non-numeric THRESHOLD emits a warning and falls back to default."""
    monkeypatch.setenv("THRESHOLD", "not-a-number")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.threshold == 2.5


def _clear_asset_env(monkeypatch):
    for var in ("PROVIDER", "ASSET", "QUOTE_CURRENCY", "SYMBOL", "BASELINE_FILE", "FINNHUB_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_symbol_and_baseline_derived_from_asset(monkeypatch, tmp_path):
    """SYMBOL and BASELINE_FILE default per asset so switching assets never reuses another asset's baseline."""
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", "bitcoin")
    monkeypatch.setenv("QUOTE_CURRENCY", "EUR")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.symbol == "BTC"
    assert cfg.quote_currency == "eur"
    assert cfg.baseline_file == "/tmp/btc_last_price"


def test_unknown_asset_symbol_is_upper_cased(monkeypatch, tmp_path):
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", "dogecoin")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.symbol == "DOGECOIN"


def test_explicit_symbol_and_baseline_win(monkeypatch, tmp_path):
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", "dogecoin")
    monkeypatch.setenv("SYMBOL", "DOGE")
    monkeypatch.setenv("BASELINE_FILE", "/var/lib/doge")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.symbol == "DOGE"
    assert cfg.baseline_file == "/var/lib/doge"


def test_ticker_asset_defaults_to_yahoo(monkeypatch, tmp_path):
    """Stocks need no PROVIDER: an upper-case ticker picks Yahoo, which needs no API key."""
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", "AAPL")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.provider == "yahoo"
    assert cfg.symbol == "AAPL"
    assert cfg.baseline_file == "/tmp/aapl_last_price"
    assert "FINNHUB_API_KEY" not in cfg.missing_vars


@pytest.mark.parametrize("asset", ["SAP.DE", "EURUSD=X", "BTC-USD", "7203.T"])
def test_yahoo_style_symbols_default_to_yahoo(monkeypatch, tmp_path, asset):
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", asset)

    assert load_config(env_file=str(tmp_path / "nonexistent.env")).provider == "yahoo"


@pytest.mark.parametrize("asset", ["ethereum", "bitcoin", "usd-coin"])
def test_coingecko_ids_default_to_coingecko(monkeypatch, tmp_path, asset):
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", asset)

    assert load_config(env_file=str(tmp_path / "nonexistent.env")).provider == "coingecko"


def test_explicit_provider_overrides_detection(monkeypatch, tmp_path):
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("ASSET", "AAPL")
    monkeypatch.setenv("PROVIDER", "finnhub")

    assert load_config(env_file=str(tmp_path / "nonexistent.env")).provider == "finnhub"


def test_finnhub_requires_api_key(monkeypatch, tmp_path):
    _clear_asset_env(monkeypatch)
    monkeypatch.setenv("PROVIDER", "Finnhub")
    monkeypatch.setenv("ASSET", "AAPL")

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.provider == "finnhub"
    assert cfg.symbol == "AAPL"
    assert "FINNHUB_API_KEY" in cfg.missing_vars


def test_coingecko_does_not_require_finnhub_key(monkeypatch, tmp_path):
    _clear_asset_env(monkeypatch)

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert "FINNHUB_API_KEY" not in cfg.missing_vars
