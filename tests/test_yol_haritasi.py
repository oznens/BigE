"""Çoklu-bölge yol haritası testleri."""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.yol_haritasi import yol_haritasi_uret, YolHaritasi, Bolge


def _df(closes, hacimler=None):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="4h", tz="UTC")
    c = np.array(closes, dtype=float)
    v = np.array(hacimler, dtype=float) if hacimler else np.ones(len(closes))
    return pd.DataFrame({
        "open": c, "high": c * 1.004, "low": c * 0.996, "close": c, "volume": v
    }, index=idx)


def test_yol_haritasi_yapisi():
    rng = np.random.default_rng(5)
    fiyatlar = list(100 + np.cumsum(rng.normal(0, 1.2, 500)))
    df = _df(fiyatlar)
    yh = yol_haritasi_uret(df, symbol="BTCUSDT", interval="4h", n=3, min_guc=40)
    assert isinstance(yh, YolHaritasi)
    assert yh.fiyat > 0
    assert isinstance(yh.metin, str) and len(yh.metin) > 0
    for b in yh.bolgeler:
        assert isinstance(b, Bolge)
        # Rol ile tip tutarlı olmalı
        if b.tip == "Direnç":
            assert b.rol == "SHORT"
        else:
            assert b.rol == "LONG"


def test_short_ust_long_alt():
    """SHORT bölgeleri fiyatın üstünde, LONG bölgeleri altında olmalı."""
    seviyeler = []
    for _ in range(5):
        seviyeler += list(np.linspace(125, 100, 8))
        seviyeler += list(np.linspace(100, 150, 8))
        seviyeler += list(np.linspace(150, 125, 8))
    df = _df(seviyeler)
    yh = yol_haritasi_uret(df, symbol="X", interval="4h", n=3, min_guc=30)
    for b in yh.bolgeler:
        if b.rol == "SHORT":
            assert b.merkez > yh.fiyat
        else:
            assert b.merkez < yh.fiyat


def test_bolgeler_ustten_alta_sirali():
    rng = np.random.default_rng(9)
    df = _df(list(200 + np.cumsum(rng.normal(0, 1.5, 400))))
    yh = yol_haritasi_uret(df, symbol="X", interval="4h", n=4, min_guc=40)
    merkezler = [b.merkez for b in yh.bolgeler]
    assert merkezler == sorted(merkezler, reverse=True), "Üst→alt sıralı olmalı"
