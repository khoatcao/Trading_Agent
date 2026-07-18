from apscheduler.schedulers.blocking import BlockingScheduler
from graph.graph import graph
from tools.exchange import fetch_all_usdt_perpetuals
from notifications.report import send_daily_report, send_weekly_report, send_monthly_report
from config import TIMEFRAME, MIN_VOLUME_USDT, MAX_SYMBOLS, SYMBOL_REFRESH_HOURS
import uuid

_active_symbols: list = []


def refresh_symbols():
    global _active_symbols
    try:
        symbols = fetch_all_usdt_perpetuals(
            min_volume_usdt=MIN_VOLUME_USDT,
            max_symbols=MAX_SYMBOLS,
        )
        _active_symbols = symbols
        print(f"[SCANNER] Active symbols updated: {len(_active_symbols)} pairs")
    except Exception as e:
        print(f"[SCANNER] Failed to refresh symbols: {e}")


def run_trading_cycle(symbol: str):
    print(f"[CYCLE START] {symbol} | {TIMEFRAME}")

    initial_state = {
        "symbol": symbol,
        "timeframe": TIMEFRAME,
        "market_data": {},
        "signals": {},
        "risk": {},
        "order_result": {},
        "monitor_action": "HOLD",
        "close_reason": "",
        "messages": [],
        "iteration": 0,
        "errors": [],
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    for event in graph.stream(initial_state, config=config):
        node_name = list(event.keys())[0]
        print(f"  [{node_name}] done")

    print(f"[CYCLE END] {symbol}")


def run_all_symbols():
    if not _active_symbols:
        print("[SCHEDULER] No symbols loaded yet — skipping cycle")
        return
    for symbol in _active_symbols:
        try:
            run_trading_cycle(symbol)
        except Exception as e:
            print(f"[SCHEDULER] Error in cycle for {symbol}: {e}")


def main():
    print("[SCANNER] Fetching active USDT perpetuals from Bybit...")
    refresh_symbols()

    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_all_symbols,
        trigger="interval",
        minutes=1,
        id="trading_all_symbols",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )

    scheduler.add_job(
        refresh_symbols,
        trigger="interval",
        hours=SYMBOL_REFRESH_HOURS,
        id="symbol_refresh",
    )

    # daily report — every day at 00:00 UTC
    scheduler.add_job(
        send_daily_report,
        trigger="cron",
        hour=0, minute=0,
        id="daily_report",
    )

    # weekly report — every Monday at 00:00 UTC
    scheduler.add_job(
        send_weekly_report,
        trigger="cron",
        day_of_week="mon",
        hour=0, minute=0,
        id="weekly_report",
    )

    # monthly report — 1st of each month at 00:00 UTC
    scheduler.add_job(
        send_monthly_report,
        trigger="cron",
        day=1,
        hour=0, minute=0,
        id="monthly_report",
    )

    print(f"[SCHEDULER] Scanning {len(_active_symbols)} pairs every 1 minute")
    print(f"[SCHEDULER] Symbol list refreshes every {SYMBOL_REFRESH_HOURS} hour(s)")
    print(f"[SCHEDULER] Reports: daily at 00:00 UTC | weekly Monday | monthly 1st")
    print("[SCHEDULER] Press Ctrl+C to stop")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("[SCHEDULER] Stopped")


if __name__ == "__main__":
    main()
