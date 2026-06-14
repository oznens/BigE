"""Temel doğruluk testleri — look-ahead yok, sinyal mantığı, metrikler."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from walter import backtest as bt        # noqa: E402
from walter import indikatorler as ind    # noqa: E402
from walter import strateji as st         # noqa: E402


def _sahte_veri(n=2000, seed=0):
    """Saatlik UTC indeksli rastgele yürüyüş OHLCV."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="h", tz="UTC")
    ret = rng.normal(0, 0.01, n)
    close = 20000 * np.exp(np.cumsum(ret))
    df = pd.DataFrame(
        {
            "open": close,
            "high": close * 1.002,
            "low": close * 0.998,
            "close": close,
            "volume": rng.uniform(1, 10, n),
        },
        index=idx,
    )
    df.index.name = "zaman"
    return df


def test_ema_monotonik_sabit_seride():
    s = pd.Series([5.0] * 100)
    assert np.allclose(ind.ema(s, 10), 5.0)


def test_atr_pozitif():
    df = _sahte_veri()
    a = ind.atr(df, 14).dropna()
    assert (a >= 0).all()


def test_pozisyon_siniri():
    df = _sahte_veri()
    sinyal = st.uret(df)
    poz = sinyal["pozisyon"]
    assert poz.min() >= 0.0
    assert poz.max() <= st.SessionTrendParams().max_kaldirac + 1e-9


def test_backtest_look_ahead_yok():
    """Son barın pozisyonunu değiştirmek geçmiş equity'yi ETKİLEMEMELİ."""
    df = _sahte_veri()
    sinyal = st.uret(df)
    r1 = bt.calistir(sinyal)

    bozuk = sinyal.copy()
    bozuk.iloc[-1, bozuk.columns.get_loc("pozisyon")] = 99.0  # geleceği boz
    r2 = bt.calistir(bozuk)

    # Son bar hariç equity aynı kalmalı (gecikme sayesinde)
    assert np.allclose(r1.equity.iloc[:-1], r2.equity.iloc[:-1])


def test_buy_hold_tutarli():
    df = _sahte_veri()
    bh = bt.buy_hold(df)
    beklenen = (1 + df["close"].pct_change().fillna(0)).cumprod().iloc[-1]
    assert bh.equity.iloc[-1] == pytest.approx(beklenen)


def test_edge_maskesi_sarmali_aralik():
    """Edge penceresi haftanın sonuna saran aralığı doğru işaretlemeli."""
    df = _sahte_veri(n=400)
    sinyal = st.uret(df)
    assert sinyal["edge"].isin([0, 1]).all()
    # En az bir edge ve bir non-edge bar olmalı (400 saat > 1 hafta)
    assert sinyal["edge"].nunique() == 2
