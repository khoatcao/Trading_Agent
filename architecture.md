# Trading Agent Architecture

## Overview

A multi-agent crypto futures trading system built with LangChain and LangGraph.
Targets perpetual futures contracts (BTC/USDT, ETH/USDT, etc.) on Bybit.
Timeframe: 15 minutes. LLM: OpenAI gpt-4o.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER / SCHEDULER                          │
│                     (trigger: every 15 minutes)                  │
└─────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      SUPERVISOR AGENT (gpt-4o)                   │
│   • Reads current state                                          │
│   • Decides which agent to call next                             │
│   • Routes via conditional edges in LangGraph                    │
└───┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌───────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌─────────┐
│Market │ │Analyst │ │Risk    │ │Execution│ │Monitor  │
│Data   │ │Agent   │ │Agent   │ │Agent    │ │Agent    │
│Agent  │ │(gpt-4o)│ │(gpt-4o)│ │(no LLM) │ │(no LLM) │
└───┬───┘ └───┬────┘ └───┬────┘ └───┬─────┘ └───┬─────┘
    │         │          │          │            │
    └─────────────────────┴──────────┴────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        SHARED STATE                              │
│              (LangGraph StateGraph + SqliteSaver)                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent Responsibilities

| Agent | Job | LLM | Output to State |
|---|---|---|---|
| Supervisor | Routes to next agent based on current state | gpt-4o | next node name |
| Market Data | Fetches candles, funding, OI, whale data | None | state.market_data |
| Analyst | Generates trade signal (direction + score) | gpt-4o | state.signals |
| Risk | Validates trade, calculates size + liq price | gpt-4o | state.risk |
| Execution | Places entry, stop-loss, take-profit orders | None | state.order_result |
| Monitor | Watches open position every 2 minutes | None | state.monitor_action |

---

## Folder Structure

```
trading_agent/
├── .env                          ← API keys (Bybit, OpenAI, Arkham, Coinglass, Whale Alert, CryptoQuant, Telegram)
├── config.py                     ← global settings (symbols, timeframe=15m, limits)
├── main.py                       ← entry point, runs the graph
│
├── graph/
│   ├── state.py                  ← TradingState schema
│   └── graph.py                  ← StateGraph wiring + edges
│
├── agents/
│   ├── supervisor.py             ← routing logic, next-node decision
│   ├── market_data.py            ← fetch candles, funding, OI, whale data
│   ├── analyst.py                ← technical + futures + whale signal generation
│   ├── risk.py                   ← position sizing, liq price, safety checks
│   ├── execution.py              ← place/close orders, set leverage/margin
│   └── monitor.py                ← watch open position every 2 min, manage exit
│
├── tools/
│   ├── exchange.py               ← ccxt Bybit wrappers (connect, fetch, order)
│   ├── indicators.py             ← RSI, MACD, EMA, BB, volume
│   ├── risk_calc.py              ← liquidation price, margin ratio, sizing
│   └── whale_data.py             ← Arkham, Coinglass, Whale Alert, CryptoQuant
│
├── prompts/
│   ├── analyst_prompt.py         ← LLM prompt for signal reasoning
│   ├── risk_prompt.py            ← LLM prompt for risk narrative
│   └── supervisor_prompt.py      ← LLM prompt for routing decision
│
├── memory/
│   ├── checkpointer.py           ← SqliteSaver setup for graph state
│   └── trade_log.py              ← persist trade history to DB
│
├── notifications/
│   └── alert.py                  ← Telegram alert on trade/error
│
└── tests/
    ├── test_market_data.py
    ├── test_analyst.py
    ├── test_risk.py
    └── test_execution.py         ← paper trade tests only
```

---

## Agent Flow

### One Full Cycle (e.g. BTC/USDT Perpetual on Bybit)

```
EVERY 15 MINUTES (scheduler triggers)
          │
          ▼
┌───────────────────────────┐
│    MARKET DATA AGENT      │
│                           │
│  Bybit (ccxt):            │
│  ├─ 15m OHLCV candles     │
│  ├─ Funding rate          │
│  ├─ Open Interest         │
│  ├─ Mark price / ticker   │
│  └─ Order book depth      │
│                           │
│  Bybit (free, ccxt):      │
│  ├─ Long/Short ratio      │
│  └─ Liquidations          │
│                           │
│  CoinGecko (free):        │
│  ├─ 24h price change %    │
│  ├─ 24h volume            │
│  └─ High / Low 24h        │
│                           │
│  DefiLlama (no key):      │
│  └─ Global TVL change     │
│                           │
│  Whale Alert:             │
│  └─ Large on-chain txns   │
│                           │
│  CryptoQuant:             │
│  └─ Exchange inflow/outflow│
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│     ANALYST AGENT         │
│     (gpt-4o)              │
│                           │
│  Technical signals:       │
│  ├─ RSI(14)               │
│  ├─ MACD                  │
│  ├─ EMA(20, 50, 200)      │
│  └─ Bollinger Bands       │
│                           │
│  Futures signals:         │
│  ├─ Funding rate trend    │
│  ├─ OI divergence         │
│  └─ L/S ratio skew        │
│                           │
│  Whale signals:           │
│  ├─ Arkham entity flows   │
│  ├─ Exchange inflow spike │
│  └─ Liquidation cascade   │
│                           │
│  gpt-4o synthesizes all   │
│  → direction + score      │
└───────────┬───────────────┘
            │
     ┌──────┴──────┐
     │ score < 0.6?│
     │ → END       │
     └──────┬──────┘
            │ score ≥ 0.6
            ▼
┌───────────────────────────┐
│      RISK AGENT           │
│      (gpt-4o)             │
│                           │
│  Calculates:              │
│  ├─ Position size         │
│  ├─ Leverage (max 10x)    │
│  ├─ Entry price           │
│  ├─ Stop Loss             │
│  ├─ Take Profit           │
│  └─ Liquidation price     │
│                           │
│  Safety checks:           │
│  ├─ Liq distance > 15%? ✓ │
│  ├─ Leverage ≤ 10x?     ✓ │
│  ├─ Exposure ≤ 20%?     ✓ │
│  └─ Daily drawdown ok?  ✓ │
└───────────┬───────────────┘
            │
     ┌──────┴──────┐
     │ check fail? │
     │ → END       │
     └──────┬──────┘
            │ all pass
            ▼
┌───────────────────────────┐
│    EXECUTION AGENT        │
│    (no LLM, pure API)     │
│                           │
│  Bybit via ccxt:          │
│  ├─ Set leverage          │
│  ├─ Set margin → ISOLATED │
│  ├─ Place entry order     │
│  ├─ Place stop-loss       │
│  └─ Place take-profit     │
│                           │
│  ├─ Send Telegram alert   │
│  └─ Log to DB             │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│     MONITOR AGENT         │
│     (no LLM, pure logic)  │
│     runs every 2 minutes  │
│                           │
│  Watches:                 │
│  ├─ PnL vs stop-loss      │
│  ├─ PnL vs take-profit    │
│  ├─ Funding rate spike    │
│  └─ Margin ratio > 80%    │
└───────────┬───────────────┘
            │
    ┌───────┼────────┐
    │       │        │
  HOLD   CLOSE   REDUCE
    │       │        │
  loop     END   Execution
                     │
                    END
```

---

## LangGraph Edge Routing

```
START
  │
  ▼
[market_data_node]
  │
  ▼
[analyst_node]
  │
  ├─ score < 0.6 ──────────────────────────────► END
  │
  ▼
[risk_node]
  │
  ├─ approved = False ─────────────────────────► END
  │
  ▼
[execution_node]  (open position)
  │
  ▼
[monitor_node]  (loop every 2 min)
  │
  ├─ HOLD ─────────────────────────────────────► loop
  ├─ CLOSE / REDUCE ───────────────────────────► [execution_node]
  │                                                    │
  └─────────────────────────────────────────────────► END
```

---

## Scenario Handling

| Scenario | Agent that catches it | Action |
|---|---|---|
| Market is ranging, no clear signal | Analyst | score < 0.6 → no trade |
| Signal exists but leverage too high | Risk | approved = False → no trade |
| Trade open, price hits stop-loss | Monitor | close position → exit with loss |
| Trade open, price hits take-profit | Monitor | close position → exit with gain |
| Funding rate spikes while in trade | Monitor | early exit to avoid funding cost |
| Margin ratio approaches liquidation | Monitor | reduce position size urgently |
| Whale moves large amount to exchange | Analyst | bearish signal, lower score |
| Exchange API fails | Any agent | retry 3x → alert → END safely |

---

## Shared State Schema

```
state.market_data     ← filled by market_data.py  (candles, funding, OI, whale data)
state.signals         ← filled by analyst.py       (direction, score, confidence)
state.risk            ← filled by risk.py          (approved, size, leverage, liq_price)
state.order_result    ← filled by execution.py     (order_id, filled_price, status)
state.monitor_action  ← filled by monitor.py       (HOLD | CLOSE | REDUCE)
```

Each agent reads from state and writes to state.
Nothing passes directly between agents — only through shared state.

---

## Data Sources

| Source | Data | Used By |
|---|---|---|
| Bybit (ccxt) | OHLCV, funding rate, OI, mark price, order book | Market Data Agent |
| Bybit (free, ccxt) | Long/Short ratio, liquidations | Market Data Agent |
| DefiLlama (free, no key) | Global TVL change | Market Data Agent |
| Coinglass | Global liquidations, L/S ratio, cross-exchange OI | Market Data Agent |
| Whale Alert | Large on-chain transfers | Market Data Agent |
| CryptoQuant | Exchange inflow/outflow, miner flows | Market Data Agent |

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph |
| Agent framework | LangChain |
| LLM | OpenAI gpt-4o (Supervisor, Analyst, Risk agents only) |
| Exchange API | ccxt (Bybit) |
| Whale data | Bybit (free, ccxt), DefiLlama (free, no key) |
| Technical indicators | pandas-ta |
| State persistence | SqliteSaver |
| Notifications | Telegram Bot API |
| Scheduler | APScheduler (every 15 minutes) |
| API layer (optional) | FastAPI |
