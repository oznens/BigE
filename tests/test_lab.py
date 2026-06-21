"""Price Action Labs (backtest motoru) testleri."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.lab import _simule, LabRapor, Islem


def _df(bars):
    """bars: list of (low, high) → OHLC df (open=close=orta)."""
    low = np.array([b[0] for b in bars], dtype=float)
    high = np.array([b[1] for b in bars], dtype=float)
    mid = (low + high) / 2
    return pd.DataFrame({"open": mid, "high": high, "low": low,
                         "close": mid, "volume": np.ones(len(bars))})


def test_simule_tp():
    # bar0 setup; giriş 100, stop 95, hedef 110
    # bar1 düşer girişe dokunur (low 99), bar2 hedefe çıkar (high 111)
    df = _df([(100, 100), (99, 101), (108, 111), (100, 100)])
    sonuc, j = _simule(df, 0, giris=100, stop=95, hedef=110, max_bar=5)
    assert sonuc == "TP"


def test_simule_stop():
    # giriş dolar (bar1 low 99), sonra stop'a düşer (bar2 low 94)
    df = _df([(100, 100), (99, 101), (94, 98), (100, 100)])
    sonuc, j = _simule(df, 0, giris=100, stop=95, hedef=110, max_bar=5)
    assert sonuc == "STOP"


def test_simule_dolmadi():
    # fiyat hiç girişe (100) inmez → Dolmadı
    df = _df([(105, 106), (106, 108), (107, 109)])
    sonuc, j = _simule(df, 0, giris=100, stop=95, hedef=110, max_bar=5)
    assert sonuc == "Dolmadı"


def test_simule_ayni_bar_stop_oncelik():
    # giriş dolu; bir bar hem stop hem hedefi içerir → muhafazakâr STOP
    df = _df([(100, 100), (94, 111)])
    sonuc, j = _simule(df, 0, giris=100, stop=95, hedef=110, max_bar=3)
    assert sonuc == "STOP"


def test_rapor_istatistik():
    r = LabRapor(islemler=[
        Islem(0, 100, 95, 110, 2.0, "A", 80, "TP", 2.0),
        Islem(5, 100, 95, 110, 2.0, "A", 78, "STOP", -1.0),
        Islem(9, 100, 95, 110, 2.0, "B", 60, "TP", 2.0),
        Islem(12, 100, 95, 110, 2.0, "C", 55, "Dolmadı", 0.0),
    ])
    assert len(r.dolan) == 3                 # Dolmadı sayılmaz
    assert abs(r.win_rate - 66.6667) < 0.1   # 2/3
    assert r.toplam_r == 3.0                 # +2 -1 +2
    kg = r.kaliteye_gore()
    assert kg["A"]["wr"] == 50.0 and kg["B"]["wr"] == 100.0


# ---- _kur_islem mod mantığı ----

from dataclasses import dataclass as _dc
from miraz.lab import _kur_islem


@_dc
class _Kutu:
    alt: float


@_dc
class _S:
    bolge_alt: float = 100.0
    bolge_ust: float = 110.0
    mavi_daire: float = None
    fitil_seviye: float = 98.0
    kritik_seviye: float = 100.0
    ara_hedef: float = 116.0
    hedef_kutu: object = None


def test_kur_islem_giris_modlari():
    s = _S(hedef_kutu=_Kutu(alt=130.0))
    assert _kur_islem(s, "ust", "fitil", "ana")[0] == 110.0    # bölge üstü
    assert _kur_islem(s, "alt", "fitil", "ana")[0] == 100.0    # bölge altı
    assert _kur_islem(s, "orta", "fitil", "ana")[0] == 105.0   # orta


def test_kur_islem_tp_modlari():
    s = _S(hedef_kutu=_Kutu(alt=130.0))
    assert _kur_islem(s, "orta", "fitil", "ara")[2] == 116.0   # mor çizgi
    assert _kur_islem(s, "orta", "fitil", "ana")[2] == 130.0   # ana hedef
    # rr2: giriş 105, stop 98 → hedef = 105 + 2*(105-98) = 119
    assert _kur_islem(s, "orta", "fitil", "rr2")[2] == 119.0


def test_kur_islem_stop_girisin_altinda():
    s = _S(hedef_kutu=_Kutu(alt=130.0))
    giris, stop, hedef, rr = _kur_islem(s, "orta", "fitil", "ana")
    assert stop < giris and hedef > giris and rr > 0
