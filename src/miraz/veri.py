"""OHLCV veri çekme — Binance.US klines, parquet cache."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.binance.us/api/v3/klines"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Veri kaynakları sırayla denenir: Binance.US başarısız/eksikse MEXC'e düşer.
# MEXC saatlik için "60m" kullanır (Binance "1h"); interval_map bunu eşler.
_BORSALAR = [
    ("binance.us", "https://api.binance.us/api/v3/klines", {}),
    ("mexc", "https://api.mexc.com/api/v3/klines", {"1h": "60m"}),
]

# Binance 12, MEXC 8 kolon döndürür; ilk 8 ortak ve bize yeten kısım.
_KOLONLAR = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume",
]


def _borsadan_cek(base: str, symbol: str, interval: str, start_ms: int,
                  end_ms: int) -> list:
    """Tek bir borsadan sayfalı klines çeker (boş liste = veri yok)."""
    parcalar: list = []
    imlec = start_ms
    while imlec < end_ms:
        r = requests.get(base, params={
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
    return parcalar


def indir(symbol: str = "BTCUSDT", interval: str = "4h",
          gun: int = 500, force: bool = False,
          borsa: str | None = None) -> pd.DataFrame:
    """OHLCV veriyi indirir, parquet cache kullanır.

    Veri kaynakları sırayla denenir (Binance.US → MEXC); biri başarısız olur
    veya sembolü sunmazsa diğerine geçilir. borsa verilirse yalnızca o kaynak.

    Döndürür: UTC indeksli, float kolonlu OHLCV DataFrame.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yol = DATA_DIR / f"{symbol}_{interval}.parquet"
    if yol.exists() and not force:
        return pd.read_parquet(yol)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - gun * 24 * 3600 * 1000

    kaynaklar = [b for b in _BORSALAR if borsa is None or b[0] == borsa]
    parcalar: list = []
    hatalar: list = []
    for ad, base, ara_map in kaynaklar:
        iv = ara_map.get(interval, interval)
        try:
            parcalar = _borsadan_cek(base, symbol, iv, start_ms, end_ms)
        except Exception as e:               # geo-engel, 4xx, ağ vb.
            hatalar.append(f"{ad}: {e}")
            parcalar = []
        if parcalar:
            break

    if not parcalar:
        detay = " | ".join(hatalar) if hatalar else "veri yok"
        raise RuntimeError(f"{symbol}/{interval} veri çekilemedi ({detay}).")

    # Borsalar farklı sayıda kolon döndürür (Binance 12, MEXC 8) → ilk 8'i al
    parcalar = [satir[:8] for satir in parcalar]
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
