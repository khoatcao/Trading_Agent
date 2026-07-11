from langgraph.checkpoint.sqlite import SqliteSaver
from config import DB_PATH


def get_checkpointer() -> SqliteSaver:
    return SqliteSaver.from_conn_string(DB_PATH)
