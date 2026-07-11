from dotenv import load_dotenv
import os

load_dotenv()

# Exchange
EXCHANGE_NAME = "bybit"
TESTNET = os.getenv("TESTNET", "true").lower() == "true"

# Automatically pick the correct API keys based on TESTNET flag
if TESTNET:
    EXCHANGE_API_KEY = os.getenv("TESTNET_API_KEY")
    EXCHANGE_API_SECRET = os.getenv("TESTNET_API_SECRET")
else:
    EXCHANGE_API_KEY = os.getenv("LIVE_API_KEY")
    EXCHANGE_API_SECRET = os.getenv("LIVE_API_SECRET")

# Trading
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
TIMEFRAME = "15m"
CANDLE_LIMIT = 200
MONITOR_INTERVAL_SECONDS = 120

# Risk
MAX_LEVERAGE = 10
MARGIN_MODE = "isolated"
RISK_PER_TRADE = 0.02        # 2% of balance per trade
MAX_EXPOSURE = 0.20          # max 20% of portfolio in one position
MAX_DAILY_DRAWDOWN = 0.05    # halt if -5% on the day
MIN_LIQ_DISTANCE = 0.15      # liquidation must be >15% away from entry
SIGNAL_THRESHOLD = 0.6       # minimum score to take a trade

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = "gpt-4o"
LLM_TEMPERATURE = 0.0

# Whale data — Bybit (ccxt) + DefiLlama only, both free, no extra keys needed

# Notifications
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Database
DB_PATH = os.getenv("DB_PATH", "./memory/trades.db")
