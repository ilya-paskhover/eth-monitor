import logging
import os
from datetime import datetime
from pathlib import Path


class BaselineStore:
    """Persists the last alerted ETH price and timestamp to a flat file.

    File format (two lines):
        <price as float>
        <timestamp as YYYY-MM-DD HH:MM:SS>

    All errors (missing file, corrupted content) are handled gracefully:
    load() returns (None, None) rather than raising.
    """

    _TS_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, path: str, logger: logging.Logger) -> None:
        self._path = Path(path)
        self._logger = logger

    def load(self) -> tuple[float | None, datetime | None]:
        """Return (price, timestamp) from the baseline file, or (None, None) on any issue."""
        if not self._path.exists():
            self._logger.debug("Baseline file not found: %s (first run or /tmp cleared).", self._path)
            return None, None

        self._logger.debug("Baseline file found: %s", self._path)
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            self._logger.error("Could not read baseline file: %s", exc)
            return None, None

        price_line = lines[0].strip() if lines else ""
        ts_line = lines[1].strip() if len(lines) > 1 else ""

        try:
            price = float(price_line)
        except ValueError:
            self._logger.error("Baseline file has invalid price line: %r. Resetting baseline.", price_line)
            return None, None

        timestamp: datetime | None = None
        if ts_line:
            try:
                timestamp = datetime.strptime(ts_line, self._TS_FORMAT)
            except ValueError:
                self._logger.warning("Baseline file has invalid timestamp: %r. Continuing without it.", ts_line)

        self._logger.debug("Loaded baseline: price=%.2f, timestamp=%s", price, timestamp)
        return price, timestamp

    def save(self, price: float, timestamp: datetime) -> bool:
        """Atomically write price and timestamp to the baseline file.

        Returns True on success, False on failure (logged internally).
        """
        tmp_path = self._path.with_suffix(".tmp")
        content = f"{price}\n{timestamp.strftime(self._TS_FORMAT)}\n"
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, self._path)  # atomic on POSIX; best-effort on Windows
            self._logger.debug("Baseline saved: price=%.2f, timestamp=%s", price, timestamp)
            return True
        except OSError as exc:
            self._logger.error("Failed to save baseline: %s", exc)
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
