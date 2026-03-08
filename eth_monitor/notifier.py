import logging

import requests

from .config import Config

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = (10, 20)


class TelegramNotifier:
    """Sends messages to a Telegram chat via the Bot API."""

    def __init__(self, config: Config, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger

    def send(self, message: str) -> bool:
        """Send a message to the configured Telegram chat.

        Returns True on success, False if credentials are missing or the request fails.
        """
        if not self._is_configured():
            return False

        url = _TELEGRAM_API.format(token=self._config.telegram_bot_token)
        return self._post(url, message)

    def test(self) -> bool:
        """Send a test notification to confirm Telegram integration is working."""
        message = (
            "Test alert: This is only a test notification from the ETH monitor.\n"
            "No actual price changes were detected."
        )
        result = self.send(message)
        if result:
            self._logger.debug("TEST Telegram alert sent successfully.")
        else:
            self._logger.error("Failed to send TEST Telegram alert.")
        return result

    def _is_configured(self) -> bool:
        if not self._config.telegram_bot_token or not self._config.telegram_chat_id:
            self._logger.warning(
                "Telegram credentials not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing). "
                "Skipping notification."
            )
            return False
        return True

    def _post(self, url: str, message: str) -> bool:
        try:
            response = requests.post(
                url,
                data={
                    "chat_id": self._config.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            self._logger.debug("Telegram alert sent successfully.")
            return True
        except requests.exceptions.RequestException as exc:
            self._logger.error("Failed to send Telegram alert: %s", exc)
            return False
