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
