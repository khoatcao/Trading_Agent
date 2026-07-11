import json


def build_risk_prompt(symbol: str, direction: str, entry: float, stop_loss: float,
                      take_profit: float, leverage: int, position_size: float,
                      validation: dict) -> str:
    return f"""You are a risk manager for a crypto futures trading system.

## Proposed Trade
Symbol:        {symbol}
Direction:     {direction}
Entry Price:   {entry}
Stop Loss:     {stop_loss}
Take Profit:   {take_profit}
Leverage:      {leverage}x
Position Size: {position_size}

## Risk Validation Results
{json.dumps(validation, indent=2)}

## Your Task
Write a brief 2-3 sentence risk assessment of this trade.
- If approved: confirm the risk parameters are acceptable and highlight any concerns.
- If rejected: explain clearly which check failed and why it is dangerous.

Be concise and factual. Do not suggest changing the trade direction."""
