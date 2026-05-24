"""İndikatör fonksiyonları için sanity testleri."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bige.indikatorler import (
    atr,
    ema,
    heikin_ashi,
    rsi,
    stochastic,
    tdi,
    tum_indikatorler,
)


def _ornek_df(n: int = 100, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 + rng.normal(0, 1, n).cumsum()
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    open_ = close + rng.normal(0, 0.3, n)
    vol = rng.uniform(100, 1000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="Europe/Istanbul")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def test_heikin_ashi_kolonlar():
    df = _ornek_df()
    ha = heikin_ashi(df)
    for c in ["ha_open", "ha_high", "ha_low", "ha_close", "ha_bullish"]:
        assert c in ha.columns
    # HA high her zaman HA open/close'tan büyük veya eşit
    assert (ha["ha_high"] >= ha["ha_open"]).all()
    assert (ha["ha_high"] >= ha["ha_close"]).all()
    assert (ha["ha_low"] <= ha["ha_open"]).all()
    assert (ha["ha_low"] <= ha["ha_close"]).all()


def test_rsi_aralik():
    df = _ornek_df(200)
    r = rsi(df["close"], 13)
    # Wilder smoothing'de ilk mum NaN, sonrası 0-100 arası olmalı
    r_valid = r.dropna()
    assert r_valid.min() >= 0
    assert r_valid.max() <= 100


def test_tdi_kolonlar():
    df = _ornek_df(200)
    t = tdi(df["close"])
    for c in ["tdi_rsi", "tdi_green", "tdi_red", "tdi_bb_mid", "tdi_bb_upper", "tdi_bb_lower"]:
        assert c in t.columns
    # Yeşil (hızlı) ile kırmızı (yavaş) farklı seriler olmalı
    diff = (t["tdi_green"] - t["tdi_red"]).dropna()
    assert diff.std() > 0


def test_stochastic_aralik():
    df = _ornek_df(200)
    s = stochastic(df["high"], df["low"], df["close"])
    valid = s.dropna()
    assert valid["stoch_k"].min() >= 0
    assert valid["stoch_k"].max() <= 100
    assert valid["stoch_d"].min() >= 0
    assert valid["stoch_d"].max() <= 100


def test_atr_pozitif():
    df = _ornek_df(200)
    a = atr(df, 14).dropna()
    assert (a > 0).all()


def test_tum_indikatorler_birlesik():
    df = _ornek_df(300)
    out = tum_indikatorler(df)
    beklenen = ["ha_open", "ha_close", "tdi_green", "tdi_red",
                "stoch_k", "stoch_d", "ema5", "atr"]
    for c in beklenen:
        assert c in out.columns
    # Index korunmuş olmalı
    assert (out.index == df.index).all()


def test_heikin_ashi_basit_ornek():
    df = pd.DataFrame({
        "open":  [100.0, 102.0, 101.0],
        "high":  [103.0, 104.0, 102.0],
        "low":   [99.0, 101.0, 100.0],
        "close": [102.0, 101.0, 100.5],
        "volume": [1.0, 1.0, 1.0],
    })
    ha = heikin_ashi(df)
    # İlk mum: ha_open = (100+102)/2 = 101, ha_close = (100+103+99+102)/4 = 101
    assert ha["ha_open"].iat[0] == pytest.approx(101.0)
    assert ha["ha_close"].iat[0] == pytest.approx(101.0)
    # İkinci mum: ha_open = (101 + 101)/2 = 101
    assert ha["ha_open"].iat[1] == pytest.approx(101.0)
