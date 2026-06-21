"""Web sunucu testleri — JSON anlık görüntü + HTTP handler + uçtan uca tarama."""

import sys
import json
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import sunucu as sv
from miraz import gozlemci as gz
from miraz.gozlemci import Gozlemci, Defter, Kayit
from miraz.radar import RadarSatiri, RadarRapor


def _rapor():
    r = RadarRapor()
    r.satirlar = [
        RadarSatiri("BTCUSDT", "1h", 50000, "Trade", "A", 85, "destek",
                    50200, 52200, 1.0, taraf="Long", stop=48200,
                    pattern="Gartley", kaynak="Harmonik"),
        RadarSatiri("ETHUSDT", "1h", 3200, "Watch", "C", 55, "bölge",
                    3250, 3570, 0.8, taraf="Long", stop=2930, kaynak="Filtered"),
    ]
    return r


def _gozlemci_dolu():
    d = Defter()
    d.tarama_turu = 3
    d.kayitlar = [
        Kayit(1, "", "BTCUSDT", "1h", "Long", "A", 80, 50200, 48200, 52200, 1.0,
              durum="TP", r_sonuc=1.0, kaynak="Harmonik",
              kapanis_zaman="2026-06-21T12:00"),
        Kayit(2, "", "ADAUSDT", "1h", "Long", "B", 70, 0.5, 0.48, 0.54, 1.0,
              durum="STOP", r_sonuc=-1.0, kaynak="Price Action",
              kapanis_zaman="2026-06-21T13:00"),
    ]
    return Gozlemci(semboller=["BTCUSDT"], intervallar=["1h"], taraf="her",
                    defter=d)


def test_kiraz_status_modlari():
    r = _rapor()
    durum, _ = sv._kiraz_status(r)        # 1 Trade → EXECUTION
    assert durum == "EXECUTION MODE"
    r2 = RadarRapor()
    r2.satirlar = [RadarSatiri("X", "1h", 1, "Watch", "C", 50, "y",
                               1, 1.1, 1, taraf="Long", stop=0.9)]
    assert sv._kiraz_status(r2)[0] == "WATCHLIST MODE"


def test_durum_json_yapisi():
    g = _gozlemci_dolu()
    d = sv.durum_json(g, _rapor(), aralik=180)
    # üst düzey anahtarlar
    for k in ("zaman", "tarama_no", "ozet", "execution", "buckets",
              "lifecycle", "adaylar", "bildirimler", "pnl", "memory"):
        assert k in d, k
    # aday akışı: Trade + Watch
    assert len(d["adaylar"]) == 2
    assert d["adaylar"][0]["symbol"] == "BTCUSDT"     # Trade önce
    assert d["adaylar"][0]["kaynak"] == "Harmonik"
    # bildirimler: kapanan 2 kayıt
    assert len(d["bildirimler"]) == 2
    # execution: kiraz EXECUTION (Trade var)
    assert d["execution"]["kiraz_durum"] == "EXECUTION MODE"
    assert d["execution"]["wallet"] >= 5000   # 5000 + R kazancı
    # buckets gerçek motor isimleri
    assert "Price Action" in d["buckets"] and "Harmonik" in d["buckets"]
    # JSON serileştirilebilir olmalı
    json.dumps(d)


def test_durum_deposu_kilitli():
    depo = sv.DurumDeposu()
    assert depo.oku()["hazir"] is False
    depo.yaz({"x": 1})
    assert depo.oku()["hazir"] is True and depo.oku()["x"] == 1


def test_handler_serve_uctan_uca(monkeypatch):
    """Sunucuyu gerçek bir portta çalıştır, /api/durum ve / yanıtlarını doğrula."""
    # radar'ı taklit et (ağ yok)
    monkeypatch.setattr(gz, "radar_tara", lambda *a, **k: _rapor())
    monkeypatch.setattr(gz.veri, "indir",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("yok")))

    s = sv.Sunucu(semboller=["BTCUSDT"], intervallar=["1h"], taraf="her",
                  aralik=999, port=8731, host="127.0.0.1")
    # bir tarama yap → depoyu doldur
    s._bir_tarama()

    from http.server import ThreadingHTTPServer
    httpd = ThreadingHTTPServer((s.host, s.port), sv._handler_sinifi(s.depo))
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    try:
        durum = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{s.port}/api/durum", timeout=3).read())
        assert durum["hazir"] is True
        assert durum["tarama_no"] == 1
        assert len(durum["adaylar"]) == 2
        html = urllib.request.urlopen(
            f"http://127.0.0.1:{s.port}/", timeout=3).read().decode("utf-8")
        assert "TERMINAL" in html and "api/durum" in html
    finally:
        httpd.shutdown()
        httpd.server_close()
