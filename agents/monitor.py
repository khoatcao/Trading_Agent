import time
from graph.state import TradingState
from tools.exchange import fetch_positions, fetch_funding_rate
from tools.risk_calc import calculate_stop_loss, calculate_take_profit, calculate_liquidation_price
from notifications.alert import send_alert
from config import MONITOR_INTERVAL_SECONDS, MAX_LEVERAGE


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


def resume_monitor_node(state: TradingState) -> TradingState:
    """Rebuilds signals and risk from an existing open position, skipping analyst/risk/execution."""
    symbol = state["symbol"]
    open_position = state.get("market_data", {}).get("open_position", {})

    side = open_position.get("side", "Buy")
    direction = "LONG" if side == "Buy" else "SHORT"
    entry_price = float(open_position.get("entryPrice") or 0)

    stop_loss = float(open_position.get("stopLoss") or 0) or calculate_stop_loss(entry_price, direction)
    take_profit = float(open_position.get("takeProfit") or 0) or calculate_take_profit(entry_price, direction)
    liq_price = calculate_liquidation_price(entry_price, MAX_LEVERAGE, direction)

    print(f"[RESUME_MONITOR] {symbol} existing {direction} entry={entry_price} sl={stop_loss} tp={take_profit}")

    return {
        **state,
        "signals": {
            "direction": direction,
            "score": 0.0,
            "confidence": "n/a",
            "reason": "Resuming monitor for existing open position",
        },
        "risk": {
            "approved": True,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "liq_price": liq_price,
            "liq_distance_pct": abs(entry_price - liq_price) / entry_price if entry_price else 0,
            "leverage": MAX_LEVERAGE,
            "margin_mode": "isolated",
            "checks": {},
            "reason": "Reconstructed from existing position",
        },
    }


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
