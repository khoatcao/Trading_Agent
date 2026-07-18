import sqlite3
from datetime import datetime, timezone
from config import DB_PATH


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT,
            direction   TEXT,
            entry_price REAL,
            close_price REAL,
            position_size REAL,
            leverage    INTEGER,
            stop_loss   REAL,
            take_profit REAL,
            liq_price   REAL,
            pnl         REAL,
            status      TEXT,
            reason      TEXT,
            timestamp   TEXT
        )
    """)
    conn.commit()
    return conn


def log_trade(trade: dict):
    conn = _get_connection()
    conn.execute("""
        INSERT INTO trades (
            symbol, direction, entry_price, close_price,
            position_size, leverage, stop_loss, take_profit,
            liq_price, pnl, status, reason, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade.get("symbol"),
        trade.get("direction"),
        trade.get("entry_price"),
        trade.get("close_price"),
        trade.get("position_size"),
        trade.get("leverage"),
        trade.get("stop_loss"),
        trade.get("take_profit"),
        trade.get("liq_price"),
        trade.get("pnl"),
        trade.get("status"),
        trade.get("reason"),
        trade.get("timestamp", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    conn.close()


def get_trades(limit: int = 50) -> list:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
    )
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_summary(from_ts: str, to_ts: str) -> dict:
    conn = _get_connection()
    cursor = conn.execute("""
        SELECT pnl, symbol, direction, entry_price, close_price, timestamp
        FROM trades
        WHERE status = 'closed'
          AND timestamp >= ?
          AND timestamp < ?
    """, (from_ts, to_ts))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "best_trade": None,
            "worst_trade": None,
        }

    pnls = [r[0] or 0 for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    best_idx = pnls.index(max(pnls))
    worst_idx = pnls.index(min(pnls))

    return {
        "total_trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(rows) * 100, 1),
        "total_pnl": round(sum(pnls), 4),
        "best_trade": {"symbol": rows[best_idx][1], "pnl": round(rows[best_idx][0], 4)},
        "worst_trade": {"symbol": rows[worst_idx][1], "pnl": round(rows[worst_idx][0], 4)},
    }
