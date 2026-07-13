from dotenv import load_dotenv
import os

load_dotenv(override=True)

# Exchange
EXCHANGE_NAME = "bybit"
TESTNET = os.getenv("TESTNET", "true").lower() == "true"

# Validate known placeholder values and key type mismatches
def _validate_exchange_credentials(api_key: str, api_secret: str, mode: str) -> None:
    placeholder_values = {
        "your_live_api_key_here",
        "your_live_api_secret_here",
        "your_testnet_api_key_here",
        "your_testnet_api_secret_here",
        "replace_with_your_live_api_key",
        "replace_with_your_live_api_secret",
        "replace_with_your_testnet_api_key",
        "replace_with_your_testnet_api_secret",
    }

    lowered_key = (api_key or "").strip().lower()
    lowered_secret = (api_secret or "").strip().lower()

    if lowered_key in placeholder_values or lowered_secret in placeholder_values:
        raise ValueError(
            f"{mode.upper()} API credentials appear to be placeholders. "
            "Replace them with your actual Bybit API key and secret in .env."
        )

    if mode == "live" and lowered_key.startswith("zyuuiee2cg"):
        raise ValueError(
            "LIVE_API_KEY appears to be a Bybit testnet key. "
            "Set TESTNET=true for testnet keys or replace LIVE_API_KEY with a live key."
        )
    if mode == "testnet" and not lowered_key.startswith("zyuuiee2cg"):
        raise ValueError(
            "TESTNET_API_KEY does not look like a Bybit testnet key. "
            "Verify you are using a testnet key and set TESTNET=true."
        )

# Automatically pick the correct API keys based on TESTNET flag
if TESTNET:
    EXCHANGE_API_KEY = os.getenv("TESTNET_API_KEY")
    EXCHANGE_API_SECRET = os.getenv("TESTNET_API_SECRET")
    if not EXCHANGE_API_KEY or not EXCHANGE_API_SECRET:
        raise ValueError(
            "TESTNET=true requires TESTNET_API_KEY and TESTNET_API_SECRET in .env"
        )
    _validate_exchange_credentials(EXCHANGE_API_KEY, EXCHANGE_API_SECRET, mode="testnet")
else:
    EXCHANGE_API_KEY = os.getenv("LIVE_API_KEY")
    EXCHANGE_API_SECRET = os.getenv("LIVE_API_SECRET")
    if not EXCHANGE_API_KEY or not EXCHANGE_API_SECRET:
        raise ValueError(
            "TESTNET=false requires LIVE_API_KEY and LIVE_API_SECRET in .env"
        )
    _validate_exchange_credentials(EXCHANGE_API_KEY, EXCHANGE_API_SECRET, mode="live")

if not EXCHANGE_API_KEY or not EXCHANGE_API_SECRET:
    raise ValueError(
        "Missing exchange API keys. Set TESTNET=true with TESTNET_API_KEY/TESTNET_API_SECRET "
        "or TESTNET=false with LIVE_API_KEY/LIVE_API_SECRET."
    )

# Trading
<<<<<<< HEAD
SYMBOLS = [s.strip() for s in os.getenv(
    "SYMBOLS", "DOGE/USDT:USDT"
).split(",") if s.strip()]
TIMEFRAME = "1m"
=======
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
TIMEFRAME = os.getenv("TIMEFRAME", "15m")   # override with TIMEFRAME=1m for testing
>>>>>>> d0b86c9 (update local model)
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
