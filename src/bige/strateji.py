"""Big E strateji motoru — sinyal üretimi ve pozisyon yönetimi.

Mum mum çağrılmak üzere tasarlandı. Her mum için indikatörlerden gelen state'i
okur, entry/exit kararı verir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd


class Yon(Enum):
    LONG = 1
    SHORT = -1


@dataclass
class Pozisyon:
    yon: Yon
    giris_indeks: int
    giris_fiyati: float
    stop_loss: float
    miktar: float
    giris_zamani: pd.Timestamp


@dataclass
class Trade:
    yon: Yon
    giris_indeks: int
    cikis_indeks: int
    giris_fiyati: float
    cikis_fiyati: float
    miktar: float
    giris_zamani: pd.Timestamp
    cikis_zamani: pd.Timestamp
    sebep: str   # 'tdi_exit' | 'stop_loss'
    pnl_brut: float = 0.0
    pnl_net: float = 0.0   # komisyon + slipaj sonrası


@dataclass
class StratejiParams:
    # Entry filtreleri
    max_candle_age_after_cross: int = 1   # Big E: candle #1 veya #2 — yani cross'tan sonra ≤1 mum
    tdi_angle_min: float = 1.0   # son 2 mumdaki yeşil çizgi |delta| ≥ bu (saat 12-2 / 4-6)
    tdi_oversold: float = 32.0
    tdi_overbought: float = 68.0
    near_extreme_margin: float = 5.0   # 68'e veya 32'ye yakınsa pas
    min_ha_body_atr_ratio: float = 0.2   # gövde < bu*ATR ise küçük mum → pas
    require_stoch_confirm: bool = True
    stoch_lower: float = 20.0
    stoch_upper: float = 80.0

    # Trend filtresi (yeni)
    trend_filtresi_aktif: bool = True
    trend_ema_period: int = 50   # uzun EMA — long sadece price > EMA, short tersi

    # Çıkış
    tdi_flat_threshold: float = 0.25
    tdi_flat_lookback: int = 2

    # Risk / sizing
    risk_per_trade_pct: float = 1.0
    sl_mode: str = "atr"           # "swing" (eski) | "atr" (yeni default) | "hybrid"
    sl_lookback_candles: int = 3   # swing modu için, 2'den 3'e çıkarıldı
    sl_atr_period: int = 14
    sl_atr_multiplier: float = 2.0  # ATR × bu

    # Yönler
    allow_long: bool = True
    allow_short: bool = True


def _cross_yukari(g_prev: float, r_prev: float, g_now: float, r_now: float) -> bool:
    return g_prev <= r_prev and g_now > r_now


def _cross_asagi(g_prev: float, r_prev: float, g_now: float, r_now: float) -> bool:
    return g_prev >= r_prev and g_now < r_now


def _bul_son_cross_yas(df: pd.DataFrame, i: int, yon: Yon, max_geri: int = 5) -> int | None:
    """Cross'tan kaç mum geçti? None = son max_geri mumda cross yok."""
    for geri in range(max_geri + 1):
        if i - geri - 1 < 0:
            return None
        g_prev = df["tdi_green"].iat[i - geri - 1]
        r_prev = df["tdi_red"].iat[i - geri - 1]
        g_now = df["tdi_green"].iat[i - geri]
        r_now = df["tdi_red"].iat[i - geri]
        if pd.isna(g_prev) or pd.isna(r_prev):
            return None
        if yon is Yon.LONG and _cross_yukari(g_prev, r_prev, g_now, r_now):
            return geri
        if yon is Yon.SHORT and _cross_asagi(g_prev, r_prev, g_now, r_now):
            return geri
    return None


def _tdi_egim(df: pd.DataFrame, i: int, lookback: int = 2) -> float:
    """Son `lookback` mumda yeşil çizginin ortalama delta'sı."""
    if i - lookback < 0:
        return 0.0
    deltas = []
    for k in range(lookback):
        a = df["tdi_green"].iat[i - k]
        b = df["tdi_green"].iat[i - k - 1]
        if pd.isna(a) or pd.isna(b):
            return 0.0
        deltas.append(a - b)
    return float(np.mean(deltas))


def _ha_govde_atr_oranı(df: pd.DataFrame, i: int) -> float:
    body = abs(df["ha_close"].iat[i] - df["ha_open"].iat[i])
    a = df["atr"].iat[i]
    if pd.isna(a) or a == 0:
        return np.inf
    return body / a


def _stoch_yonu(df: pd.DataFrame, i: int) -> int:
    """+1 yukarı, -1 aşağı, 0 belirsiz."""
    k_now = df["stoch_k"].iat[i]
    d_now = df["stoch_d"].iat[i]
    if pd.isna(k_now) or pd.isna(d_now):
        return 0
    if k_now > d_now and k_now > 50:
        return 1
    if k_now < d_now and k_now < 50:
        return -1
    if k_now > d_now:
        return 1
    if k_now < d_now:
        return -1
    return 0


def giris_sinyali(df: pd.DataFrame, i: int, p: StratejiParams) -> Yon | None:
    """Mum `i` kapandı, bir sonraki mumun açılışında işleme girilecek mi?

    None = giriş yok. Yon.LONG / Yon.SHORT = giriş sinyali.
    """
    if i < 50:
        return None

    g = df["tdi_green"].iat[i]
    r = df["tdi_red"].iat[i]
    if pd.isna(g) or pd.isna(r):
        return None

    # LONG denemesi
    if p.allow_long:
        yas = _bul_son_cross_yas(df, i, Yon.LONG, max_geri=p.max_candle_age_after_cross)
        if yas is not None and yas <= p.max_candle_age_after_cross:
            if _long_filtreler(df, i, p):
                return Yon.LONG

    # SHORT denemesi
    if p.allow_short:
        yas = _bul_son_cross_yas(df, i, Yon.SHORT, max_geri=p.max_candle_age_after_cross)
        if yas is not None and yas <= p.max_candle_age_after_cross:
            if _short_filtreler(df, i, p):
                return Yon.SHORT

    return None


def _trend_yonu(df: pd.DataFrame, i: int, p: StratejiParams) -> int:
    """Long EMA bazlı uzun trend: +1 yukarı, -1 aşağı."""
    if not p.trend_filtresi_aktif:
        return 0   # nötr — filtre yok
    col = "trend_ema"
    if col not in df.columns:
        return 0
    ema = df[col].iat[i]
    if pd.isna(ema):
        return 0
    return 1 if df["close"].iat[i] > ema else -1


def _long_filtreler(df: pd.DataFrame, i: int, p: StratejiParams) -> bool:
    # HA yeşil mum (cross sonrası yön)
    if not bool(df["ha_bullish"].iat[i]):
        return False
    # TDI açısı (yukarı eğim)
    if _tdi_egim(df, i, lookback=2) < p.tdi_angle_min:
        return False
    # 68'e yakın değil
    if df["tdi_green"].iat[i] >= p.tdi_overbought - p.near_extreme_margin:
        return False
    # HA gövde küçük değil
    if _ha_govde_atr_oranı(df, i) < p.min_ha_body_atr_ratio:
        return False
    # Stoch teyit
    if p.require_stoch_confirm and _stoch_yonu(df, i) != 1:
        return False
    # Uzun trend filtresi
    if p.trend_filtresi_aktif:
        t = _trend_yonu(df, i, p)
        if t != 1 and t != 0:
            return False
    return True


def _short_filtreler(df: pd.DataFrame, i: int, p: StratejiParams) -> bool:
    if bool(df["ha_bullish"].iat[i]):
        return False
    if _tdi_egim(df, i, lookback=2) > -p.tdi_angle_min:
        return False
    if df["tdi_green"].iat[i] <= p.tdi_oversold + p.near_extreme_margin:
        return False
    if _ha_govde_atr_oranı(df, i) < p.min_ha_body_atr_ratio:
        return False
    if p.require_stoch_confirm and _stoch_yonu(df, i) != -1:
        return False
    if p.trend_filtresi_aktif:
        t = _trend_yonu(df, i, p)
        if t != -1 and t != 0:
            return False
    return True


def cikis_sinyali(df: pd.DataFrame, i: int, pos: Pozisyon, p: StratejiParams) -> bool:
    """Açık pozisyon var; mum `i` kapandı, çıkalım mı?"""
    g = df["tdi_green"].iat[i]
    r = df["tdi_red"].iat[i]
    if pd.isna(g) or pd.isna(r):
        return False

    # 1) Resmi check-mark: yeşil kırmızıyı ters kesti
    g_prev = df["tdi_green"].iat[i - 1]
    r_prev = df["tdi_red"].iat[i - 1]
    if pos.yon is Yon.LONG and _cross_asagi(g_prev, r_prev, g, r):
        return True
    if pos.yon is Yon.SHORT and _cross_yukari(g_prev, r_prev, g, r):
        return True

    # 2) Hook: yön değiştiren eğim
    egim = _tdi_egim(df, i, lookback=p.tdi_flat_lookback)
    if pos.yon is Yon.LONG and egim < -p.tdi_flat_threshold:
        return True
    if pos.yon is Yon.SHORT and egim > p.tdi_flat_threshold:
        return True

    # 3) Flat: momentum kayboldu
    if abs(egim) < p.tdi_flat_threshold * 0.5:
        # Sadece pozisyon kâra geçtiyse flat exit aktif olsun
        if pos.yon is Yon.LONG and df["close"].iat[i] > pos.giris_fiyati:
            return True
        if pos.yon is Yon.SHORT and df["close"].iat[i] < pos.giris_fiyati:
            return True

    return False


def stop_loss_hesapla(
    df: pd.DataFrame,
    i: int,
    yon: Yon,
    p: StratejiParams,
    giris_fiyat: float | None = None,
) -> float:
    """Stop loss seviyesi.

    Modlar:
      - "swing": girilen mumdan sl_lookback_candles mum geri swing high/low
      - "atr":   giriş fiyatı ± sl_atr_multiplier × ATR
      - "hybrid": ikisinden hangisi daha uzaksa onu kullan (daha güvenli)
    """
    px = giris_fiyat if giris_fiyat is not None else float(df["close"].iat[i])

    def swing_seviye() -> float:
        bas = max(0, i - p.sl_lookback_candles)
        son = i
        if son <= bas:
            return px
        if yon is Yon.LONG:
            return float(df["low"].iloc[bas:son].min())
        return float(df["high"].iloc[bas:son].max())

    def atr_seviye() -> float:
        a = df["atr"].iat[i]
        if pd.isna(a) or a == 0:
            return swing_seviye()
        return px - p.sl_atr_multiplier * a if yon is Yon.LONG else px + p.sl_atr_multiplier * a

    if p.sl_mode == "swing":
        return swing_seviye()
    if p.sl_mode == "atr":
        return atr_seviye()
    # hybrid: long için en düşük SL (en uzak), short için en yüksek SL
    s, a = swing_seviye(), atr_seviye()
    return min(s, a) if yon is Yon.LONG else max(s, a)
