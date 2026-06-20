"""Çift Tepe / Çift Dip tespiti testleri."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.ikili import ikili_bul, metin


def _df(fiyatlar):
    f = np.array(fiyatlar, dtype=float)
    return pd.DataFrame({
        "open": f, "high": f * 1.001, "low": f * 0.999, "close": f,
        "volume": np.ones(len(f)),
    })


def _zikzak(noktalar, adim=8):
    seri = []
    for i in range(len(noktalar) - 1):
        seri.extend(np.linspace(noktalar[i], noktalar[i + 1], adim,
                                endpoint=False))
    seri.append(noktalar[-1])
    return seri


def test_cift_tepe_onayli():
    # İki benzer tepe (100, 99.5), boyun 85, sonra boyun altına kapanış (80)
    nokta = [70, 100, 85, 99.5, 80]
    f = ikili_bul(_df(_zikzak(nokta)), n=3)
    assert f is not None
    assert f.tip == "Çift Tepe" and f.yon == "Bearish"
    assert f.onayli is True
    assert f.hedef < f.boyun


def test_cift_dip_onayli():
    # İki benzer dip (60, 60.5), boyun 80, sonra boyun üstüne kapanış (90)
    nokta = [100, 60, 80, 60.5, 90]
    f = ikili_bul(_df(_zikzak(nokta)), n=3)
    assert f is not None
    assert f.tip == "Çift Dip" and f.yon == "Bullish"
    assert f.onayli is True
    assert f.hedef > f.boyun


def test_benzer_degil_yok():
    # İki tepe çok farklı (100 vs 80) → çift tepe değil
    nokta = [70, 100, 85, 80, 88]
    f = ikili_bul(_df(_zikzak(nokta)), n=3, tolerans=0.02)
    assert f is None or f.tip != "Çift Tepe"


def test_metin():
    nokta = [70, 100, 85, 99.5, 80]
    f = ikili_bul(_df(_zikzak(nokta)), n=3)
    s = metin(f)
    assert "Çift Tepe" in s and "hedef" in s.lower()
    assert metin(None) == ""
