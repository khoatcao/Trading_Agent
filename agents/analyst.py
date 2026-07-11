from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from graph.state import TradingState
from tools.indicators import get_all_indicators
from prompts.analyst_prompt import build_analyst_prompt
from config import LLM_MODEL, LLM_TEMPERATURE, SIGNAL_THRESHOLD, OPENAI_API_KEY, OPENAI_API_BASE
import json
import re


def normalize_json_response(raw: str) -> str:
    cleaned = raw or ""
    cleaned = cleaned.strip()
    # remove typical markdown fences and language markers
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE)
    # unwrap surrounding quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    # extract first {...} block robustly
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end+1]
    else:
        # fallback to regex capture for multiline braces
        match = re.search(r"(\{(?:.*\n)*.*\})", cleaned, flags=re.DOTALL)
        if match:
            cleaned = match.group(1)
    return cleaned.strip()


llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)


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
            timeframe=state["timeframe"],
            indicators=indicators,
            futures=futures_context,
            whale=whale_context,
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        cleaned = normalize_json_response(raw)
        print(f"[ANALYST] symbol={state['symbol']} raw_response={raw!r}")
        print(f"[ANALYST] symbol={state['symbol']} cleaned_response={cleaned!r}")

        parsed = json.loads(cleaned)
        signals = {
            "direction": parsed.get("direction", "NONE"),
            "score": float(parsed.get("score", 0.0)),
            "confidence": parsed.get("confidence", "low"),
            "reason": parsed.get("reason", ""),
            "technical": parsed.get("technical", {}),
            "futures": parsed.get("futures", {}),
            "whale": parsed.get("whale", {}),
        }
        print(f"[ANALYST] symbol={state['symbol']} direction={signals['direction']} score={signals['score']} confidence={signals['confidence']}")

    except json.JSONDecodeError as jde:
        errors.append(f"analyst:json_decode_error:{str(jde)}")
        signals = {"direction": "NONE", "score": 0.0, "confidence": "low", "reason": f"Invalid JSON from analyst: {str(jde)}"}
        print(f"[ANALYST] symbol={state['symbol']} json error={jde} raw_response={raw!r} cleaned_response={cleaned!r}")
    except Exception as e:
        errors.append(f"analyst:{str(e)}")
        signals = {"direction": "NONE", "score": 0.0, "confidence": "low", "reason": str(e)}
        print(f"[ANALYST] symbol={state['symbol']} error={e}")

    return {**state, "signals": signals, "errors": errors}
