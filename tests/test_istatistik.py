from types import SimpleNamespace

import pytest

from miraz.istatistik import (
    bootstrap_beklenti_ci,
    kalibrasyon,
    max_drawdown_r,
    performans,
    profit_factor,
)
from miraz.lab_v2 import LiveLabRapor


def _islem(r, guven, sonuc):
    return SimpleNamespace(r=r, guven=guven, sonuc=sonuc)


def test_risk_metrics():
    rler = [1.0, -1.0, -0.5, 2.0]
    assert max_drawdown_r(rler) == pytest.approx(1.5)
    assert profit_factor(rler) == pytest.approx(2.0)


def test_bootstrap_is_deterministic_and_contains_mean():
    rler = [1.0, 1.0, -1.0, 0.5, -0.5]
    a = bootstrap_beklenti_ci(rler, tekrar=500, seed=7)
    b = bootstrap_beklenti_ci(rler, tekrar=500, seed=7)
    assert a == b
    assert a[0] <= sum(rler) / len(rler) <= a[1]


def test_calibration_bins_observed_win_rate():
    rapor = LiveLabRapor(islemler=[
        _islem(1.0, 72, "TP"),
        _islem(-1.0, 78, "STOP"),
        _islem(1.0, 84, "TP"),
    ])
    bins = kalibrasyon(rapor, bin_genislik=10)
    b70 = next(x for x in bins if x.alt == 70)
    assert b70.n == 2
    assert b70.ort_guven == pytest.approx(75.0)
    assert b70.gercek_wr == pytest.approx(50.0)
    assert b70.fark == pytest.approx(-25.0)


def test_performans_net_r_metrics():
    rapor = LiveLabRapor(islemler=[
        _islem(0.9, 75, "TP"),
        _islem(-1.1, 70, "STOP"),
        _islem(0.0, 80, "Dolmadı"),
        _islem(1.4, 85, "TP"),
    ])
    p = performans(rapor, bootstrap_tekrar=300)
    assert p.n == 3
    assert p.win_rate == pytest.approx(66.67, abs=0.01)
    assert p.toplam_r == pytest.approx(1.2)
    assert p.beklenti_r == pytest.approx(0.4)
    assert p.profit_factor == pytest.approx(2.3 / 1.1, abs=1e-4)
    assert p.max_drawdown_r == pytest.approx(1.1)
