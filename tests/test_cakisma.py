"""Çakışma (confluence) tespit testleri."""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.cakisma import (
    cakismalari_bul, _band_icinde, _cakisma_skoru, _en_iyi_kutu, Cakisma,
)
from miraz.harmonik import HarmonikSonuc
from miraz.kutular import Kutu


def _kutu(alt, ust, renk, tip, guc=80.0):
    return Kutu(alt=alt, ust=ust, merkez=(alt + ust) / 2, renk=renk, tip=tip,
               dokunus=3, guc=guc, hacim_orani=1.5, son_idx=100,
               mesafe_yuzde=-2.0)


def _pat(yon, D, kalite=70.0):
    return HarmonikSonuc(
        isim="Gartley", yon=yon, X_idx=0, A_idx=1, B_idx=2, C_idx=3, D_idx=4,
        X=100, A=200, B=150, C=180, D=D, entry=D, sl=D * 0.99, tp1=D * 1.05,
        tp2=160, rr=2.0, oranlar={}, kalite=kalite)


def test_band_icinde():
    k = _kutu(100, 110, "Mavi", "Destek")
    assert _band_icinde(105, k)          # tam içinde
    assert _band_icinde(112, k)          # tolerans içinde (band genişliği 10, tol 5)
    assert not _band_icinde(120, k)      # uzakta


def test_cakisma_skoru_artar():
    dusuk = _cakisma_skoru(kalite=50, guc=50, renk_uyum=0.4)
    yuksek = _cakisma_skoru(kalite=90, guc=90, renk_uyum=1.0)
    assert yuksek > dusuk
    assert 0 <= dusuk <= 100 and 0 <= yuksek <= 100


def test_en_iyi_kutu_yon_uyumu():
    """Bullish pattern sadece Destek kutusuyla çakışmalı."""
    pat = _pat("Bullish", D=105)
    kutular = [
        _kutu(100, 110, "Mavi", "Destek", guc=85),
        _kutu(100, 110, "Mor", "Direnç", guc=90),   # yanlış tip
    ]
    kutu, uyum = _en_iyi_kutu(pat, kutular)
    assert kutu is not None
    assert kutu.tip == "Destek" and kutu.renk == "Mavi"
    assert uyum == 1.0   # Mavi bullish için ideal


def test_en_iyi_kutu_renk_onceligi():
    """Aynı banda iki destek kutusu varsa renk×güç en yüksek seçilir."""
    pat = _pat("Bullish", D=105)
    kutular = [
        _kutu(100, 110, "Turuncu", "Destek", guc=95),  # 0.4*95=38
        _kutu(100, 110, "Mavi", "Destek", guc=80),     # 1.0*80=80 → kazanır
    ]
    kutu, _ = _en_iyi_kutu(pat, kutular)
    assert kutu.renk == "Mavi"


def test_en_iyi_kutu_cakisma_yok():
    pat = _pat("Bullish", D=200)
    kutular = [_kutu(100, 110, "Mavi", "Destek")]
    kutu, uyum = _en_iyi_kutu(pat, kutular)
    assert kutu is None and uyum == 0.0


def _df(closes, hacimler=None):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="h", tz="UTC")
    c = np.array(closes, dtype=float)
    v = np.array(hacimler, dtype=float) if hacimler else np.ones(len(closes))
    return pd.DataFrame({
        "open": c, "high": c * 1.003, "low": c * 0.997, "close": c, "volume": v
    }, index=idx)


def test_cakismalari_bul_calisir():
    """Uçtan uca: çağrı patlamamalı, liste döndürmeli."""
    rng = np.random.default_rng(0)
    fiyatlar = list(100 + np.cumsum(rng.normal(0, 1, 400)))
    df = _df(fiyatlar)
    sonuc = cakismalari_bul(df, pivot_n=3, min_kalite=0.0)
    assert isinstance(sonuc, list)
    for c in sonuc:
        assert isinstance(c, Cakisma)
        assert 0 <= c.skor <= 100
