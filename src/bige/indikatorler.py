"""Big E modelinin indikatörleri.

Tüm fonksiyonlar pandas Series/DataFrame alır, kolon eklenmiş DataFrame veya
yeni Series döndürür. NaN ilk N mum için doğal olarak oluşur, doldurulmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """OHLC → HA OHLC. Giriş df'de ['open','high','low','close'] olmalı.

    Çıkış: ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'ha_bullish']
    """
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    ha_open = np.empty(n)
    ha_close = (o + h + l + c) / 4.0

    ha_open[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0

    ha_high = np.maximum.reduce([h, ha_open, ha_close])
    ha_low = np.minimum.reduce([l, ha_open, ha_close])

    out = df.copy()
    out["ha_open"] = ha_open
    out["ha_high"] = ha_high
    out["ha_low"] = ha_low
    out["ha_close"] = ha_close
    out["ha_bullish"] = ha_close >= ha_open
    return out


def rsi(series: pd.Series, period: int = 13) -> pd.Series:
    """Wilder RSI (TDI'nın bazı buna göre)."""
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    # Wilder smoothing = EMA with alpha = 1/period
    roll_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).rename("rsi")


def tdi(
    close: pd.Series,
    rsi_period: int = 13,
    fast_ma: int = 2,
    slow_ma: int = 7,
    bb_period: int = 34,
    bb_stddev: float = 1.6185,
) -> pd.DataFrame:
    """Big E sadeleştirilmiş TDI.

    Çıkış kolonları:
      tdi_green (RSI'nın hızlı SMA'sı), tdi_red (yavaş SMA), tdi_rsi (ham RSI),
      tdi_bb_upper, tdi_bb_lower, tdi_bb_mid (bilgi amaçlı, sinyal değil)
    """
    r = rsi(close, rsi_period)
    green = r.rolling(fast_ma, min_periods=fast_ma).mean()
    red = r.rolling(slow_ma, min_periods=slow_ma).mean()
    bb_mid = r.rolling(bb_period, min_periods=bb_period).mean()
    bb_std = r.rolling(bb_period, min_periods=bb_period).std(ddof=0)
    bb_upper = bb_mid + bb_stddev * bb_std
    bb_lower = bb_mid - bb_stddev * bb_std
    return pd.DataFrame({
        "tdi_rsi": r,
        "tdi_green": green,
        "tdi_red": red,
        "tdi_bb_mid": bb_mid,
        "tdi_bb_upper": bb_upper,
        "tdi_bb_lower": bb_lower,
    })


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 8,
    d_period: int = 3,
    smoothing: int = 3,
) -> pd.DataFrame:
    """Stochastic 8,3,3 (Big E'nin teyit indikatörü).

    %K_raw = 100 * (close - lowest_low) / (highest_high - lowest_low)
    %K     = SMA(%K_raw, smoothing)   (yavaşlatılmış)
    %D     = SMA(%K,     d_period)
    """
    ll = low.rolling(k_period, min_periods=k_period).min()
    hh = high.rolling(k_period, min_periods=k_period).max()
    raw_k = 100.0 * (close - ll) / (hh - ll).replace(0.0, np.nan)
    k = raw_k.rolling(smoothing, min_periods=smoothing).mean()
    d = k.rolling(d_period, min_periods=d_period).mean()
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def ema(series: pd.Series, period: int = 5) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean().rename("ema")


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ATR — stop loss ve filtreler için."""
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([
        (h - l).abs(),
        (h - prev_c).abs(),
        (l - prev_c).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean().rename("atr")


def mtf_trend_ekle(df: pd.DataFrame, df_yuksek_tf: pd.DataFrame, ema_p: int = 50) -> pd.DataFrame:
    """Yüksek TF EMA trend yönünü düşük TF'ye merge et.

    df: düşük TF (örn 4h), df_yuksek_tf: yüksek TF (örn 1d).
    Sonuç df'ye 'mtf_trend' kolonu ekler (+1 = yukarı, -1 = aşağı).
    """
    yuksek_ema = ema(df_yuksek_tf["close"], ema_p)
    yuksek_yon = (df_yuksek_tf["close"] > yuksek_ema).astype(int) * 2 - 1
    # Düşük TF index'ine forward-fill (yüksek TF mumu kapandıkça yenilenir)
    out = df.copy()
    out["mtf_trend"] = yuksek_yon.reindex(out.index, method="ffill")
    return out


def tum_indikatorler(
    df: pd.DataFrame,
    rsi_period: int = 13,
    tdi_fast: int = 2,
    tdi_slow: int = 7,
    stoch_k: int = 8,
    stoch_d: int = 3,
    stoch_smooth: int = 3,
    ema_p: int = 5,
    atr_p: int = 14,
    trend_ema_p: int = 50,
) -> pd.DataFrame:
    """Tüm indikatörleri tek seferde hesapla ve df'e ekle.

    Giriş df: open, high, low, close, volume (İstanbul saat indeksli).
    """
    out = heikin_ashi(df)
    tdi_df = tdi(df["close"], rsi_period, tdi_fast, tdi_slow)
    stoch_df = stochastic(df["high"], df["low"], df["close"], stoch_k, stoch_d, stoch_smooth)
    out = pd.concat([out, tdi_df, stoch_df], axis=1)
    out["ema5"] = ema(df["close"], ema_p)
    out["trend_ema"] = ema(df["close"], trend_ema_p)
    out["atr"] = atr(df, atr_p)
    return out
