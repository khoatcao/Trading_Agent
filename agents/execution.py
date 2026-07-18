from graph.state import TradingState
from tools.exchange import (
    set_leverage, set_margin_mode, create_order, cancel_order,
    fetch_positions, set_trading_stop, cancel_all_conditional_orders
)
from tools.risk_calc import calculate_stop_loss, calculate_take_profit
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

        # Step 1: place market order with no SL/TP attached
        print(f"[EXECUTION-DEBUG] placing entry order symbol={symbol} side={side} amount={risk['position_size']}")
        try:
            entry_order = create_order(
                symbol=symbol,
                order_type="market",
                side=side,
                amount=risk["position_size"],
            )
            print(f"[EXECUTION-DEBUG] entry_order response={entry_order}")
        except Exception as e:
            errors.append(f"execution:create_entry_order:{str(e)}")
            print(f"[EXECUTION-ERROR] entry_order failed for {symbol}: {e}")
            raise

        # Step 2: get actual fill price from the order response
        fill_price = float(entry_order.get("average") or entry_order.get("price") or risk["entry_price"])

        # Step 3: recalculate SL/TP from actual fill price (not stale mark price)
        actual_stop_loss = calculate_stop_loss(fill_price, direction)
        actual_take_profit = calculate_take_profit(fill_price, direction)
        print(f"[EXECUTION-DEBUG] fill={fill_price} actual_sl={actual_stop_loss} actual_tp={actual_take_profit} (stale_sl={risk['stop_loss']} stale_tp={risk['take_profit']})")

        # Step 4: set SL/TP on the open position — fatal if fails
        try:
            set_trading_stop(symbol, actual_stop_loss, actual_take_profit)
            print(f"[EXECUTION-DEBUG] trading stop set sl={actual_stop_loss} tp={actual_take_profit}")
        except Exception as e:
            errors.append(f"execution:set_trading_stop:{str(e)}")
            print(f"[EXECUTION-CRITICAL] set_trading_stop failed for {symbol}: {e}")
            send_alert(
                f"🚨 *CRITICAL — UNPROTECTED POSITION*\n"
                f"Symbol: `{symbol}`\n"
                f"SL/TP could not be set: `{e}`\n"
                f"Attempting emergency close!"
            )
            try:
                create_order(symbol, "market", "sell" if direction == "LONG" else "buy",
                             risk["position_size"], params={"reduceOnly": True})
                send_alert(f"✅ Emergency close successful for `{symbol}`")
            except Exception as close_e:
                send_alert(f"🚨 *EMERGENCY CLOSE FAILED* for `{symbol}`: `{close_e}` — MANUAL ACTION REQUIRED")
            raise

        order_result = {
            "order_id": entry_order["id"],
            "filled_price": fill_price,
            "status": "open",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # update risk with actual fill-based SL/TP so monitor uses correct values
        updated_risk = {
            **risk,
            "entry_price": fill_price,
            "stop_loss": actual_stop_loss,
            "take_profit": actual_take_profit,
        }

        print(f"[EXECUTION] symbol={symbol} order_id={order_result['order_id']} side={side} amount={risk['position_size']} fill={fill_price} sl={actual_stop_loss} tp={actual_take_profit}")

        send_alert(
            f"✅ *TRADE OPENED*\n"
            f"Symbol: `{symbol}`\n"
            f"Direction: *{direction}*\n"
            f"Entry: `{fill_price}`\n"
            f"Size: `{risk['position_size']}`\n"
            f"Leverage: `{risk['leverage']}x` | Margin: `{risk['margin_mode']}`\n"
            f"Stop Loss: `{actual_stop_loss}`\n"
            f"Take Profit: `{actual_take_profit}`\n"
            f"Liquidation: `{risk['liq_price']}` ({round(risk['liq_distance_pct'] * 100, 1)}% away)\n"
            f"Score: `{state['signals'].get('score', 'N/A')}` | Confidence: `{state['signals'].get('confidence', 'N/A')}`"
        )

        log_trade({
            "symbol": symbol,
            "direction": direction,
            "entry_price": fill_price,
            "position_size": risk["position_size"],
            "leverage": risk["leverage"],
            "stop_loss": actual_stop_loss,
            "take_profit": actual_take_profit,
            "liq_price": risk["liq_price"],
            "status": "open",
            "timestamp": order_result["timestamp"],
        })

    except Exception as e:
        errors.append(f"execution:{str(e)}")
        order_result = {"status": "failed", "reason": str(e)}
        updated_risk = risk
        print(f"[EXECUTION-ERROR] execution failed for {symbol}: {e}")

    return {**state, "order_result": order_result, "risk": updated_risk, "errors": errors}


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

        # cancel existing SL/TP conditional orders before closing
        cancel_all_conditional_orders(symbol)

        close_order = create_order(
            symbol=symbol,
            order_type="market",
            side=close_side,
            amount=size,
            params={"reduceOnly": True},
        )

        # use realized PnL from close order, fall back to unrealized
        pnl = float(
            close_order.get("info", {}).get("cumRealisedPnl") or
            close_order.get("info", {}).get("realizedPnl") or
            position.get("unrealizedPnl", 0)
        )
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
            "reason": close_reason,
        })

    except Exception as e:
        errors.append(f"close_position:{str(e)}")

    return {**state, "errors": errors}
