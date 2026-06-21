"""Piyasa Radar testleri (terminalMiraz tarzı tarayıcı)."""

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.radar import (RadarRapor, RadarSatiri, _kategori_belirle,
                         _gec_kalmis, CEKIRDEK_EVREN, GENIS_EVREN,
                         VARSAYILAN_EVREN, TERMINALMIRAZ_TF, RISK_MODLARI,
                         _UST_TF)


def test_evren_genis_ve_tekil():
    """Geniş evren büyük, tekrarsız ve hepsi USDT paritesi."""
    assert len(GENIS_EVREN) >= 80
    assert len(GENIS_EVREN) == len(set(GENIS_EVREN))   # tekrar yok
    assert all(s.endswith("USDT") for s in GENIS_EVREN)
    # Çekirdek evren geniş evrenin alt kümesi
    assert set(CEKIRDEK_EVREN).issubset(set(GENIS_EVREN))
    assert VARSAYILAN_EVREN == CEKIRDEK_EVREN


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
    # Long: giriş 100, hedef 110; fiyat 106 → %60 katedildi (≥%50) → geç
    assert _gec_kalmis(106, 100, 110, "Long") is True


def test_gec_kalmis_long_taze():
    # fiyat 102 → %20 katedildi → geç değil
    assert _gec_kalmis(102, 100, 110, "Long") is False


def test_gec_kalmis_short_gec():
    # Short: giriş 100, hedef 90; fiyat 94 → %60 düştü → geç
    assert _gec_kalmis(94, 100, 90, "Short") is True


def test_gec_kalmis_eksik_veri():
    assert _gec_kalmis(None, 100, 110, "Long") is False
    assert _gec_kalmis(100, 100, 100, "Long") is False   # toplam 0


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
    assert TERMINALMIRAZ_TF == ["15m", "30m", "1h", "2h"]
    # her TF için bir HTF eşlemesi tanımlı olmalı
    for tf in TERMINALMIRAZ_TF:
        assert tf in _UST_TF


def test_risk_modlari():
    assert RISK_MODLARI["guvenli"] == 1.0
    assert RISK_MODLARI["dengeli"] == 1.5
    assert RISK_MODLARI["riskli"] == 2.0
