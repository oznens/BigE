"""Grafik üretim smoke testi — dosya gerçekten oluşuyor mu."""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import grafik
from miraz.harmonik import HarmonikSonuc
from miraz.kutular import Kutu


def _df(n=120):
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    rng = np.random.default_rng(1)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({
        "open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1.0
    }, index=idx)


def test_setup_ciz_dosya_olusturur(tmp_path):
    df = _df(120)
    p = HarmonikSonuc(
        isim="Gartley", yon="Bullish", X_idx=10, A_idx=30, B_idx=50,
        C_idx=70, D_idx=90, X=95, A=110, B=102, C=107, D=99,
        entry=99, sl=94, tp1=104, tp2=102, rr=2.0, oranlar={}, kalite=75)
    k = Kutu(alt=97, ust=101, merkez=99, renk="Mavi", tip="Destek",
             dokunus=3, guc=80, hacim_orani=1.2, son_idx=90, mesafe_yuzde=-1.0)
    cikti = tmp_path / "setup.png"
    yol = grafik.setup_ciz(df, p, [k], dosya=cikti, baslik="Test", son_n=120)
    assert yol.exists()
    assert yol.stat().st_size > 1000   # boş değil


def test_setup_ciz_patternsiz(tmp_path):
    """Pattern None olsa da sadece kutularla çizebilmeli."""
    df = _df(80)
    k = Kutu(alt=97, ust=101, merkez=99, renk="Mor", tip="Direnç",
             dokunus=2, guc=60, hacim_orani=1.0, son_idx=70, mesafe_yuzde=2.0)
    yol = grafik.setup_ciz(df, None, [k], dosya=tmp_path / "k.png", son_n=80)
    assert yol.exists()
