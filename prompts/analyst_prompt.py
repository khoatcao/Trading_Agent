import json


def build_analyst_prompt(symbol: str, indicators: dict, futures: dict, whale: dict) -> str:
    return f"""You are a professional crypto futures trader analyzing {symbol} on a 15-minute timeframe.

## Technical Indicators
{json.dumps(indicators, indent=2)}

## Futures Market Data
{json.dumps(futures, indent=2)}

## Whale & On-Chain Data
{json.dumps(whale, indent=2)}

## Your Task
Analyze all data above and decide whether to go LONG, SHORT, or take NO trade.

Rules:
- RSI > 70 = overbought (bearish signal), RSI < 30 = oversold (bullish signal)
- Price above EMA_200 = bullish bias, below = bearish bias
- MACD histogram positive and rising = bullish momentum
- Funding rate > +0.05% = crowded longs = bearish signal
- Funding rate < -0.05% = crowded shorts = bullish signal
- OI rising with price rising = trend confirmation
- OI rising with price falling = bearish divergence
- Large exchange inflow from whale = sell pressure incoming (bearish)
- Large exchange outflow from whale = accumulation (bullish)
- High liquidations on shorts = bullish momentum
- High liquidations on longs = bearish momentum

Score rules:
- Score range: -1.0 (strong SHORT) to +1.0 (strong LONG)
- Score 0.0 = no clear signal
- Only recommend a trade if |score| >= 0.6

Respond ONLY with valid JSON in this exact format:
{{
  "direction": "LONG" | "SHORT" | "NONE",
  "score": <float between -1.0 and 1.0>,
  "confidence": "low" | "medium" | "high",
  "reason": "<one paragraph explanation>",
  "technical": {{
    "rsi_signal": "<bullish|bearish|neutral>",
    "macd_signal": "<bullish|bearish|neutral>",
    "ema_signal": "<bullish|bearish|neutral>",
    "bb_signal": "<bullish|bearish|neutral>"
  }},
  "futures": {{
    "funding_signal": "<bullish|bearish|neutral>",
    "oi_signal": "<bullish|bearish|neutral>"
  }},
  "whale": {{
    "arkham_signal": "<bullish|bearish|neutral>",
    "inflow_signal": "<bullish|bearish|neutral>",
    "liquidation_signal": "<bullish|bearish|neutral>"
  }}
}}"""
