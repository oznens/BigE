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
                    3250, 3570, 0.8, taraf="Long", stop=2930,
                    kaynak="Filtered", lifecycle="Watch"),
        RadarSatiri("TAOUSDT", "1h", 270, "Elenen", "D", 20, "riskli",
                    220, 200, 1.0, taraf="Short", stop=280,
                    pattern="Deep Crab", kaynak="Late", lifecycle="Cancelled"),
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
    # aday akışı: Trade + Watch (Elenen aday listesine girmez)
    assert len(d["adaylar"]) == 2
    assert d["adaylar"][0]["symbol"] == "BTCUSDT"     # Trade önce
    assert d["adaylar"][0]["kaynak"] == "Harmonik"
    assert d["adaylar"][0]["skor_modeli"] == "BigE heuristic v1"
    assert d["adaylar"][0]["kalite_kademe"] is None
    assert d["adaylar"][0]["test_asamasi"] == 5
    assert d["adaylar"][0]["asama_basi_kontrol"] == 4
    assert d["adaylar"][0]["kalite_filtre_detayi"] == 4
    assert d["adaylar"][0]["filtre_esleme"] == "undisclosed-by-archive"
    assert "ana_tf_yapi" in d["adaylar"][0]
    assert d["adaylar"][0]["ltf_yapi"] == "not-implemented"
    # bildirimler: kapanan 2 kayıt
    assert len(d["bildirimler"]) == 2
    # execution: kiraz EXECUTION (Trade var)
    assert d["execution"]["kiraz_durum"] == "EXECUTION MODE"
    assert d["execution"]["wallet"] >= 5000   # 5000 + R kazancı
    assert d["execution"]["stop_tetik"] == "candle-close"
    # buckets gerçek motor isimleri
    assert "Price Action" in d["buckets"] and "Harmonik" in d["buckets"]
    assert "parite_karakter" in d["memory"]
    # Anlık radar lifecycle kalıcı Result Journal toplamına karışmaz.
    assert d["lifecycle"]["Cancelled"] == 0
    assert d["lifecycle_ozet"]["Cancelled"] == 0
    assert d["radar_lifecycle"]["Cancelled"] == 1
    assert d["result_journal_policy"]["radar_snapshot_included"] is False
    assert d["result_journal_policy"]["late_detection"] == "undisclosed-by-archive"
    assert d["result_journal_policy"]["late_auto_classification"] is False
    assert d["htf_policy"]["archive_status"] == \
        "implemented-in-testing-announced"
    assert d["htf_policy"]["archive_confirmation_scope"] == "upper-and-lower-timeframes"
    assert d["htf_policy"]["exact_tf_mapping"] == "undisclosed-by-archive"
    assert d["htf_policy"]["ltf_implementation"] == "observation-only"
    assert d["htf_policy"]["current_implementation"] == \
        "upper-veto-plus-lower-observation"
    assert d["dynamic_quality_policy"]["history"] == "persisted-on-change"
    assert d["dynamic_quality_policy"]["check_count"] == "undisclosed-by-archive"
    assert d["shelved_policy"]["criteria"] == "undisclosed-by-archive"
    assert d["shelved_policy"]["automatic"] is False
    assert d["shelved_policy"]["reason_required_for_audit"] is True
    lp = d["terminal_lifecycle_policy"]
    assert lp["No-Entry"]["meaning"] == "entry-zone-not-reached"
    assert lp["No-Entry"]["automatic"] is False
    assert lp["Expired"]["exact_archive_rule"] == "undisclosed-by-archive"
    assert lp["stale_target_seen"]["not_no_entry"] is True
    assert d["filtered_reason_policy"]["reason_taxonomy_origin"] == \
        "BigE-audit-derived-from-radar-notes"
    assert d["filtered_reason_policy"]["miraz_exact_reason_mapping"] == \
        "undisclosed-by-archive"
    assert "filtered_nedenleri" in d
    assert d["filtered_etki"]["engellenen_stop"] is None
    assert d["filtered_etki"]["claim_allowed"] is False
    assert set(d["filtered_etki"]["kirilimlar"]) == {
        "motor", "timeframe", "kalite", "neden"}
    assert "filtered_takip" in d
    assert "filtered_kalite_gecisleri" in d
    assert "htf_denetim" in d
    assert "ltf_gozlem" in d
    assert d["ltf_gozlem"]["causality_claim"] == "not-made"
    assert d["mtf_kalibrasyon"]["policy"]["state"] == "locked"
    assert d["mtf_kalibrasyon"]["policy"]["minimum_verified_samples"] is None
    assert d["mtf_kalibrasyon"]["policy"]["trade_effect"] == "none"
    assert "pa_alt_turleri" in d
    assert d["pa_alt_turleri"]["ob_label"] == "OB Proxy"
    assert "pa_capraz" in d
    assert d["pa_capraz"]["automatic_recommendation"] is False
    assert d["htf_denetim"]["miraz_exact_mapping"] == "undisclosed-by-archive"
    assert d["filtered_kalite_gecisleri"]["causality_claim"] == "not-made"
    assert d["filtered_reason_policy"]["untracked_stop_claim"] == "forbidden"
    assert d["result_journal_policy"]["evidence_tweet_ids"] == [
        "2065351367544181110", "2059325292926148742"]
    assert d["adaylar"][1]["lifecycle"] == "Watch"
    # JSON serileştirilebilir olmalı
    json.dumps(d)


def test_seviye_bul():
    durum = {"adaylar": [{"symbol": "BTCUSDT", "interval": "1h", "giris": 100,
                          "stop": 95, "hedef": 110, "taraf": "Long",
                          "pattern": "Gartley", "kaynak": "Harmonik", "rr": 1.0}],
             "bildirimler": []}
    s = sv._seviye_bul(durum, "BTCUSDT", "1h")
    assert s["giris"] == 100 and s["stop"] == 95 and s["pattern"] == "Gartley"
    assert sv._seviye_bul(durum, "XXX", "1h") is None


def test_grafik_veri(monkeypatch):
    """grafik_veri(): mum + MACD + seviye (ZONE dâhil) üretir, JSON'lanabilir."""
    import numpy as np
    import pandas as pd
    n = 80
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    fiyat = np.linspace(100, 110, n)
    df = pd.DataFrame({"open": fiyat, "high": fiyat + 1, "low": fiyat - 1,
                       "close": fiyat, "volume": 1.0}, index=idx)
    monkeypatch.setattr(sv.veri, "indir", lambda *a, **k: df)

    durum = {"adaylar": [{"symbol": "BTCUSDT", "interval": "1h", "giris": 108,
                          "stop": 104, "hedef": 112, "taraf": "Long",
                          "pattern": "Gartley", "kaynak": "Harmonik"}]}
    g = sv.grafik_veri("BTCUSDT", "1h", durum=durum, bar=60)
    assert len(g["mumlar"]) == 60
    assert len(g["mumlar"][0]) == 5           # [ts,o,h,l,c]
    assert g["seviye"]["giris"] == 108 and g["seviye"]["stop"] == 104
    assert "macd" in g and len(g["macd"]["macd"]) == 60
    assert "harmonik" in g                     # harmonik anahtarı her zaman var
    json.dumps(g)                              # serileştirilebilir


def _zigzag(pivots, seg=10):
    """Verilen fiyat dönüş noktalarından lineer zigzag bir DataFrame üretir.

    Her ardışık pivot arası `seg` bar lineer enterpolasyon — iç pivotlar n=5
    swing tespitiyle yakalanır. İlk/son eleman yalnızca bağlam (kenar pivotu).
    """
    import numpy as np
    import pandas as pd
    vals = [pivots[0]]
    pos = [0]
    for k in range(1, len(pivots)):
        onceki, simdi = pivots[k - 1], pivots[k]
        for j in range(1, seg + 1):
            vals.append(onceki + (simdi - onceki) * j / seg)
        pos.append(len(vals) - 1)
    arr = np.array(vals)
    idx = pd.date_range("2026-01-01", periods=len(arr), freq="h", tz="UTC")
    df = pd.DataFrame({"open": arr, "high": arr, "low": arr, "close": arr,
                       "volume": 1.0}, index=idx)
    return df, pos


def test_harmonik_ciz_tamamlanan_xabcd():
    """_harmonik_ciz(): net bir bullish Gartley → 5 noktalı XABCD çizim verisi."""
    # X=100, A=200, B=138.2, C=169.1, D=121.4 (ideal Gartley oranları)
    df, pos = _zigzag([150, 100, 200, 138.2, 169.1, 121.4, 160], seg=10)
    h = sv._harmonik_ciz(df, {})
    assert "tamamlanan" in h
    t = h["tamamlanan"]
    assert t["yon"] == "Bullish"
    assert len(t["noktalar"]) == 5
    # noktalar mumlar konum indeksiyle (X..D = pos[1..5])
    idxler = [p[0] for p in t["noktalar"]]
    assert idxler == [pos[1], pos[2], pos[3], pos[4], pos[5]]
    # AB/XA oranı ~0.618
    assert 0.55 <= t["oranlar"]["AB_XA"] <= 0.69
    # entry ≈ D, JSON'lanabilir
    assert abs(t["entry"] - 121.4) < 5
    json.dumps(h)


def test_harmonik_ciz_setupa_baglanir():
    """Çizilen XABCD setup'a bağlanır: yön eşleşmeli, D girişe en yakın olmalı."""
    df, pos = _zigzag([150, 100, 200, 138.2, 169.1, 121.4, 160], seg=10)
    # Bullish Gartley D≈121.4 — Long setup, giriş 121 → çizilir, yön Bullish
    h = sv._harmonik_ciz(df, {"taraf": "Long", "giris": 121.0, "pattern": None})
    assert "tamamlanan" in h and h["tamamlanan"]["yon"] == "Bullish"
    assert h["tamamlanan"]["noktalar"][4][0] == pos[5]      # D barı
    # Short setup istenir ama bu pencerede bearish tamamlanan yok → çizilmez
    h2 = sv._harmonik_ciz(df, {"taraf": "Short", "giris": 121.0})
    assert "tamamlanan" not in h2


def test_harmonik_ciz_pivot_yoksa_bos():
    """Düz/pivotsuz seri → harmonik boş sözlük (çökme yok)."""
    import numpy as np
    import pandas as pd
    n = 40
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    duz = np.linspace(100, 101, n)
    df = pd.DataFrame({"open": duz, "high": duz, "low": duz, "close": duz,
                       "volume": 1.0}, index=idx)
    assert sv._harmonik_ciz(df, {}) == {}


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
        assert "api/grafik" in html and "CANLI GRAFİK" in html
        assert "FILTER IMPACT" in html
        assert "pi-filter-reasons" in html
        assert "pi-filter-tracks" in html
        assert "pi-filter-motor" in html and "pi-filter-timeframe" in html
        assert "pi-filter-quality-transitions" in html
        assert "HTF AUDIT" in html and "pi-htf-records" in html
        assert "pi-ltf-outcomes" in html
        assert "MTF CALIBRATION GATE" in html and "pi-mtf-gate" in html
        assert "PRICE ACTION SUBTYPE AUDIT" in html
        assert "pi-pa-subtypes" in html
        assert "PA CROSS MATRIX" in html and "pi-pa-cross" in html
        assert "KARŞI-OLGUSAL TAKİP YOK" in html
        # /api/grafik symbol'süz → 400
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{s.port}/api/grafik", timeout=3)
            assert False, "400 beklenecekti"
        except urllib.error.HTTPError as he:
            assert he.code == 400
    finally:
        httpd.shutdown()
        httpd.server_close()
