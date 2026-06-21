"""Fibonacci retracement testleri (@finansalTRader tarzı)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.fib import fib_retracement, metin


def _df(fiyatlar):
    f = np.array(fiyatlar, dtype=float)
    return pd.DataFrame({
        "open": f, "high": f * 1.001, "low": f * 0.999, "close": f,
        "volume": np.ones(len(f)),
    })


def _zikzak(noktalar, adim=10):
    seri = []
    for i in range(len(noktalar) - 1):
        seri.extend(np.linspace(noktalar[i], noktalar[i + 1], adim,
                                endpoint=False))
    seri.append(noktalar[-1])
    return seri


def test_yukselis_golden_pocket():
    # Dip 100 → tepe 200, sonra 0.618'e geri çekilme (138.2 civarı)
    nokta = [130, 100, 200, 138]
    fr = fib_retracement(_df(_zikzak(nokta)), n=3, son_n=300)
    assert fr is not None
    assert fr.yon == "Yükseliş"
    assert fr.swing_dusuk < fr.swing_yuksek
    # 0.618 seviyesi = 200 - 0.618*100 = 138.2
    s618 = next(s for s in fr.seviyeler if s.oran == 0.618)
    assert abs(s618.fiyat - 138.2) < 1.0
    assert s618.golden is True


def test_dusus_yon():
    # Tepe 200 → dip 100, sonra yukarı geri çekilme
    nokta = [80, 200, 100, 160]
    fr = fib_retracement(_df(_zikzak(nokta)), n=3, son_n=300)
    assert fr is not None
    assert fr.yon == "Düşüş"
    # düşüşte 0.618 = 100 + 0.618*100 = 161.8 (direnç adayı)
    s618 = next(s for s in fr.seviyeler if s.oran == 0.618)
    assert abs(s618.fiyat - 161.8) < 1.0


def test_golden_icinde_tespit():
    # Fiyat tam golden pocket içinde bitiyor
    nokta = [130, 100, 200, 135]
    fr = fib_retracement(_df(_zikzak(nokta)), n=3, son_n=300)
    assert fr.fiyat_golden_icinde is True
    assert "GOLDEN POCKET" in metin(fr).upper()


def test_metin_bos():
    assert metin(None) == ""
