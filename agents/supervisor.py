from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from graph.state import TradingState
from prompts.supervisor_prompt import build_supervisor_prompt
from notifications.alert import send_alert
from config import LLM_MODEL, LLM_TEMPERATURE, SIGNAL_THRESHOLD, OLLAMA_BASE_URL


llm = ChatOllama(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    base_url=OLLAMA_BASE_URL,
)


def route_after_market_data(state: TradingState) -> str:
    open_position = state.get("market_data", {}).get("open_position")
    symbol = state.get("symbol", "UNKNOWN")
    if open_position:
        print(f"[SUPERVISOR] route_after_market_data -> resume_monitor (position already open for {symbol})")
        return "resume_monitor"
    print(f"[SUPERVISOR] route_after_market_data -> analyst (no open position for {symbol})")
    return "analyst"


def route_after_analyst(state: TradingState) -> str:
    signals = state.get("signals", {})
    score = abs(float(signals.get("score", 0.0)))
    direction = signals.get("direction", "NONE")
    symbol = state.get("symbol", "UNKNOWN")

    route = "end" if direction == "NONE" or score < SIGNAL_THRESHOLD else "risk"

    print(
        f"[SUPERVISOR] route_after_analyst -> {route} "
        f"(direction={direction}, score={score})"
    )
    return route


def route_after_risk(state: TradingState) -> str:
    risk = state.get("risk", {})
    approved = bool(risk.get("approved", False))
    symbol = state.get("symbol", "UNKNOWN")

    route = "execution" if approved else "end"

    if not approved:
        checks = risk.get("checks", {})
        failed = [k for k, v in checks.items() if not v]
        send_alert(
            f"🚫 *RISK REJECTED*\n"
            f"Symbol: `{symbol}`\n"
            f"Direction: `{state.get('signals', {}).get('direction', 'N/A')}`\n"
            f"Failed checks: `{', '.join(failed) if failed else 'unknown'}`\n"
            f"Assessment: {risk.get('reason', '')[:300]}"
        )

    print(f"[SUPERVISOR] route_after_risk -> {route} (approved={approved})")
    return route


def route_after_monitor(state: TradingState) -> str:
    action = state.get("monitor_action", "HOLD")

    if action in ("CLOSE", "REDUCE"):
        route = "close_position"
    else:
        route = "end"

    print(f"[SUPERVISOR] route_after_monitor -> {route} (action={action})")
    return route