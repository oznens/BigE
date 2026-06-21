"""Kısa (Short) senaryo motoru testleri."""

import sys
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.kisa import kisa_senaryo, _short_karar, KisaSenaryo


# ---------------------------------------------------------------------------
# _short_karar — bearish skorlama mantığı (sahte nesnelerle)
# ---------------------------------------------------------------------------

@dataclass
class _Kutu:
    guc: float = 70.0
    alt: float = 110.0
    ust: float = 112.0
    merkez: float = 111.0


@dataclass
class _Yapi:
    durum: str


@dataclass
class _Div:
    tip: str


@dataclass
class _Ikili:
    tip: str
    onayli: bool


@dataclass
class _Obo:
    tip: str


def test_short_karar_direnc_yoksa_skip():
    ks = KisaSenaryo(fiyat=100.0, direnc_kutu=None)
    k = _short_karar(ks, rr=2.0)
    assert k.karar == "Skip" and k.kalite == "D"


def test_short_karar_dususte_guclu():
    """Düşüş yapısı + bearish divergence + çift tepe → Trade."""
    ks = KisaSenaryo(
        fiyat=100.0, direnc_kutu=_Kutu(guc=85),
        market_yapisi=_Yapi("düşüş"), divergence=_Div("Bearish"),
        ikili=_Ikili("Çift Tepe", True), mtf_yapi="problemli", rsi=72)
    k = _short_karar(ks, rr=2.5)
    assert k.karar == "Trade"
    assert k.guven >= 70


def test_short_karar_yukselis_aleyhine():
    """Yükseliş yapısı + bullish divergence + çift dip → Skip (short kötü)."""
    ks = KisaSenaryo(
        fiyat=100.0, direnc_kutu=_Kutu(guc=55),
        market_yapisi=_Yapi("yükseliş"), divergence=_Div("Bullish"),
        ikili=_Ikili("Çift Dip", True), mtf_yapi="sağlıklı", rsi=40)
    k = _short_karar(ks, rr=0.8)
    assert k.karar == "Skip"
    assert k.guven < 50


def test_short_karar_mtf_tersine_yorumlanir():
    """Long bakışı 'problemli' (HTF aşağı) short için OLUMLU olmalı."""
    taban = KisaSenaryo(fiyat=100.0, direnc_kutu=_Kutu(guc=60))
    n = _short_karar(taban, rr=2.0)
    problemli = KisaSenaryo(fiyat=100.0, direnc_kutu=_Kutu(guc=60),
                            mtf_yapi="problemli")
    p = _short_karar(problemli, rr=2.0)
    assert p.guven > n.guven       # HTF aşağı short güvenini artırır


def test_short_karar_rsi_asiri_alim_pozitif():
    ks = KisaSenaryo(fiyat=100.0, direnc_kutu=_Kutu(guc=60), rsi=75)
    taban = KisaSenaryo(fiyat=100.0, direnc_kutu=_Kutu(guc=60), rsi=50)
    assert _short_karar(ks, rr=2.0).guven > _short_karar(taban, rr=2.0).guven


# ---------------------------------------------------------------------------
# kisa_senaryo — uçtan uca (sentetik veri)
# ---------------------------------------------------------------------------

def _df_dususte():
    """Tepe yapıp düşen, üstte direnç bırakan sentetik seri."""
    rng = np.random.default_rng(7)
    # 0..60 yüksel (60→100), 60..120 düşüş (100→80) → üstte 100 direnci
    yukar = np.linspace(60, 100, 60)
    asagi = np.linspace(100, 82, 60)
    taban = np.concatenate([yukar, asagi])
    close = taban + rng.normal(0, 0.4, len(taban))
    high = close + 1.0
    low = close - 1.0
    idx = pd.date_range("2024-01-01", periods=len(close), freq="4h", tz="UTC")
    return pd.DataFrame({"open": close, "high": high, "low": low,
                         "close": close, "volume": np.ones(len(close))},
                        index=idx)


def test_kisa_senaryo_calisir():
    """Sentetik düşüş verisinde short senaryo üretir, çökmer."""
    ks = kisa_senaryo(_df_dususte())
    assert isinstance(ks, KisaSenaryo)
    assert ks.karar is not None
    # Direnç bulunduysa giriş üstte, hedef altta olmalı
    if ks.direnc_kutu is not None:
        assert ks.bolge_alt > ks.fiyat or ks.bolge_ust > ks.fiyat
        if ks.hedef is not None:
            assert ks.hedef < ks.bolge_alt
            assert ks.fitil_seviye > ks.bolge_ust * 0.999


def test_kisa_senaryo_metin():
    ks = kisa_senaryo(_df_dususte())
    assert "fiyat" in ks.metin.lower()
