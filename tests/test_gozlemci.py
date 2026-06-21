"""Canlı Gözlemci / Learning Journal (Defter) testleri."""

import sys
import json
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.gozlemci import Defter, Kayit, Gozlemci
from miraz.portfoy import Portfoy


@dataclass
class _Satir:
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    kategori: str = "Trade"
    kalite: str = "A"
    guven: float = 80.0
    giris: float = 100.0
    hedef: float = 110.0
    rr: float = 1.0
    taraf: str = "Long"
    stop: float = 95.0
    pattern: str = "Gartley"
    kaynak: str = "Scanner"


def test_setup_ekle_ve_dedup():
    d = Defter()
    k1 = d.setup_ekle(_Satir())
    assert k1 is not None and k1.durum == "Aday" and k1.pattern == "Gartley"
    # Aynı sembol+interval+taraf aktifken tekrar eklenmez
    k2 = d.setup_ekle(_Satir())
    assert k2 is None
    assert len(d.kayitlar) == 1


def test_setup_ekle_farkli_taraf():
    d = Defter()
    d.setup_ekle(_Satir(taraf="Long"))
    d.setup_ekle(_Satir(taraf="Short", hedef=90.0, stop=105.0))
    assert len(d.kayitlar) == 2


def test_senkronize_portfoyden():
    d = Defter()
    d.setup_ekle(_Satir())
    pf = Portfoy()
    # Portföyde aynı setup TP olmuş gibi
    p = pf.ekle("BTCUSDT", "1h", giris=100, stop=95, hedef=110, rr=1.0,
                kalite="A", guven=80, yon="Long")
    p.durum = "TP"
    p.r_sonuc = 1.0
    p.kapanis_zaman = "2025-01-01T00:00:00+00:00"
    d.senkronize(pf)
    assert d.kayitlar[0].durum == "TP"
    assert d.kayitlar[0].r_sonuc == 1.0
    assert not d.kayitlar[0].aktif


def test_ozet_sayar():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "A", 80, 100, 95, 110, 1.0, durum="TP",
              r_sonuc=1.0),
        Kayit(2, "", "B", "1h", "Long", "B", 70, 100, 95, 110, 1.0, durum="STOP",
              r_sonuc=-1.0),
        Kayit(3, "", "C", "1h", "Long", "C", 60, 100, 95, 110, 1.0, durum="Açık"),
    ]
    o = d.ozet()
    assert o["toplam"] == 3 and o["aktif"] == 1
    assert o["TP"] == 1 and o["STOP"] == 1
    assert o["wr"] == 50.0
    assert o["toplam_r"] == 0.0     # +1 -1


def test_ozet_bucket_kaynak():
    """ozet() her strateji motorunu (Price Action/Harmonik/Late) ayrı sayar."""
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "A", 80, 100, 95, 110, 1.0, durum="TP",
              r_sonuc=1.0, kaynak="Harmonik"),
        Kayit(2, "", "B", "1h", "Long", "B", 70, 100, 95, 110, 1.0, durum="STOP",
              r_sonuc=-1.0, kaynak="Harmonik"),
        Kayit(3, "", "C", "1h", "Long", "C", 60, 100, 95, 110, 1.0, durum="TP",
              r_sonuc=1.0, kaynak="Price Action"),
        Kayit(4, "", "D", "1h", "Long", "C", 60, 100, 95, 110, 1.0, durum="TP",
              r_sonuc=1.0, kaynak="Late"),
    ]
    b = d.ozet()["buckets"]
    assert b["Harmonik"] == {"tp": 1, "stop": 1, "toplam": 2, "wr": 50.0}
    assert b["Price Action"] == {"tp": 1, "stop": 0, "toplam": 1, "wr": 100.0}
    assert b["Late"] == {"tp": 1, "stop": 0, "toplam": 1, "wr": 100.0}


def test_ozet_lifecycle_sayar():
    """ozet() RESULT JOURNAL lifecycle durumlarını ayrı sayar."""
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "A", 80, 100, 95, 110, 1.0,
              durum="No-Entry"),
        Kayit(2, "", "B", "1h", "Long", "B", 70, 100, 95, 110, 1.0,
              durum="Cancelled"),
        Kayit(3, "", "C", "1h", "Long", "C", 60, 100, 95, 110, 1.0,
              durum="Shelved"),
        Kayit(4, "", "D", "1h", "Long", "C", 60, 100, 95, 110, 1.0,
              durum="Expired"),
    ]
    o = d.ozet()
    assert o["No-Entry"] == 1 and o["Cancelled"] == 1
    assert o["Shelved"] == 1 and o["Expired"] == 1


def test_pnl_analitik():
    """pnl_analitik(): profit factor, açık/kapalı PNL, en iyi/kötü gün, kırılım."""
    d = Defter()
    d.kayitlar = [
        Kayit(1, "2026-06-01T10:00", "BTCUSDT", "1h", "Long", "A", 80,
              100, 95, 110, 1.0, durum="TP", r_sonuc=2.0, kaynak="Harmonik",
              kapanis_zaman="2026-06-01T12:00"),
        Kayit(2, "2026-06-01T10:00", "ETHUSDT", "4h", "Long", "B", 70,
              100, 95, 110, 1.0, durum="STOP", r_sonuc=-1.0,
              kaynak="Price Action", kapanis_zaman="2026-06-01T13:00"),
        Kayit(3, "2026-06-02T10:00", "BTCUSDT", "1h", "Long", "A", 80,
              100, 95, 110, 1.0, durum="TP", r_sonuc=1.0, kaynak="Harmonik",
              kapanis_zaman="2026-06-02T12:00"),
        Kayit(4, "2026-06-02T10:00", "SOLUSDT", "1h", "Long", "C", 60,
              100, 95, 110, 1.0, durum="Açık", r_sonuc=0.5),
    ]
    a = d.pnl_analitik()
    assert a["net_pnl"] == 2.0          # 2 -1 +1
    assert a["acik_pnl"] == 0.5
    assert a["tp"] == 2 and a["stop"] == 1
    assert a["profit_factor"] == 3.0    # kazanç 3 / zarar 1
    # 06-01: +2-1=+1 · 06-02: +1 → her iki gün de +1R
    assert a["en_iyi_gun"] == 1.0 and a["en_kotu_gun"] == 1.0
    assert a["kazanc_gun"] == 2 and a["zarar_gun"] == 0
    # parite kırılımı: BTC 2 işlem, +3R
    assert a["parite"]["BTCUSDT"]["r"] == 3.0
    assert a["parite"]["BTCUSDT"]["wr"] == 100.0
    # TF kırılımı
    assert "1h" in a["tf"] and "4h" in a["tf"]


def test_setup_ekle_kaynak_tasinir():
    """Radar satırındaki kaynak alanı kayda işlenir."""
    d = Defter()
    k = d.setup_ekle(_Satir(kaynak="Harmonik"))
    assert k.kaynak == "Harmonik"


def test_yukle_kaynaksiz_eski_kayit(tmp_path):
    """kaynak alanı olmayan eski defter.json yüklenince varsayılan Price Action."""
    dosya = tmp_path / "defter.json"
    dosya.write_text(json.dumps({
        "id_sayac": 1, "tarama_turu": 1, "toplam_tarama": 1, "son_dongu": "",
        "kayitlar": [{
            "id": 1, "acilis_zaman": "", "sembol": "BTCUSDT", "interval": "1h",
            "taraf": "Long", "kalite": "A", "guven": 80, "giris": 100,
            "stop": 95, "hedef": 110, "rr": 1.0, "pattern": None,
            "durum": "TP", "kapanis_zaman": "", "r_sonuc": 1.0,
        }],
    }), encoding="utf-8")
    d = Defter.yukle(dosya)
    assert d.kayitlar[0].kaynak == "Price Action"
    assert d.ozet()["buckets"]["Price Action"]["tp"] == 1



def test_defter_kalicilik(tmp_path):
    d = Defter()
    d.setup_ekle(_Satir())
    d.tarama_turu = 3
    dosya = tmp_path / "defter.json"
    d.kaydet(dosya)
    d2 = Defter.yukle(dosya)
    assert d2.tarama_turu == 3
    assert len(d2.kayitlar) == 1
    assert d2.kayitlar[0].sembol == "BTCUSDT"
    assert d2.id_sayac == 1


def test_yukle_yoksa_bos(tmp_path):
    d = Defter.yukle(tmp_path / "yok.json")
    assert d.kayitlar == [] and d.tarama_turu == 0


def test_gozlemci_dongu_radar_yamali(monkeypatch):
    """dongu(): radar taklit edilir; setup deftere+portföye işlenmeli."""
    from miraz import gozlemci as gz

    @dataclass
    class _Rapor:
        satirlar: list
        @property
        def ozet(self):
            return {"Trade": 1, "Watch": 0, "Skip": 0, "Elenen": 0, "toplam": 1}

    monkeypatch.setattr(gz, "radar_tara",
                        lambda *a, **k: _Rapor([_Satir()]))
    # Pozisyon güncellemesi için veri indirme atlansın
    monkeypatch.setattr(gz.veri, "indir",
                        lambda *a, **k: (_ for _ in ()).throw(Exception("yok")))

    g = Gozlemci(semboller=["BTCUSDT"], intervallar=["1h"], taraf="long")
    sonuc = g.dongu()
    assert sonuc.eklenen == 1
    assert sonuc.defter_ozet["toplam"] == 1
    assert len(g.portfoy.pozisyonlar) == 1
    assert g.defter.tarama_turu == 1
