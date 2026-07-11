Build Order

1. config.py          ← symbols, timeframe, limits, model name
2. .env               ← all API keys in one place
3. graph/state.py     ← TradingState schema (foundation everything depends on)
4. tools/exchange.py  ← Bybit connection via ccxt (needed by agents)
5. tools/whale_data.py← Arkham, Coinglass, Whale Alert, CryptoQuant fetchers
6. tools/indicators.py← RSI, MACD, EMA, BB (needed by analyst)
7. tools/risk_calc.py ← liquidation price, position sizing math
8. agents/market_data.py ← uses exchange.py + whale_data.py
9. agents/analyst.py  ← uses indicators.py + gpt-4o
10. agents/risk.py    ← uses risk_calc.py + gpt-4o
11. agents/execution.py ← uses exchange.py
12. agents/monitor.py ← uses exchange.py
13. agents/supervisor.py ← uses gpt-4o
14. prompts/*.py      ← analyst, risk, supervisor prompts
15. graph/graph.py    ← wire everything together
16. memory/checkpointer.py ← SqliteSaver
17. memory/trade_log.py    ← trade history DB
18. notifications/alert.py ← Telegram
19. main.py           ← entry point
20. tests/            ← test each agent in paper mode

---
Why This Order