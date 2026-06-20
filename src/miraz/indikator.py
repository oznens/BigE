"""Klasik indikatörler — @finansalTRader (hoca) tarzı.

Miraz saf Price Action kullanır (indikatörsüz); hocası @finansalTRader RSI,
hareketli ortalamalar ve MACD gibi klasik araçları kullanır. Bu modül onların
saf hesaplamalarını sağlar (yalnızca OHLC'den; dış veri gerekmez).

  - RSI (Wilder) — momentum
  - EMA / SMA — hareketli ortalama
  - MACD — trend/momentum (EMA12 − EMA26, sinyal EMA9)
"""

from __future__ import annotations

import pandas as pd


def sma(seri: pd.Series, periyot: int = 20) -> pd.Series:
    """Basit hareketli ortalama."""
    return seri.rolling(periyot, min_periods=periyot).mean()


def ema(seri: pd.Series, periyot: int = 20) -> pd.Series:
    """Üstel hareketli ortalama."""
    return seri.ewm(span=periyot, adjust=False).mean()


def rsi(seri: pd.Series, periyot: int = 14) -> pd.Series:
    """Wilder RSI (0–100). 70 üstü aşırı alım, 30 altı aşırı satım."""
    delta = seri.diff()
    kazanc = delta.clip(lower=0.0)
    kayip = -delta.clip(upper=0.0)
    # Wilder yumuşatması (alpha = 1/periyot)
    ort_kazanc = kazanc.ewm(alpha=1 / periyot, min_periods=periyot,
                            adjust=False).mean()
    ort_kayip = kayip.ewm(alpha=1 / periyot, min_periods=periyot,
                          adjust=False).mean()
    rs = ort_kazanc / ort_kayip
    return 100 - (100 / (1 + rs))


def macd(seri: pd.Series, hizli: int = 12, yavas: int = 26,
         sinyal: int = 9) -> pd.DataFrame:
    """MACD çizgisi, sinyal çizgisi ve histogram döndürür."""
    macd_cizgi = ema(seri, hizli) - ema(seri, yavas)
    sinyal_cizgi = macd_cizgi.ewm(span=sinyal, adjust=False).mean()
    histogram = macd_cizgi - sinyal_cizgi
    return pd.DataFrame({
        "macd": macd_cizgi, "sinyal": sinyal_cizgi, "histogram": histogram,
    })
