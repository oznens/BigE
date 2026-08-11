"""Karar motoru (Setup Intelligence) testleri."""

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.karar import (karar_uret, _kalite, BIGE_SKOR_AGIRLIKLARI,
                         SKOR_MODELI, SKOR_KANIT_DURUMU)


@dataclass
class _Kutu:
    guc: float = 70.0


@dataclass
class _Yapi:
    durum: str


@dataclass
class _Ikili:
    tip: str
    onayli: bool


@dataclass
class _Sen:
    destek_kutu: object
    mavi_daire: float = None
    mtf_yapi: str = None
    market_yapisi: object = None
    kirilma_riski: bool = False
    trend: object = None
    ikili: object = None
    hedef_kutu: object = None


def test_kalite_esikleri():
    assert _kalite(90) == "A+"
    assert _kalite(78) == "A"
    assert _kalite(68) == "B"
    assert _kalite(55) == "C"
    assert _kalite(40) == "D"


def test_sayisal_skor_miraz_kurali_diye_etiketlenmez():
    s = _Sen(destek_kutu=_Kutu(guc=70))
    k = karar_uret(s, rr=1.0)
    assert k.skor_modeli == SKOR_MODELI == "BigE heuristic v1"
    assert k.skor_kanit_durumu == SKOR_KANIT_DURUMU == "weights-unverified"
    assert BIGE_SKOR_AGIRLIKLARI["trade_esik"] == 70.0


def test_destek_yoksa_skip():
    k = karar_uret(_Sen(destek_kutu=None))
    assert k.karar == "Skip" and k.kalite == "D" and k.guven == 0.0


def test_guclu_setup_trade():
    s = _Sen(destek_kutu=_Kutu(guc=90), mavi_daire=100.0,
             mtf_yapi="sağlıklı", market_yapisi=_Yapi("yükseliş"),
             trend=object(), hedef_kutu=_Kutu())
    k = karar_uret(s, rr=2.5)
    assert k.karar == "Trade"
    assert k.kalite in ("A", "A+")
    assert k.guven >= 75


def test_zayif_setup_skip():
    s = _Sen(destek_kutu=_Kutu(guc=50), mtf_yapi="problemli",
             market_yapisi=_Yapi("düşüş"),
             ikili=_Ikili("Çift Tepe", True))
    k = karar_uret(s, rr=0.8)
    assert k.karar == "Skip"
    assert k.guven < 50


def test_hacim_riski_en_fazla_watch():
    # Güçlü setup ama hacimli kırılma riski → Trade değil, Watch
    s = _Sen(destek_kutu=_Kutu(guc=90), mavi_daire=100.0,
             mtf_yapi="sağlıklı", market_yapisi=_Yapi("yükseliş"),
             kirilma_riski=True, hedef_kutu=_Kutu())
    k = karar_uret(s, rr=2.5)
    assert k.karar == "Watch"


def test_gerekceler_dolu():
    s = _Sen(destek_kutu=_Kutu(guc=80), mavi_daire=100.0)
    k = karar_uret(s, rr=1.5)
    assert len(k.gerekceler) >= 2
    assert "Mavi daire" in " ".join(k.gerekceler)


def test_ek_guven_cluster_pozitif():
    """Cluster ek güveni skoru yükseltir ve gerekçeye yansır."""
    # Düşük tabanlı setup (tavana çarpmasın): 50 + 3(güç) + 3(rr) = 56
    s = _Sen(destek_kutu=_Kutu(guc=60))
    temel = karar_uret(s, rr=1.5)
    artmis = karar_uret(s, rr=1.5, ek_guven=10.0,
                        ek_gerekce="Cluster: WR %80")
    assert artmis.guven == temel.guven + 10.0
    assert "Cluster" in " ".join(artmis.gerekceler)


def test_ek_guven_negatif_karar_dusurur():
    """Negatif cluster etkisi güveni düşürür."""
    # Taban 50 + 6(güç) + 10(mtf) = 66 (tavana uzak)
    s = _Sen(destek_kutu=_Kutu(guc=70), mtf_yapi="sağlıklı")
    temel = karar_uret(s, rr=1.5)
    dusuk = karar_uret(s, rr=1.5, ek_guven=-12.0)
    assert dusuk.guven < temel.guven
    assert dusuk.guven == temel.guven - 12.0
