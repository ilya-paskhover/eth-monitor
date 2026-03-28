import os

import pytest

from eth_monitor.config import Config, load_config


def test_defaults_when_no_env(monkeypatch, tmp_path):
    """load_config uses defaults when no .env file exists and env vars are unset."""
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "THRESHOLD", "BASELINE_FILE",
                "DEBUG_LOG", "MAX_RETRIES", "RETRY_DELAY", "COINGECKO_API_URL"):
        monkeypatch.delenv(var, raising=False)

    cfg = load_config(env_file=str(tmp_path / "nonexistent.env"))

    assert cfg.threshold == 2.5
    assert cfg.max_retries == 3
    assert cfg.retry_delay == 2.0
    assert cfg.telegram_bot_token is None
    assert cfg.telegram_chat_id is None


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
