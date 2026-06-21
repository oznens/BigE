"""OBO / TOBO (omuz-baş-omuz) testleri."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.obo import obo_bul, metin


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


def test_obo_tepe_onayli():
    # H-L-H-L-H: sol omuz 120, baş 150, sağ omuz 119 (benzer omuz), boyun ~100
    # son fiyat boyun altında (95) → onaylı bearish
    nokta = [90, 120, 100, 150, 101, 119, 95]
    o = obo_bul(_df(_zikzak(nokta)), n=3)
    assert o is not None
    assert o.tip == "OBO" and o.yon == "Bearish"
    assert o.bas > o.sol_omuz and o.bas > o.sag_omuz
    assert o.onayli is True
    assert o.hedef < o.boyun


def test_tobo_dip_onayli():
    # L-H-L-H-L ters: sol omuz 80, baş 50, sağ omuz 81, boyun ~100, fiyat 105
    nokta = [110, 80, 100, 50, 99, 81, 105]
    o = obo_bul(_df(_zikzak(nokta)), n=3)
    assert o is not None
    assert o.tip == "TOBO" and o.yon == "Bullish"
    assert o.bas < o.sol_omuz and o.bas < o.sag_omuz
    assert o.onayli is True
    assert o.hedef > o.boyun


def test_omuzlar_benzer_degilse_yok():
    # omuzlar çok farklı (120 vs 90) → OBO değil
    nokta = [80, 120, 100, 150, 101, 90, 95]
    o = obo_bul(_df(_zikzak(nokta)), n=3, omuz_tol=0.03)
    assert o is None or o.tip != "OBO"


def test_metin():
    nokta = [90, 120, 100, 150, 101, 119, 95]
    o = obo_bul(_df(_zikzak(nokta)), n=3)
    s = metin(o)
    assert "OBO" in s and "omuz" in s.lower()
    assert metin(None) == ""
