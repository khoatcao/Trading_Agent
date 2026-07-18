# Trading Agent Architecture

## Overview

A multi-agent crypto futures trading system built with LangChain and LangGraph.
Targets perpetual futures contracts (DOGE, XRP, ADA on USDT) on Bybit.
Timeframe: 15 minutes. LLM: qwen2.5:7b via local Ollama (no API key needed).

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
│                   SUPERVISOR AGENT (rule-based routing)          │
│   • Reads current state                                          │
│   • Decides which agent to call next                             │
│   • Routes via conditional edges in LangGraph                    │
└───┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌───────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌─────────┐
│Market │ │Analyst │ │Risk    │ │Execution│ │Monitor  │
│Data   │ │Agent   │ │Agent   │ │Agent    │ │Agent    │
│Agent  │ │(Ollama)│ │(Ollama)│ │(no LLM) │ │(no LLM) │
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
| Supervisor | Routes to next agent based on current state | None (rule-based) | next node name |
| Market Data | Fetches candles, funding, OI, whale data | None | state.market_data |
| Analyst | Generates trade signal (direction + score) | qwen2.5:7b | state.signals |
| Risk | Validates trade, calculates size + liq price | qwen2.5:7b | state.risk |
| Execution | Places entry, stop-loss, take-profit orders | None | state.order_result |
| Monitor | Watches open position every 2 minutes | None | state.monitor_action, state.close_reason |

---

## Folder Structure

```
trading_agent/
├── .env                          ← API keys (Bybit, Telegram)
├── config.py                     ← global settings (symbols, timeframe=15m, limits)
├── main.py                       ← entry point, runs the graph
│
├── graph/
│   ├── state.py                  ← TradingState schema
│   └── graph.py                  ← StateGraph wiring + edges
│
├── agents/
│   ├── supervisor.py             ← routing logic, next-node decision + alerts on skip/reject
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
│   └── whale_data.py             ← exchange inflows/outflows via Bybit + DefiLlama
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
│   └── alert.py                  ← Telegram alerts (trade open/close/skip/reject/error)
│
└── tests/
    └── test_run.py               ← dry run test
```

---

## Agent Flow

### One Full Cycle (e.g. DOGE/USDT Perpetual on Bybit)

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
│  └─ Liquidations          │
│                           │
│  DefiLlama (no key):      │
│  └─ Whale inflow/outflow  │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│     ANALYST AGENT         │
│     (qwen2.5:7b)          │
│                           │
│  Technical signals:       │
│  ├─ RSI(14)               │
│  ├─ MACD                  │
│  ├─ EMA(20, 50, 200)      │
│  └─ Bollinger Bands       │
│                           │
│  Futures signals:         │
│  ├─ Funding rate trend    │
│  └─ OI divergence         │
│                           │
│  Whale signals:           │
│  ├─ Exchange inflow spike │
│  └─ Liquidation cascade   │
│                           │
│  qwen2.5:7b synthesizes   │
│  → direction + score      │
└───────────┬───────────────┘
            │
     ┌──────┴──────┐
     │ score < 0.6?│  ── ⏭️ Telegram: SIGNAL SKIPPED
     │ → END       │
     └──────┬──────┘
            │ score ≥ 0.6
            ▼
┌───────────────────────────┐
│      RISK AGENT           │
│      (qwen2.5:7b)         │
│                           │
│  Calculates:              │
│  ├─ Position size         │
│  ├─ Leverage (max 2x)     │
│  ├─ Entry price           │
│  ├─ Stop Loss (3%)        │
│  ├─ Take Profit (5%)      │
│  └─ Liquidation price     │
│                           │
│  Safety checks:           │
│  ├─ Liq distance > 15%? ✓ │
│  ├─ Leverage ≤ 2x?      ✓ │
│  ├─ Exposure ≤ 25%?     ✓ │
│  └─ Daily drawdown ok?  ✓ │
└───────────┬───────────────┘
            │
     ┌──────┴──────┐
     │ check fail? │  ── 🚫 Telegram: RISK REJECTED
     │ → END       │
     └──────┬──────┘
            │ all pass
            ▼
┌───────────────────────────┐
│    EXECUTION AGENT        │
│    (no LLM, pure API)     │
│                           │
│  Bybit via ccxt:          │
│  ├─ Set leverage (2x)     │
│  ├─ Set margin → ISOLATED │
│  ├─ Place entry order     │
│  ├─ Attach stop-loss      │
│  └─ Attach take-profit    │
│                           │
│  ├─ ✅ Telegram: OPENED   │
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
│  ├─ Price vs stop-loss    │
│  ├─ Price vs take-profit  │
│  ├─ Funding rate spike    │
│  └─ Margin ratio > 80%   │
│       ⚠️ Telegram: MARGIN │
└───────────┬───────────────┘
            │
    ┌───────┼────────┐
    │       │        │
  HOLD   CLOSE   REDUCE
    │       │        │
  loop    🟢🔴      Execution
         Telegram      │
         CLOSED       END
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
  ├─ CLOSE / REDUCE ───────────────────────────► [close_position_node]
  │                                                    │
  └─────────────────────────────────────────────────► END
```

---

## Telegram Alerts

| Alert | Emoji | Trigger |
|---|---|---|
| Trade Opened | ✅ | Order placed on Bybit |
| Trade Closed | 🟢 / 🔴 | Position closed (green=profit, red=loss) |
| Signal Skipped | ⏭️ | Score < 0.6 or direction = NONE |
| Risk Rejected | 🚫 | One or more risk checks failed |
| Margin Warning | ⚠️ | Margin ratio hits 80% |
| Market Data Error | 🔴 | OHLCV fetch fails — cycle skipped |

### Close reasons (shown in Trade Closed alert):
- `Stop Loss Hit (mark=X, sl=Y)`
- `Take Profit Hit (mark=X, tp=Y)`
- `Funding Rate Spike Against Position`
- `High Margin Ratio (X%)`
- `Position Not Found on Exchange`

---

## Risk Management

| Parameter | Value |
|---|---|
| Max leverage | 2x (isolated margin) |
| Risk per trade | 1% of balance |
| Max portfolio exposure | 25% per position |
| Stop loss | 3% from entry |
| Take profit | 5% from entry |
| Risk:Reward ratio | 1 : 1.67 |
| Min liquidation distance | 15% from entry |
| Daily drawdown halt | 5% |
| Funding rate exit threshold | 0.1% against position |
| Margin ratio reduce threshold | 80% |

---

## Scenario Handling

| Scenario | Agent | Action |
|---|---|---|
| Market is ranging, no clear signal | Analyst | score < 0.6 → skip + Telegram |
| Signal exists but risk check fails | Risk | approved = False → reject + Telegram |
| Trade open, price hits stop-loss | Monitor | close position → Telegram with reason |
| Trade open, price hits take-profit | Monitor | close position → Telegram with reason |
| Funding rate spikes while in trade | Monitor | early exit → Telegram with reason |
| Margin ratio approaches liquidation | Monitor | reduce position + Telegram warning |
| OHLCV fetch fails | Market Data | alert Telegram → cycle skipped |
| Server crash | Exchange | SL/TP still active on Bybit exchange side |

---

## Shared State Schema

```
state.symbol          ← trading pair (e.g. DOGE/USDT:USDT)
state.timeframe       ← candle timeframe (15m)
state.market_data     ← filled by market_data.py  (candles, funding, OI, whale data)
state.signals         ← filled by analyst.py       (direction, score, confidence, reason)
state.risk            ← filled by risk.py          (approved, size, leverage, liq_price, sl, tp)
state.order_result    ← filled by execution.py     (order_id, filled_price, status)
state.monitor_action  ← filled by monitor.py       (HOLD | CLOSE | REDUCE)
state.close_reason    ← filled by monitor.py       (human-readable reason for closing)
state.messages        ← agent reasoning trace
state.iteration       ← cycle counter
state.errors          ← error list from any agent
```

Each agent reads from state and writes to state.
Nothing passes directly between agents — only through shared state.

---

## Data Sources

| Source | Data | Auth |
|---|---|---|
| Bybit (ccxt) | OHLCV, funding rate, OI, mark price, order book, liquidations | API key |
| DefiLlama | Whale inflow/outflow proxy | Free, no key |

---

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph |
| Agent framework | LangChain |
| LLM | qwen2.5:7b via Ollama (local, no API cost) |
| Exchange API | ccxt (Bybit) |
| Technical indicators | ta (pandas-based) |
| State persistence | SqliteSaver |
| Notifications | Telegram Bot API |
| Symbols | DOGE/USDT:USDT, XRP/USDT:USDT, ADA/USDT:USDT |
