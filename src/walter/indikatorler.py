"""Teknik indikatörler — hepsi vektörize, look-ahead bias'sız.

Kural: bir bardaki indikatör değeri yalnızca o bar ve öncesindeki veriyi
kullanır. Sinyaller backtest'te bir bar gecikmeyle uygulanır (bkz. backtest.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(seri: pd.Series, periyot: int) -> pd.Series:
    """Üssel hareketli ortalama."""
    return seri.ewm(span=periyot, adjust=False).mean()


def atr(df: pd.DataFrame, periyot: int = 14) -> pd.Series:
    """Average True Range — volatilite / stop mesafesi için."""
    high, low, close = df["high"], df["low"], df["close"]
    onceki_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - onceki_close).abs(),
            (low - onceki_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=periyot, adjust=False).mean()


def realized_vol(close: pd.Series, periyot: int = 24,
                 yillik_bar: int = 24 * 365) -> pd.Series:
    """Yıllıklandırılmış realize volatilite (log getiri std'sinden).

    `yillik_bar` = bir yıldaki bar sayısı (saatlik veri için 24*365).
    Volatilite hedefleme pozisyon boyutu için kullanılır.
    """
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(periyot).std() * np.sqrt(yillik_bar)


def momentum(close: pd.Series, periyot: int = 24) -> pd.Series:
    """`periyot` bar önceki fiyata göre yüzde değişim."""
    return close / close.shift(periyot) - 1.0
