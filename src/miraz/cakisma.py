"""Çakışma (confluence) tespiti — harmonik PRZ + renkli kutu örtüşmesi.

@tradermiraz'ın asıl gücü tek bir sinyalde değil, sinyallerin çakışmasında:
bir harmonik pattern'in D noktası (PRZ — potansiyel dönüş bölgesi) aynı anda
güçlü bir destek/direnç kutusuna denk geliyorsa, dönüş ihtimali çok daha yüksek.

Mantık:
  - Bullish harmonik (D'de LONG)  →  bir DESTEK kutusuyla çakışmalı (ideal: Mavi)
  - Bearish harmonik (D'de SHORT) →  bir DİRENÇ kutusuyla çakışmalı (ideal: Mor/Kırmızı)

Çakışma skoru = harmonik kalite + kutu gücü + renk uyumu bonusu.
Sadece D, kutu bandının içinde (veya yakın toleransında) ise çakışma sayılır.

Referans: notlar/metodoloji.md, notlar/kutular.md
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import harmonik as hrm
from . import kutular as kt
from . import pivotlar as pv

# Bullish için ideal destek renkleri, Bearish için ideal direnç renkleri
_IDEAL_RENK = {
    "Bullish": {"Mavi": 1.0, "Yeşil": 0.7, "Turuncu": 0.4, "Kırmızı": 0.6},
    "Bearish": {"Mor": 1.0, "Kırmızı": 0.8, "Turuncu": 0.4},
}
# D'nin kutu bandına yakınlık toleransı (band genişliğinin katı kadar taşma)
_BAND_TOLERANS = 0.5


@dataclass
class Cakisma:
    pattern: hrm.HarmonikSonuc
    kutu: kt.Kutu | None       # çakışan kutu (yoksa None)
    cakisma_var: bool
    skor: float                # 0–100 birleşik çakışma skoru
    aciklama: str


def _band_icinde(d: float, kutu: kt.Kutu) -> bool:
    """D fiyatı kutu bandının içinde mi (toleranslı)?"""
    genislik = kutu.ust - kutu.alt
    pay = genislik * _BAND_TOLERANS
    return (kutu.alt - pay) <= d <= (kutu.ust + pay)


def _en_iyi_kutu(
    pattern: hrm.HarmonikSonuc, kutular: list[kt.Kutu]
) -> tuple[kt.Kutu | None, float]:
    """Pattern'in D'sine denk gelen, yön-uyumlu en güçlü kutuyu bulur.

    Döndürür: (kutu | None, renk_uyum_katsayisi)
    """
    istenen_tip = "Destek" if pattern.yon == "Bullish" else "Direnç"
    renk_agirlik = _IDEAL_RENK[pattern.yon]

    adaylar = [
        k for k in kutular
        if k.tip == istenen_tip and _band_icinde(pattern.D, k)
    ]
    if not adaylar:
        return None, 0.0

    # renk uyumu × kutu gücü en yüksek olanı seç
    def puan(k: kt.Kutu) -> float:
        return renk_agirlik.get(k.renk, 0.3) * k.guc

    en_iyi = max(adaylar, key=puan)
    return en_iyi, renk_agirlik.get(en_iyi.renk, 0.3)


def _cakisma_skoru(kalite: float, guc: float, renk_uyum: float) -> float:
    """Harmonik kalite + kutu gücü + renk uyumu → 0–100 birleşik skor."""
    # kalite %45, kutu gücü %35, renk uyumu %20
    return round(0.45 * kalite + 0.35 * guc + 0.20 * (renk_uyum * 100), 1)


def cakismalari_bul(
    df: pd.DataFrame,
    pivot_n: int = 5,
    min_kalite: float = 40.0,
    tolerans: float = 0.015,
    min_dokunus: int = 2,
    sadece_cakisan: bool = False,
) -> list[Cakisma]:
    """Bir DataFrame üzerinde harmonik + kutu çakışmalarını bulur.

    Parametreler
    ------------
    df             : OHLCV DataFrame
    pivot_n        : swing pivot pencere boyutu
    min_kalite     : harmonik kalite eşiği
    tolerans       : kutu kümeleme toleransı
    min_dokunus    : kutu için minimum pivot dokunuşu
    sadece_cakisan : True ise sadece çakışan setup'ları döndürür

    Döndürür: skora göre azalan sıralı Cakisma listesi.
    """
    pivlar = pv.pivot_listesi(df, n=pivot_n)
    patternler = hrm.tara(df, pivlar, min_kalite=min_kalite)
    # Kutular: harmonik PRZ'ler uzakta olabileceği için mesafe limitini gevşet
    kutular = kt.kutulari_bul(
        df, n=pivot_n, tolerans=tolerans, min_dokunus=min_dokunus,
        mesafe_limit=None,
    )

    sonuclar: list[Cakisma] = []
    for p in patternler:
        kutu, renk_uyum = _en_iyi_kutu(p, kutular)
        if kutu is not None:
            skor = _cakisma_skoru(p.kalite, kutu.guc, renk_uyum)
            aciklama = (f"{p.yon} {p.isim} D={p.D:.2f} → "
                        f"{kutu.renk} {kutu.tip} [{kutu.alt:.2f}–{kutu.ust:.2f}] "
                        f"çakışıyor (kutu güç {kutu.guc:.0f})")
            sonuclar.append(Cakisma(p, kutu, True, skor, aciklama))
        elif not sadece_cakisan:
            # Çakışma yok → sadece harmonik kalitesinin yarısı kadar skor
            skor = round(p.kalite * 0.45, 1)
            sonuclar.append(Cakisma(
                p, None, False, skor,
                f"{p.yon} {p.isim} D={p.D:.2f} → kutu çakışması YOK"))

    sonuclar.sort(key=lambda c: c.skor, reverse=True)
    return sonuclar


def ozet_yazdir(symbol: str, interval: str, cakismalar: list[Cakisma]) -> None:
    """Çakışmaları terminale yazar."""
    print(f"\n{'='*78}\n{symbol} / {interval}\n{'='*78}")
    if not cakismalar:
        print("  Setup bulunamadı.")
        return
    for c in cakismalar:
        isaret = "⭐ ÇAKIŞMA" if c.cakisma_var else "  tekil  "
        p = c.pattern
        print(f"{isaret}  skor {c.skor:>5.1f}  R:R {p.rr:>4.1f}  "
              f"entry {p.entry:>10,.2f}  SL {p.sl:>10,.2f}  TP1 {p.tp1:>10,.2f}")
        print(f"            {c.aciklama}")
