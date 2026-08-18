"""Canlı edge motorunun Result Journal kanıt zinciri testleri."""

import importlib

import pandas as pd
import pytest

from miraz import gozlemci
from miraz.portfoy import Portfoy


@pytest.fixture(autouse=True)
def _restore_live_monkeypatches():
    """Canlı script importunun diğer birim testlerine sızmasını önler."""
    original_update = Portfoy.guncelle
    original_radar = gozlemci.radar_tara
    yield
    Portfoy.guncelle = original_update
    gozlemci.radar_tara = original_radar


def _edge_module():
    return importlib.import_module("backtest.live_edge_filter")


def _position(direction="Long"):
    portfolio = Portfoy()
    if direction == "Long":
        entry, stop, target = 100.0, 95.0, 105.0
    else:
        entry, stop, target = 100.0, 105.0, 95.0
    position = portfolio.ekle(
        "BTCUSDT", "15m", entry, stop, target, 1.0, "A", 80.0,
        direction, zaman="2024-12-31T23:45:00+00:00",
    )
    return portfolio, position


def _bars(rows):
    index = pd.date_range("2025-01-01", periods=len(rows), freq="15min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=index)


def test_live_edge_tp_persists_entry_and_result_evidence():
    portfolio, position = _position()
    bars = _bars([
        (101, 102, 99, 101, 10),
        (101, 106, 100, 104, 30),
    ])

    _edge_module()._miraz_guncelle(portfolio, "BTCUSDT", "15m", bars)

    assert position.durum == "TP"
    assert position.entry_zaman == "2025-01-01T00:00:00+00:00"
    assert position.entry_bekleme_bar == 1
    assert position.entry_bekleme_limiti == 24
    assert position.entry_hacim == 10
    assert position.entry_hacim_pencere == 0
    assert position.sonuc_mum_zaman == "2025-01-01T00:15:00+00:00"
    assert position.sonuc_tetik == "target-touch"
    assert position.sonuc_mum_ohlc == {
        "open": 101.0, "high": 106.0, "low": 100.0, "close": 104.0,
    }
    assert position.denetim_durumu == "verified-entry-to-result"


def test_live_edge_stop_requires_close_beyond_invalidation_and_persists_evidence():
    portfolio, position = _position()
    bars = _bars([
        (101, 102, 99, 101, 10),
        (98, 99, 94, 95, 20),  # seviyede kapanış: invalidasyon değil
        (96, 97, 93, 94, 30),  # seviyenin ötesinde kapanış: STOP
    ])

    _edge_module()._miraz_guncelle(portfolio, "BTCUSDT", "15m", bars)

    assert position.durum == "STOP"
    assert position.kapanis_zaman == "2025-01-01T00:30:00+00:00"
    assert position.sonuc_mum_zaman == "2025-01-01T00:30:00+00:00"
    assert position.sonuc_tetik == "candle-close"
    assert position.sonuc_mum_ohlc["close"] == 94.0
    assert position.denetim_durumu == "verified-entry-to-result"


def test_live_edge_short_stop_also_requires_close_beyond_invalidation():
    portfolio, position = _position("Short")
    bars = _bars([
        (99, 101, 98, 99, 10),
        (103, 106, 102, 105, 20),  # seviyede kapanış: invalidasyon değil
        (104, 107, 103, 106, 30),  # seviyenin ötesinde kapanış: STOP
    ])

    _edge_module()._miraz_guncelle(portfolio, "BTCUSDT", "15m", bars)

    assert position.durum == "STOP"
    assert position.sonuc_mum_zaman == "2025-01-01T00:30:00+00:00"
    assert position.sonuc_tetik == "candle-close"
