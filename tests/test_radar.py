"""Piyasa Radar testleri (terminalMiraz tarzı tarayıcı)."""

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.radar import (RadarRapor, RadarSatiri, _kategori_belirle,
                         CEKIRDEK_EVREN, GENIS_EVREN, VARSAYILAN_EVREN)


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
