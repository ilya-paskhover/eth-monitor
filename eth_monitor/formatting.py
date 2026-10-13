from .config import Config

_CURRENCY_SIGNS: dict[str, str] = {
    "usd": "$",
    "eur": "€",
    "gbp": "£",
    "jpy": "¥",
}


def format_pair(config: Config) -> str:
    """Return the display pair, e.g. "ETH/USD" or "AAPL/USD"."""
    return f"{config.symbol}/{config.quote_currency.upper()}"


def format_money(amount: float, currency: str) -> str:
    """Format an amount with its currency sign ("$3,000.00"), or code suffix when unknown ("3,000.00 CHF")."""
    sign = _CURRENCY_SIGNS.get(currency.lower())
    if sign:
        return f"{sign}{amount:,.2f}"
    return f"{amount:,.2f} {currency.upper()}"
