"""Piyasa Radar testleri (terminalMiraz tarzı tarayıcı)."""

import sys
import pandas as pd
from types import SimpleNamespace
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.radar import (RadarRapor, RadarSatiri, _kategori_belirle,
                         _gec_kalmis, _lifecycle_belirle,
                         CEKIRDEK_EVREN, GENIS_EVREN,
                         VARSAYILAN_EVREN, TERMINALMIRAZ_TF, RISK_MODLARI,
                         KANITLI_KALITE_YAPISI, _UST_TF, _ALT_TF,
                         _ltf_snapshot, HTF_POLICY, MTF_KALIBRASYON_POLICY,
                         mtf_kalibrasyon_kapisi, _pa_setup_turleri)


def test_evren_genis_ve_tekil():
    """Geniş evren büyük, tekrarsız ve hepsi USDT paritesi."""
    assert len(GENIS_EVREN) >= 80
    assert len(GENIS_EVREN) == len(set(GENIS_EVREN))   # tekrar yok
    assert all(s.endswith("USDT") for s in GENIS_EVREN)
    # Çekirdek evren geniş evrenin alt kümesi
    assert set(CEKIRDEK_EVREN).issubset(set(GENIS_EVREN))
    assert VARSAYILAN_EVREN == CEKIRDEK_EVREN


def test_ltf_esleme_gozlenen_merdivende_bir_alt_tf_ve_15m_bos():
    assert _ALT_TF == {"30m": "15m", "1h": "30m", "2h": "1h",
                       "4h": "2h", "1d": "4h"}
    assert "15m" not in _ALT_TF
    assert HTF_POLICY["ltf_mapping_origin"] == \
        "BigE-adjacent-observed-TF-interpretation"
    assert HTF_POLICY["ltf_decision_effect"] == "none-until-calibrated"


def test_ltf_snapshot_long_short_aynasidir_ve_karar_uretmez(monkeypatch):
    from miraz import yapi
    df = pd.DataFrame({"close": [1.0]})
    monkeypatch.setattr(yapi, "market_yapisi",
                        lambda _df: SimpleNamespace(durum="yükseliş"))
    assert _ltf_snapshot(df, "Long") == ("yükseliş", "trend-devam")
    assert _ltf_snapshot(df, "Short") == ("yükseliş", "zayiflama")
    monkeypatch.setattr(yapi, "market_yapisi",
                        lambda _df: SimpleNamespace(durum="düşüş"))
    assert _ltf_snapshot(df, "Short") == ("düşüş", "trend-devam")
    assert _ltf_snapshot(None, "Long") == ("not-available", "not-available")


def test_mtf_kalibrasyon_kapisi_esik_uydurmaz_ve_trade_etkisini_kilitler():
    p = MTF_KALIBRASYON_POLICY
    assert p["state"] == "locked"
    assert p["automatic_activation"] is False
    assert p["minimum_verified_samples"] is None
    assert p["minimum_sample_origin"] == "undisclosed-by-archive"
    assert p["effect_formula"] == "undisclosed-by-archive"
    assert p["trade_effect"] == "none"
    # Çok büyük örnek sayısı dahi açıklanmış eşik/formül olmadan kapıyı açmaz.
    karar = mtf_kalibrasyon_kapisi("zayiflama", 1_000_000)
    assert karar["eligible"] is False and karar["effect"] == 0
    assert karar["state"] == "locked"


def test_pa_setup_turleri_gercek_senaryo_nesnelerinden_cok_etiketlidir():
    s = SimpleNamespace(
        destek_kutu=SimpleNamespace(tip="Destek", guc=82),
        divergence=SimpleNamespace(tip="Bullish"),
        ikili=SimpleNamespace(tip="Çift Dip", onayli=True),
        obo=SimpleNamespace(tip="TOBO", onayli=False),
        fib=SimpleNamespace(aktif=True, yon="yükseliş",
                            fiyat_golden_icinde=True,
                            golden_alt=100, golden_ust=105),
        market_yapisi=SimpleNamespace(kirilim="CHoCH-yukarı"))
    turler, detay = _pa_setup_turleri(s, "Long")
    assert turler == ["OB Proxy", "Divergence", "Double Top/Bottom",
                      "OBO/TOBO", "Fibonacci Retracement", "Golden Pocket",
                      "MSB"]
    assert detay["OB Proxy"]["origin"] == \
        "BigE-zone-heuristic-not-exact-order-block"
    assert detay["Double Top/Bottom"]["onayli"] is True
    assert detay["OBO/TOBO"]["onayli"] is False
    assert detay["MSB"]["exact_signal"] == "CHoCH-yukarı"


def _satir(kat, guven, sym="BTCUSDT"):
    return RadarSatiri(symbol=sym, interval="4h", fiyat=100.0, kategori=kat,
                       kalite="A", guven=guven, yon="Yükseliş",
                       giris=99, hedef=110, rr=2.0)


def test_ozet_sayar():
    r = RadarRapor(satirlar=[_satir("Trade", 80), _satir("Watch", 60),
                             _satir("Skip", 30), _satir("Elenen", 70)])
    o = r.ozet
    assert o["Trade"] == 1 and o["Watch"] == 1
    assert o["Skip"] == 1 and o["Elenen"] == 1 and o["toplam"] == 4


def test_kanitli_kademe_sayisi_filtre_icerigi_diye_sunulmaz():
    pa = _satir("Trade", 80)
    hrm = RadarSatiri(symbol="BTCUSDT", interval="1h", fiyat=100,
                      kategori="Trade", kalite="A", guven=80, yon="yukarı",
                      giris=99, hedef=110, rr=1, pattern="Gartley")
    assert pa.kalite_kademe == 3 and hrm.kalite_kademe is None
    assert hrm.test_asamasi == 5 and hrm.asama_basi_kontrol == 4
    assert hrm.kalite_filtre_detayi == 4
    assert KANITLI_KALITE_YAPISI["Price Action"]["kalite_kademe"] == 3
    assert pa.filtre_esleme == "undisclosed-by-archive"


def test_tablo_siralama():
    # Trade en üstte, Elenen en altta; aynı kategoride güven azalan
    r = RadarRapor(satirlar=[_satir("Elenen", 90, "AAA"),
                             _satir("Trade", 70, "BBB"),
                             _satir("Trade", 85, "CCC")])
    t = r.tablo()
    i_ccc = t.index("CCC"); i_bbb = t.index("BBB"); i_aaa = t.index("AAA")
    assert i_ccc < i_bbb < i_aaa       # Trade(85) < Trade(70) < Elenen
    assert "ÖZET" in t


def test_tablo_sadece_filtre():
    r = RadarRapor(satirlar=[_satir("Trade", 80, "TRD"),
                             _satir("Skip", 30, "SKP")])
    t = r.tablo(sadece="Trade")
    assert "TRD" in t and "SKP" not in t


@dataclass
class _Karar:
    karar: str
    kalite: str = "A"
    guven: float = 75.0


@dataclass
class _Sen:
    karar: object
    mtf_yapi: str = None
    mavi_daire: float = None
    mavi_daire_isim: str = None
    pamonic: bool = False
    ikili: object = None
    kirilma_riski: bool = False
    fib: object = None


def test_htf_asagi_elenen():
    # terminalMiraz kuralı: Trade ama HTF problemli → Elenen
    s = _Sen(karar=_Karar("Trade"), mtf_yapi="problemli")
    kat, _ = _kategori_belirle(s)
    assert kat == "Elenen"


def test_htf_saglikli_trade_kalir():
    s = _Sen(karar=_Karar("Trade"), mtf_yapi="sağlıklı")
    kat, _ = _kategori_belirle(s)
    assert kat == "Trade"


def test_skip_elenen_olmaz():
    # Skip kararı HTF problemli olsa da Skip kalır (Elenen'e dönmez)
    s = _Sen(karar=_Karar("Skip"), mtf_yapi="problemli")
    kat, _ = _kategori_belirle(s)
    assert kat == "Skip"


# ---- Late filtresi (_gec_kalmis) ----

def test_gec_kalmis_long_gec():
    # Arşiv eşiği açıklamadığı için varsayılan otomatik Miraz etiketi üretmez.
    assert _gec_kalmis(106, 100, 110, "Long") is False
    # %50 yalnız açıkça seçilmiş BigE deneyi olarak kullanılabilir.
    assert _gec_kalmis(106, 100, 110, "Long", esik=.5) is True


def test_gec_kalmis_long_taze():
    # fiyat 102 → %20 katedildi → geç değil
    assert _gec_kalmis(102, 100, 110, "Long", esik=.5) is False


def test_gec_kalmis_short_gec():
    # Short: giriş 100, hedef 90; fiyat 94 → %60 düştü → geç
    assert _gec_kalmis(94, 100, 90, "Short", esik=.5) is True


def test_gec_kalmis_eksik_veri():
    assert _gec_kalmis(None, 100, 110, "Long") is False
    assert _gec_kalmis(100, 100, 100, "Long") is False   # toplam 0


def test_lifecycle_karardan_bagimsiz_neden_saklar():
    assert _lifecycle_belirle("Elenen", "Late (geç kalmış)", None) == "Late"
    assert _lifecycle_belirle(
        "Elenen", "stop bölgesi çiğnenmiş", "Deep Crab") == "Cancelled"
    assert _lifecycle_belirle(
        "Elenen", "bölge çiğnenmiş (hedef zaten görüldü)", None) == "Filtered"
    assert _lifecycle_belirle(
        "Elenen", "Entry bölgesine gelmedi", None) == "No-Entry"
    assert _lifecycle_belirle("Elenen", "HTF aşağı", None) == "Filtered"
    assert _lifecycle_belirle("Trade", "", None) == "Candidate"


def test_htf_esleme_miraz_kurali_diye_sunulmaz():
    from miraz.radar import HTF_POLICY
    assert HTF_POLICY["exact_tf_mapping"] == "undisclosed-by-archive"
    assert HTF_POLICY["current_mapping_origin"] == "BigE-interpretation"
    assert HTF_POLICY["direction_veto_origin"] == "BigE-safeguard-not-Miraz-rule"


# ---- Bayat bölge filtresi (_hedef_zaten_gorundu) ----

def test_radar_ilerleme_callback(monkeypatch):
    """radar_tara her parite/TF sonrası ilerleme(yapilan, toplam, rapor) çağırır."""
    import pandas as pd
    import numpy as np
    from miraz import radar as r
    n = 80
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    base = 100 + np.cumsum(np.random.RandomState(0).randn(n))
    df = pd.DataFrame({"open": base, "high": base + 1, "low": base - 1,
                       "close": base, "volume": 1.0}, index=idx)
    monkeypatch.setattr(r.veri, "indir", lambda *a, **k: df)

    cagrilar = []
    r.radar_tara(["BTCUSDT", "ETHUSDT"], ["1h"], taraf="long",
                 goreceli=False, ilerleme=lambda y, t, rp: cagrilar.append((y, t)))
    assert cagrilar == [(1, 2), (2, 2)]          # yapilan artar, toplam=2


def test_radar_veri_hatasi_ilerlemeyi_kesmez(monkeypatch):
    """Bir paritede veri hatası olsa da ilerleme sayacı ilerler (df=None yolu)."""
    from miraz import radar as r

    def patla(sym, tf, **k):
        raise RuntimeError("veri yok")
    monkeypatch.setattr(r.veri, "indir", patla)

    cagrilar = []
    rep = r.radar_tara(["BTCUSDT", "ETHUSDT"], ["1h"], taraf="long",
                       goreceli=False,
                       ilerleme=lambda y, t, rp: cagrilar.append(y))
    assert cagrilar == [1, 2]                     # hata olsa da sayaç ilerledi
    assert len(rep.hatalar) == 2                  # iki parite de hata listesinde


def test_hedef_zaten_gorundu():
    import pandas as pd
    from miraz.radar import _hedef_zaten_gorundu
    # Short: hedef 90; son barlarda düşük 88 görülmüş → hedef zaten görüldü
    df = pd.DataFrame({"high": [105, 104, 103], "low": [100, 88, 95]})
    assert _hedef_zaten_gorundu(df, 90, "Short") is True
    # Short: düşük hiç 90'a inmemiş → taze
    df2 = pd.DataFrame({"high": [105, 104], "low": [100, 98]})
    assert _hedef_zaten_gorundu(df2, 90, "Short") is False
    # Long: hedef 110; son yüksek 112 → zaten görüldü
    df3 = pd.DataFrame({"high": [108, 112, 109], "low": [100, 101, 102]})
    assert _hedef_zaten_gorundu(df3, 110, "Long") is True
    # eksik veri
    assert _hedef_zaten_gorundu(None, 90, "Short") is False


def test_stop_zaten_vuruldu():
    import pandas as pd
    from miraz.radar import _stop_zaten_vuruldu
    # Short: fitil 1.49 olsa da ancak 1.47 üstü kapanış invalidasyon.
    df = pd.DataFrame({"high": [1.45, 1.49, 1.46], "low": [1.42, 1.44, 1.43],
                       "close": [1.44, 1.48, 1.45]})
    assert _stop_zaten_vuruldu(df, 1.47, "Short") is True
    # Short: yüksek hiç stopa değmemiş → geçerli
    df2 = pd.DataFrame({"high": [1.45, 1.49], "low": [1.42, 1.43],
                        "close": [1.44, 1.46]})
    assert _stop_zaten_vuruldu(df2, 1.47, "Short") is False
    # Long: stop 95 altında kapanış invalidasyon.
    df3 = pd.DataFrame({"high": [105, 104], "low": [98, 93],
                        "close": [101, 94]})
    assert _stop_zaten_vuruldu(df3, 95, "Long") is True
    # Long: düşük stopun üstünde kalmış → geçerli
    df4 = pd.DataFrame({"high": [105, 104], "low": [98, 93],
                        "close": [101, 97]})
    assert _stop_zaten_vuruldu(df4, 95, "Long") is False
    # eksik veri
    assert _stop_zaten_vuruldu(None, 95, "Long") is False
    assert _stop_zaten_vuruldu(df3, None, "Long") is False


# ---- Konsept confluence skoru ----

class _KS:
    def __init__(self, yon, guc):
        self.yon = yon
        self.guc = guc


def test_konsept_etki_teyit_celiski():
    from miraz.radar import _konsept_etki, KONSEPT_TAVAN
    # 2 teyit (Long) - 1 çelişki (Short) → net pozitif ama ölçülü
    ks = {"Root": _KS("Long", 80), "Cavity": _KS("Long", 70),
          "Shade": _KS("Short", 75)}
    etki, metin = _konsept_etki(ks, "Long")
    assert etki > 0 and "teyit" in metin and "çelişki" in metin
    # ters yön için aynı sinyaller net negatif
    etki_s, _ = _konsept_etki(ks, "Short")
    assert etki_s < 0
    # çok sayıda güçlü teyit tavanı aşmaz
    cok = {k: _KS("Long", 100) for k in
           ("Reservoir", "Shear", "Strike", "Root", "Torque", "Cavity")}
    etki_cok, _ = _konsept_etki(cok, "Long")
    assert etki_cok == KONSEPT_TAVAN


def test_konsept_etki_bossa_sifir():
    from miraz.radar import _konsept_etki
    assert _konsept_etki({}, "Long") == (0.0, None)
    # sadece Nötr → etki yok
    assert _konsept_etki({"Buffer": _KS("Nötr", 90)}, "Long") == (0.0, None)


def test_konsept_skor_watch_trade_terfi():
    from miraz.radar import _konsept_skor_uygula

    class K:
        karar = "Watch"; kalite = "C"; guven = 60.0
    k = K()
    _konsept_skor_uygula(k, 15.0)            # 60+15=75 ≥70 → Trade
    assert k.karar == "Trade" and k.guven == 75.0
    # trade_engeli (hacim riski) varken terfi olmaz
    k2 = K(); k2.guven = 60.0; k2.karar = "Watch"
    _konsept_skor_uygula(k2, 15.0, trade_engeli=True)
    assert k2.karar == "Watch"               # ≥70 ama engelli → Watch kalır
    # negatif etki Trade'i Watch'a düşürür
    k3 = K(); k3.guven = 72.0; k3.karar = "Trade"
    _konsept_skor_uygula(k3, -18.0)          # 54 → Watch
    assert k3.karar == "Watch"


# ---- PaMonic notu ----

def test_pamonic_notu():
    s = _Sen(karar=_Karar("Trade"), mavi_daire=100.0,
             mavi_daire_isim="Gartley", pamonic=True)
    _, notu = _kategori_belirle(s)
    assert "PaMonic" in notu and "Gartley" in notu


def test_mavi_daire_pamonic_yoksa_normal_not():
    s = _Sen(karar=_Karar("Trade"), mavi_daire=100.0,
             mavi_daire_isim="Bat", pamonic=False)
    _, notu = _kategori_belirle(s)
    assert "PaMonic" not in notu and "Bat D" in notu


# ---- terminalMiraz TF + risk modları ----

def test_terminalmiraz_tf():
    assert TERMINALMIRAZ_TF == ["15m", "30m", "1h", "2h", "4h"]
    # her TF için bir HTF eşlemesi tanımlı olmalı
    for tf in TERMINALMIRAZ_TF:
        assert tf in _UST_TF


def test_risk_modlari():
    assert RISK_MODLARI["guvenli"] == 1.0
    assert RISK_MODLARI["dengeli"] == 2.0
    assert RISK_MODLARI["riskli"] == 3.5
