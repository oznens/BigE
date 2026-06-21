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
    """bars: [(low, high), ...] → UTC-indexed OHLCV DataFrame."""
    low = np.array([b[0] for b in bars], dtype=float)
    high = np.array([b[1] for b in bars], dtype=float)
    mid = (low + high) / 2
    idx = pd.date_range("2025-01-01", periods=len(bars), freq="4h", tz="UTC")
    return pd.DataFrame({"open": mid, "high": high, "low": low,
                         "close": mid, "volume": np.ones(len(bars))},
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


# ---------------------------------------------------------------------------
# Güncelleme — giriş/TP/STOP simülasyonu
# ---------------------------------------------------------------------------

def test_guncelle_giris_doldu():
    """Fiyat giriş seviyesine inince durum Bekliyor → Açık."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: 2025-01-01 00:00 zaten acilis_zaman, bar1 sonrası kontrol
    # df 3 bar: bar0 yüksek (fill yok), bar1 girişe değer (low=99)
    df = _df([(102, 105), (99, 103), (100, 104)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "Açık"


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
    """Giriş dolduktan sonra stop vurulunca STOP."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: low=99 (giriş dolar), bar1: low=94 (stop=95 kırılır)
    df = _df([(99, 103), (94, 98), (100, 102)])
    pf.guncelle("BTC", "4h", df)
    p = pf.pozisyonlar[0]
    assert p.durum == "STOP"
    assert p.r_sonuc == pytest.approx(-1.0)


def test_guncelle_ayni_bar_stop_oncelik():
    """Aynı barda hem stop hem hedef → muhafazakâr STOP."""
    pf = Portfoy()
    _ekle(pf)
    # bar0: giriş dolar, bar1: hem stop hem hedef
    df = _df([(99, 103), (94, 111)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "STOP"


def test_guncelle_hicbir_degisiklik():
    """Fiyat ne girişe ne stop'a ne hedefe ulaşmaz → Bekliyor kalır."""
    pf = Portfoy()
    _ekle(pf)
    # Fiyat 102–106 arası, giriş=100 yok
    df = _df([(102, 104), (103, 106), (102, 105)])
    pf.guncelle("BTC", "4h", df)
    assert pf.pozisyonlar[0].durum == "Bekliyor"


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
