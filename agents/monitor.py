import time
from graph.state import TradingState
from tools.exchange import fetch_positions, fetch_funding_rate
from notifications.alert import send_alert
from config import MONITOR_INTERVAL_SECONDS


FUNDING_RATE_THRESHOLD = 0.001   # 0.1% — spike threshold
MARGIN_RATIO_THRESHOLD = 0.80    # 80% margin usage — reduce position


def monitor_node(state: TradingState) -> TradingState:
    symbol = state["symbol"]
    risk = state["risk"]
    errors = state.get("errors", [])
    monitor_action = "HOLD"
    close_reason = ""

    try:
        positions = fetch_positions(symbol)
        if not positions:
            close_reason = "Position Not Found on Exchange"
            return {**state, "monitor_action": "CLOSE", "close_reason": close_reason, "errors": errors}

        position = positions[0]
        unrealized_pnl = float(position.get("unrealizedPnl", 0))
        entry_price = float(position.get("entryPrice", risk["entry_price"]))
        mark_price = float(position.get("markPrice", entry_price))
        margin_ratio = float(position.get("marginRatio", 0))
        direction = state["signals"]["direction"]

        # check stop loss
        if direction == "LONG" and mark_price <= risk["stop_loss"]:
            monitor_action = "CLOSE"
            close_reason = f"Stop Loss Hit (mark={mark_price}, sl={risk['stop_loss']})"
        elif direction == "SHORT" and mark_price >= risk["stop_loss"]:
            monitor_action = "CLOSE"
            close_reason = f"Stop Loss Hit (mark={mark_price}, sl={risk['stop_loss']})"

        # check take profit
        elif direction == "LONG" and mark_price >= risk["take_profit"]:
            monitor_action = "CLOSE"
            close_reason = f"Take Profit Hit (mark={mark_price}, tp={risk['take_profit']})"
        elif direction == "SHORT" and mark_price <= risk["take_profit"]:
            monitor_action = "CLOSE"
            close_reason = f"Take Profit Hit (mark={mark_price}, tp={risk['take_profit']})"

        # check funding rate spike
        elif _funding_rate_spiked(symbol, direction):
            monitor_action = "CLOSE"
            close_reason = "Funding Rate Spike Against Position"

        # check margin ratio
        elif margin_ratio >= MARGIN_RATIO_THRESHOLD:
            monitor_action = "REDUCE"
            close_reason = f"High Margin Ratio ({round(margin_ratio * 100, 1)}%)"
            send_alert(
                f"⚠️ *MARGIN WARNING*\n"
                f"Symbol: `{symbol}`\n"
                f"Margin Ratio: {round(margin_ratio * 100, 1)}%\n"
                f"Unrealized PnL: {unrealized_pnl}\n"
                f"Action: Reducing position"
            )

    except Exception as e:
        errors.append(f"monitor:{str(e)}")

    return {**state, "monitor_action": monitor_action, "close_reason": close_reason, "errors": errors}


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
