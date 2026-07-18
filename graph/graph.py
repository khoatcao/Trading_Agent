import sqlite3

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from config import DB_PATH
from graph.state import TradingState
from agents.market_data import market_data_node
from agents.analyst import analyst_node
from agents.risk import risk_node
from agents.execution import execution_node, close_position_node
from agents.monitor import monitor_node, resume_monitor_node
from agents.supervisor import (
    route_after_market_data,
    route_after_analyst,
    route_after_risk,
    route_after_monitor,
)


def build_graph():
    builder = StateGraph(TradingState)

    # Nodes
    builder.add_node("market_data", market_data_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("risk", risk_node)
    builder.add_node("execution", execution_node)
    builder.add_node("monitor", monitor_node)
    builder.add_node("resume_monitor", resume_monitor_node)
    builder.add_node("close_position", close_position_node)

    # Entry
    builder.set_entry_point("market_data")

    # After market data: go to monitor if position already open, else analyse
    builder.add_conditional_edges(
        "market_data",
        route_after_market_data,
        {
            "analyst": "analyst",
            "resume_monitor": "resume_monitor",
        }
    )

    # Resume monitor feeds straight into monitor
    builder.add_edge("resume_monitor", "monitor")
    builder.add_edge("execution", "monitor")

    # Analyst -> Risk / End
    builder.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {
            "risk": "risk",
            "end": END,
        },
    )

    # Risk -> Execution / End
    builder.add_conditional_edges(
        "risk",
        route_after_risk,
        {
            "execution": "execution",
            "end": END,
        },
    )

    # Monitor -> Close Position / End
    builder.add_conditional_edges(
        "monitor",
        route_after_monitor,
        {
            "close_position": "close_position",
            "end": END,
        },
    )

    # Close Position -> End
    builder.add_edge("close_position", END)

    # Checkpointer
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph()