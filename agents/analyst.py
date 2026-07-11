from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from graph.state import TradingState
from tools.indicators import get_all_indicators
from prompts.analyst_prompt import build_analyst_prompt
from config import LLM_MODEL, LLM_TEMPERATURE, SIGNAL_THRESHOLD
import json


llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)


def analyst_node(state: TradingState) -> TradingState:
    market_data = state["market_data"]
    errors = state.get("errors", [])
    signals = {}

    try:
        indicators = get_all_indicators(market_data["ohlcv"])

        futures_context = {
            "funding_rate": market_data.get("funding_rate"),
            "open_interest": market_data.get("open_interest"),
            "mark_price": market_data.get("mark_price"),
            "last_price": market_data.get("last_price"),
        }

        whale_context = market_data.get("whale_data", {})

        prompt = build_analyst_prompt(
            symbol=state["symbol"],
            indicators=indicators,
            futures=futures_context,
            whale=whale_context,
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        parsed = json.loads(raw)
        signals = {
            "direction": parsed.get("direction", "NONE"),
            "score": float(parsed.get("score", 0.0)),
            "confidence": parsed.get("confidence", "low"),
            "reason": parsed.get("reason", ""),
            "technical": parsed.get("technical", {}),
            "futures": parsed.get("futures", {}),
            "whale": parsed.get("whale", {}),
        }

    except Exception as e:
        errors.append(f"analyst:{str(e)}")
        signals = {"direction": "NONE", "score": 0.0, "confidence": "low", "reason": str(e)}

    return {**state, "signals": signals, "errors": errors}
