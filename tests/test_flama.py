"""Flama (yakınsayan üçgen) tespiti testleri."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.flama import flama_bul, metin


def _df(fiyatlar):
    f = np.array(fiyatlar, dtype=float)
    return pd.DataFrame({
        "open": f, "high": f * 1.001, "low": f * 0.999, "close": f,
        "volume": np.ones(len(f)),
    })


def _flama_serisi():
    """Simetrik üçgen: tepe düşüyor, dip yükseliyor, aralık daralıyor."""
    seri = []
    tepe, dip = 100.0, 60.0
    for k in range(7):                       # 7 salınım
        # her salınımda tepe iner, dip yükselir → daralma
        ust = tepe - k * 2.5
        alt = dip + k * 2.5
        seri.extend(np.linspace(alt, ust, 5, endpoint=False))   # dip→tepe
        seri.extend(np.linspace(ust, alt + 2.5, 5, endpoint=False))  # tepe→yeni dip
    return seri


def test_flama_tespit():
    f = flama_bul(_df(_flama_serisi()), n=2, son_n=120, min_dokunus=2)
    assert f is not None
    assert f.direnc.egim < 0       # üst çizgi düşüyor
    assert f.destek.egim > 0       # alt çizgi yükseliyor
    assert f.daralma is True
    assert f.apeks_bar > 0


def test_flama_yok_duz_trend():
    # Tek yönlü düz yükseliş → flama yok
    duz = list(np.linspace(50, 120, 80))
    assert flama_bul(_df(duz), n=2, son_n=120, min_dokunus=2) is None


def test_metin():
    f = flama_bul(_df(_flama_serisi()), n=2, son_n=120, min_dokunus=2)
    s = metin(f)
    assert "Flama" in s
    assert metin(None) == ""
