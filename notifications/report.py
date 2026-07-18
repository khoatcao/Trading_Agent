from datetime import datetime, timezone, timedelta
from memory.trade_log import get_summary
from notifications.alert import send_alert
from tools.exchange import fetch_balance


def _get_balance() -> float:
    try:
        data = fetch_balance()
        return round(float(data["USDT"]["total"]), 2)
    except Exception:
        return 0.0


def _format_summary(summary: dict, balance: float, period: str) -> str:
    if summary["total_trades"] == 0:
        return (
            f"📊 *{period}*\n"
            f"No closed trades in this period.\n"
            f"Balance: `{balance} USDT`"
        )

    pnl = summary["total_pnl"]
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    best = summary["best_trade"]
    worst = summary["worst_trade"]

    return (
        f"📊 *{period}*\n"
        f"──────────────────────\n"
        f"Trades:    `{summary['total_trades']}`\n"
        f"Wins:      `{summary['wins']}` | Losses: `{summary['losses']}`\n"
        f"Win Rate:  `{summary['win_rate']}%`\n"
        f"──────────────────────\n"
        f"Total PnL: {pnl_emoji} `{pnl} USDT`\n"
        f"Best:      `{best['symbol']}` → `+{best['pnl']} USDT`\n"
        f"Worst:     `{worst['symbol']}` → `{worst['pnl']} USDT`\n"
        f"──────────────────────\n"
        f"Balance:   `{balance} USDT`"
    )


def send_daily_report():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=1)
    end = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    summary = get_summary(start.isoformat(), end.isoformat())
    balance = _get_balance()
    period = f"Daily Report — {start.strftime('%d %b %Y')}"
    send_alert(_format_summary(summary, balance, period))
    print(f"[REPORT] Daily report sent for {start.date()}")


def send_weekly_report():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=7)
    end = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    summary = get_summary(start.isoformat(), end.isoformat())
    balance = _get_balance()
    period = f"Weekly Report — {start.strftime('%d %b')} to {end.strftime('%d %b %Y')}"
    send_alert(_format_summary(summary, balance, period))
    print(f"[REPORT] Weekly report sent")


def send_monthly_report():
    now = datetime.now(timezone.utc)
    if now.month == 1:
        start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
    else:
        start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
    end = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    summary = get_summary(start.isoformat(), end.isoformat())
    balance = _get_balance()
    period = f"Monthly Report — {start.strftime('%B %Y')}"
    send_alert(_format_summary(summary, balance, period))
    print(f"[REPORT] Monthly report sent for {start.strftime('%B %Y')}")
