import time
from graph.state import TradingState
from tools.exchange import fetch_positions, fetch_funding_rate
from config import MONITOR_INTERVAL_SECONDS


FUNDING_RATE_THRESHOLD = 0.001   # 0.1% — spike threshold
MARGIN_RATIO_THRESHOLD = 0.80    # 80% margin usage — reduce position


def monitor_node(state: TradingState) -> TradingState:
    symbol = state["symbol"]
    risk = state["risk"]
    errors = state.get("errors", [])
    monitor_action = "HOLD"

    try:
        positions = fetch_positions(symbol)
        if not positions:
            return {**state, "monitor_action": "CLOSE", "errors": errors}

        position = positions[0]
        unrealized_pnl = float(position.get("unrealizedPnl", 0))
        entry_price = float(position.get("entryPrice", risk["entry_price"]))
        mark_price = float(position.get("markPrice", entry_price))
        margin_ratio = float(position.get("marginRatio", 0))
        direction = state["signals"]["direction"]

        # check stop loss
        if direction == "LONG" and mark_price <= risk["stop_loss"]:
            monitor_action = "CLOSE"
        elif direction == "SHORT" and mark_price >= risk["stop_loss"]:
            monitor_action = "CLOSE"

        # check take profit
        elif direction == "LONG" and mark_price >= risk["take_profit"]:
            monitor_action = "CLOSE"
        elif direction == "SHORT" and mark_price <= risk["take_profit"]:
            monitor_action = "CLOSE"

        # check funding rate spike
        elif _funding_rate_spiked(symbol, direction):
            monitor_action = "CLOSE"

        # check margin ratio
        elif margin_ratio >= MARGIN_RATIO_THRESHOLD:
            monitor_action = "REDUCE"

    except Exception as e:
        errors.append(f"monitor:{str(e)}")

    return {**state, "monitor_action": monitor_action, "errors": errors}


def _funding_rate_spiked(symbol: str, direction: str) -> bool:
    try:
        funding = fetch_funding_rate(symbol)
        rate = float(funding.get("fundingRate", 0))
        if direction == "LONG" and rate > FUNDING_RATE_THRESHOLD:
            return True
        if direction == "SHORT" and rate < -FUNDING_RATE_THRESHOLD:
            return True
    except Exception:
        pass
    return False
