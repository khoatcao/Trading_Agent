import ccxt
from config import (
    EXCHANGE_NAME, EXCHANGE_API_KEY, EXCHANGE_API_SECRET,
    TIMEFRAME, CANDLE_LIMIT
)

_exchange: ccxt.bybit | None = None
_connected: bool = False


def get_exchange() -> ccxt.bybit:
    exchange = ccxt.bybit({
        "enableRateLimit": True,
        "options": {"defaultType": "linear", "fetchCurrencies": False},
    })
    exchange.load_markets()
    exchange.apiKey = EXCHANGE_API_KEY
    exchange.secret = EXCHANGE_API_SECRET
    exchange.verbose = False
    return exchange


def fetch_all_usdt_perpetuals(min_volume_usdt: float = 5_000_000, max_symbols: int = 50) -> list:
    exchange = get_exchange()
    tickers = exchange.fetch_tickers()

    pairs = []
    for symbol, ticker in tickers.items():
        market = exchange.markets.get(symbol, {})
        if not market.get("linear") or not market.get("swap"):
            continue
        if not symbol.endswith("/USDT:USDT"):
            continue
        quote_volume = float(ticker.get("quoteVolume") or 0)
        if quote_volume < min_volume_usdt:
            continue
        pairs.append((symbol, quote_volume))

    pairs.sort(key=lambda x: x[1], reverse=True)
    result = [s for s, _ in pairs[:max_symbols]]
    print(f"[SCANNER] Found {len(result)} USDT perpetuals with >{min_volume_usdt/1_000_000:.0f}M volume")
    return result


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
    try:
        return exchange.set_leverage(leverage, symbol)
    except Exception as e:
        err = str(e).lower()
        if "leverage not modified" in err or "110043" in err:
            print(f"[EXCHANGE] leverage already set for {symbol}: {leverage}x")
            return {}
        raise


def set_margin_mode(symbol: str, margin_mode: str) -> dict:
    exchange = get_exchange()
    try:
        return exchange.set_margin_mode(margin_mode, symbol)
    except Exception as e:
        err = str(e).lower()
        if "margin mode not modified" in err or "margin not modified" in err:
            print(f"[EXCHANGE] margin mode already set for {symbol}: {margin_mode}")
            return {}
        raise


def create_order(symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = {}) -> dict:
    exchange = get_exchange()
    return exchange.create_order(symbol, order_type, side, amount, price, params)


def set_trading_stop(symbol: str, stop_loss: float, take_profit: float) -> dict:
    exchange = get_exchange()
    market = exchange.market(symbol)
    bybit_symbol = market["id"]  # e.g. DOGE/USDT:USDT → DOGEUSDT
    return exchange.private_post_v5_position_trading_stop({
        "category": "linear",
        "symbol": bybit_symbol,
        "stopLoss": str(stop_loss),
        "takeProfit": str(take_profit),
        "slTriggerBy": "MarkPrice",
        "tpTriggerBy": "MarkPrice",
        "tpslMode": "Full",
        "slOrderType": "Market",
        "tpOrderType": "Market",
        "positionIdx": 0,
    })


def cancel_order(order_id: str, symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.cancel_order(order_id, symbol)


def fetch_order(order_id: str, symbol: str) -> dict:
    exchange = get_exchange()
    return exchange.fetch_order(order_id, symbol)
