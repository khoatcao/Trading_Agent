from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class TradingState(TypedDict):
    # inputs
    symbol: str
    timeframe: str

    # market data (filled by market_data agent)
    market_data: dict
    # keys: ohlcv, funding_rate, predicted_funding, open_interest,
    #       mark_price, last_price, order_book,
    #       arkham_flows, coinglass_data, whale_alerts, cryptoquant_data

    # signals (filled by analyst agent)
    signals: dict
    # keys: direction (LONG|SHORT|NONE), score (-1.0 to 1.0),
    #       confidence, reason, technical, futures, whale

    # risk assessment (filled by risk agent)
    risk: dict
    # keys: approved (bool), position_size, leverage, entry_price,
    #       stop_loss, take_profit, liq_price, margin_mode, reason

    # execution result (filled by execution agent)
    order_result: dict
    # keys: order_id, sl_order_id, tp_order_id,
    #       filled_price, status, timestamp

    # monitor decision (filled by monitor agent)
    monitor_action: str
    # values: HOLD | CLOSE | REDUCE

    # agent messages / reasoning trace
    messages: Annotated[list, add_messages]

    # control
    iteration: int
    errors: list
