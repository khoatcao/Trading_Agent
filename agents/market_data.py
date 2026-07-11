from graph.state import TradingState
from tools.exchange import (
    fetch_ohlcv, fetch_ticker, fetch_funding_rate,
    fetch_open_interest, fetch_order_book
)
from tools.whale_data import fetch_all_whale_data


def market_data_node(state: TradingState) -> TradingState:
    symbol = state["symbol"]
    timeframe = state["timeframe"]
    base_asset = symbol.split("/")[0]  # "BTC" from "BTC/USDT:USDT"

    errors = state.get("errors", [])
    market_data = {}

    try:
        market_data["ohlcv"] = fetch_ohlcv(symbol, timeframe)
    except Exception as e:
        errors.append(f"market_data:ohlcv:{str(e)}")

    try:
        ticker = fetch_ticker(symbol)
        market_data["mark_price"] = ticker.get("info", {}).get("markPrice") or ticker.get("last")
        market_data["last_price"] = ticker.get("last")
        market_data["bid"] = ticker.get("bid")
        market_data["ask"] = ticker.get("ask")
    except Exception as e:
        errors.append(f"market_data:ticker:{str(e)}")

    try:
        funding = fetch_funding_rate(symbol)
        market_data["funding_rate"] = funding.get("fundingRate")
        market_data["next_funding_time"] = funding.get("fundingDatetime")
    except Exception as e:
        errors.append(f"market_data:funding:{str(e)}")

    try:
        oi = fetch_open_interest(symbol)
        market_data["open_interest"] = oi.get("openInterest")
    except Exception as e:
        errors.append(f"market_data:open_interest:{str(e)}")

    try:
        market_data["order_book"] = fetch_order_book(symbol)
    except Exception as e:
        errors.append(f"market_data:order_book:{str(e)}")

    try:
        market_data["whale_data"] = fetch_all_whale_data(base_asset)
    except Exception as e:
        errors.append(f"market_data:whale:{str(e)}")

    return {**state, "market_data": market_data, "errors": errors}
