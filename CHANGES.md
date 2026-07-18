# Trading Bot — Changes & Improvements

## Overview
This document tracks all changes made to the trading bot from the initial version.

---

## 1. Telegram Alerts — Full Coverage

**Files:** `notifications/alert.py`, `agents/execution.py`, `agents/supervisor.py`, `agents/monitor.py`, `agents/market_data.py`

**Before:** Only 2 alerts — Trade Opened and Trade Closed (with no close reason).

**After:** 6 alerts with full detail:

| Alert | Emoji | Trigger |
|---|---|---|
| Trade Opened | ✅ | Order placed on Bybit |
| Trade Closed | 🟢 / 🔴 | Position closed (green=profit, red=loss) |
| Risk Rejected | 🚫 | Risk checks failed |
| Margin Warning | ⚠️ | Margin ratio hits 80% |
| Market Data Error | 🔴 | OHLCV fetch fails |
| Critical Unprotected Position | 🚨 | SL/TP failed to set |

**Trade Closed now shows real reason:**
- `Stop Loss Hit (mark=X, sl=Y)`
- `Take Profit Hit (mark=X, tp=Y)`
- `Funding Rate Spike Against Position`
- `High Margin Ratio (X%)`
- `Position Not Found on Exchange`

**Trade Opened now shows full detail:**
- Entry price, size, leverage, margin mode
- Stop loss, take profit, liquidation price + distance %
- Signal score and confidence

**Removed:** Signal Skipped alert (was flooding Telegram with 50 messages/minute)

---

## 2. SL/TP Calculated From Actual Fill Price

**File:** `agents/execution.py`, `tools/exchange.py`

**Before:** SL/TP calculated from stale mark price fetched during risk agent. By the time order filled, price had moved — SL could be only 0.05% away causing immediate close.

**After:**
1. Market order placed with no SL/TP attached
2. Actual fill price extracted from order response
3. SL/TP recalculated from real fill price
4. SL/TP set via separate `set_trading_stop()` API call

**New function added:** `set_trading_stop()` in `tools/exchange.py` using Bybit's `/v5/position/trading-stop` endpoint.

---

## 3. SL/TP Failure Is Now Fatal

**File:** `agents/execution.py`

**Before:** SL/TP failure silently logged error and continued — position left open with no protection.

**After:** SL/TP failure triggers:
1. 🚨 Critical Telegram alert
2. Emergency market close of the position
3. If emergency close fails → another alert requiring manual action

---

## 4. Duplicate Trade Prevention

**Files:** `agents/market_data.py`, `agents/monitor.py`, `agents/supervisor.py`, `graph/graph.py`

**Before:** No check for existing open positions — same pair could open twice.

**After:** At start of every cycle, market data agent checks for open positions:
- Position exists → skip to `resume_monitor_node` (watch it)
- No position → run full cycle (analyst → risk → execution)

**New node added:** `resume_monitor_node` — rebuilds signals and risk from existing position data so monitor works correctly without re-entering.

---

## 5. Exchange Singleton — No More Rate Bans

**File:** `tools/exchange.py`

**Before:** `get_exchange()` created a new Bybit connection and called `load_markets()` on every single API call — ~850 unnecessary API calls per minute with 10 pairs.

**After:** Module-level singleton — connection created once, reused for all calls:
```python
_exchange: ccxt.bybit | None = None

def get_exchange() -> ccxt.bybit:
    global _exchange
    if _exchange is None:
        _exchange = ccxt.bybit({...})
        _exchange.load_markets()
    return _exchange
```

---

## 6. Daily Drawdown Check Fixed

**Files:** `agents/risk.py`, `memory/trade_log.py`

**Before:** Both `starting_balance` and `current_balance` were set to the same `equity` value — drawdown was always 0%, the 5% halt never triggered.

**After:**
- Start-of-day balance saved to SQLite on first cycle each day
- Drawdown calculated as `(starting_balance - current_equity) / starting_balance`
- If drawdown ≥ 5% → all new trades rejected for the rest of the day

**New functions:** `save_daily_starting_balance()`, `get_daily_starting_balance()` in `memory/trade_log.py`

---

## 7. Max Concurrent Positions

**Files:** `config.py`, `agents/risk.py`, `tools/exchange.py`

**Before:** No portfolio-level limit — all 10 pairs could open simultaneously.

**After:** Risk agent checks total open positions before approving any new trade:
```python
MAX_POSITIONS = 3  # config.py
```
If 3 positions already open → new trade rejected with clear reason.

**New function:** `fetch_all_positions()` in `tools/exchange.py`

---

## 8. Minimum Order Notional Check

**Files:** `config.py`, `tools/risk_calc.py`

**Before:** No check — orders below Bybit's $10 minimum silently failed at the exchange after the full analysis pipeline had already run.

**After:** Added `notional_ok` check in `validate_risk()`:
```python
MIN_NOTIONAL_USDT = 11.0  # $10 Bybit minimum + $1 buffer
```
Trades rejected before reaching execution if position value < $11.

---

## 9. Correct Realized PnL Logging

**File:** `agents/execution.py`

**Before:** PnL logged as `unrealizedPnl` captured from position snapshot before close order executed — incorrect value.

**After:** PnL extracted from close order response:
```python
pnl = (
    close_order.get("info", {}).get("cumRealisedPnl") or
    close_order.get("info", {}).get("realizedPnl") or
    position.get("unrealizedPnl", 0)
)
```

---

## 10. Cancel Ghost SL/TP Orders on Close

**Files:** `agents/execution.py`, `tools/exchange.py`

**Before:** Manual position close left old SL/TP conditional orders active on Bybit — could trigger against next trade on same symbol.

**After:** `cancel_all_conditional_orders()` called before every manual close.

**New function:** `cancel_all_conditional_orders()` in `tools/exchange.py`

---

## 11. OHLCV Failure Early Exit

**File:** `agents/market_data.py`

**Before:** OHLCV failure sent alert saying "cycle skipped" but kept running — analyst then crashed with `KeyError` on missing data.

**After:** OHLCV failure returns immediately from `market_data_node` — cycle truly skipped, no downstream crashes.

---

## 12. SQLite WAL Mode

**File:** `memory/trade_log.py`

**Before:** Two SQLite writers (LangGraph checkpointer + trade log) on same DB file caused frequent "database is locked" errors.

**After:** WAL (Write-Ahead Logging) mode enabled on every connection:
```python
conn.execute("PRAGMA journal_mode=WAL")
```

---

## 13. SL/TP Configurable from config.py

**Files:** `config.py`, `tools/risk_calc.py`

**Before:** Stop loss (3%) and take profit (5%) hardcoded in `risk_calc.py`.

**After:** Controlled from `config.py`:
```python
STOP_LOSS_PCT   = 0.03   # 3%
TAKE_PROFIT_PCT = 0.09   # 9%  →  1:3 R:R
```

---

## 14. Daily / Weekly / Monthly Telegram Reports

**Files:** `notifications/report.py`, `main.py`, `memory/trade_log.py`

**Before:** No performance summary — no way to know total PnL, win rate, or trade count.

**After:** Automated reports sent to Telegram:

| Report | Schedule |
|---|---|
| Daily | Every day at 00:00 UTC |
| Weekly | Every Monday at 00:00 UTC |
| Monthly | 1st of each month at 00:00 UTC |

Each report shows: trades, wins, losses, win rate, total PnL, best trade, worst trade, current balance.

---

## 15. Oracle Cloud Deployment

**File:** `setup.sh`

One-command deployment script for Oracle Cloud Ubuntu 22.04:
- Installs system packages, Ollama, pulls `qwen2.5:7b`
- Clones repo, sets up Python venv + dependencies
- Creates `.env` template
- Registers systemd service (auto-start + auto-restart on crash)

```bash
bash setup.sh
```

---

## Risk Settings Summary

| Parameter | Value |
|---|---|
| Max leverage | 2x (isolated) |
| Risk per trade | 10% of balance |
| Max exposure | 200% (to meet $10 Bybit minimum) |
| Stop loss | 3% from fill price |
| Take profit | 9% from fill price |
| Risk:Reward | 1 : 3 |
| Max positions | 3 concurrent |
| Min notional | $11 USDT |
| Daily drawdown halt | 5% |
| Min liq distance | 15% |
| Signal threshold | 0.6 |

---

## Trading Cost Per Trade

```
Position notional:  ~$10 USDT
Bybit taker fee:    0.055% per side

Entry fee:   $0.0055
Exit fee:    $0.0055
Total:       $0.011 per round trip (~$1/month)
```

---

## Branches

| Branch | Purpose |
|---|---|
| `main` | Stable — 10 hardcoded pairs |
| `feature/market-scanner` | Dynamic scanner — all liquid Bybit USDT perpetuals |
