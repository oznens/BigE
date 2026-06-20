"""OHLCV veri çekme — Binance.US klines, parquet cache."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.binance.us/api/v3/klines"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_KOLONLAR = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "_",
]


def indir(symbol: str = "BTCUSDT", interval: str = "4h",
          gun: int = 500, force: bool = False) -> pd.DataFrame:
    """OHLCV veriyi indirir, parquet cache kullanır.

    Döndürür: UTC indeksli, float kolonlu OHLCV DataFrame.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yol = DATA_DIR / f"{symbol}_{interval}.parquet"
    if yol.exists() and not force:
        return pd.read_parquet(yol)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - gun * 24 * 3600 * 1000
    parcalar: list = []
    imlec = start_ms

    while imlec < end_ms:
        r = requests.get(BASE, params={
            "symbol": symbol, "interval": interval,
            "startTime": imlec, "endTime": end_ms, "limit": 1000,
        }, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        parcalar.extend(chunk)
        son = chunk[-1][6] + 1
        if son <= imlec or len(chunk) < 1000:
            break
        imlec = son
        time.sleep(0.2)

    if not parcalar:
        raise RuntimeError(f"{symbol}/{interval} veri çekilemedi.")

    df = pd.DataFrame(parcalar, columns=_KOLONLAR)
    df = df.drop_duplicates("open_time")
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.index.name = "zaman"
    for k in ["open", "high", "low", "close", "volume"]:
        df[k] = df[k].astype(float)
    df = df[["open", "high", "low", "close", "volume"]].sort_index()
    df.to_parquet(yol)
    return df


if __name__ == "__main__":
    df = indir(force=True)
    print(f"{len(df)} mum | {df.index[0].date()} → {df.index[-1].date()}")
    print(df.tail(3))
