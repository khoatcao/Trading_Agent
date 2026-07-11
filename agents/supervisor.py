from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from graph.state import TradingState
from prompts.supervisor_prompt import build_supervisor_prompt
from config import LLM_MODEL, LLM_TEMPERATURE, SIGNAL_THRESHOLD, OPENAI_API_KEY, OPENAI_API_BASE


llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)


def route_after_analyst(state: TradingState) -> str:
    signals = state.get("signals", {})
    score = abs(float(signals.get("score", 0.0)))
    direction = signals.get("direction", "NONE")

    if direction == "NONE" or score < SIGNAL_THRESHOLD:
        return "end"
    return "risk"


def route_after_risk(state: TradingState) -> str:
    risk = state.get("risk", {})
    if not risk.get("approved", False):
        return "end"
    return "execution"


def route_after_monitor(state: TradingState) -> str:
    action = state.get("monitor_action", "HOLD")
    if action in ("CLOSE", "REDUCE"):
        return "execution"
    return "monitor"
