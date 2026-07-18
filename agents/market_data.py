from graph.state import TradingState
from tools.exchange import (
    fetch_ohlcv, fetch_ticker, fetch_funding_rate,
    fetch_open_interest, fetch_order_book, fetch_positions
)
from tools.whale_data import fetch_all_whale_data
from notifications.alert import send_alert


def market_data_node(state: TradingState) -> TradingState:
    symbol = state["symbol"]
    timeframe = state["timeframe"]
    base_asset = symbol.split("/")[0]  # "BTC" from "BTC/USDT:USDT"

    errors = state.get("errors", [])
    market_data = {}

    try:
        market_data["ohlcv"] = fetch_ohlcv(symbol, timeframe)
    except Exception as e:
        err = f"market_data:ohlcv:{type(e).__name__}:{e}"
        print(f"[MARKET_DATA] symbol={symbol} ohlcv error={err}")
        errors.append(err)
        send_alert(
            f"🔴 *MARKET DATA ERROR*\n"
            f"Symbol: `{symbol}`\n"
            f"Failed to fetch OHLCV (candle data) — cycle skipped\n"
            f"Error: `{type(e).__name__}: {e}`"
        )

    try:
        ticker = fetch_ticker(symbol)
        market_data["mark_price"] = ticker.get("info", {}).get("markPrice") or ticker.get("last")
        market_data["last_price"] = ticker.get("last")
        market_data["bid"] = ticker.get("bid")
        market_data["ask"] = ticker.get("ask")
    except Exception as e:
        err = f"market_data:ticker:{type(e).__name__}:{e}"
        print(f"[MARKET_DATA] symbol={symbol} ticker error={err}")
        errors.append(err)

    try:
        funding = fetch_funding_rate(symbol)
        market_data["funding_rate"] = funding.get("fundingRate")
        market_data["next_funding_time"] = funding.get("fundingDatetime")
    except Exception as e:
        err = f"market_data:funding:{type(e).__name__}:{e}"
        print(f"[MARKET_DATA] symbol={symbol} funding error={err}")
        errors.append(err)

    try:
        oi = fetch_open_interest(symbol)
        market_data["open_interest"] = oi.get("openInterest")
    except Exception as e:
        err = f"market_data:open_interest:{type(e).__name__}:{e}"
        print(f"[MARKET_DATA] symbol={symbol} open_interest error={err}")
        errors.append(err)

    try:
        market_data["order_book"] = fetch_order_book(symbol)
    except Exception as e:
        err = f"market_data:order_book:{type(e).__name__}:{e}"
        print(f"[MARKET_DATA] symbol={symbol} order_book error={err}")
        errors.append(err)

    try:
        market_data["whale_data"] = fetch_all_whale_data(base_asset)
    except Exception as e:
        err = f"market_data:whale:{type(e).__name__}:{e}"
        print(f"[MARKET_DATA] symbol={symbol} whale error={err}")
        errors.append(err)

    try:
        existing = fetch_positions(symbol)
        market_data["open_position"] = existing[0] if existing else None
        if market_data["open_position"]:
            print(f"[MARKET_DATA] symbol={symbol} open position found — will skip to monitor")
    except Exception as e:
        market_data["open_position"] = None

    return {**state, "market_data": market_data, "errors": errors}
