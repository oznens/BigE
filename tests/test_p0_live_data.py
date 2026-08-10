"""P0 canlı veri doğruluğu regression testleri."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.portfoy import Portfoy
from miraz.veri import _cache_guncel, _kapanmis_mumlar


def _ohlcv(index, lows=None, highs=None):
    n = len(index)
    lows = lows or [99.0] * n
    highs = highs or [101.0] * n
    close = [(lo + hi) / 2 for lo, hi in zip(lows, highs)]
    return pd.DataFrame(
        {
            "open": close,
            "high": highs,
            "low": lows,
            "close": close,
            "volume": [1.0] * n,
        },
        index=index,
    )


def test_kapanmamis_son_mum_analize_girmez():
    idx = pd.date_range("2026-08-09T00:00:00Z", periods=3, freq="1h")
    df = _ohlcv(idx)
    # 02:30'da 00:00 ve 01:00 mumları kapanmıştır; 02:00 hâlâ açıktır.
    now_ms = int(pd.Timestamp("2026-08-09T02:30:00Z").timestamp() * 1000)
    sonuc = _kapanmis_mumlar(df, "1h", now_ms=now_ms)
    assert list(sonuc.index) == list(idx[:2])


def test_cache_yeni_kapanmis_bar_eksikse_bayat():
    idx = pd.date_range("2026-08-09T00:00:00Z", periods=2, freq="1h")
    df = _ohlcv(idx)  # son cache barı 01:00

    # 02:30'da 01:00 son kapanmış bardır → cache güncel.
    now_0230 = int(pd.Timestamp("2026-08-09T02:30:00Z").timestamp() * 1000)
    assert _cache_guncel(df, "1h", now_ms=now_0230) is True

    # 03:01'de 02:00 barı da kapanmıştır fakat cache'de yok → bayat.
    now_0301 = int(pd.Timestamp("2026-08-09T03:01:00Z").timestamp() * 1000)
    assert _cache_guncel(df, "1h", now_ms=now_0301) is False


def test_tp_kapanis_zamani_gercek_ohlcv_bari():
    pf = Portfoy()
    pf.ekle(
        "BTCUSDT", "4h", giris=100.0, stop=95.0, hedef=110.0,
        rr=2.0, kalite="A", guven=80.0,
        zaman="2025-01-01T00:00:00+00:00",
    )
    idx = pd.date_range("2025-01-01T04:00:00Z", periods=3, freq="4h")
    # 04:00 giriş dolar, 08:00 hedef vurur.
    df = _ohlcv(idx, lows=[99, 101, 101], highs=[103, 111, 103])
    pf.guncelle("BTCUSDT", "4h", df)

    p = pf.pozisyonlar[0]
    assert p.durum == "TP"
    assert pd.Timestamp(p.kapanis_zaman) == idx[1]


def test_stop_kapanis_zamani_gercek_ohlcv_bari():
    pf = Portfoy()
    pf.ekle(
        "BTCUSDT", "4h", giris=100.0, stop=95.0, hedef=110.0,
        rr=2.0, kalite="A", guven=80.0,
        zaman="2025-01-01T00:00:00+00:00",
    )
    idx = pd.date_range("2025-01-01T04:00:00Z", periods=3, freq="4h")
    # 04:00 giriş dolar, 08:00 stop vurur.
    df = _ohlcv(idx, lows=[99, 94, 101], highs=[103, 99, 103])
    pf.guncelle("BTCUSDT", "4h", df)

    p = pf.pozisyonlar[0]
    assert p.durum == "STOP"
    assert pd.Timestamp(p.kapanis_zaman) == idx[1]
