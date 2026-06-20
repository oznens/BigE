"""Trend çizgisi ve senaryo motoru testleri."""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.trend import trend_cizgisi_bul, kanal_bul, TrendCizgisi
from miraz.senaryo import (
    senaryo_uret, Senaryo, gelis_hacim_orani, _mtf_yapi,
)


def _df(closes, hacimler=None):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="4h", tz="UTC")
    c = np.array(closes, dtype=float)
    v = np.array(hacimler, dtype=float) if hacimler else np.ones(len(closes))
    return pd.DataFrame({
        "open": c, "high": c * 1.004, "low": c * 0.996, "close": c, "volume": v
    }, index=idx)


def _yukselen_dip_serisi():
    """Yükselen diplere sahip testere serisi (yükselen destek çizgisi)."""
    seri = []
    taban = 100.0
    for k in range(6):
        tepe = taban + 15
        seri += list(np.linspace(taban, tepe, 6))    # yukarı
        taban_yeni = taban + 5                         # her dip biraz yukarıda
        seri += list(np.linspace(tepe, taban_yeni, 6))  # aşağı (daha yüksek dip)
        taban = taban_yeni
    return seri


def test_yukselen_destek_cizgisi():
    df = _df(_yukselen_dip_serisi())
    cizgi = trend_cizgisi_bul(df, "Destek", n=2, tolerans=0.03, min_dokunus=3)
    assert cizgi is not None, "Yükselen destek çizgisi bulunmalı"
    assert cizgi.egim > 0, "Eğim pozitif (yükselen) olmalı"
    assert cizgi.yon == "Yükselen"
    assert cizgi.dokunus >= 3


def test_deger_dogru_hesaplanir():
    cizgi = TrendCizgisi(tip="Destek", egim=2.0, bar0=10, fiyat0=100.0,
                         dokunus=3, guncel_deger=0, yon="Yükselen")
    assert cizgi.deger(10) == 100.0
    assert cizgi.deger(15) == 110.0   # 100 + 2*5
    assert cizgi.deger(5) == 90.0


def test_trend_yetersiz_pivot_none():
    df = _df([100, 101, 100, 102])
    assert trend_cizgisi_bul(df, "Destek", n=2, min_dokunus=3) is None


def test_kanal_destek_dondurur():
    df = _df(_yukselen_dip_serisi())
    kanal = kanal_bul(df, n=2, tolerans=0.03, min_dokunus=3)
    assert kanal is not None
    assert kanal.destek is not None


# --- Senaryo motoru ---

def test_senaryo_yapisi():
    """Senaryo gerçek benzeri veride çalışmalı ve metin üretmeli."""
    rng = np.random.default_rng(3)
    fiyatlar = list(100 + np.cumsum(rng.normal(0.05, 1, 400)))
    df = _df(fiyatlar)
    s = senaryo_uret(df, n=3, min_guc=40)
    assert isinstance(s, Senaryo)
    assert s.fiyat > 0
    assert isinstance(s.metin, str) and len(s.metin) > 0
    assert s.yon in ("Yükseliş tepkisi", "Düşüş riski", "Nötr")


def test_senaryo_kritik_fitil_iliskisi():
    """Fitil seviyesi kritik seviyenin altında olmalı."""
    rng = np.random.default_rng(7)
    fiyatlar = list(200 + np.cumsum(rng.normal(0, 1.5, 500)))
    df = _df(fiyatlar)
    s = senaryo_uret(df, n=4, min_guc=40)
    if s.kritik_seviye is not None:
        assert s.fitil_seviye < s.kritik_seviye, "Fitil kritik seviyenin altında olmalı"


def test_gelis_hacim_orani_artar():
    """Son barlarda hacim patlarsa geliş hacim oranı >1 olmalı."""
    closes = list(100 + np.zeros(80))
    hacimler = [1.0] * 72 + [5.0] * 8     # son 8 barda hacim patlaması
    df = _df(closes, hacimler)
    oran = gelis_hacim_orani(df)
    assert oran > 1.5, "Hacimli geliş yüksek oran vermeli"

    sakin = _df(list(100 + np.zeros(80)), [1.0] * 80)
    assert gelis_hacim_orani(sakin) == 1.0


def test_mtf_yapi_yon():
    """Üst zaman dilimi düşüşte 'problemli', yükselişte 'sağlıklı' olmalı."""
    dusus = _df(list(np.linspace(200, 150, 40)))   # belirgin düşüş
    yukselis = _df(list(np.linspace(150, 200, 40)))  # belirgin yükseliş
    yatay = _df([180 + (i % 2) * 0.2 for i in range(40)])
    assert _mtf_yapi(dusus) == "problemli"
    assert _mtf_yapi(yukselis) == "sağlıklı"
    assert _mtf_yapi(yatay) == "nötr"


def test_senaryo_mtf_ve_ara_hedef():
    """df_ust verilince mtf_yapi dolmalı; ara_hedef ana hedeften küçük olmalı."""
    rng = np.random.default_rng(11)
    df = _df(list(120 + np.cumsum(rng.normal(0.05, 1, 400))))
    df_ust = _df(list(np.linspace(160, 120, 60)))   # üst zaman düşüşte
    s = senaryo_uret(df, n=3, min_guc=40, df_ust=df_ust)
    assert s.mtf_yapi in ("problemli", "sağlıklı", "nötr")
    if s.ara_hedef is not None and s.hedef_kutu is not None:
        assert s.ara_hedef <= s.hedef_kutu.ust


def test_kirilma_riski_hacimli_geliste():
    """Destek bölgesine hacimli geliş kırılma riski işaretlemeli."""
    # Destek oluşturan testere + son barlarda hacim patlaması
    seviyeler, hacimler = [], []
    for k in range(5):
        seviyeler += list(np.linspace(110, 100, 8)); hacimler += [1.0] * 8
        seviyeler += list(np.linspace(100, 110, 8)); hacimler += [1.0] * 8
    # son inişte hacmi patlat
    for i in range(1, 9):
        hacimler[-i] = 6.0
    df = _df(seviyeler, hacimler)
    s = senaryo_uret(df, n=3, min_guc=0)
    if s.destek_kutu is not None:
        assert s.kirilma_riski, "Hacimli gelişte kırılma riski işaretlenmeli"
        assert "kırılma" in s.yon.lower() or s.kirilma_riski
