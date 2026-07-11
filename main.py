from apscheduler.schedulers.blocking import BlockingScheduler
from graph.graph import graph
from config import SYMBOLS, TIMEFRAME
import uuid


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
        "messages": [],
        "iteration": 0,
        "errors": [],
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    for event in graph.stream(initial_state, config=config):
        node_name = list(event.keys())[0]
        print(f"  [{node_name}] done")

    print(f"[CYCLE END] {symbol}")


def main():
    scheduler = BlockingScheduler()

    for symbol in SYMBOLS:
        scheduler.add_job(
            run_trading_cycle,
            trigger="interval",
            minutes=15,
            args=[symbol],
            id=f"trading_{symbol.replace('/', '_')}",
        )

    print(f"[SCHEDULER] Running for symbols: {SYMBOLS} every 15 minutes")
    print("[SCHEDULER] Press Ctrl+C to stop")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("[SCHEDULER] Stopped")


if __name__ == "__main__":
    main()
