import ccxt
from config import (
    EXCHANGE_NAME, EXCHANGE_API_KEY, EXCHANGE_API_SECRET,
    TESTNET, TIMEFRAME, CANDLE_LIMIT
)

_exchange: ccxt.bybit | None = None
_connected: bool = False


def get_exchange() -> ccxt.bybit:
    global _exchange, _connected
    if _exchange is not None:
        return _exchange

    _exchange = ccxt.bybit({
        "apiKey": EXCHANGE_API_KEY,
        "secret": EXCHANGE_API_SECRET,
        "enableRateLimit": True,
        "options": {"defaultType": "linear"},
    })
    if TESTNET:
        _exchange.set_sandbox_mode(True)
    if not _connected:
        _connected = True
        if TESTNET:
            print("[EXCHANGE] Connected to Bybit TESTNET (demo account)")
        else:
            print("[EXCHANGE] Connected to Bybit LIVE account")
    return _exchange


def fetch_ohlcv(symbol: str, timeframe: str = TIMEFRAME, limit: int = CANDLE_LIMIT) -> list:
    exchange = get_exchange()
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


def fetch_ticker(symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.fetch_ticker(symbol)


def fetch_funding_rate(symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.fetch_funding_rate(symbol)


def fetch_open_interest(symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.fetch_open_interest(symbol)


def fetch_order_book(symbol: str, limit: int = 20) -> dict:
    exchange = get_exchange()
    return exchange.fetch_order_book(symbol, limit=limit)


def fetch_balance() -> dict:
    exchange = get_exchange()
    return exchange.fetch_balance({"type": "future"})


def fetch_positions(symbol: str) -> list:
    exchange = get_exchange()
    positions = exchange.fetch_positions([symbol])
    return [p for p in positions if float(p["contracts"]) > 0]


def set_leverage(symbol: str, leverage: int) -> dict:
    exchange = get_exchange()
    return exchange.set_leverage(leverage, symbol)


def set_margin_mode(symbol: str, margin_mode: str) -> dict:
    exchange = get_exchange()
    return exchange.set_margin_mode(margin_mode, symbol)


def create_order(symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = {}) -> dict:
    exchange = get_exchange()
    return exchange.create_order(symbol, order_type, side, amount, price, params)


def cancel_order(order_id: str, symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.cancel_order(order_id, symbol)


def fetch_order(order_id: str, symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.fetch_order(order_id, symbol)
