import pandas as pd

from miraz.miraz_v2 import (
    MirazV2Ayar,
    kapanis_hacim_onayi,
    plan_uret,
    retest_onayi,
    yonetim_simule,
)


def _df(rows):
    idx = pd.date_range("2026-01-01", periods=len(rows), freq="15min", tz="UTC")
    return pd.DataFrame(rows, index=idx)


def test_plan_2r_and_partial_levels_long():
    p = plan_uret(100.0, 98.0, "Long")
    assert p is not None
    assert p.ilk_hedef == 102.0
    assert p.ana_hedef == 104.0
    assert p.rr == 2.0
    assert p.ilk_kar_orani == 0.65


def test_close_volume_confirmation_rejects_wick_only():
    rows = []
    for _ in range(20):
        rows.append({"open": 99, "high": 100, "low": 98, "close": 99, "volume": 100})
    rows.append({"open": 99, "high": 101.5, "low": 98.5, "close": 99.5, "volume": 200})
    d = _df(rows)
    assert not kapanis_hacim_onayi(d, 100.0, "Long")


def test_close_volume_confirmation_accepts_close_break():
    rows = []
    for _ in range(20):
        rows.append({"open": 99, "high": 100, "low": 98, "close": 99, "volume": 100})
    rows.append({"open": 99, "high": 102, "low": 98.5, "close": 101, "volume": 120})
    d = _df(rows)
    assert kapanis_hacim_onayi(d, 100.0, "Long")


def test_retest_requires_acceptance_close():
    d = _df([
        {"open": 101, "high": 102, "low": 100.1, "close": 101.5, "volume": 100},
        {"open": 101.5, "high": 102, "low": 99.9, "close": 100.4, "volume": 100},
    ])
    assert retest_onayi(d, 100.0, "Long", kirilim_idx=0,
                        ayar=MirazV2Ayar(retest_tolerans=0.002))


def test_partial_then_be_returns_positive_r():
    p = plan_uret(100.0, 98.0, "Long")
    d = _df([
        {"open": 100, "high": 102.2, "low": 100.1, "close": 102, "volume": 100},
        {"open": 102, "high": 102.4, "low": 99.9, "close": 100.2, "volume": 100},
    ])
    s = yonetim_simule(d, p)
    assert s.durum == "BE"
    assert s.gross_r == 0.65


def test_partial_then_2r_returns_135r():
    p = plan_uret(100.0, 98.0, "Long")
    d = _df([
        {"open": 100, "high": 102.2, "low": 100.1, "close": 102, "volume": 100},
        {"open": 102, "high": 104.2, "low": 101.5, "close": 104, "volume": 100},
    ])
    s = yonetim_simule(d, p)
    assert s.durum == "TP2"
    assert s.gross_r == 1.35


def test_same_bar_stop_wins_before_partial():
    p = plan_uret(100.0, 98.0, "Long")
    d = _df([
        {"open": 100, "high": 102.5, "low": 97.5, "close": 101, "volume": 100},
    ])
    s = yonetim_simule(d, p)
    assert s.durum == "STOP"
    assert s.gross_r == -1.0
