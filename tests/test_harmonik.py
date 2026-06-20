"""Harmonik tarayıcı unit testleri — look-ahead yok, oran doğruluğu."""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.harmonik import tara, _bullish_oranlar, _bearish_oranlar, HarmonikSonuc
from miraz.pivotlar import pivot_listesi, swing_high_maske, swing_low_maske


# ---------------------------------------------------------------------------
# Yardımcı: sentetik OHLCV DataFrame
# ---------------------------------------------------------------------------

def _df(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="h", tz="UTC")
    c = np.array(closes, dtype=float)
    return pd.DataFrame({
        "open": c, "high": c * 1.005, "low": c * 0.995, "close": c, "volume": 1.0
    }, index=idx)


# ---------------------------------------------------------------------------
# Pivot testleri
# ---------------------------------------------------------------------------

def test_swing_high_tepe_noktasi():
    vals = [1, 2, 3, 5, 3, 2, 1, 2, 3, 5, 3, 2, 1]
    df = _df(vals)
    sh = swing_high_maske(df, n=2)
    assert sh[3] and sh[9], "Tepe noktaları swing high olmalı"


def test_swing_low_dip_noktasi():
    vals = [5, 3, 1, 3, 5, 3, 1, 3, 5]
    df = _df(vals)
    sl = swing_low_maske(df, n=2)
    assert sl[2] and sl[6], "Dip noktaları swing low olmalı"


def test_pivot_alternating():
    """Pivot listesi H-L-H-L sıralamasında olmalı."""
    vals = [1, 3, 1, 4, 1, 5, 1, 4, 1]
    df = _df(vals)
    pivlar = pivot_listesi(df, n=1)
    tipler = [p[2] for p in pivlar]
    for i in range(len(tipler) - 1):
        assert tipler[i] != tipler[i + 1], "Ardışık aynı tip pivot olamaz"


# ---------------------------------------------------------------------------
# Fibonacci oran testleri
# ---------------------------------------------------------------------------

def test_bullish_oranlar_gartley():
    """Mükemmel Bullish Gartley için oranlar 0.618/0.786 olmalı."""
    X, A = 100.0, 200.0   # XA = 100 (yukarı)
    B = A - 61.8           # AB/XA = 0.618
    C = B + 50.0           # BC/AB = 50/61.8 ≈ 0.809
    D = A - 78.6           # XD/XA = 0.786

    oranlar = _bullish_oranlar(X, A, B, C, D)
    assert oranlar is not None
    assert abs(oranlar["AB_XA"] - 0.618) < 0.01
    assert abs(oranlar["XD_XA"] - 0.786) < 0.01


def test_bearish_oranlar_bat():
    """Mükemmel Bearish Bat için AB/XA ≈ 0.5 ve XD/XA ≈ 0.886 olmalı."""
    X, A = 200.0, 100.0   # XA = 100 (aşağı)
    B = A + 50.0           # AB/XA = 0.5
    C = B - 30.0           # BC/AB = 0.6
    D = A + 88.6           # XD/XA = 0.886

    oranlar = _bearish_oranlar(X, A, B, C, D)
    assert oranlar is not None
    assert abs(oranlar["AB_XA"] - 0.5) < 0.01
    assert abs(oranlar["XD_XA"] - 0.886) < 0.01


# ---------------------------------------------------------------------------
# Tarama testleri
# ---------------------------------------------------------------------------

def _gartley_df():
    """Bullish Gartley içeren sentetik fiyat serisi (gerçekçi rampa hareketi).

    X=100, A=200, B=138.2, C=178.2, D=121.4
    AB/XA=0.618, BC/AB=0.647, CD/BC=1.42, XD/XA=0.786 — Gartley oranları.
    """
    X, A = 100.0, 200.0
    B = A - 61.8     # 138.2
    C = B + 40.0     # 178.2
    D = A - 78.6     # 121.4
    n = 8            # her bacak için bar sayısı
    fiyatlar = (
        list(np.linspace(X, X, 3)) +         # X bölgesi başlangıç
        list(np.linspace(X, A, n)) +          # X → A (yükseliş)
        list(np.linspace(A, B, n)) +          # A → B (düşüş)
        list(np.linspace(B, C, n)) +          # B → C (yükseliş)
        list(np.linspace(C, D, n)) +          # C → D (düşüş - PRZ)
        list(np.linspace(D, D, 3))            # D plateau
    )
    return _df(fiyatlar)


def test_gartley_tespit():
    df = _gartley_df()
    pivlar = pivot_listesi(df, n=2)
    sonuclar = tara(df, pivlar, min_kalite=0.0)
    isimler = [s.isim for s in sonuclar]
    assert "Gartley" in isimler, f"Gartley tespit edilemedi. Bulunanlar: {isimler}"


def test_tarama_bos_df():
    """Yetersiz veri ile tarama boş liste döndürmeli."""
    df = _df([100, 200, 100])
    pivlar = pivot_listesi(df, n=1)
    assert tara(df, pivlar) == []


def test_sonuc_sl_tp_mantigi():
    """Bullish pattern'de SL < entry < TP1 olmalı."""
    df = _gartley_df()
    pivlar = pivot_listesi(df, n=2)
    sonuclar = tara(df, pivlar, min_kalite=0.0)
    for s in sonuclar:
        if s.yon == "Bullish":
            assert s.sl < s.entry, "Bullish SL entry'nin altında olmalı"
            assert s.tp1 > s.entry, "Bullish TP1 entry'nin üstünde olmalı"
        else:
            assert s.sl > s.entry, "Bearish SL entry'nin üstünde olmalı"
            assert s.tp1 < s.entry, "Bearish TP1 entry'nin altında olmalı"
