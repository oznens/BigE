"""OHLCV veri çekme + cache.

Binance.US klines endpoint'inden saatlik BTC verisi çeker, sayfalama ile
geçmişe doğru indirir ve parquet olarak cache'ler. Binance global (api.binance.com)
bazı bölgelerden HTTP 451 verdiği için Binance.US (api.binance.us) kullanılır.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.binance.us/api/v3/klines"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Binance kline kolonları
_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def _cache_yolu(symbol: str, interval: str) -> Path:
    return DATA_DIR / f"{symbol}_{interval}.parquet"


def _ham_cek(symbol: str, interval: str, start_ms: int, end_ms: int,
             limit: int = 1000) -> list[list]:
    """Tek bir kline isteği (en fazla `limit` mum)."""
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }
    r = requests.get(BASE_URL, params=params, timeout=15,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()


def indir(symbol: str = "BTCUSDT", interval: str = "1h",
          gun: int = 1500, force: bool = False) -> pd.DataFrame:
    """OHLCV veriyi indirir (cache varsa onu döndürür).

    Parametreler
    ------------
    symbol : Borsa sembolü (ör. "BTCUSDT")
    interval : Mum aralığı (ör. "1h", "15m", "4h")
    gun : Kaç günlük geçmiş indirilecek
    force : True ise cache'i yok say, yeniden indir

    Döndürür
    --------
    UTC DatetimeIndex'li, float kolonlu OHLCV DataFrame.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yol = _cache_yolu(symbol, interval)
    if yol.exists() and not force:
        return pd.read_parquet(yol)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - gun * 24 * 60 * 60 * 1000

    parcalar: list[list] = []
    imlec = start_ms
    while imlec < end_ms:
        chunk = _ham_cek(symbol, interval, imlec, end_ms, limit=1000)
        if not chunk:
            break
        parcalar.extend(chunk)
        son_close = chunk[-1][6]  # close_time
        yeni_imlec = son_close + 1
        if yeni_imlec <= imlec:
            break
        imlec = yeni_imlec
        if len(chunk) < 1000:
            break
        time.sleep(0.25)  # rate limit nazikliği

    if not parcalar:
        raise RuntimeError(f"{symbol} {interval} için veri çekilemedi.")

    df = pd.DataFrame(parcalar, columns=_KLINE_COLS)
    df = df.drop_duplicates(subset="open_time")
    ts = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index(ts)
    df.index.name = "zaman"

    for kol in ["open", "high", "low", "close", "volume"]:
        df[kol] = df[kol].astype(float)

    df = df[["open", "high", "low", "close", "volume"]].sort_index()
    df.to_parquet(yol)
    return df


if __name__ == "__main__":
    df = indir(force=True)
    print(f"İndirildi: {len(df)} mum")
    print(f"Aralık: {df.index[0]}  ->  {df.index[-1]}")
    print(df.tail())
