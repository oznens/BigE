"""Statik site üreteci — hafıza (defter/portföy) kalıcılığı testleri.

GitHub Actions konteynerı her run'da temiz başladığı için, statik_site önceki
snapshot'ın yayınladığı defter.json/portfoy.json'u indirip yükler. Bu round-trip
çalışmazsa her tarama sıfırdan başlar ve setuplar/lifecycle kaybolur.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import backtest.statik_site as s
from miraz.gozlemci import Defter, Kayit
from miraz.portfoy import Portfoy


def test_playback_kalite_zaman_cizelgesi_webde_var():
    html = (s.WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    assert "KALİTE ZAMAN ÇİZELGESİ" in html
    assert "function pbKaliteCiz" in html
    assert "GÜÇLENDİ" in html and "ZAYIFLADI" in html
    assert "z<=simdi" in html


def test_aktif_tradeler_scanner_ekraninda_da_gorunur():
    html = (s.WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    assert 'id="sc-active"' in html
    assert 'id="sc-active-n"' in html
    assert "aktifTradeKartlari(ats)" in html
    assert "TRADE AKTİF" in html


def test_aktif_trade_karti_grafigi_acar():
    html = (s.WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    assert 'data-active-trade="1"' in html
    assert '.tm-kart.tik' in html
    assert 'grafikYukle(k.dataset.sym,k.dataset.ivl)' in html
    assert 'scrollIntoView({behavior:"smooth",block:"center"})' in html
    assert "longSetup?kapanis<sv.stop:kapanis>sv.stop" in html
    assert "KAYITLI PRZ" in html


def test_grafik_hedefleri_aktif_tradeleri_de_kapsar():
    durum = {
        "adaylar": [],
        "bildirimler": [],
        "trade_memory": [],
        "aktif_tradeler": [
            {"sembol": "FETUSDT", "interval": "15m"},
            {"sembol": "SOLUSDT", "interval": "30m"},
        ],
        "varsayilan_grafik": None,
    }
    assert s._grafik_hedefleri(durum) == [
        ("FETUSDT", "15m"), ("SOLUSDT", "30m")]


def test_playback_kanitli_sureci_tasir():
    d = Defter()
    d.kayitlar = [Kayit(
        1, "2026-06-01T10:00:00+00:00", "BTCUSDT", "1h", "Long",
        "A", 90, 100, 95, 105, 1.0, durum="TP",
        kapanis_zaman="2026-06-01T15:00:00+00:00", r_sonuc=1.0,
    )]
    trade = s._playback_trade_memory(d)[0]
    assert [x["asama"] for x in trade["surec"]] == ["SETUP OLUŞUMU", "SONUÇ"]
    assert trade["surec"][-1]["durum"] == "TP"
    assert trade["playback_kanit"]["tweet_id"] == "2056806486127346084"
    assert trade["playback_kanit"]["kararsizlik_etiketi"] == "kayit-yoksa-uretilmez"


def test_playback_sonuc_mumu_denetim_kanitini_tasir():
    d = Defter(kayitlar=[Kayit(
        1, "2026-06-01T10:00:00+00:00", "BTCUSDT", "1h", "Long",
        "A", 90, 100, 95, 105, 1.0, durum="TP", r_sonuc=1.0,
        entry_zaman="2026-06-01T11:00:00+00:00",
        kapanis_zaman="2026-06-01T12:00:00+00:00",
        sonuc_mum_zaman="2026-06-01T12:00:00+00:00",
        sonuc_tetik="target-touch",
        sonuc_mum_ohlc={"open": 104, "high": 105, "low": 103, "close": 104},
        denetim_durumu="verified-entry-to-result")])
    trade = s._playback_trade_memory(d)[0]
    assert trade["sonuc_mum_zaman"] == "2026-06-01T12:00:00+00:00"
    assert trade["sonuc_tetik"] == "target-touch"
    assert trade["denetim_durumu"] == "verified-entry-to-result"


def test_grafik_renderer_pa_ve_kayitli_olay_katmanlarini_icerir():
    html = (s.WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    assert "GÜÇ ${Math.round(k.guc||0)}" in html
    assert "ENTRY MUMU" in html
    assert "ev.sonuc_tetik" in html
    assert "T.oranlar.XD_XA" in html


def test_harmonik_playback_yalniz_kayitli_olaylari_tasir():
    d = Defter(kayitlar=[Kayit(
        1, "2026-06-01T10:00:00+00:00", "BTCUSDT", "1h", "Long",
        "A", 90, 100, 95, 105, 1.0, pattern="Gartley",
        durum="Cancelled", kapanis_zaman="2026-06-01T12:00:00+00:00",
        durum_nedeni="harmonic-pattern-changed-or-disappeared",
        harmonik_gecmisi=[
            {"zaman": "2026-06-01T10:00:00+00:00",
             "olay": "pattern-detected", "pattern": "Gartley",
             "prz": {"merkez": 100}},
            {"zaman": "2026-06-01T12:00:00+00:00",
             "olay": "pattern-changed-or-disappeared",
             "onceki_pattern": "Gartley", "yeni_pattern": None},
        ])])
    trade = s._playback_trade_memory(d)[0]
    assert trade["durum"] == "Cancelled"
    assert len(trade["harmonik_gecmisi"]) == 2
    assert trade["entry_zaman"] is None
    assert trade["entry_zaman_durumu"] == "legacy-not-recorded"
    assert trade["playback_kanit"]["harmonik_olay_politikasi"] == \
        "recorded-events-only-no-backfill"


def test_harmonik_playback_kayitli_entry_barini_tasir():
    d = Defter(kayitlar=[Kayit(
        1, "2026-06-01T10:00:00+00:00", "BTCUSDT", "1h", "Long",
        "A", 90, 100, 95, 105, 1.0, pattern="Gartley", durum="TP",
        entry_zaman="2026-06-01T11:00:00+00:00",
        kapanis_zaman="2026-06-01T12:00:00+00:00")])
    trade = s._playback_trade_memory(d)[0]
    assert trade["entry_zaman"] == "2026-06-01T11:00:00+00:00"
    assert trade["entry_zaman_durumu"] == "recorded-entry-touch-bar"


def test_harmonik_playback_web_renderer_var():
    html = (s.WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    assert "HARMONİK / PRZ OLAYLARI" in html
    assert "function pbHarmonikCiz" in html
    assert "LEGACY · KAYITLI DEĞİL" in html


def _ornek_kayit(id_=1, durum="Açık"):
    return {"id": id_, "acilis_zaman": "2026-06-22T00:00:00+00:00",
            "sembol": "BTCUSDT", "interval": "1h", "taraf": "Long",
            "kalite": "A", "guven": 80.0, "giris": 100.0, "stop": 95.0,
            "hedef": 110.0, "rr": 2.0, "durum": durum}


def test_onceki_state_yayinlanani_yukler(tmp_path):
    """Yayınlanmış defter.json/portfoy.json → bir sonraki run yükler (file://)."""
    # Önceki snapshot'ı taklit et: cikti dizinine state dosyaları yaz
    defter = Defter()
    (tmp_path / "defter.json").write_text(json.dumps(
        {"id_sayac": 5, "tarama_turu": 7, "toplam_tarama": 40,
         "son_dongu": "2026-06-22T00:00:00+00:00",
         "kayitlar": [_ornek_kayit(1, "Açık"), _ornek_kayit(2, "Aday")]},
        ensure_ascii=False), encoding="utf-8")
    Portfoy(r_dolar=25.0).kaydet(tmp_path / "portfoy.json")
    (tmp_path / "state_epoch.json").write_text(
        json.dumps({"epoch": s.STATE_EPOCH}), encoding="utf-8")

    taban = tmp_path.resolve().as_uri()          # file:///.../tmp
    d, p = s._onceki_state(tmp_path, taban)
    assert len(d.kayitlar) == 2                    # iki kayıt taşındı
    assert d.tarama_turu == 7                      # sayaç korundu
    assert d.kayitlar[0].sembol == "BTCUSDT"
    assert isinstance(p, Portfoy)


def test_onceki_state_epoch_degistiğinde_temiz_baslar(tmp_path):
    """Eski canlı dönem Journal/portföyü yeni temiz başlangıca taşınmaz."""
    (tmp_path / "defter.json").write_text(json.dumps(
        {"id_sayac": 105, "tarama_turu": 73, "toplam_tarama": 40480,
         "son_dongu": "2026-08-11T10:00:00+00:00",
         "kayitlar": [_ornek_kayit(105, "TP")]}, ensure_ascii=False),
        encoding="utf-8")
    p = Portfoy(r_dolar=25.0)
    p.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    p.kaydet(tmp_path / "portfoy.json")
    (tmp_path / "state_epoch.json").write_text(
        json.dumps({"epoch": "old-era"}), encoding="utf-8")

    d2, p2 = s._onceki_state(tmp_path, tmp_path.resolve().as_uri())
    assert d2.kayitlar == [] and d2.tarama_turu == 0
    assert p2.pozisyonlar == []


def test_onceki_state_yoksa_bos_baslar(tmp_path):
    """İlk run / 404 / ağ yok → boş defter+portföy (patlamaz)."""
    d, p = s._onceki_state(tmp_path, None)
    assert len(d.kayitlar) == 0
    assert len(p.pozisyonlar) == 0
    # erişilemez URL de sessizce boş başlatmalı
    d2, p2 = s._onceki_state(tmp_path, "http://127.0.0.1:0/yok")
    assert len(d2.kayitlar) == 0 and len(p2.pozisyonlar) == 0


def test_onceki_state_bozuk_portfoy_bos_doner(tmp_path):
    """Bozuk portfoy.json yüklemeyi patlatmaz, boş Portföy döner."""
    (tmp_path / "portfoy.json").write_text("{bozuk json", encoding="utf-8")
    _, p = s._onceki_state(tmp_path, None)
    assert isinstance(p, Portfoy) and len(p.pozisyonlar) == 0
