"""Forex verisi (yfinance) — Big E'nin orijinal pair'leri için.

yfinance 1h verisini çekip 4h'e resample eder, İstanbul saatine çevirir.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from .zaman import istanbul_index, ISTANBUL

# Big E'nin sık bahsettiği pair'ler → yfinance ticker
FOREX_TICKERS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "AUDUSD": "AUDUSD=X",
    "USDJPY": "USDJPY=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "AUDJPY": "AUDJPY=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
}


def indir_yfinance(
    pair: str,
    aralik_1h_periyodu: str = "730d",
    target_aralik: str = "4h",
) -> pd.DataFrame:
    """yfinance 1h verisini çekip hedef aralığa resample et.

    yfinance limitleri: 1h max 730d, 1d sınırsız.
    Bu yüzden 4h için 1h çekip resample yapıyoruz.
    """
    if pair not in FOREX_TICKERS:
        raise ValueError(f"Bilinmeyen pair: {pair}. Geçerli: {list(FOREX_TICKERS)}")

    ticker = FOREX_TICKERS[pair]
    if target_aralik == "1d":
        df = yf.Ticker(ticker).history(period="max", interval="1d")
    else:
        # 1h çek, sonra resample
        df = yf.Ticker(ticker).history(period=aralik_1h_periyodu, interval="1h")

    if df.empty:
        return df

    # Kolonları normalize et
    df = df.rename(columns=str.lower)
    df = df[["open", "high", "low", "close", "volume"]]
    # Forex'te volume genelde 0 — anlamsız, yine de tut
    df.index.name = "open_time"

    # Timezone → İstanbul
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.tz_convert(ISTANBUL)

    # Hedef aralığa resample
    if target_aralik == "4h":
        df = _resample_ohlcv(df, "4h")
    elif target_aralik == "1h":
        pass  # zaten 1h
    elif target_aralik == "1d":
        # yfinance zaten günlük; sadece tz_convert sonrası temizleme
        df = df.resample("1D").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
    else:
        raise ValueError(f"Desteklenmeyen target_aralik: {target_aralik}")

    return df


def _resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """1h → 4h gibi OHLCV resampling."""
    return df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()


def kaydet(df: pd.DataFrame, pair: str, aralik: str, klasor: Path = Path("data")) -> Path:
    klasor.mkdir(parents=True, exist_ok=True)
    yol = klasor / f"forex_{pair}_{aralik}.parquet"
    df.to_parquet(yol)
    return yol


def yukle(pair: str, aralik: str, klasor: Path = Path("data")) -> pd.DataFrame:
    return pd.read_parquet(klasor / f"forex_{pair}_{aralik}.parquet")
