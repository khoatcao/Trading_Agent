import pandas as pd
import pandas_ta as ta


def build_dataframe(ohlcv: list) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return ta.rsi(df["close"], length=period)


def compute_macd(df: pd.DataFrame) -> pd.DataFrame:
    return ta.macd(df["close"])


def compute_ema(df: pd.DataFrame, periods: list = [20, 50, 200]) -> pd.DataFrame:
    result = pd.DataFrame()
    for p in periods:
        result[f"ema_{p}"] = ta.ema(df["close"], length=p)
    return result


def compute_bollinger_bands(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    return ta.bbands(df["close"], length=period)


def compute_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return ta.sma(df["volume"], length=period)


def get_all_indicators(ohlcv: list) -> dict:
    df = build_dataframe(ohlcv)
    rsi = compute_rsi(df)
    macd = compute_macd(df)
    ema = compute_ema(df)
    bb = compute_bollinger_bands(df)
    vol_sma = compute_volume_sma(df)

    latest = -1
    return {
        "rsi": round(float(rsi.iloc[latest]), 2),
        "macd": round(float(macd["MACD_12_26_9"].iloc[latest]), 4),
        "macd_signal": round(float(macd["MACDs_12_26_9"].iloc[latest]), 4),
        "macd_hist": round(float(macd["MACDh_12_26_9"].iloc[latest]), 4),
        "ema_20": round(float(ema["ema_20"].iloc[latest]), 4),
        "ema_50": round(float(ema["ema_50"].iloc[latest]), 4),
        "ema_200": round(float(ema["ema_200"].iloc[latest]), 4),
        "bb_upper": round(float(bb[f"BBU_20_2.0"].iloc[latest]), 4),
        "bb_mid": round(float(bb[f"BBM_20_2.0"].iloc[latest]), 4),
        "bb_lower": round(float(bb[f"BBL_20_2.0"].iloc[latest]), 4),
        "volume": round(float(df["volume"].iloc[latest]), 4),
        "volume_sma": round(float(vol_sma.iloc[latest]), 4),
        "close": round(float(df["close"].iloc[latest]), 4),
    }
