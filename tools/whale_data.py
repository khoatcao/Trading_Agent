import requests
from tools.exchange import get_exchange


# --- Bybit (free, already connected via ccxt) ---

def fetch_bybit_long_short_ratio(symbol: str = "BTC/USDT:USDT") -> dict:
    exchange = get_exchange()
    try:
        return exchange.fetch_long_short_ratio(symbol, "1h")
    except Exception:
        ticker = exchange.fetch_ticker(symbol)
        return {"info": ticker.get("info", {})}


def fetch_bybit_liquidations(symbol: str = "BTC/USDT:USDT") -> dict:
    exchange = get_exchange()
    try:
        liquidations = exchange.fetch_liquidations(symbol)
        return {"liquidations": liquidations[:20]}
    except Exception:
        return {"liquidations": []}


# --- DefiLlama (completely free, no API key) ---

def fetch_defillama_global_tvl() -> dict:
    url = "https://api.llama.fi/v2/globalCharts"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and len(data) >= 2:
        latest = data[-1].get("totalLiquidityUSD", 0)
        previous = data[-2].get("totalLiquidityUSD", 0)
        change_pct = ((latest - previous) / previous * 100) if previous else 0
        return {"global_tvl": latest, "tvl_change_pct_1h": round(change_pct, 4)}
    return {"global_tvl": None, "tvl_change_pct_1h": None}


# --- Aggregator ---

def fetch_all_whale_data(symbol: str = "BTC") -> dict:
    bybit_symbol = f"{symbol}/USDT:USDT"
    results = {}

    try:
        results["bybit_long_short_ratio"] = fetch_bybit_long_short_ratio(bybit_symbol)
    except Exception as e:
        results["bybit_long_short_ratio"] = {"error": str(e)}

    try:
        results["bybit_liquidations"] = fetch_bybit_liquidations(bybit_symbol)
    except Exception as e:
        results["bybit_liquidations"] = {"error": str(e)}

    try:
        results["defillama_global_tvl"] = fetch_defillama_global_tvl()
    except Exception as e:
        results["defillama_global_tvl"] = {"error": str(e)}

    return results
