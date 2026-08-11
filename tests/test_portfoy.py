"""Portföy paper-trading motoru testleri."""

import sys
import json
import tempfile
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.portfoy import Portfoy, Pozisyon, radar_sinyallerini_ekle


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _df(bars):
    """bars: (low, high[, close[, volume]])."""
    low = np.array([b[0] for b in bars], dtype=float)
    high = np.array([b[1] for b in bars], dtype=float)
    mid = np.array([b[2] if len(b) > 2 else (b[0] + b[1]) / 2
                    for b in bars], dtype=float)
    volume = np.array([b[3] if len(b) > 3 else 1.0 for b in bars],
                      dtype=float)
    idx = pd.date_range("2025-01-01", periods=len(bars), freq="4h", tz="UTC")
    return pd.DataFrame({"open": mid, "high": high, "low": low,
                         "close": mid, "volume": volume},
                        index=idx)


def _ekle(pf, sem="BTC", ivl="4h"):
    """100'de giriş, 95 stop, 110 hedef (RR=2) pozisyon ekler.

    acilis_zaman / son_kontrol_zaman test df'inden önce ayarlanır ki
    guncelle() ilk barı da inceleyebilsin.
    """
    return pf.ekle(sem, ivl, giris=100.0, stop=95.0, hedef=110.0,
                   rr=2.0, kalite="A", guven=78.0,
                   zaman="2024-12-31T20:00:00+00:00")  # test barlarından önce


# ---------------------------------------------------------------------------
# Temel ekleme testleri
# ---------------------------------------------------------------------------

def test_ekle_bekliyor():
    pf = Portfoy()
    p = _ekle(pf)
    assert p is not None
    assert p.durum == "Bekliyor"
    assert len(pf.pozisyonlar) == 1


def test_ekle_duplicate_engeli():
    """Aynı sembol+interval için Bekliyor/Açık varsa ikinci ekleme None döner."""
    pf = Portfoy()
    p1 = _ekle(pf)
    p2 = _ekle(pf)
    assert p1 is not None and p2 is None
    assert len(pf.pozisyonlar) == 1


def test_ekle_farkli_tf():
    """Farklı zaman dilimleri ayrı pozisyonlar açabilir."""
    pf = Portfoy()
    p1 = _ekle(pf, ivl="4h")
    p2 = _ekle(pf, ivl="1d")
    assert p1 is not None and p2 is not None
    assert len(pf.pozisyonlar) == 2


def test_bekleyen_emir_kalite_filtresiyle_iptal():
    pf = Portfoy()
    p = _ekle(pf)
    assert pf.bekleyen_iptal(p.id, "Filtered") is True
    assert p.durum == "Filtered" and p in pf.kapali and p not in pf.aktif
    assert pf.bekleyen_iptal(p.id, "Cancelled") is False


# ---------------------------------------------------------------------------
# Güncelleme — giriş/TP/STOP simülasyonu
# ---------------------------------------------------------------------------

def test_guncelle_giris_doldu():
    """Fiyat giriş seviyesine inince durum Bekliyor → Açık."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: 2025-01-01 00:00 zaten acilis_zaman, bar1 sonrası kontrol
    # df 3 bar: bar0 yüksek (fill yok), bar1 girişe değer (low=99)
    df = _df([(102, 105, 103, 2), (99, 103, 101, 6), (100, 104, 102, 1)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "Açık"
    assert pf.pozisyonlar[0].entry_zaman == "2025-01-01T04:00:00+00:00"
    assert pf.pozisyonlar[0].entry_hacim == 6
    assert pf.pozisyonlar[0].entry_hacim_oran == 3
    assert pf.pozisyonlar[0].entry_hacim_pencere == 1
    assert pf.pozisyonlar[0].entry_kapanis == 101
    assert pf.pozisyonlar[0].entry_bekleme_bar == 2
    assert pf.pozisyonlar[0].entry_bekleme_limiti == 24


def test_guncelle_tp():
    """Giriş dolduktan sonra hedef vurulunca TP."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: low=99 (giriş dolar), bar1: high=111 (hedef=110 geçilir)
    df = _df([(99, 103), (108, 111), (100, 102)])
    pf.guncelle("BTC", "4h", df)
    p = pf.pozisyonlar[0]
    assert p.durum == "TP"
    assert p.r_sonuc == pytest.approx(2.0)


def test_guncelle_stop():
    """Giriş dolduktan sonra stop altında kapanış gelince STOP."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: low=99 (giriş dolar), bar1: low=94 (stop=95 kırılır)
    df = _df([(99, 103), (94, 98, 94.5), (100, 102)])
    pf.guncelle("BTC", "4h", df)
    p = pf.pozisyonlar[0]
    assert p.durum == "STOP"
    assert p.r_sonuc == pytest.approx(-1.0)


def test_guncelle_stop_fitili_hedef_temasinda_tp():
    """Stop fitili invalidasyon değildir; kapanış içerideyse hedef teması TP."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: giriş dolar, bar1: hem stop hem hedef
    df = _df([(99, 103), (94, 111)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "TP"


def test_guncelle_stop_fitili_tek_basina_acik_kalir():
    pf = Portfoy()
    p = _ekle(pf)
    pf.guncelle("BTC", "4h", _df([(99, 103), (94, 100, 97)]))
    assert p.durum == "Açık"


def test_guncelle_hicbir_degisiklik():
    """Fiyat ne girişe ne stop'a ne hedefe ulaşmaz → Bekliyor kalır."""
    pf = Portfoy()
    _ekle(pf)
    # Fiyat 102–106 arası, giriş=100 yok
    df = _df([(102, 104), (103, 106), (102, 105)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "Bekliyor"


def test_guncelle_expired():
    """Bekliyor emir max_bekleme bar içinde dolmazsa → Expired (terminalMiraz)."""
    pf = Portfoy()
    _ekle(pf)
    # 6 bar boyunca giriş (100) hiç dolmaz, fiyat hep üstte
    df = _df([(102, 106)] * 6)
    deg = pf.guncelle("BTC", "4h", df, max_bekleme=5)
    assert pf.pozisyonlar[0].durum == "Expired"
    assert pf.pozisyonlar[0].r_sonuc == 0.0
    assert pf.pozisyonlar[0] in deg
    assert len(pf.aktif) == 0


def test_guncelle_expired_olmadan_dolarsa():
    """max_bekleme'den önce giriş dolarsa Expired olmaz, Açık olur."""
    pf = Portfoy()
    _ekle(pf)
    # 2. barda giriş (100) dolar
    df = _df([(102, 106), (99, 101), (102, 105)])
    pf.guncelle("BTC", "4h", df, max_bekleme=5)
    assert pf.pozisyonlar[0].durum in ("Açık", "TP", "STOP")


# ---------------------------------------------------------------------------
# Short pozisyon simülasyonu (yön-duyarlı)
# ---------------------------------------------------------------------------

def _ekle_short(pf, sem="BTC", ivl="4h"):
    """Short: 100 giriş, 105 stop (yukarıda), 90 hedef (aşağıda), RR=2."""
    return pf.ekle(sem, ivl, giris=100.0, stop=105.0, hedef=90.0,
                   rr=2.0, kalite="A", guven=78.0, yon="Short",
                   zaman="2024-12-31T20:00:00+00:00")


def test_short_giris_doldu():
    """Short: fiyat girişe ÇIKINCA (high ≥ giriş) Bekliyor → Açık."""
    pf = Portfoy()
    _ekle_short(pf)
    # bar0 high 99 (dolmaz), bar1 high 101 (giriş 100 dolar)
    df = _df([(97, 99), (99, 101), (98, 100)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "Açık"


def test_short_tp():
    """Short: giriş dolunca, fiyat hedefe DÜŞÜNCE (low ≤ hedef) TP."""
    pf = Portfoy()
    _ekle_short(pf)
    # bar0 high 101 (giriş dolar), bar1 low 89 (hedef 90 vurulur)
    df = _df([(99, 101), (89, 92), (95, 97)])
    pf.guncelle("BTC", "4h", df)
    p = pf.pozisyonlar[0]
    assert p.durum == "TP" and p.r_sonuc == pytest.approx(2.0)


def test_short_stop():
    """Short: giriş dolunca, stop üstünde kapanış gelirse STOP."""
    pf = Portfoy()
    _ekle_short(pf)
    # bar0 high 101 (giriş dolar), bar1 high 106 (stop 105 vurulur)
    df = _df([(99, 101), (103, 106, 105.5), (100, 102)])
    pf.guncelle("BTC", "4h", df)
    p = pf.pozisyonlar[0]
    assert p.durum == "STOP" and p.r_sonuc == pytest.approx(-1.0)


def test_short_stop_fitili_hedef_temasinda_tp():
    """Short stop fitili invalidasyon değildir; hedef teması TP olur."""
    pf = Portfoy()
    _ekle_short(pf)
    df = _df([(99, 101), (89, 106)])    # giriş dolar; sonra hem TP hem STOP
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "TP"


# ---------------------------------------------------------------------------
# İstatistikler
# ---------------------------------------------------------------------------

def test_istatistikler():
    pf = Portfoy(r_dolar=25.0)
    # 2 TP, 1 STOP, 1 Bekliyor (hesaba katılmaz)
    from miraz.portfoy import _simdi
    pf.pozisyonlar = [
        Pozisyon(id=0, sembol="A", interval="4h", durum="TP",
                 giris=100, stop=95, hedef=110, rr=2.0, kalite="A", guven=80,
                 r_sonuc=2.0, acilis_zaman=_simdi(), kapanis_zaman=_simdi()),
        Pozisyon(id=1, sembol="B", interval="4h", durum="STOP",
                 giris=100, stop=95, hedef=110, rr=2.0, kalite="B", guven=60,
                 r_sonuc=-1.0, acilis_zaman=_simdi(), kapanis_zaman=_simdi()),
        Pozisyon(id=2, sembol="C", interval="4h", durum="TP",
                 giris=100, stop=95, hedef=110, rr=2.0, kalite="A", guven=75,
                 r_sonuc=2.0, acilis_zaman=_simdi(), kapanis_zaman=_simdi()),
        Pozisyon(id=3, sembol="D", interval="4h", durum="Bekliyor",
                 giris=100, stop=95, hedef=110, rr=2.0, kalite="C", guven=55,
                 r_sonuc=0.0, acilis_zaman=_simdi()),
    ]
    pf.id_sayac = 4

    assert pf.toplam_r == pytest.approx(3.0)          # +2 -1 +2
    assert pf.win_rate == pytest.approx(66.7, abs=0.1) # 2/3 dolan
    assert len(pf.aktif) == 1
    assert len(pf.kapali) == 3


# ---------------------------------------------------------------------------
# Kalıcılık (kaydet / yükle)
# ---------------------------------------------------------------------------

def test_kaydet_yukle(tmp_path):
    pf = Portfoy(r_dolar=50.0)
    _ekle(pf)
    dosya = tmp_path / "pf.json"
    pf.kaydet(dosya)
    pf2 = Portfoy.yukle(dosya)
    assert pf2.r_dolar == 50.0
    assert len(pf2.pozisyonlar) == 1
    assert pf2.pozisyonlar[0].durum == "Bekliyor"


# ---------------------------------------------------------------------------
# Manuel kapatma
# ---------------------------------------------------------------------------

def test_kapat_manuel():
    pf = Portfoy()
    _ekle(pf)
    assert pf.kapat_manuel(0) is True
    assert pf.pozisyonlar[0].durum == "Manuel"
    # İkinci kapatma False döner (zaten kapalı)
    assert pf.kapat_manuel(0) is False


# ---------------------------------------------------------------------------
# radar_sinyallerini_ekle
# ---------------------------------------------------------------------------

@dataclass
class _Satir:
    symbol: str
    interval: str
    kategori: str
    kalite: str
    guven: float
    giris: float | None
    hedef: float | None
    rr: float | None
    taraf: str = "Long"


@dataclass
class _Rapor:
    satirlar: list


def test_radar_sinyallerini_ekle():
    pf = Portfoy()
    rapor = _Rapor(satirlar=[
        _Satir("BTCUSDT", "4h", "Trade", "A", 80, 95000, 105000, 2.0),
        _Satir("ETHUSDT", "4h", "Watch", "B", 60, 3000, 3500, 2.0),   # Watch → atla
        _Satir("SOLUSDT", "4h", "Trade", "A", 75, 200, 240, 2.0),
    ])
    n = radar_sinyallerini_ekle(pf, rapor)
    assert n == 2
    assert len(pf.aktif) == 2
    sembolleri = {p.sembol for p in pf.aktif}
    assert "BTCUSDT" in sembolleri and "SOLUSDT" in sembolleri


def test_radar_sinyali_short_yon_ve_stop():
    """Short Trade sinyali yön=Short ve stop>giriş olarak eklenir."""
    pf = Portfoy()
    # Short: giriş 100, hedef 90 (aşağı), rr 2 → stop = 100 - (90-100)/2 = 105
    rapor = _Rapor(satirlar=[
        _Satir("DOTUSDT", "4h", "Trade", "A", 85, 100, 90, 2.0, taraf="Short"),
    ])
    n = radar_sinyallerini_ekle(pf, rapor)
    assert n == 1
    p = pf.aktif[0]
    assert p.yon == "Short"
    assert p.stop == pytest.approx(105.0)   # stop girişin ÜSTÜNDE
    assert p.hedef < p.giris < p.stop


# ---------------------------------------------------------------------------
# tablo() / ozet_metin() — sadece string üretip çökmediğini kontrol et
# ---------------------------------------------------------------------------

def test_tablo_calisir():
    pf = Portfoy()
    _ekle(pf)
    t = pf.tablo()
    assert "PORTFÖY" in t
    assert "BTC" in t


def test_ozet_metin_calisir():
    pf = Portfoy()
    _ekle(pf)
    s = pf.ozet_metin()
    assert "açık" in s or "Portföy" in s
