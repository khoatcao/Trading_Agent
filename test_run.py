import uuid
import json
from graph.graph import graph

state = {
    "symbol": "BTC/USDT:USDT",
    "timeframe": "1m",
    "market_data": {},
    "signals": {},
    "risk": {},
    "order_result": {},
    "monitor_action": "HOLD",
    "messages": [],
    "iteration": 0,
    "errors": [],
}

print("=" * 60)
print("TRADING AGENT TEST RUN — 1m timeframe")
print("=" * 60)

for event in graph.stream(state, config={"configurable": {"thread_id": str(uuid.uuid4())}}):
    node = list(event.keys())[0]
    data = event[node]

    print(f"\n{'─' * 40}")
    print(f"NODE: {node.upper()}")
    print(f"{'─' * 40}")

    if node == "market_data":
        md = data.get("market_data", {})
        print(f"  mark_price     : {md.get('mark_price')}")
        print(f"  funding_rate   : {md.get('funding_rate')}")
        print(f"  open_interest  : {md.get('open_interest')}")
        whale = md.get("whale_data", {})
        print(f"  defillama_tvl  : {whale.get('defillama_global_tvl')}")

    elif node == "analyst":
        sig = data.get("signals", {})
        print(f"  direction      : {sig.get('direction')}")
        print(f"  score          : {sig.get('score')}")
        print(f"  confidence     : {sig.get('confidence')}")
        print(f"  reason         : {sig.get('reason', '')[:200]}")

    elif node == "risk":
        risk = data.get("risk", {})
        print(f"  approved       : {risk.get('approved')}")
        print(f"  position_size  : {risk.get('position_size')}")
        print(f"  leverage       : {risk.get('leverage')}")
        print(f"  entry          : {risk.get('entry_price')}")
        print(f"  stop_loss      : {risk.get('stop_loss')}")
        print(f"  take_profit    : {risk.get('take_profit')}")
        print(f"  liq_price      : {risk.get('liq_price')}")

    elif node == "execution":
        order = data.get("order_result", {})
        print(f"  status         : {order.get('status')}")
        print(f"  order_id       : {order.get('order_id')}")
        print(f"  filled_price   : {order.get('filled_price')}")

    elif node == "monitor":
        print(f"  action         : {data.get('monitor_action')}")

    errors = data.get("errors", [])
    if errors:
        print(f"  ⚠ ERRORS:")
        for e in errors:
            print(f"    - {e}")

print("\n" + "=" * 60)
print("TEST RUN COMPLETE")
print("=" * 60)
