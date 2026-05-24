"""Binance'tan OHLCV verisi çekme.

Backtest için 4h ve 1D mumları indirir, İstanbul saatine çevirir.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from .zaman import istanbul_index

BINANCE_API = "https://api.binance.com/api/v3/klines"

# Binance kline interval kodları
INTERVAL = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h",
    "4h": "4h", "1d": "1d", "1w": "1w",
}


def indir(
    sembol: str = "BTCUSDT",
    aralik: str = "4h",
    limit: int = 1000,
    bitis_ms: int | None = None,
) -> pd.DataFrame:
    """Tek seferde max 1000 mum (Binance limiti)."""
    if aralik not in INTERVAL:
        raise ValueError(f"Desteklenmeyen aralık: {aralik}")

    params = {"symbol": sembol, "interval": INTERVAL[aralik], "limit": limit}
    if bitis_ms is not None:
        params["endTime"] = bitis_ms

    r = requests.get(BINANCE_API, params=params, timeout=15)
    r.raise_for_status()
    rows = r.json()

    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("open_time")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df[["open", "high", "low", "close", "volume"]]
    return istanbul_index(df)


def indir_tarihsel(
    sembol: str,
    aralik: str,
    baslangic: str,
    bitis: str | None = None,
) -> pd.DataFrame:
    """Tarih aralığında tüm mumları sayfa sayfa indirir.

    Tarihler ISO formatında, İstanbul saati varsayılır.
    Örn: indir_tarihsel("BTCUSDT", "4h", "2022-01-01", "2024-12-31")
    """
    bas_ts = pd.Timestamp(baslangic, tz="Europe/Istanbul")
    bit_ts = pd.Timestamp(bitis, tz="Europe/Istanbul") if bitis else pd.Timestamp.now(tz="Europe/Istanbul")

    bitis_ms = int(bit_ts.timestamp() * 1000)
    parcalar: list[pd.DataFrame] = []

    while True:
        parca = indir(sembol, aralik, limit=1000, bitis_ms=bitis_ms)
        if parca.empty:
            break
        parcalar.append(parca)
        en_eski = parca.index.min()
        if en_eski <= bas_ts:
            break
        bitis_ms = int(en_eski.timestamp() * 1000) - 1

    if not parcalar:
        return pd.DataFrame()

    df = pd.concat(parcalar).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df.loc[bas_ts:bit_ts]


def kaydet(df: pd.DataFrame, sembol: str, aralik: str, klasor: Path = Path("data")) -> Path:
    klasor.mkdir(parents=True, exist_ok=True)
    yol = klasor / f"{sembol}_{aralik}.parquet"
    df.to_parquet(yol)
    return yol


def yukle(sembol: str, aralik: str, klasor: Path = Path("data")) -> pd.DataFrame:
    yol = klasor / f"{sembol}_{aralik}.parquet"
    return pd.read_parquet(yol)
