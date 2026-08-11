"""Zamansal sağlama — sagla_kayit() birim testleri.

OHLCV verisi mock'lanır; gerçek ağ çağrısı yapılmaz.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backtest.sagla import sagla_kayit, SaglaSonuc


# ---------------------------------------------------------------------------
# OHLCV mock yardımcısı
# ---------------------------------------------------------------------------

def _df(rows: list[tuple]) -> pd.DataFrame:
    """(low, high) veya (low, high, close) OHLCV verisi üretir."""
    idx = pd.date_range("2026-01-01 00:00", periods=len(rows), freq="1h", tz="UTC")
    lows = [r[0] for r in rows]
    highs = [r[1] for r in rows]
    closes = [r[2] if len(r) > 2 else (r[0] + r[1]) / 2 for r in rows]
    return pd.DataFrame({
        "open":  closes,
        "high":  list(highs),
        "low":   list(lows),
        "close": closes,
        "volume": [1.0] * len(rows),
    }, index=idx)


def _kayit(taraf="Long", giris=100.0, stop=95.0, hedef=110.0, rr=2.0,
           durum="TP", acilis="2026-01-01T00:00:00+00:00"):
    return {
        "id": 1, "sembol": "BTCUSDT", "interval": "1h", "taraf": taraf,
        "giris": giris, "stop": stop, "hedef": hedef, "rr": rr,
        "durum": durum, "acilis_zaman": acilis,
    }


# ---------------------------------------------------------------------------
# Testler
# ---------------------------------------------------------------------------

def test_long_tp_dogru():
    """Long: giriş dolar (bar 0: low≤giris), ardından TP vurur (bar 3: high≥hedef)."""
    mock_df = _df([
        (99, 101),    # bar 0: low=99≤100 → giriş dolar
        (100, 105),   # bar 1: açık, ne stop ne TP
        (100, 108),   # bar 2: açık
        (100, 112),   # bar 3: high=112≥110 → TP ✅
    ])
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Long", giris=100, stop=95, hedef=110,
                               durum="TP"))
    assert s.gercek_durum == "TP"
    assert s.eslesme is True
    assert s.surec_bar == 3
    assert s.bekleme_bar == 0


def test_long_stop_dogru():
    """Long: giriş dolar (bar 0), ardından STOP vurur (bar 2: low≤stop)."""
    mock_df = _df([
        (99, 101),    # bar 0: giriş dolar
        (97, 103),    # bar 1: açık
        (93, 99, 94), # bar 2: close=94<95 → STOP ✅
        (91, 97),     # bar 3: (erişilmemeli)
    ])
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Long", giris=100, stop=95, hedef=110,
                               durum="STOP"))
    assert s.gercek_durum == "STOP"
    assert s.eslesme is True


def test_long_tp_ama_kayit_stop_uyusmaz():
    """OHLCV'ye göre TP, kayıtta STOP yazıyor → uyuşmazlık."""
    mock_df = _df([
        (99, 101),    # giriş dolar
        (100, 112),   # TP vurur
    ])
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Long", giris=100, stop=95, hedef=110,
                               durum="STOP"))
    assert s.gercek_durum == "TP"
    assert s.eslesme is False


def test_short_tp_dogru():
    """Short: giriş dolar (bar 0: high≥giris), hedef aşağıda (bar 2: low≤hedef)."""
    mock_df = _df([
        (99, 101),    # bar 0: high=101≥100 → kısa giriş dolar
        (97, 100),    # bar 1: açık
        (87, 95),     # bar 2: low=87≤90 → TP ✅ (short hedef=90)
    ])
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Short", giris=100, stop=105, hedef=90,
                               durum="TP"))
    assert s.gercek_durum == "TP"
    assert s.eslesme is True


def test_short_stop_dogru():
    """Short: giriş dolar (bar 0), stop yukarıda (bar 1: high≥stop=105)."""
    mock_df = _df([
        (99, 101),    # giriş dolar
        (100, 106, 105.5), # close=105.5>105 → STOP ✅
    ])
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Short", giris=100, stop=105, hedef=90,
                               durum="STOP"))
    assert s.gercek_durum == "STOP"
    assert s.eslesme is True


def test_giris_gelmiyor_expired():
    """24 bar sonra giriş dolmadıysa → GirisYok; kayıt Expired ise eşleşme."""
    bars = [(103, 107)] * 30   # low hep >100, long için giriş dolmaz
    mock_df = _df(bars)
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Long", giris=100, stop=95, hedef=110,
                               durum="Expired"))
    assert s.gercek_durum == "GirisYok"
    assert s.eslesme is True


def test_ayni_bar_stop_fitili_ve_tp_kapanis_icerideyse_tp():
    """Stop fitili ama kapanış içerideyse hedef teması TP."""
    mock_df = _df([
        (99, 101),    # giriş dolar
        (91, 115),    # low≤stop=95 VE high≥hedef=110 → STOP (muhafazakâr)
    ])
    with patch("backtest.sagla._ohlcv", return_value=mock_df):
        s = sagla_kayit(_kayit(taraf="Long", giris=100, stop=95, hedef=110,
                               durum="TP"))
    assert s.gercek_durum == "TP"


def test_veri_yok_acilis_zaman_bos():
    """acilis_zaman boş → VeriYok, patlamamalı."""
    s = sagla_kayit(_kayit(acilis="", durum="TP"))
    assert s.gercek_durum == "VeriYok"
    assert s.eslesme is False
