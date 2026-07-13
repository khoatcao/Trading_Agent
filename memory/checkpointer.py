import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from config import DB_PATH


def get_checkpointer() -> SqliteSaver:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return SqliteSaver(conn)
