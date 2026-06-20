"""Market yapısı (market structure) testleri."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.yapi import market_yapisi, metin, MarketYapisi


def _df(fiyatlar):
    """Basit OHLC DataFrame (high=low=close=open=fiyat + küçük fitil)."""
    f = np.array(fiyatlar, dtype=float)
    return pd.DataFrame({
        "open": f, "high": f * 1.001, "low": f * 0.999, "close": f,
        "volume": np.ones(len(f)),
    })


def _zikzak(noktalar, adim=8):
    """Pivot noktaları arasında lineer rampa ile seri üretir."""
    seri = []
    for i in range(len(noktalar) - 1):
        seri.extend(np.linspace(noktalar[i], noktalar[i + 1], adim,
                                endpoint=False))
    seri.append(noktalar[-1])
    return seri


def test_yukselis_yapisi():
    # HH + HL: her tepe ve dip bir öncekinden yüksek
    nokta = [100, 120, 110, 140, 130, 160]
    my = market_yapisi(_df(_zikzak(nokta)), n=3)
    assert my is not None
    assert my.durum == "yükseliş"


def test_dusus_yapisi():
    # LH + LL: her tepe ve dip bir öncekinden düşük (MSTR senaryosu)
    nokta = [160, 130, 140, 110, 120, 90]
    my = market_yapisi(_df(_zikzak(nokta)), n=3)
    assert my is not None
    assert my.durum == "düşüş"


def test_metin_bos():
    g = MarketYapisi("düşüş", "BOS-aşağı", 150.0, 120.0, "x")
    s = metin(g)
    assert "📉" in s and "temkinli" in s
    assert metin(None) == ""


def test_choch_donus():
    g = MarketYapisi("yükseliş", "CHoCH-aşağı", 150.0, 120.0,
                     "Market yapısı yükselişte — yapı AŞAĞIYA döndü")
    s = metin(g)
    assert "AŞAĞIYA döndü" in s
