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

    try:
        set_margin_mode(symbol, risk["margin_mode"])
        set_leverage(symbol, risk["leverage"])

        print(f"[EXECUTION-DEBUG] placing entry order symbol={symbol} side={side} amount={risk['position_size']}")
        try:
            entry_order = create_order(
                symbol=symbol,
                order_type="market",
                side=side,
                amount=risk["position_size"],
                params={"positionIdx": 1},
            )
            print(f"[EXECUTION-DEBUG] entry_order response={entry_order}")
        except Exception as e:
            errors.append(f"execution:create_entry_order:{str(e)}")
            print(f"[EXECUTION-ERROR] entry_order failed for {symbol}: {e}")
            raise

        print(f"[EXECUTION-DEBUG] placing SL order symbol={symbol} side={close_side} stop={risk['stop_loss']}")
        try:
            sl_order = create_order(
                symbol=symbol,
                order_type="stop_market",
                side=close_side,
                amount=risk["position_size"],
                params={
                    "stopPrice": risk["stop_loss"],
                    "reduceOnly": True,
                    "positionIdx": 1,
                },
            )
            print(f"[EXECUTION-DEBUG] sl_order response={sl_order}")
        except Exception as e:
            errors.append(f"execution:create_sl_order:{str(e)}")
            print(f"[EXECUTION-ERROR] sl_order failed for {symbol}: {e}")
            raise

        print(f"[EXECUTION-DEBUG] placing TP order symbol={symbol} side={close_side} tp={risk['take_profit']}")
        try:
            tp_order = create_order(
                symbol=symbol,
                order_type="take_profit_market",
                side=close_side,
                amount=risk["position_size"],
                params={
                    "stopPrice": risk["take_profit"],
                    "reduceOnly": True,
                    "positionIdx": 1,
                },
            )
            print(f"[EXECUTION-DEBUG] tp_order response={tp_order}")
        except Exception as e:
            errors.append(f"execution:create_tp_order:{str(e)}")
            print(f"[EXECUTION-ERROR] tp_order failed for {symbol}: {e}")
            raise

        order_result = {
            "order_id": entry_order["id"],
            "sl_order_id": sl_order["id"],
            "tp_order_id": tp_order["id"],
            "filled_price": entry_order.get("average") or risk["entry_price"],
            "status": "open",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print(f"[EXECUTION] symbol={symbol} order_id={order_result['order_id']} side={side} amount={risk['position_size']} status={order_result['status']}")

        send_alert(
            f"TRADE OPENED\n"
            f"Symbol: {symbol}\n"
            f"Direction: {direction}\n"
            f"Entry: {order_result['filled_price']}\n"
            f"Size: {risk['position_size']}\n"
            f"Leverage: {risk['leverage']}x\n"
            f"SL: {risk['stop_loss']}  TP: {risk['take_profit']}\n"
            f"Liq: {risk['liq_price']}"
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

        pnl = position.get("unrealizedPnl", 0)
        send_alert(
            f"TRADE CLOSED\n"
            f"Symbol: {symbol}\n"
            f"Reason: {state.get('monitor_action', 'CLOSE')}\n"
            f"PnL: {pnl}"
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
