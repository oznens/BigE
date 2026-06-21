"""Cluster hafızası testleri (setup benzerliği & geçmiş başarı)."""

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.cluster import (setup_imzasi, ClusterHafiza, Cluster,
                           benzerlik, _rr_kovasi)


# ---------------------------------------------------------------------------
# Sahte senaryo nesneleri
# ---------------------------------------------------------------------------

@dataclass
class _Karar:
    kalite: str = "A"
    guven: float = 78.0


@dataclass
class _Yapi:
    durum: str = "yükseliş"


@dataclass
class _Div:
    tip: str = "Bullish"


@dataclass
class _Sen:
    karar: object = None
    mavi_daire: float = None
    mtf_yapi: str = None
    market_yapisi: object = None
    divergence: object = None


# ---------------------------------------------------------------------------
# İmza üretimi
# ---------------------------------------------------------------------------

def test_rr_kovasi():
    assert _rr_kovasi(3.0) == "rr≥2.5"
    assert _rr_kovasi(2.0) == "rr1.5-2.5"
    assert _rr_kovasi(1.0) == "rr<1.5"
    assert _rr_kovasi(None) == "rr?"


def test_setup_imzasi_tam():
    s = _Sen(karar=_Karar("A"), mavi_daire=100.0, mtf_yapi="sağlıklı",
             market_yapisi=_Yapi("yükseliş"), divergence=_Div("Bullish"))
    imza = setup_imzasi(s, rr=3.0)
    assert imza == ("A", "mavi", "sağlıklı", "yükseliş", "Bullish", "rr≥2.5")


def test_setup_imzasi_eksik_alanlar():
    """Alanlar None ise makul varsayılanlar kullanılır."""
    s = _Sen(karar=None)
    imza = setup_imzasi(s)
    assert imza == ("D", "düz", "nötr", "yatay", "yok", "rr?")


# ---------------------------------------------------------------------------
# ClusterHafiza — kaydet/sorgu
# ---------------------------------------------------------------------------

def test_kaydet_sonuc_istatistik():
    h = ClusterHafiza()
    imza = ("A", "mavi", "sağlıklı", "yükseliş", "yok", "rr≥2.5")
    for _ in range(8):
        h.kaydet_sonuc(imza, "TP", 3.0)
    for _ in range(2):
        h.kaydet_sonuc(imza, "STOP", -1.0)
    c = h.clusterlar[imza]
    assert c.n == 10 and c.tp == 8 and c.stop == 2
    assert c.wr == 80.0
    # beklenti = (8*3 + 2*-1)/10 = 22/10 = 2.2
    assert abs(c.beklenti - 2.2) < 0.001


def test_ara_tam_imza_yeterli_ornek():
    h = ClusterHafiza()
    imza = ("A", "mavi", "sağlıklı", "yükseliş", "yok", "rr≥2.5")
    for _ in range(10):
        h.kaydet_sonuc(imza, "TP", 2.0)
    cluster, kesinlik = h.ara(imza)
    assert cluster is not None
    assert kesinlik == 0           # tam imza eşleşti
    assert cluster.wr == 100.0


def test_ara_kaba_imzaya_dusus():
    """Tam imza yetersizse daha kaba imzaya düşer (fallback)."""
    h = ClusterHafiza()
    # Aynı (kalite, mavi, HTF) ama farklı yapı/divergence → tam imza azar azar
    base = ("A", "mavi", "sağlıklı")
    for ek in [("yükseliş", "yok", "rr≥2.5"), ("yatay", "Bullish", "rr1.5-2.5"),
               ("düşüş", "yok", "rr<1.5")]:
        imza = base + ek
        for _ in range(4):           # her tam imza 4 örnek (<8 eşik)
            h.kaydet_sonuc(imza, "TP", 2.0)
    sorgu = base + ("yükseliş", "yok", "rr≥2.5")
    cluster, kesinlik = h.ara(sorgu)
    assert cluster is not None
    assert kesinlik == 1            # (kalite, mavi, HTF) seviyesinde birleşti
    assert cluster.n == 12          # 3×4 birleşti


def test_ara_hic_yok():
    h = ClusterHafiza()
    cluster, kesinlik = h.ara(("A", "mavi", "sağlıklı", "yükseliş",
                               "yok", "rr≥2.5"))
    assert cluster is None and kesinlik == -1


# ---------------------------------------------------------------------------
# benzerlik() — güven etkisi
# ---------------------------------------------------------------------------

def test_benzerlik_yuksek_wr_pozitif_etki():
    h = ClusterHafiza()
    imza = ("A", "mavi", "sağlıklı", "yükseliş", "yok", "rr≥2.5")
    for _ in range(9):
        h.kaydet_sonuc(imza, "TP", 3.0)
    for _ in range(1):
        h.kaydet_sonuc(imza, "STOP", -1.0)
    s = _Sen(karar=_Karar("A"), mavi_daire=100.0, mtf_yapi="sağlıklı",
             market_yapisi=_Yapi("yükseliş"), divergence=None)
    sonuc = benzerlik(s, h, rr=3.0)
    assert sonuc.bulundu
    assert sonuc.wr == 90.0
    assert sonuc.guven_etkisi == 10.0     # WR≥65 tam imza → +10
    assert "Cluster" in sonuc.metin


def test_benzerlik_dusuk_wr_negatif_etki():
    h = ClusterHafiza()
    imza = ("C", "düz", "problemli", "düşüş", "yok", "rr<1.5")
    for _ in range(8):
        h.kaydet_sonuc(imza, "STOP", -1.0)
    for _ in range(2):
        h.kaydet_sonuc(imza, "TP", 1.2)
    s = _Sen(karar=_Karar("C"), mavi_daire=None, mtf_yapi="problemli",
             market_yapisi=_Yapi("düşüş"), divergence=None)
    sonuc = benzerlik(s, h, rr=1.0)
    assert sonuc.bulundu
    assert sonuc.wr == 20.0
    assert sonuc.guven_etkisi == -10.0    # WR≤35 → −10


def test_benzerlik_bulunamadi():
    h = ClusterHafiza()
    s = _Sen(karar=_Karar("A"), mavi_daire=100.0)
    sonuc = benzerlik(s, h, rr=3.0)
    assert not sonuc.bulundu
    assert "yeterli geçmiş örnek yok" in sonuc.metin


def test_benzerlik_kaba_eslesmede_etki_yarim():
    """Kaba imza eşleşince güven etkisi yarıya iner."""
    h = ClusterHafiza()
    # Sadece (kalite, mavi) seviyesinde örnek toplansın
    for ek in [("nötr", "yatay", "yok", "rr≥2.5"),
               ("nötr", "yükseliş", "Bullish", "rr1.5-2.5"),
               ("sağlıklı", "yatay", "yok", "rr<1.5")]:
        imza = ("A", "mavi") + ek
        for _ in range(4):
            h.kaydet_sonuc(imza, "TP", 2.0)
    # Sorgu: (kalite, mavi, HTF) seviyesinde de yeterli yok → (kalite,mavi)'ye düşer
    s = _Sen(karar=_Karar("A"), mavi_daire=100.0, mtf_yapi="çok-farklı-htf",
             market_yapisi=_Yapi("yatay"), divergence=None)
    sonuc = benzerlik(s, h, rr=3.0)
    assert sonuc.bulundu
    assert sonuc.kesinlik >= 2             # kaba eşleşme
    assert sonuc.wr == 100.0
    assert sonuc.guven_etkisi == 5.0       # +10 yarıya indi


# ---------------------------------------------------------------------------
# Kalıcılık
# ---------------------------------------------------------------------------

def test_kaydet_yukle(tmp_path):
    h = ClusterHafiza(toplam_setup=42)
    imza = ("A", "mavi", "sağlıklı", "yükseliş", "yok", "rr≥2.5")
    for _ in range(5):
        h.kaydet_sonuc(imza, "TP", 2.0)
    dosya = tmp_path / "cluster.json"
    h.kaydet(dosya)
    h2 = ClusterHafiza.yukle(dosya)
    assert h2.toplam_setup == 42
    assert imza in h2.clusterlar
    assert h2.clusterlar[imza].tp == 5
