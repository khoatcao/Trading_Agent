Build Order

1. config.py             ← symbols (DOGE, XRP, ADA), timeframe, risk limits, Ollama model
2. .env                  ← Bybit API keys + Telegram bot token + chat ID
3. graph/state.py        ← TradingState schema (foundation everything depends on)
4. tools/exchange.py     ← Bybit connection via ccxt (needed by agents)
5. tools/whale_data.py   ← whale inflow/outflow via Bybit + DefiLlama (free, no key)
6. tools/indicators.py   ← RSI, MACD, EMA, BB (needed by analyst)
7. tools/risk_calc.py    ← liquidation price, position sizing math
8. agents/market_data.py ← uses exchange.py + whale_data.py
9. agents/analyst.py     ← uses indicators.py + qwen2.5:7b (Ollama)
10. agents/risk.py       ← uses risk_calc.py + qwen2.5:7b (Ollama)
11. agents/execution.py  ← uses exchange.py, sends Telegram on open/close
12. agents/monitor.py    ← uses exchange.py, sets close_reason, sends Telegram margin warning
13. agents/supervisor.py ← rule-based routing + Telegram on signal skip / risk reject
14. prompts/*.py         ← analyst, risk, supervisor prompts
15. graph/graph.py       ← wire everything together
16. memory/checkpointer.py ← SqliteSaver
17. memory/trade_log.py  ← trade history DB
18. notifications/alert.py ← Telegram Bot API wrapper
19. main.py              ← entry point
20. test_run.py          ← dry run to verify agents without placing real orders

---

## Why This Order

- `config.py` and `.env` first — every other file imports from them
- `state.py` second — defines the shared data contract all agents depend on
- `tools/` before `agents/` — agents import from tools, not the other way around
- `notifications/alert.py` before agents — agents call `send_alert` directly
- `graph/graph.py` last among source files — wires agents together, needs all of them
- `main.py` after graph — just invokes the graph
- `test_run.py` last — validates the full pipeline end to end

---

## Key Config Values (config.py)

| Setting | Value |
|---|---|
| Exchange | Bybit |
| Symbols | DOGE/USDT:USDT, XRP/USDT:USDT, ADA/USDT:USDT |
| Timeframe | 15m |
| Candle limit | 200 |
| LLM model | qwen2.5:7b (local Ollama) |
| Max leverage | 2x |
| Margin mode | isolated |
| Risk per trade | 1% of balance |
| Max exposure | 25% of portfolio |
| Stop loss | 3% from entry |
| Take profit | 5% from entry |
| Min liq distance | 15% |
| Max daily drawdown | 5% |
| Signal threshold | 0.6 (score must be ≥ 0.6 to trade) |
| Monitor interval | 120 seconds (every 2 minutes) |
