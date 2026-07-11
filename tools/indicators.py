import pandas as pd
import ta


def build_dataframe(ohlcv: list) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def get_all_indicators(ohlcv: list) -> dict:
    df = build_dataframe(ohlcv)

    rsi = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    macd_obj = ta.trend.MACD(df["close"])
    macd = macd_obj.macd()
    macd_signal = macd_obj.macd_signal()
    macd_hist = macd_obj.macd_diff()

    ema_20 = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    ema_50 = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    ema_200 = ta.trend.EMAIndicator(df["close"], window=200).ema_indicator()

    bb = ta.volatility.BollingerBands(df["close"], window=20)
    bb_upper = bb.bollinger_hband()
    bb_mid = bb.bollinger_mavg()
    bb_lower = bb.bollinger_lband()

    vol_sma = ta.trend.SMAIndicator(df["volume"], window=20).sma_indicator()

    latest = -1
    return {
        "rsi": round(float(rsi.iloc[latest]), 2),
        "macd": round(float(macd.iloc[latest]), 4),
        "macd_signal": round(float(macd_signal.iloc[latest]), 4),
        "macd_hist": round(float(macd_hist.iloc[latest]), 4),
        "ema_20": round(float(ema_20.iloc[latest]), 4),
        "ema_50": round(float(ema_50.iloc[latest]), 4),
        "ema_200": round(float(ema_200.iloc[latest]), 4),
        "bb_upper": round(float(bb_upper.iloc[latest]), 4),
        "bb_mid": round(float(bb_mid.iloc[latest]), 4),
        "bb_lower": round(float(bb_lower.iloc[latest]), 4),
        "volume": round(float(df["volume"].iloc[latest]), 4),
        "volume_sma": round(float(vol_sma.iloc[latest]), 4),
        "close": round(float(df["close"].iloc[latest]), 4),
    }
