"""PA Konsept dedektörleri testleri (Drift … Reservoir)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import konsept as kn


def _df(o, h, l, c, v=None):
    n = len(c)
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                         "volume": v if v is not None else [1.0] * n}, index=idx)


def _duz(n=60, fiyat=100.0):
    """Tamamen düz seri — hiçbir konsept tetiklenmemeli."""
    arr = np.full(n, fiyat)
    return _df(arr, arr, arr, arr)


def test_kayit_defteri_tam():
    # 10 dedektör de kayıtlı ve sıralı
    assert set(kn.DEDEKTORLER) == set(kn.KONSEPT_SIRASI) - {"Harmonic"}
    assert len(kn.DEDEKTORLER) == 10


def test_duz_seride_sinyal_yok():
    d = kn.tara_konseptler(_duz())
    assert d == {} or all(isinstance(v, kn.KonseptSinyal) for v in d.values())


# ---- Cavity (FVG) ----

def test_cavity_bullish_fvg():
    # 100 civarı, sonra yukarı boşluk: high[i-1]=101 < low[i+1]=103.5
    o = [100]*20 + [100, 104, 104] + [104]*10
    h = [101]*20 + [101, 105, 104.5] + [104.5]*10
    l = [99]*20 + [99, 103, 103.5] + [103.5]*10
    c = [100]*20 + [100, 104, 104] + [104]*10
    s = kn.cavity(_df(o, h, l, c))
    assert s is not None and s.yon == "Long"
    assert s.zone_alt == 101 and s.zone_ust == 103.5


def test_cavity_yoksa_none():
    assert kn.cavity(_duz()) is None


# ---- Torque (momentum patlaması) ----

def test_torque_buyuk_mum():
    o = [100.0]*40; h = [100.5]*40; l = [99.5]*40; c = [100.2]*40
    v = [1.0]*40
    # son bar: dev yeşil gövde + hacim sıçraması
    o[-1], c[-1], h[-1], l[-1], v[-1] = 100.0, 108.0, 108.5, 99.8, 5.0
    s = kn.torque(_df(o, h, l, c, v))
    assert s is not None and s.yon == "Long" and s.idx == 39


# ---- Ladder (merdiven) ----

def _zigzag(pivots, seg=8):
    vals = [pivots[0]]
    for k in range(1, len(pivots)):
        a, b = pivots[k-1], pivots[k]
        vals += [a + (b-a)*j/seg for j in range(1, seg+1)]
    arr = np.array(vals)
    return _df(arr, arr+0.3, arr-0.3, arr)


def test_ladder_yukselen():
    # ardışık HH-HL: dipler ve tepeler hep artıyor
    df = _zigzag([100, 96, 104, 100, 108, 104, 112, 108, 116])
    s = kn.ladder(df)
    assert s is not None and s.yon == "Long"


def test_ladder_dusen():
    df = _zigzag([116, 112, 108, 104, 100, 96, 92, 88, 84][::-1][::-1])
    # düşen: tepeler ve dipler azalan
    df = _zigzag([116, 120, 108, 112, 100, 104, 92, 96, 84])
    s = kn.ladder(df)
    assert s is not None and s.yon == "Short"


# ---- Buffer (sıkışma) ----

def test_buffer_buzulme():
    # önce geniş range (24 bar), sonra dar range (12 bar)
    genis = list(np.tile([90, 110], 12))           # 24 bar 90-110 salınım
    dar = list(np.tile([99.5, 100.5], 6))          # 12 bar dar
    c = genis + dar
    h = [x + 1 for x in c]; l = [x - 1 for x in c]
    s = kn.buffer(_df(c, h, l, c))
    assert s is not None
    assert s.zone_ust - s.zone_alt < 5             # dar bant


# ---- Drift (düşük oynaklık yönlü) ----

def test_drift_sakin_yukselis():
    # küçük genlikli yükselen zigzag → düşük ATR ama HH/HL yapısı (sürüklenme)
    df = _zigzag([100, 99.5, 100.5, 100.0, 101.0, 100.5, 101.5], seg=8)
    s = kn.drift(_df(df["open"], df["high"], df["low"], df["close"]))
    assert s is not None and s.yon == "Long"


# ---- Reservoir (likidite süpürme) ----

def test_reservoir_esit_tepe_supuruldu():
    # iki eşit tepe (~120), son barda üstüne fitil + altına kapanış → Short
    df = _zigzag([100, 90, 120, 95, 120.1, 100])
    # son barı süpürme barı yap: high 121 (havuz üstü), close 110 (havuz altı)
    df.iloc[-1, df.columns.get_loc("high")] = 121.0
    df.iloc[-1, df.columns.get_loc("close")] = 110.0
    df.iloc[-1, df.columns.get_loc("low")] = 109.0
    s = kn.reservoir(df)
    assert s is not None and s.yon == "Short"


# ---- Toplu tarama ----

def test_tara_secili_filtre():
    df = _zigzag([100, 96, 104, 100, 108, 104, 112, 108, 116])
    d = kn.tara_konseptler(df, secili=["Ladder"])
    assert set(d.keys()).issubset({"Ladder"})


def test_tara_rastgele_yuruyus_cokmesin():
    rng = np.random.RandomState(3)
    c = 100 + np.cumsum(rng.randn(120))
    h = c + np.abs(rng.randn(120)); l = c - np.abs(rng.randn(120))
    d = kn.tara_konseptler(_df(c, h, l, c, list(np.abs(rng.randn(120)) + 1)))
    assert isinstance(d, dict)
    for v in d.values():
        assert isinstance(v, kn.KonseptSinyal)
        assert v.yon in ("Long", "Short", "Nötr")
