from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from graph.state import TradingState
from tools.risk_calc import (
    calculate_stop_loss, calculate_take_profit,
    calculate_position_size, validate_risk
)
from tools.exchange import fetch_balance
from prompts.risk_prompt import build_risk_prompt
from config import LLM_MODEL, LLM_TEMPERATURE, MAX_LEVERAGE, MARGIN_MODE, OPENAI_API_KEY, OPENAI_API_BASE
import json


llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)


def risk_node(state: TradingState) -> TradingState:
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
            starting_balance=equity,
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

    except Exception as e:
        errors.append(f"risk:{str(e)}")
        risk = {"approved": False, "reason": str(e)}

    return {**state, "risk": risk, "errors": errors}
