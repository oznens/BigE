"""Strateji ve backtest motoru sanity testleri."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams


def _trendli_df(n: int = 500, seed: int = 0) -> pd.DataFrame:
    """Çıkan + inen + çıkan: backtest motorunun her iki yönü de almasını test eder."""
    rng = np.random.default_rng(seed)
    yon = np.concatenate([
        np.ones(n // 3),
        -np.ones(n // 3),
        np.ones(n - 2 * (n // 3)),
    ])
    noise = rng.normal(0, 0.3, n)
    drift = 0.5 * yon
    close = 100.0 + (drift + noise).cumsum()
    close = np.maximum(close, 1.0)
    high = close + np.abs(rng.normal(0, 0.4, n))
    low = close - np.abs(rng.normal(0, 0.4, n))
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = rng.uniform(100, 1000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="Europe/Istanbul")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def test_backtest_calisir_hatasiz():
    df = _trendli_df(500)
    sonuc = calistir(df, StratejiParams(), BacktestKonfig())
    assert sonuc.bakiye_serisi is not None
    assert len(sonuc.bakiye_serisi) == len(df)


def test_backtest_trend_yakalar():
    """Belirgin trendli sentetik veride en az birkaç trade açmalı."""
    df = _trendli_df(800, seed=42)
    # Sentetik veriyle uzun trend EMA çalışmaz — filtreleri gevşeterek test ediyoruz
    p = StratejiParams(
        trend_filtresi_aktif=False,
        tdi_angle_min=0.2,
        min_ha_body_atr_ratio=0.05,
        require_stoch_confirm=False,
    )
    sonuc = calistir(df, p, BacktestKonfig())
    assert len(sonuc.trades) > 0, "Trend varken hiç trade açılmadı"


def test_istatistikler_yapisi():
    df = _trendli_df(500)
    sonuc = calistir(df, StratejiParams(), BacktestKonfig())
    ist = sonuc.istatistikler()
    assert "trade_sayisi" in ist
    if ist["trade_sayisi"] > 0:
        for k in ["win_rate", "toplam_pnl", "profit_factor", "max_drawdown"]:
            assert k in ist
