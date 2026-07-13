from dotenv import load_dotenv
import os

load_dotenv(override=True)

# Exchange
EXCHANGE_NAME = "bybit"
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
EXCHANGE_API_SECRET = os.getenv("EXCHANGE_API_SECRET")

# Trading
SYMBOLS = ["DOGE/USDT:USDT"]
TIMEFRAME = os.getenv("TIMEFRAME", "15m")   # override with TIMEFRAME=1m for testing
CANDLE_LIMIT = 200
MONITOR_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "120"))

# Risk
MAX_LEVERAGE = 2
MARGIN_MODE = "isolated"
RISK_PER_TRADE = 0.0005      # 0.05% of balance per trade (reduced for small-balance testing)
MAX_EXPOSURE = 0.20          # max 20% of portfolio in one position
MAX_DAILY_DRAWDOWN = 0.05    # halt if -5% on the day
MIN_LIQ_DISTANCE = 0.15      # liquidation must be >15% away from entry
SIGNAL_THRESHOLD = 0.6       # minimum score to take a trade

# LLM (local Ollama — no API key needed)
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
LLM_TEMPERATURE = 0.0

# LangSmith observability (set LANGCHAIN_TRACING_V2=true in .env to enable)
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "trading-agent")

# Whale data — Bybit (ccxt) + DefiLlama only, both free, no extra keys needed

# Notifications
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Database
DB_PATH = os.getenv("DB_PATH", "./memory/trades.db")
