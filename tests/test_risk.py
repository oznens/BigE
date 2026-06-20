"""R-bazlı risk / pozisyon boyutlama testleri."""

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.risk import pozisyon_boyutu, risk_plani, kademeli_plan


def test_pozisyon_boyutu_tam_r():
    # Giriş 100, stop 95 → %5 risk. 1R=25$ → pozisyon = 25/0.05 = 500$
    poz_dolar, poz_miktar, risk_yuzde = pozisyon_boyutu(100, 95, 25)
    assert risk_yuzde == 5.0
    assert poz_dolar == 500.0
    assert poz_miktar == 5.0          # 500$ / 100 = 5 adet


def test_pozisyon_boyutu_yari_r():
    poz_dolar, _, _ = pozisyon_boyutu(100, 95, 25, carpan=0.5)
    assert poz_dolar == 250.0         # yarısı


def test_pozisyon_gecersiz():
    assert pozisyon_boyutu(100, 100, 25) == (0.0, 0.0, 0.0)
    assert pozisyon_boyutu(0, 95, 25) == (0.0, 0.0, 0.0)


@dataclass
class _SahteKutu:
    alt: float


@dataclass
class _SahteYapi:
    durum: str


@dataclass
class _SahteSenaryo:
    destek_kutu: object
    bolge_alt: float
    bolge_ust: float
    mavi_daire: float | None
    fitil_seviye: float
    kritik_seviye: float
    ara_hedef: float | None
    hedef_kutu: object
    mtf_yapi: str | None = None
    market_yapisi: object = None


def _senaryo(**kw):
    base = dict(
        destek_kutu=object(), bolge_alt=100.0, bolge_ust=110.0,
        mavi_daire=None, fitil_seviye=98.0, kritik_seviye=100.0,
        ara_hedef=None, hedef_kutu=_SahteKutu(alt=130.0))
    base.update(kw)
    return _SahteSenaryo(**base)


def test_risk_plani_trend_yonu():
    rp = risk_plani(_senaryo(), r_dolar=25)
    assert rp is not None
    assert rp.yon == "Long"
    assert rp.giris == 105.0          # bölge ortası
    assert rp.stop == 98.0
    assert rp.hedef == 130.0
    assert "½R" not in rp.pozisyon_tipi


def test_risk_plani_karsi_trend_yari_r():
    # MTF problemli → ½R
    rp1 = risk_plani(_senaryo(mtf_yapi="problemli"), r_dolar=25)
    rp2 = risk_plani(_senaryo(), r_dolar=25)
    assert "½R" in rp1.pozisyon_tipi
    assert rp1.poz_buyukluk_dolar == rp2.poz_buyukluk_dolar / 2


def test_risk_plani_market_yapisi_dusus_yari_r():
    rp = risk_plani(_senaryo(market_yapisi=_SahteYapi(durum="düşüş")), r_dolar=25)
    assert "½R" in rp.pozisyon_tipi


def test_risk_plani_mavi_daire_giris():
    rp = risk_plani(_senaryo(mavi_daire=103.0), r_dolar=25)
    assert rp.giris == 103.0          # mavi daire önceliklidir


def test_risk_plani_destek_yoksa_none():
    assert risk_plani(_senaryo(destek_kutu=None)) is None


def test_kademeli_plan_iki_kademe():
    kp = kademeli_plan(_senaryo(), r_dolar=25, paylar=(0.5, 0.5))
    assert kp is not None
    assert len(kp.kademeler) == 2
    # 1. kademe üst destek (bölge üstü=110), 2. kademe alt (bölge altı=100)
    assert kp.kademeler[0].seviye == 110.0
    assert kp.kademeler[1].seviye == 100.0
    # ortalama giriş iki seviye arasında
    assert 100.0 < kp.ort_giris < 110.0
    assert kp.stop == 98.0


def test_kademeli_toplam_risk_1r():
    # Toplam risk (stop olursa kayıp) ≈ r_dolar olmalı (tam R, trend yönünde)
    kp = kademeli_plan(_senaryo(), r_dolar=25, paylar=(0.5, 0.5))
    kayip = sum(kd.poz_dolar * (kd.seviye - kp.stop) / kd.seviye
                for kd in kp.kademeler)
    assert abs(kayip - 25.0) < 0.5


def test_kademeli_karsi_trend_yari():
    kp = kademeli_plan(_senaryo(mtf_yapi="problemli"), r_dolar=25)
    kayip = sum(kd.poz_dolar * (kd.seviye - kp.stop) / kd.seviye
                for kd in kp.kademeler)
    assert abs(kayip - 12.5) < 0.5      # ½R


def test_kademeli_uc_kademe_seviyeler():
    kp = kademeli_plan(_senaryo(), r_dolar=30, paylar=(0.4, 0.3, 0.3))
    assert len(kp.kademeler) == 3
    assert kp.kademeler[0].seviye == 110.0
    assert kp.kademeler[-1].seviye == 100.0
    assert kp.kademeler[1].seviye == 105.0   # ortada
