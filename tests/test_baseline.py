import logging
from datetime import datetime

import pytest

from eth_monitor.baseline import BaselineStore

_LOGGER = logging.getLogger("test_baseline")
_TS = datetime(2026, 3, 9, 12, 0, 0)


def _store(tmp_path) -> BaselineStore:
    return BaselineStore(path=str(tmp_path / "baseline"), logger=_LOGGER)


def test_load_returns_none_when_missing(tmp_path):
    store = _store(tmp_path)
    price, ts = store.load()
    assert price is None
    assert ts is None


def test_save_and_load_roundtrip(tmp_path):
    store = _store(tmp_path)
    assert store.save(3456.78, _TS) is True
    price, ts = store.load()
    assert price == 3456.78
    assert ts == _TS


def test_load_returns_none_on_invalid_price(tmp_path):
    path = tmp_path / "baseline"
    path.write_text("not-a-number\n2026-03-09 12:00:00\n")
    store = BaselineStore(path=str(path), logger=_LOGGER)
    price, ts = store.load()
    assert price is None
    assert ts is None


def test_load_handles_missing_timestamp_line(tmp_path):
    path = tmp_path / "baseline"
    path.write_text("1234.56\n")
    store = BaselineStore(path=str(path), logger=_LOGGER)
    price, ts = store.load()
    assert price == 1234.56
    assert ts is None


def test_load_handles_invalid_timestamp(tmp_path):
    path = tmp_path / "baseline"
    path.write_text("1234.56\nbad-timestamp\n")
    store = BaselineStore(path=str(path), logger=_LOGGER)
    price, ts = store.load()
    assert price == 1234.56
    assert ts is None


def test_save_overwrites_previous(tmp_path):
    store = _store(tmp_path)
    store.save(1000.0, _TS)
    store.save(2000.0, _TS)
    price, _ = store.load()
    assert price == 2000.0


def test_save_creates_parent_dirs(tmp_path):
    nested = tmp_path / "a" / "b" / "baseline"
    store = BaselineStore(path=str(nested), logger=_LOGGER)
    assert store.save(1.0, _TS) is True
    price, _ = store.load()
    assert price == 1.0
