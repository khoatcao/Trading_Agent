from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from graph.state import TradingState
from tools.risk_calc import (
    calculate_stop_loss, calculate_take_profit,
    calculate_position_size, validate_risk
)
from tools.exchange import fetch_balance, fetch_all_positions
from memory.trade_log import get_daily_starting_balance, save_daily_starting_balance
from prompts.risk_prompt import build_risk_prompt
from config import LLM_MODEL, LLM_TEMPERATURE, MAX_LEVERAGE, MARGIN_MODE, MAX_POSITIONS, OLLAMA_BASE_URL
import json


llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE, base_url=OLLAMA_BASE_URL)


def risk_node(state: TradingState) -> TradingState:
    symbol = state.get("symbol", "UNKNOWN")
    signals = state["signals"]
    market_data = state["market_data"]
    errors = state.get("errors", [])
    risk = {}

    try:
        direction = signals["direction"]
        entry = float(market_data["mark_price"])

        balance_data = fetch_balance()
        balance = float(balance_data["USDT"]["free"])
        equity = float(balance_data["USDT"]["total"])

        # check max concurrent positions
        open_positions = fetch_all_positions()
        if len(open_positions) >= MAX_POSITIONS:
            risk = {
                "approved": False,
                "checks": {"max_positions_ok": False},
                "reason": f"Max concurrent positions ({MAX_POSITIONS}) already open — skipping new trade.",
            }
            print(f"[RISK] symbol={state.get('symbol')} rejected — max positions reached ({len(open_positions)}/{MAX_POSITIONS})")
            return {**state, "risk": risk, "errors": errors}

        # get or save today's starting balance for drawdown check
        starting_balance = get_daily_starting_balance()
        if starting_balance is None:
            starting_balance = equity
            save_daily_starting_balance(equity)

        stop_loss = calculate_stop_loss(entry, direction)
        take_profit = calculate_take_profit(entry, direction)
        leverage = min(MAX_LEVERAGE, 5)

        position_size = calculate_position_size(balance, entry, stop_loss)

        validation = validate_risk(
            entry=entry,
            leverage=leverage,
            direction=direction,
            position_size=position_size,
            balance=balance,
            starting_balance=starting_balance,
            current_balance=equity,
        )

        prompt = build_risk_prompt(
            symbol=state["symbol"],
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage,
            position_size=position_size,
            validation=validation,
        )
        response = llm.invoke([HumanMessage(content=prompt)])

        symbol = state.get("symbol", "UNKNOWN")
        risk = {
            "approved": validation["approved"],
            "position_size": position_size,
            "leverage": leverage,
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "liq_price": validation["liq_price"],
            "liq_distance_pct": validation["liq_distance_pct"],
            "margin_mode": MARGIN_MODE,
            "checks": validation["checks"],
            "reason": response.content.strip(),
        }
        print(f"[RISK] symbol={symbol} approved={risk['approved']} position_size={risk['position_size']} leverage={risk['leverage']} entry={risk['entry_price']} stop_loss={risk['stop_loss']} tp={risk['take_profit']}")
        if not risk["approved"]:
            print(f"[RISK] symbol={symbol} decision=REJECTED reason={risk.get('reason')}")
        # verbose debug: show balance, position value and validation checks
        try:
            print(f"[RISK-DEBUG] balance={balance} position_value={round(validation.get('position_value', position_size*entry),6)} checks={validation['checks']} liq_price={validation['liq_price']} liq_distance_pct={validation['liq_distance_pct']}")
        except Exception:
            pass

    except Exception as e:
        errors.append(f"risk:{str(e)}")
        risk = {"approved": False, "reason": str(e)}
        print(f"[RISK] symbol={state.get('symbol')} error={e}")

    return {**state, "risk": risk, "errors": errors}
