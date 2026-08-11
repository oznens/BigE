"""Canlı Gözlemci / Learning Journal (Defter) testleri."""

import sys
import json
import pandas as pd
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
    lifecycle: str = "Candidate"
    not_: str = ""
    ana_tf_yapi: str = "yükseliş"
    htf_tf: str = "4h"
    htf_yapi: str = "sağlıklı"
    ltf_tf: str = ""
    ltf_yapi: str = "not-implemented"
    harmonik_detay: dict | None = None


def test_setup_ekle_ve_dedup():
    d = Defter()
    k1 = d.setup_ekle(_Satir())
    assert k1 is not None and k1.durum == "Aday" and k1.pattern == "Gartley"
    assert k1.harmonik_gecmisi[0]["olay"] == "pattern-detected"
    assert k1.ana_tf_yapi == "yükseliş" and k1.htf_tf == "4h"
    assert k1.htf_yapi == "sağlıklı" and k1.ltf_yapi == "not-implemented"
    assert len(k1.kalite_gecmisi) == 1
    assert k1.kalite_gecmisi[0]["kalite"] == "A"
    # Aynı sembol+interval+taraf aktifken tekrar eklenmez
    k2 = d.setup_ekle(_Satir())
    assert k2 is None
    assert len(d.kayitlar) == 1


def test_setup_ekle_farkli_taraf():
    d = Defter()
    d.setup_ekle(_Satir(taraf="Long"))
    d.setup_ekle(_Satir(taraf="Short", hedef=90.0, stop=105.0))
    assert len(d.kayitlar) == 2


def test_harmonik_snapshot_kalici_ve_pattern_ozeti_ayri():
    d = Defter()
    detay = {
        "yon": "Bullish", "X": 90.0, "A": 120.0, "B": 101.46,
        "C": 113.0, "D": 96.42, "oranlar": {"AB_XA": 0.618},
        "motor_kalite": 88.0, "prz": {"merkez": 96.42,
                                         "kaynak": "completed-D"},
    }
    k = d.setup_ekle(_Satir(harmonik_detay=detay, kaynak="Harmonik"))
    assert k.harmonik_detay["oranlar"]["AB_XA"] == 0.618
    k.durum = "TP"
    o = d.harmonik_pattern_ozeti()
    assert o["harmonik_setup_sayisi"] == 1
    assert o["detayli_snapshot_sayisi"] == 1
    assert o["patternler"][0]["journal_tp"] == 1
    assert o["patternler"][0]["motor_kalite_ortalama"] == 88.0
    assert o["minimum_sample"] is None


def test_harmonik_pattern_ozeti_legacy_detayi_tahmin_etmez():
    d = Defter(kayitlar=[
        Kayit(1, "", "BTCUSDT", "1h", "Long", "A", 80,
              100, 95, 110, 1.0, pattern="Deep Crab", durum="STOP",
              kaynak="Harmonik")])
    o = d.harmonik_pattern_ozeti()
    assert o["detayli_snapshot_sayisi"] == 0
    assert o["snapshot_scope"] == "new-records-only-no-legacy-backfill"


def test_harmonik_capraz_ham_kalite_prz_ve_cd_ayri():
    detay = {"motor_kalite": 88.25,
             "prz": {"merkez": 100.0, "kaynak": "completed-D"}}
    d = Defter(kayitlar=[
        Kayit(1, "", "BTCUSDT", "1h", "Long", "A", 80,
              100, 95, 110, 1.0, pattern="Gartley", durum="TP",
              kaynak="Harmonik", harmonik_detay=detay),
        Kayit(2, "", "ETHUSDT", "4h", "Short", "B", 70,
              100, 105, 90, 1.0, pattern="Deep Crab", durum="Cancelled",
              kaynak="Harmonik",
              durum_nedeni="harmonic-pattern-changed-or-disappeared"),
    ])
    o = d.harmonik_capraz_ozeti()
    assert o["automatic_recommendation"] is False
    assert o["minimum_sample"] is None
    assert any(x["boyut"] == "motor-quality-exact" and x["deger"] == "88.2"
               for x in o["hucreler"])
    assert any(x["boyut"] == "prz-snapshot" and x["deger"] == "completed-D"
               for x in o["hucreler"])
    assert any(x["boyut"] == "cd-status" and
               x["deger"] == "cancelled-pattern-changed-or-disappeared"
               for x in o["hucreler"])


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


def test_bekleyen_aday_yeni_kaliteyle_filtrelenir():
    pf = Portfoy()
    p = pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(), pf)

    class _Rapor:
        satirlar = [_Satir(kategori="Watch", kalite="C", guven=54,
                           lifecycle="Filtered")]

    degisen = d.adaylari_yeniden_degerlendir(_Rapor(), pf)
    assert degisen == [k]
    assert k.durum == "Filtered" and k.kalite == "C" and k.guven == 54
    assert p.durum == "Filtered"
    assert k.durum_nedeni == "quality-weakened"
    assert [(x["kalite"], x["guven"]) for x in k.kalite_gecmisi] == [
        ("A", 80.0), ("C", 54)]


def test_filtered_nedenleri_htf_bayat_ve_legacy_ayrilir():
    from miraz.gozlemci import _filtered_nedeni
    assert _filtered_nedeni(_Satir(not_="HTF aşağı")) == "htf-conflict"
    assert _filtered_nedeni(
        _Satir(not_="bölge çiğnenmiş (hedef zaten görüldü)")) == "stale-zone"
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="Filtered", durum_nedeni="htf-conflict"),
        Kayit(2, "", "B", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="Filtered"),
    ]
    assert d.filtered_neden_ozeti() == {
        "htf-conflict": 1, "legacy-unknown": 1}


def test_filtered_etki_dogrulanmayan_stop_iddiasi_uretmez():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="Filtered", durum_nedeni="htf-conflict")]
    etki = d.filtered_etki_ozeti()
    assert etki["setup_sayisi"] == 1
    assert etki["engellenen_stop"] is None
    assert etki["claim_allowed"] is False


def test_filtered_etki_yalniz_acikca_dogrulanmis_sonucu_sayar():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="Filtered", durum_nedeni="htf-conflict"),
        Kayit(2, "", "B", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="TP", r_sonuc=1.0),
    ]
    assert d.karsi_olgusal_sonuc_kaydet(1, "stop") is True
    assert d.karsi_olgusal_sonuc_kaydet(2, "STOP") is False
    assert d.karsi_olgusal_sonuc_kaydet(1, "belirsiz") is False
    etki = d.filtered_etki_ozeti()
    assert etki["dogrulanmis_n"] == 1
    assert etki["engellenen_stop"] == 1
    assert etki["olasi_tp"] == 0
    assert etki["kapsama_yuzde"] == 100.0
    assert etki["claim_allowed"] is True
    assert d.kayitlar[1].r_sonuc == 1.0


def test_filtered_etki_motor_tf_kalite_ve_neden_kirilimlari():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "15m", "Long", "A", 80, 1, .9, 1.1, 1,
              durum="Filtered", kaynak="Price Action",
              durum_nedeni="htf-conflict", karsi_olgusal_sonuc="STOP"),
        Kayit(2, "", "B", "15m", "Long", "B", 65, 1, .9, 1.1, 1,
              durum="Filtered", kaynak="Price Action",
              durum_nedeni="quality-weakened", karsi_olgusal_sonuc="TP"),
        Kayit(3, "", "C", "1h", "Short", "A", 78, 1, 1.1, .9, 1,
              durum="Filtered", kaynak="Harmonik",
              durum_nedeni="htf-conflict"),
    ]
    e = d.filtered_etki_ozeti()
    motor = {x["ad"]: x for x in e["kirilimlar"]["motor"]}
    assert motor["Price Action"] == {
        "ad": "Price Action", "setup_sayisi": 2, "dogrulanmis_n": 2,
        "engellenen_stop": 1, "olasi_tp": 1, "stop_payi_yuzde": 50.0,
        "kapsama_yuzde": 100.0, "claim_allowed": True}
    assert motor["Harmonik"]["engellenen_stop"] is None
    assert motor["Harmonik"]["claim_allowed"] is False
    tf = {x["ad"]: x for x in e["kirilimlar"]["timeframe"]}
    assert tf["15m"]["dogrulanmis_n"] == 2
    kalite = {x["ad"]: x for x in e["kirilimlar"]["kalite"]}
    assert kalite["A"]["setup_sayisi"] == 2
    neden = {x["ad"]: x for x in e["kirilimlar"]["neden"]}
    assert neden["htf-conflict"]["setup_sayisi"] == 2


def test_filtered_kalite_gecisleri_gercek_snapshotlardan_ve_tekrarsiz_cikar():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "15m", "Long", "B", 60, 1, .9, 1.1, 1,
              durum="Filtered", karsi_olgusal_sonuc="STOP",
              kalite_gecmisi=[{"kalite": "A"}, {"kalite": "B"},
                               {"kalite": "A"}, {"kalite": "B"}]),
        Kayit(2, "", "B", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="Filtered", karsi_olgusal_sonuc="TP",
              kalite_gecmisi=[{"kalite": "B"}, {"kalite": "B"},
                               {"kalite": "C"}]),
        Kayit(3, "", "C", "4h", "Short", "A", 75, 1, 1.1, .9, 1,
              durum="Filtered"),
    ]
    o = d.filtered_kalite_gecis_ozeti()
    g = {x["gecis"]: x for x in o["gecisler"]}
    assert g["A→B"]["setup_sayisi"] == 1  # aynı setup'ta tekrar sayılmaz
    assert g["A→B"]["yon"] == "zayifladi"
    assert g["A→B"]["engellenen_stop"] == 1
    assert g["B→A"]["yon"] == "guclendi"
    assert g["B→C"]["olasi_tp"] == 1
    assert o["gecisli_setup_sayisi"] == 2
    assert o["filtered_setup_sayisi"] == 3
    assert o["gecmis_kapsama_yuzde"] == 66.7
    assert o["causality_claim"] == "not-made"


def test_htf_denetimi_esleme_motor_kalite_gecisi_ve_sonucu_birlestirir():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "B", 60, 1, .9, 1.1, 1,
              durum="Filtered", kaynak="Price Action",
              durum_nedeni="htf-conflict", ana_tf_yapi="yükseliş",
              htf_tf="4h", htf_yapi="problemli",
              karsi_olgusal_sonuc="STOP", karsi_olgusal_durum="STOP",
              kalite_gecmisi=[{"kalite": "A"}, {"kalite": "B"}]),
        Kayit(2, "", "B", "15m", "Short", "A", 75, 1, 1.1, .9, 1,
              durum="Filtered", kaynak="Harmonik",
              durum_nedeni="htf-conflict", ana_tf_yapi="düşüş",
              htf_tf="1h", htf_yapi="sağlıklı"),
        Kayit(3, "", "C", "1h", "Long", "C", 50, 1, .9, 1.1, 1,
              durum="Filtered", durum_nedeni="quality-weakened"),
    ]
    o = d.htf_denetim_ozeti()
    assert o["setup_sayisi"] == 2 and o["dogrulanmis_n"] == 1
    assert o["kapsama_yuzde"] == 50.0
    esleme = {x["ad"]: x for x in o["kirilimlar"]["tf_esleme"]}
    assert esleme["1h→4h"]["engellenen_stop"] == 1
    assert esleme["15m→1h"]["engellenen_stop"] is None
    assert o["kayitlar"][1]["kalite_gecisleri"] == ["A→B"]
    assert o["mapping_origin"] == "BigE-interpretation"
    assert o["ltf_status"] == "observation-only"


def test_ltf_gozlem_siniflari_sonuc_ve_snapshot_kapsamini_ayirir():
    d = Defter()
    ortak = dict(durum="Filtered", ltf_tf="30m", ltf_yapi="yükseliş")
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "A", 80, 1, .9, 1.1, 1,
              kaynak="Price Action", ltf_onay="trend-devam",
              karsi_olgusal_sonuc="TP", **ortak),
        Kayit(2, "", "B", "1h", "Long", "B", 65, 1, .9, 1.1, 1,
              kaynak="Harmonik", ltf_onay="trend-devam", **ortak),
        Kayit(3, "", "C", "1h", "Short", "C", 50, 1, 1.1, .9, 1,
              kaynak="Price Action", ltf_onay="zayiflama",
              karsi_olgusal_sonuc="STOP", **ortak),
        Kayit(4, "", "D", "1h", "Long", "B", 60, 1, .9, 1.1, 1,
              kaynak="Price Action", ltf_onay="notr", **ortak),
        Kayit(5, "", "E", "15m", "Long", "A", 75, 1, .9, 1.1, 1,
              durum="Filtered", ltf_onay="not-available"),
    ]
    o = d.ltf_gozlem_ozeti()
    assert o["filtered_setup_sayisi"] == 5
    assert o["gozlemli_setup_sayisi"] == 4
    assert o["gozlem_kapsama_yuzde"] == 80.0
    assert o["dogrulanmis_n"] == 2 and o["sonuc_kapsama_yuzde"] == 50.0
    sinif = {x["ad"]: x for x in o["siniflar"]}
    assert sinif["trend-devam"]["setup_sayisi"] == 2
    assert sinif["trend-devam"]["counterfactual_tp"] == 1
    assert sinif["zayiflama"]["counterfactual_stop"] == 1
    assert sinif["notr"]["counterfactual_tp"] is None
    assert o["metric_name"] == \
        "verified-counterfactual-distribution-not-win-rate"
    assert o["karar_etkisi"] == "none-observation-only"


def test_pa_alt_turleri_journal_ve_counterfactual_sonuclari_ayirir():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "A", 80, 1, .9, 1.1, 1,
              durum="TP", kaynak="Price Action", r_sonuc=1,
              setup_turleri=["OB Proxy", "Divergence"]),
        Kayit(2, "", "B", "1h", "Long", "B", 65, 1, .9, 1.1, 1,
              durum="STOP", kaynak="Price Action", r_sonuc=-1,
              setup_turleri=["OB Proxy"]),
        Kayit(3, "", "C", "15m", "Short", "C", 50, 1, 1.1, .9, 1,
              durum="Filtered", kaynak="Price Action",
              karsi_olgusal_sonuc="STOP",
              setup_turleri=["Divergence", "MSB"]),
        Kayit(4, "", "D", "4h", "Long", "A", 75, 1, .9, 1.1, 1,
              durum="Filtered", kaynak="Harmonik",
              setup_turleri=["Golden Pocket"]),
        Kayit(5, "", "E", "1h", "Long", "B", 60, 1, .9, 1.1, 1,
              durum="Aday", kaynak="Price Action"),
    ]
    o = d.pa_alt_tur_ozeti()
    assert o["pa_setup_sayisi"] == 4 and o["etiketli_setup_sayisi"] == 3
    assert o["etiket_kapsama_yuzde"] == 75.0
    tur = {x["tur"]: x for x in o["turler"]}
    assert tur["OB Proxy"]["journal_n"] == 2
    assert tur["OB Proxy"]["journal_wr"] == 50.0
    assert tur["Divergence"]["counterfactual_stop"] == 1
    assert tur["MSB"]["counterfactual_kapsama_yuzde"] == 100.0
    assert tur["Unclassified"]["setup_sayisi"] == 1
    assert "Golden Pocket" not in tur  # Harmonik kayıt PA audit'e karışmaz
    assert o["rows_are_not_additive"] is True


def test_pa_capraz_hucreleri_eksik_kapsam_ve_aciklanmamis_esikte_kilitlidir():
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "A", "1h", "Long", "B", 65, 1, .9, 1.1, 1,
              durum="TP", kaynak="Price Action", setup_turleri=["OB Proxy"],
              htf_yapi="sağlıklı", ltf_onay="trend-devam",
              kalite_gecmisi=[{"kalite": "A"}, {"kalite": "B"}]),
        Kayit(2, "", "B", "1h", "Long", "B", 60, 1, .9, 1.1, 1,
              durum="Filtered", kaynak="Price Action",
              setup_turleri=["OB Proxy"], htf_yapi="sağlıklı",
              ltf_onay="trend-devam"),
        Kayit(3, "", "C", "15m", "Short", "C", 50, 1, 1.1, .9, 1,
              durum="Filtered", kaynak="Price Action",
              durum_nedeni="htf-conflict", setup_turleri=["Divergence"],
              ltf_onay="zayiflama", karsi_olgusal_sonuc="STOP"),
    ]
    o = d.pa_capraz_ozeti()
    assert o["dimensions"] == ["timeframe", "side", "htf", "ltf",
                                "quality-transition"]
    assert o["minimum_sample"] is None
    assert o["automatic_recommendation"] is False
    ob_tf = next(x for x in o["hucreler"] if
                 x["tur"] == "OB Proxy" and x["boyut"] == "timeframe")
    assert ob_tf["deger"] == "1h" and ob_tf["setup_sayisi"] == 2
    assert ob_tf["claim_state"] == "locked-incomplete-counterfactual-coverage"
    assert ob_tf["recommendation_allowed"] is False
    div_htf = next(x for x in o["hucreler"] if
                   x["tur"] == "Divergence" and x["boyut"] == "htf")
    assert div_htf["deger"] == "conflict-filtered"
    assert div_htf["counterfactual_stop"] == 1
    assert div_htf["claim_state"] == "locked-minimum-threshold-undisclosed"
    gecis = next(x for x in o["hucreler"] if
                 x["tur"] == "OB Proxy" and
                 x["boyut"] == "quality-transition" and x["deger"] == "A→B")
    assert gecis["journal_tp"] == 1


def _mumlar(baslangic, satirlar):
    idx = pd.date_range(baslangic, periods=len(satirlar), freq="h", tz="UTC")
    return pd.DataFrame(satirlar, index=idx,
                        columns=["open", "high", "low", "close"])


def test_filtered_otomatik_takip_gecmisi_sonuc_saymaz_ve_tp_bulur():
    d = Defter()
    k = Kayit(1, "", "A", "1h", "Long", "C", 50, 100, 95, 110, 1,
              durum="Filtered", durum_nedeni="quality-weakened",
              karsi_olgusal_durum="Bekliyor")
    d.kayitlar = [k]
    ilk = _mumlar("2026-01-01", [(100, 111, 94, 96)])
    d.filtered_karsi_olgusal_guncelle({("A", "1h"): ilk})
    assert k.karsi_olgusal_sonuc == ""  # ilk snapshot baseline'dır

    devam = pd.concat([ilk, _mumlar("2026-01-01 01:00", [
        (101, 105, 99, 100),       # entry dolar
        (100, 111, 94, 96),        # stop fitili geçersiz; TP teması
    ])])
    d.filtered_karsi_olgusal_guncelle({("A", "1h"): devam})
    assert k.karsi_olgusal_sonuc == "TP"
    assert k.karsi_olgusal_entry_zaman
    assert k.r_sonuc == 0.0
    assert d.ozet()["toplam_r"] == 0.0


def test_filtered_otomatik_takip_stop_icin_mum_kapanisi_ister():
    d = Defter()
    k = Kayit(1, "", "A", "1h", "Short", "C", 50, 100, 105, 90, 1,
              durum="Filtered", karsi_olgusal_durum="Bekliyor")
    d.kayitlar = [k]
    ilk = _mumlar("2026-01-01", [(99, 99, 97, 98)])
    d.filtered_karsi_olgusal_guncelle({("A", "1h"): ilk})
    devam = pd.concat([ilk, _mumlar("2026-01-01 01:00", [
        (99, 101, 98, 100),        # short entry dolar
        (100, 106, 98, 104),       # yalnız fitil: STOP değil
        (104, 107, 103, 106),      # stop ötesi kapanış
    ])])
    d.filtered_karsi_olgusal_guncelle({("A", "1h"): devam})
    assert k.karsi_olgusal_sonuc == "STOP"
    assert d.filtered_etki_ozeti()["engellenen_stop"] == 1


def test_ayni_kalite_snapshot_gecmisi_sisirmez():
    pf = Portfoy()
    pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(), pf)

    class _Rapor:
        satirlar = [_Satir()]

    d.adaylari_yeniden_degerlendir(_Rapor(), pf)
    d.adaylari_yeniden_degerlendir(_Rapor(), pf)
    assert len(k.kalite_gecmisi) == 1


def test_rafa_kaldir_yalniz_acik_kararla_bekleyeni_kapatir():
    pf = Portfoy()
    p = pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(), pf)
    sonuc = d.rafa_kaldir(k.id, pf, neden="operator-review")
    assert sonuc is k
    assert k.durum == "Shelved" and p.durum == "Shelved"
    assert k.durum_nedeni == "operator-review"
    assert k.kalite_gecmisi[-1]["lifecycle"] == "Shelved"
    assert d.rafa_kaldir(k.id, pf) is None


def test_rafa_kaldir_acik_pozisyona_dokunmaz():
    pf = Portfoy()
    p = pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(), pf)
    p.durum = "Açık"
    k.durum = "Açık"
    assert d.rafa_kaldir(k.id, pf, neden="too-late") is None
    assert k.durum == "Açık" and p.durum == "Açık"


def test_entry_olmadi_bekleyeni_sifir_r_ile_kapatir():
    pf = Portfoy()
    p = pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(), pf)
    sonuc = d.entry_olmadi(k.id, pf)
    assert sonuc is k
    assert k.durum == "No-Entry" and p.durum == "No-Entry"
    assert k.r_sonuc == 0.0
    assert k.durum_nedeni == "entry-zone-not-reached"
    assert k.kalite_gecmisi[-1]["lifecycle"] == "No-Entry"


def test_acik_pozisyona_yeniden_degerlendirme_dokunmaz():
    pf = Portfoy()
    p = pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(), pf)
    p.durum = "Açık"
    k.durum = "Açık"

    class _Rapor:
        satirlar = [_Satir(kategori="Elenen", kalite="D", guven=10,
                           lifecycle="Cancelled")]

    assert d.adaylari_yeniden_degerlendir(_Rapor(), pf) == []
    assert p.durum == "Açık" and k.durum == "Açık"


def test_bekleyen_harmonik_pattern_kaybolursa_cancelled():
    pf = Portfoy()
    p = pf.ekle("BTCUSDT", "1h", 100, 95, 110, 1.0, "A", 80, "Long")
    d = Defter()
    k = d.setup_ekle(_Satir(pattern="Deep Crab", kaynak="Harmonik"), pf)

    class _Rapor:
        # Aynı sembol/TF hâlâ Trade fakat artık harmonik değil: eski PRZ taşınmaz.
        satirlar = [_Satir(pattern=None, kaynak="Price Action")]

    degisen = d.adaylari_yeniden_degerlendir(_Rapor(), pf)
    assert degisen == [k]
    assert k.durum == "Cancelled" and p.durum == "Cancelled"


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
    assert b["Harmonik"] == {"tp": 1, "stop": 1, "toplam": 2, "wr": 50.0, "r": 0.0}
    assert b["Price Action"] == {"tp": 1, "stop": 0, "toplam": 1, "wr": 100.0, "r": 1.0}
    assert b["Late"] == {"tp": 1, "stop": 0, "toplam": 1, "wr": 100.0, "r": 1.0}
    o = d.ozet()
    assert o["toplam_r"] == 2.0
    assert o["late_katki_r"] == 1.0
    assert o["toplam_r_late_haric"] == 1.0


def test_parite_hafiza_pa_ozel_ve_skor_formulu_uydurmaz():
    d = Defter()
    d.kayitlar = [
        Kayit(i, "", "UNIUSDT", "1h", "Long", "A", 80, 1, .9, 1.1, 1,
              durum="TP" if i < 11 else "STOP", r_sonuc=1 if i < 11 else -1,
              kaynak="Price Action")
        for i in range(14)
    ]
    # Harmonik sonuç Scanner/PA parite karakterine karışmaz.
    d.kayitlar.append(Kayit(99, "", "UNIUSDT", "1h", "Long", "A", 80,
                            1, .9, 1.1, 1, durum="STOP", r_sonuc=-1,
                            kaynak="Harmonik"))
    e = d.parite_hafiza()["UNIUSDT"]
    assert e["tp"] == 11 and e["stop"] == 3 and e["wr"] == 78.6
    assert e["ornek_durumu"] == "learning"
    assert e["miraz_score"] is None and e["auto_delist"] is False


def test_parite_hafiza_yirmi_kayitta_olgun():
    d = Defter()
    d.kayitlar = [
        Kayit(i, "", "XLMUSDT", "1h", "Long", "B", 60, 1, .9, 1.1, 1,
              durum="TP" if i < 8 else "STOP", r_sonuc=1 if i < 8 else -1,
              kaynak="Price Action")
        for i in range(20)
    ]
    assert d.parite_hafiza()["XLMUSDT"]["ornek_durumu"] == "mature"


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
