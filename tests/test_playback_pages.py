"""GitHub Pages Trade Playback regression tests."""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backtest.statik_site import _grafik_hedefleri, _playback_trade_memory, _PLAYBACK_PATCH


@dataclass
class _K:
    id: int
    sembol: str
    interval: str
    durum: str
    taraf: str = "Long"
    kaynak: str = "Price Action"
    pattern: str | None = None
    r_sonuc: float = 0.0
    guven: float = 75.0
    kalite: str = "A"
    giris: float = 100.0
    stop: float = 95.0
    hedef: float = 110.0
    rr: float = 2.0
    acilis_zaman: str = "2026-01-01T00:00:00+00:00"
    kapanis_zaman: str = "2026-01-01T08:00:00+00:00"


class _D:
    def __init__(self, kayitlar):
        self.kayitlar = kayitlar


def test_playback_yalniz_tp_stop():
    d = _D([
        _K(1, "BTCUSDT", "1h", "TP", r_sonuc=2.0),
        _K(2, "ETHUSDT", "1h", "STOP", r_sonuc=-1.0),
        _K(3, "SOLUSDT", "1h", "Expired"),
        _K(4, "XRPUSDT", "1h", "No-Entry"),
    ])
    out = _playback_trade_memory(d)
    assert [x["durum"] for x in out] == ["TP", "STOP"]
    assert all("stop" in x and "hedef" in x and "acilis" in x for x in out)


def test_playback_trade_grafik_hedeflerine_girer():
    durum = {
        "adaylar": [], "bildirimler": [],
        "trade_memory": [
            {"sembol": "BTCUSDT", "interval": "1h", "durum": "TP"},
            {"sembol": "ETHUSDT", "interval": "4h", "durum": "STOP"},
        ],
        "varsayilan_grafik": {"symbol": "SOLUSDT", "interval": "1h"},
    }
    hedef = set(_grafik_hedefleri(durum))
    assert ("BTCUSDT", "1h") in hedef
    assert ("ETHUSDT", "4h") in hedef
    assert ("SOLUSDT", "1h") in hedef


def test_frontend_patch_setup_zamanina_hizalar():
    assert 't.durum==="TP" || t.durum==="STOP"' in _PLAYBACK_PATCH
    assert "setup_bar:setup>=0?setup" in _PLAYBACK_PATCH
    assert "giris:t.giris, stop:t.stop, hedef:t.hedef" in _PLAYBACK_PATCH
    assert "_playbackSon" in _PLAYBACK_PATCH
