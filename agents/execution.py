from graph.state import TradingState
from tools.exchange import (
    set_leverage, set_margin_mode, create_order, cancel_order, fetch_positions
)
from notifications.alert import send_alert
from memory.trade_log import log_trade
from datetime import datetime, timezone


def execution_node(state: TradingState) -> TradingState:
    risk = state["risk"]
    signals = state["signals"]
    symbol = state["symbol"]
    errors = state.get("errors", [])
    order_result = {}

    direction = signals["direction"]
    side = "buy" if direction == "LONG" else "sell"
    close_side = "sell" if direction == "LONG" else "buy"
    sl_trigger = 2 if direction == "LONG" else 1
    tp_trigger = 1 if direction == "LONG" else 2

    try:
        set_margin_mode(symbol, risk["margin_mode"])
        set_leverage(symbol, risk["leverage"])

        print(f"[EXECUTION-DEBUG] placing entry order symbol={symbol} side={side} amount={risk['position_size']} sl={risk['stop_loss']} tp={risk['take_profit']}")
        try:
            entry_order = create_order(
                symbol=symbol,
                order_type="market",
                side=side,
                amount=risk["position_size"],
                params={
                    "stopLoss": risk["stop_loss"],
                    "takeProfit": risk["take_profit"],
                    "slTriggerBy": "MarkPrice",
                    "tpTriggerBy": "MarkPrice",
                    "tpslMode": "Full",
                    "slOrderType": "Market",
                    "tpOrderType": "Market",
                },
            )
            print(f"[EXECUTION-DEBUG] entry_order response={entry_order}")
        except Exception as e:
            errors.append(f"execution:create_entry_order:{str(e)}")
            print(f"[EXECUTION-ERROR] entry_order failed for {symbol}: {e}")
            raise

        order_result = {
            "order_id": entry_order["id"],
            "sl_order_id": entry_order.get("info", {}).get("stopLoss"),
            "tp_order_id": entry_order.get("info", {}).get("takeProfit"),
            "filled_price": entry_order.get("average") or risk["entry_price"],
            "status": "open",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print(f"[EXECUTION] symbol={symbol} order_id={order_result['order_id']} side={side} amount={risk['position_size']} status={order_result['status']}")

        send_alert(
            f"✅ *TRADE OPENED*\n"
            f"Symbol: `{symbol}`\n"
            f"Direction: *{direction}*\n"
            f"Entry: `{order_result['filled_price']}`\n"
            f"Size: `{risk['position_size']}`\n"
            f"Leverage: `{risk['leverage']}x` | Margin: `{risk['margin_mode']}`\n"
            f"Stop Loss: `{risk['stop_loss']}`\n"
            f"Take Profit: `{risk['take_profit']}`\n"
            f"Liquidation: `{risk['liq_price']}` ({round(risk['liq_distance_pct'] * 100, 1)}% away)\n"
            f"Score: `{state['signals'].get('score', 'N/A')}` | Confidence: `{state['signals'].get('confidence', 'N/A')}`"
        )

        log_trade({
            "symbol": symbol,
            "direction": direction,
            "entry_price": order_result["filled_price"],
            "position_size": risk["position_size"],
            "leverage": risk["leverage"],
            "stop_loss": risk["stop_loss"],
            "take_profit": risk["take_profit"],
            "liq_price": risk["liq_price"],
            "status": "open",
            "timestamp": order_result["timestamp"],
        })

    except Exception as e:
        errors.append(f"execution:{str(e)}")
        order_result = {"status": "failed", "reason": str(e)}
        print(f"[EXECUTION-ERROR] execution failed for {symbol}: {e}")

    return {**state, "order_result": order_result, "errors": errors}


def close_position_node(state: TradingState) -> TradingState:
    symbol = state["symbol"]
    signals = state["signals"]
    order_result = state.get("order_result", {})
    errors = state.get("errors", [])

    direction = signals["direction"]
    close_side = "sell" if direction == "LONG" else "buy"

    sl_trigger = 2 if direction == "LONG" else 1
    tp_trigger = 1 if direction == "LONG" else 2

    try:
        positions = fetch_positions(symbol)
        if not positions:
            return {**state, "monitor_action": "CLOSE", "errors": errors}

        position = positions[0]
        size = float(position["contracts"])

        close_order = create_order(
            symbol=symbol,
            order_type="market",
            side=close_side,
            amount=size,
            params={"reduceOnly": True},
        )

        pnl = float(position.get("unrealizedPnl", 0))
        close_price = close_order.get("average") or position.get("markPrice", "N/A")
        entry_price = position.get("entryPrice", state.get("risk", {}).get("entry_price", "N/A"))
        close_reason = state.get("close_reason") or state.get("monitor_action", "CLOSE")
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        send_alert(
            f"{pnl_emoji} *TRADE CLOSED*\n"
            f"Symbol: `{symbol}`\n"
            f"Direction: *{direction}*\n"
            f"Reason: {close_reason}\n"
            f"Entry: `{entry_price}` → Close: `{close_price}`\n"
            f"PnL: `{round(pnl, 4)} USDT`"
        )

        log_trade({
            "symbol": symbol,
            "direction": direction,
            "status": "closed",
            "close_price": close_order.get("average"),
            "pnl": pnl,
            "reason": state.get("monitor_action", "CLOSE"),
        })

    except Exception as e:
        errors.append(f"close_position:{str(e)}")

    return {**state, "errors": errors}
